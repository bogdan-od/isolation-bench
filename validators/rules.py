from typing import Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
from core.logger import log
import re

@dataclass
class ValidationContext:
    """Immutable context for validation"""
    result: Dict[str, Any]
    metrics: Dict[str, float]
    baseline: Dict[str, float]
    config: Dict[str, Any]
    tool_name: str
    run_config: Dict[str, Any]

class ValidationStrategy(ABC):
    """Base class for all validation strategies"""
    
    @abstractmethod
    def validate(self, ctx: ValidationContext) -> str:
        """Returns: 'SUCCESS', 'FAILURE', 'TIMEOUT', 'PARTIAL'"""
        pass

# --- Core Strategies ---

class StandardExecutionStrategy(ValidationStrategy):
    """Normal execution - expect clean exit code 0"""
    def validate(self, ctx: ValidationContext) -> str:
        return 'SUCCESS' if ctx.result['return_code'] == 0 else 'FAILURE'

class ExpectFailStrategy(ValidationStrategy):
    """
    Command MUST fail (rc != 0) to be considered successful.
    Advanced: checks for specific error messages to distinguish failure types.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        combined = ctx.result['stdout'] + ctx.result['stderr']
        
        allowed_errors = ctx.config.get('allowed_errors', [])
        
        if rc != 0:
            # Check if failure is for the RIGHT reason
            if allowed_errors:
                for error_pattern in allowed_errors:
                    if error_pattern.lower() in combined.lower():
                        log(f"Failed with expected error: '{error_pattern}'", "DEBUG")
                        return 'SUCCESS'
                # Failed but not with expected error
                log(f"Failed with unexpected error. Expected: {allowed_errors}", "WARN")
                return 'PARTIAL'  # Failed correctly, but unclear why
            return 'SUCCESS'  # Any failure is OK
        
        # Command succeeded when it should have failed
        if ctx.result['status'] == 'TIMEOUT':
            log("Timeout on operation that should fail quickly - suspicious", "WARN")
            return 'FAILURE'
        
        log("Command succeeded when it should have been blocked", "ERROR")
        return 'FAILURE'

# --- Filesystem & Device Strategies ---

class DeviceIsolationStrategy(ValidationStrategy):
    """
    Validates access to sensitive devices.
    Checks if dangerous devices are properly blocked.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        stderr = ctx.result['stderr']
        combined = stdout + stderr
        
        blocked_devices = ctx.config.get('blocked_devices', [])
        expect_all_blocked = ctx.config.get('expect_all_blocked', True)
        
        # Parse output for device access results
        accessible_devices = []
        blocked_device_count = 0
        
        for device in blocked_devices:
            # Look for access indicators
            if f"{device}: accessible" in combined.lower() or \
               f"{device}: read" in combined.lower():
                accessible_devices.append(device)
                log(f"SECURITY BREACH: {device} is accessible!", "ERROR")
            elif "permission denied" in combined.lower() or \
                 "no such file" in combined.lower() or \
                 "operation not permitted" in combined.lower():
                blocked_device_count += 1
        
        if expect_all_blocked:
            if not accessible_devices:
                log(f"All {len(blocked_devices)} sensitive devices properly blocked", "DEBUG")
                return 'SUCCESS'
            else:
                log(f"{len(accessible_devices)} devices exposed: {accessible_devices}", "ERROR")
                return 'FAILURE'
        else:
            # Weak config - expect some access
            if accessible_devices:
                log(f"Devices accessible as expected in weak config: {accessible_devices}", "DEBUG")
                return 'FAILURE'  # This is the expected bad behavior
            else:
                return 'SUCCESS'

class CapabilityCheckStrategy(ValidationStrategy):
    """
    Validates Linux capability restrictions.
    Checks if operations requiring specific capabilities are properly blocked.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        combined = ctx.result['stdout'] + ctx.result['stderr']
        
        blocked_capabilities = ctx.config.get('blocked_capabilities', [])
        expect_failure = ctx.config.get('expect_failure', True)
        failure_keywords = ctx.config.get('failure_keywords', [
            "operation not permitted",
            "permission denied",
            "not allowed"
        ])
        
        if expect_failure:
            # Should fail due to missing capabilities
            if rc != 0:
                # Check if it's the RIGHT kind of failure
                for keyword in failure_keywords:
                    if keyword.lower() in combined.lower():
                        log(f"Capability properly restricted: '{keyword}' found", "DEBUG")
                        return 'SUCCESS'
                # Failed but unclear why
                log(f"Failed but no clear capability error. RC={rc}", "WARN")
                return 'PARTIAL'
            else:
                log(f"Operation succeeded despite missing capabilities: {blocked_capabilities}", "ERROR")
                return 'FAILURE'
        else:
            # Weak config - operation should succeed
            if rc == 0:
                log(f"Capability granted as expected in weak config", "DEBUG")
                return 'FAILURE'  # Expected bad behavior
            else:
                return 'SUCCESS'

# --- Kernel & Proc Strategies ---

class KernelVersionStrategy(ValidationStrategy):
    """
    Context-aware /proc access validation using static kernel info comparison.
    Distinguishes between virtualized and host /proc leaks.
    """
    
    def _extract_kernel_info(self, content: str) -> str:
        """
        Extracts static parts of the kernel information (version, GCC, architecture).
        Handles both verbose (standard) and minimal (gVisor) /proc/version strings.
        """
        if not content:
            return "ERROR: Empty content"
            
        # Linux version [KERNEL] ... ([GCC_INFO]) ... [ARCH]
        match_full = re.search(
            r'Linux version ([\w\.-]+).*?\((.*?)\).*?(?P<arch>\w+)$', 
            content, 
            re.DOTALL
        )

        if match_full:
            kernel_version = match_full.group(1)
            compiler_info_raw = match_full.group(2)
            architecture = match_full.group('arch')
            
            gcc_match = re.search(r'\((.*?)\).*?\)?\s*(\d+\.\d+\.\d+)', compiler_info_raw)
            gcc_version = f"{gcc_match.group(1).strip()}) {gcc_match.group(2)}" if gcc_match else compiler_info_raw.strip()

            return f"Kernel:{kernel_version}|GCC:{gcc_version}|Arch:{architecture}"
        
        # Linux version [KERNEL] #[BUILD_NUMBER] SMP [DATE]
        match_minimal = re.search(
            r'Linux version ([\w\.-]+).*?#\d+.*?\s(\w+)$',
            content
        )
        
        if match_minimal:
            kernel_version = match_minimal.group(1)
            architecture = match_minimal.group(2)
            return f"Kernel:{kernel_version}|GCC:MINIMAL|Arch:{architecture}"

        return "ERROR: Could not parse kernel info from content."

    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        tool = ctx.tool_name
        config_type = ctx.run_config.get('config', 'unknown')

        # 1. Check for access blocking
        if rc != 0:
            log("Proc read blocked - perfect isolation", "DEBUG")
            return 'SUCCESS'

        # 2. Check for empty output
        if not stdout:
            log("Empty output despite rc=0 - acceptable", "DEBUG")
            return 'SUCCESS'
        
        # 3. Extracting host kernel information
        try:
            with open("/proc/version", "r") as f:
                host_kernel_content = f.read().strip()
            
            # Use the private method to clean the information
            host_static_info = self._extract_kernel_info(host_kernel_content)
        
        except Exception as e:
            log(f"Failed to read host /proc/version: {e}", "ERROR")
            # If we cannot read the host, we cannot compare
            return 'ERROR' 
        
        if host_static_info.startswith('ERROR'):
            log(f"Failed to parse host kernel info: {host_static_info}", "ERROR")
            return 'ERROR'
        
        # 4. Extracting guest kernel information (from stdout)
        guest_static_info = self._extract_kernel_info(stdout)
        
        if guest_static_info.startswith('ERROR'):
             # This might not be /proc/version, but some other file content
             # that doesn't match the pattern. If content is not kernel-like,
             # but access was granted (rc=0), it's better to treat it as a leak.
             log(f"Guest content is not a standard /proc/version leak. Content: {stdout[:50]}...", "WARNING")
             
             # If kernel parsing fails, revert to checking for a general leak
             if config_type != 'weak':
                 log("Cannot verify kernel type, but access was granted", "ERROR")
                 return 'FAILURE'
             else:
                 return 'FAILURE' # Expected leak in weak config

        # 5. Comparison
        if host_static_info == guest_static_info:
            # Full match of static components (version, GCC, architecture)
            
            if config_type == 'weak':
                # E.g., Docker without kernel masking
                log(f"Host /proc exposed in weak config - EXPECTED for container.", "DEBUG")
                return 'FAILURE' # Still considered FAILURE as it's not full isolation
            else:
                # Serious breach for a VM or a container with strict isolation
                log(f"Host /proc exposed in {config_type} config - BREACH!", "ERROR")
                return 'FAILURE'
        
        virtualized_static_info = ctx.config.get('virtualized_kernels', {})
        
        if guest_static_info in virtualized_static_info.values():
             # E.g., gVisor always shows 4.4.0 regardless of the host
            log(f"Virtualized kernel detected ({guest_static_info}) - GOOD isolation", "DEBUG")
            return 'SUCCESS'


        # 7. If content doesn't match the host and is not a known virtualized kernel
        # This implies either a different VM kernel or a masked container kernel (kernel shim).
        log("Non-host /proc content detected - acceptable isolation", "DEBUG")
        return 'SUCCESS'

class CmdlineLeakStrategy(ValidationStrategy):
    """
    Validates /proc/1/cmdline content to check for host process command line leakage.
    Looks for known host init/system process patterns.
    """

    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout'].strip()
        config_type = ctx.run_config.get('config', 'unknown')

        # 1. Access blocked
        if rc != 0:
            log("CMDLINE read blocked - perfect isolation", "DEBUG")
            return 'SUCCESS'

        # 2. Empty output (e.g., file exists but is empty)
        if not stdout:
            log("Empty output despite rc=0 - acceptable", "DEBUG")
            return 'SUCCESS'
        
        # 3. Check for host CMDLINE patterns
        # Patters should be passed via context config, e.g., config['host_cmdline_patterns']
        host_patterns = ctx.config.get('host_cmdline_patterns')
        
        if not host_patterns:
            log("Host CMDLINE patterns missing in config. Cannot validate content.", "ERROR")
            return 'ERROR' 

        is_host_leak = any(re.search(pattern, stdout, re.IGNORECASE) 
                           for pattern in host_patterns)
        
        # 4. Final check
        if is_host_leak:
            if config_type == 'weak':
                # Typical for Docker/LXC (they often see host systemd/init)
                log(f"Host CMDLINE exposed in weak config - EXPECTED.", "DEBUG")
                return 'FAILURE'
            else:
                # Breach for strict isolation
                log(f"Host CMDLINE exposed in {config_type} config - BREACH!", "ERROR")
                return 'FAILURE'
        else:
            # Content does not match host patterns (e.g., it sees its own /bin/sh or /pause)
            log("Non-host CMDLINE content detected - acceptable isolation", "DEBUG")
            return 'SUCCESS'

class SysctlIsolationStrategy(ValidationStrategy):
    """
    Validates sysctl parameter isolation (UTS namespace).
    Checks if kernel parameters are isolated from host.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        
        if rc != 0:
            log("Sysctl read failed - possibly good isolation", "DEBUG")
            return 'SUCCESS'
        
        check_host_leak = ctx.config.get('check_host_leak', True)
        host_hostname_pattern = ctx.config.get('host_hostname_pattern', '')
        
        if check_host_leak and host_hostname_pattern:
            if host_hostname_pattern in stdout:
                log(f"Host hostname leaked: '{host_hostname_pattern}'", "ERROR")
                return 'FAILURE'
            else:
                log("Hostname properly isolated from host", "DEBUG")
                return 'SUCCESS'
        
        # Just check that sysctl is accessible
        if "kernel.hostname" in stdout or "kernel.domainname" in stdout:
            return 'SUCCESS'
        
        return 'PARTIAL'

# --- Network Strategies ---

class NetworkSniffingStrategy(ValidationStrategy):
    """
    Context-aware network sniffing validation.
    Analyzes packet captures to detect host network leaks.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        stderr = ctx.result['stderr']
        combined = stdout + stderr
        
        # Check for permission denied
        if rc != 0:
            if 'permission denied' in combined.lower() or \
               'operation not permitted' in combined.lower():
                log("tcpdump blocked by permissions - perfect isolation", "DEBUG")
                return 'SUCCESS'
            # Other errors also acceptable
            return 'SUCCESS'
        
        # Parse packet count
        packets_captured = 0
        match = re.search(r'(\d+) packets captured', combined)
        if match:
            packets_captured = int(match.group(1))
        
        # Check for host traffic indicators
        host_traffic_patterns = ctx.config.get('host_traffic_patterns', [
            r'STP 802\.1d',
            r'enp\d+s\d+',
            r'ens\d+',
        ])
        
        has_host_traffic = any(re.search(pattern, combined) 
                              for pattern in host_traffic_patterns)
        
        config_type = ctx.run_config.get('config', 'unknown')
        
        if packets_captured == 0:
            log("No packets captured - perfect isolation", "DEBUG")
            return 'SUCCESS'
        
        if has_host_traffic:
            if config_type == 'weak':
                log(f"Host traffic visible in weak config - EXPECTED", "WARN")
                return 'FAILURE'
            else:
                log(f"Host traffic visible in {config_type} - BREACH!", "ERROR")
                return 'FAILURE'
        
        # Captured internal traffic only
        log(f"Captured {packets_captured} internal packets - acceptable", "DEBUG")
        return 'SUCCESS'

class NetworkBehaviorStrategy(ValidationStrategy):
    """
    Validates general network behavior (connectivity, isolation).
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        combined = ctx.result['stdout'] + ctx.result['stderr']
        
        expect_network_access = ctx.config.get('expect_network_access', False)
        detect_patterns = ctx.config.get('detect_patterns', [])
        
        # Look for connection patterns
        has_connection = "connected" in combined.lower() or \
                        "successful" in combined.lower()
        
        has_isolation = any(pattern.lower() in combined.lower() 
                           for pattern in detect_patterns)
        
        if expect_network_access:
            # Should have network access
            if has_connection:
                return 'SUCCESS'
            else:
                log("Network access expected but blocked", "ERROR")
                return 'FAILURE'
        else:
            # Should be isolated
            if has_isolation or rc != 0:
                log("Network properly isolated", "DEBUG")
                return 'SUCCESS'
            elif has_connection:
                log("Network accessible when it should be isolated", "ERROR")
                return 'FAILURE'
            else:
                return 'PARTIAL'

# --- IPC & Namespace Strategies ---

class IPCIsolationStrategy(ValidationStrategy):
    """
    Validates IPC namespace isolation (shared memory, message queues).
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        
        if rc != 0:
            log("IPC query failed - possibly isolated", "DEBUG")
            return 'SUCCESS'
        
        expect_empty = ctx.config.get('expect_empty', True)
        host_leak_patterns = ctx.config.get('host_leak_patterns', [r'0x[0-9a-f]{8}'])
        
        # Check if output shows IPC objects
        has_ipc_objects = False
        for pattern in host_leak_patterns:
            if re.search(pattern, stdout):
                has_ipc_objects = True
                break
        
        # Also check for actual IPC listings
        lines = [l.strip() for l in stdout.split('\n') if l.strip()]
        # Skip header lines
        data_lines = [l for l in lines if not l.startswith('--') and 
                      'key' not in l.lower() and 'shmid' not in l.lower()]
        
        if expect_empty:
            if not has_ipc_objects and len(data_lines) == 0:
                log("IPC namespace properly isolated (empty)", "DEBUG")
                return 'SUCCESS'
            else:
                log(f"IPC objects visible ({len(data_lines)} entries) - potential leak", "ERROR")
                return 'FAILURE'
        else:
            # Weak config - expect to see host IPC
            if has_ipc_objects or len(data_lines) > 0:
                log("Host IPC visible as expected in weak config", "DEBUG")
                return 'FAILURE'  # Expected bad behavior
            else:
                return 'SUCCESS'

class UTSIsolationStrategy(ValidationStrategy):
    """
    Validates UTS namespace isolation (hostname, domainname).
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        
        if rc != 0:
            return 'FAILURE'
        
        host_hostname = ctx.config.get('host_hostname', '')
        expect_different = ctx.config.get('expect_different', True)
        
        if expect_different:
            # Should NOT see host hostname
            if host_hostname and host_hostname in stdout:
                log(f"Host hostname leaked: '{host_hostname}'", "ERROR")
                return 'FAILURE'
            else:
                log("Hostname properly isolated from host", "DEBUG")
                return 'SUCCESS'
        else:
            # Weak config - should see host hostname
            if host_hostname and host_hostname in stdout:
                log("Host hostname visible as expected in weak config", "DEBUG")
                return 'FAILURE'  # Expected bad behavior
            else:
                return 'SUCCESS'

class SocketIsolationStrategy(ValidationStrategy):
    """
    Validates Unix socket isolation (Docker socket escape prevention).
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        stderr = ctx.result['stderr']
        combined = stdout + stderr
        
        dangerous_sockets = ctx.config.get('dangerous_sockets', [])
        expect_no_access = ctx.config.get('expect_no_access', True)
        
        # Check if socket exists and is accessible
        socket_accessible = 'SOCKET_EXISTS' in combined
        socket_missing = 'NO_SOCKET' in combined
        
        if expect_no_access:
            # Should NOT have access
            if socket_missing or rc != 0:
                log("Dangerous sockets properly isolated", "DEBUG")
                return 'SUCCESS'
            elif socket_accessible:
                log("CRITICAL: Docker socket accessible - ESCAPE VECTOR!", "ERROR")
                return 'FAILURE'
        else:
            # Weak config - socket should be accessible
            if socket_accessible:
                log("Socket accessible as expected in weak config", "DEBUG")
                return 'FAILURE'  # Expected bad behavior
            else:
                return 'SUCCESS'

# --- Resource & Performance Strategies ---

class ContainmentPidsStrategy(ValidationStrategy):
    """Resource containment - PIDs must not explode"""
    def validate(self, ctx: ValidationContext) -> str:
        max_growth = ctx.config.get('max_pid_growth', 200)
        timeout_threshold = ctx.config.get('timeout_pid_threshold', 200)
        strict_mode = ctx.config.get('strict_mode', False)
        
        pid_growth = ctx.metrics['pids_max'] - ctx.baseline['pids_base']
        
        log(f"PID growth: +{pid_growth} (baseline: {ctx.baseline['pids_base']} → max: {ctx.metrics['pids_max']})", "DEBUG")
        
        if ctx.result['status'] == 'TIMEOUT':
            # Timeout can be SUCCESS if PIDs are contained
            if pid_growth < timeout_threshold:
                log(f"Timeout but contained (growth: {pid_growth} < {timeout_threshold})", "DEBUG")
                return 'SUCCESS' if not strict_mode else 'PARTIAL'
            else:
                log(f"Timeout AND exploded (growth: {pid_growth} >= {timeout_threshold})", "DEBUG")
                return 'FAILURE'
        else:
            # Normal exit - check growth
            if pid_growth < max_growth:
                return 'SUCCESS'
            else:
                log(f"PID explosion detected: {pid_growth} new processes", "ERROR")
                return 'FAILURE'

class ExpectOOMStrategy(ValidationStrategy):
    """Process must be killed by OOM killer"""
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stderr = ctx.result['stderr']
        
        oom_codes = ctx.config.get('oom_codes', [137])
        oom_keywords = ctx.config.get('oom_keywords', ['Killed', 'OOM'])
        allow_any_nonzero = ctx.config.get('allow_any_nonzero', True)
        
        # Check exit code
        if rc in oom_codes:
            log(f"OOM detected via exit code: {rc}", "DEBUG")
            return 'SUCCESS'
        
        # Check stderr for keywords
        if any(kw in stderr for kw in oom_keywords):
            log(f"OOM detected via stderr keywords", "DEBUG")
            return 'SUCCESS'
        
        # Fallback: any crash is acceptable
        if allow_any_nonzero and rc != 0:
            log(f"Process crashed (rc={rc}), acceptable for OOM test", "DEBUG")
            return 'SUCCESS'
        
        log("Memory hog completed successfully - limits not enforced", "ERROR")
        return 'FAILURE'

class CPUSaturationStrategy(ValidationStrategy):
    """
    Validates CPU usage patterns and throttling.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        duration = ctx.result['duration_s']
        
        min_cpu_usage = ctx.config.get('min_cpu_usage', 50.0)
        max_duration_s = ctx.config.get('max_duration_s', 999)
        
        avg_cpu = ctx.metrics['cpu_avg']
        max_cpu = ctx.metrics['cpu_max']
        
        log(f"CPU usage: avg={avg_cpu}%, max={max_cpu}%, duration={duration}s", "DEBUG")
        
        # Check completion
        if rc != 0:
            log(f"CPU burn failed with rc={rc}", "ERROR")
            return 'FAILURE'
        
        # Check duration
        if duration > max_duration_s:
            log(f"CPU burn took too long: {duration}s > {max_duration_s}s", "WARN")
            return 'PARTIAL'
        
        # Check CPU usage
        if avg_cpu < min_cpu_usage:
            log(f"CPU usage too low: {avg_cpu}% < {min_cpu_usage}% (heavy throttling)", "WARN")
            return 'PARTIAL'
        
        log("CPU saturation test passed", "DEBUG")
        return 'SUCCESS'

class DiskExhaustionStrategy(ValidationStrategy):
    """
    Validates disk quota enforcement.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        combined = ctx.result['stdout'] + ctx.result['stderr']
        
        expect_failure = ctx.config.get('expect_failure', False)
        failure_keywords = ctx.config.get('failure_keywords', [])
        max_written_mb = ctx.config.get('max_written_mb', 9999)
        
        # Check for quota enforcement
        hit_quota = any(kw.lower() in combined.lower() for kw in failure_keywords)
        
        # Parse written amount if available
        written_match = re.search(r'(\d+)\s*MB written', combined)
        written_mb = int(written_match.group(1)) if written_match else 0
        
        if expect_failure:
            # Should hit disk quota
            if hit_quota or rc != 0:
                log("Disk quota properly enforced", "DEBUG")
                return 'SUCCESS'
            elif written_mb > max_written_mb:
                log(f"Wrote {written_mb}MB, exceeding limit of {max_written_mb}MB", "ERROR")
                return 'FAILURE'
            else:
                log("Disk write succeeded when it should have been limited", "WARN")
                return 'PARTIAL'
        else:
            # Weak config - should succeed
            if rc == 0 and not hit_quota:
                log("Disk write succeeded as expected in weak config", "DEBUG")
                return 'FAILURE'  # Expected bad behavior
            else:
                return 'SUCCESS'

class IOPerformanceStrategy(ValidationStrategy):
    """
    Validates I/O performance baseline.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        stdout = ctx.result['stdout']
        
        min_throughput_mbs = ctx.config.get('min_throughput_mbs', 0)
        expect_completion = ctx.config.get('expect_completion', True)
        
        if expect_completion and rc != 0:
            log(f"I/O test failed with rc={rc}", "ERROR")
            return 'FAILURE'
        
        # Parse throughput
        throughput_match = re.search(r'(\d+\.?\d*)\s*MB/s', stdout)
        if throughput_match:
            throughput = float(throughput_match.group(1))
            log(f"I/O throughput: {throughput} MB/s", "DEBUG")
            
            if throughput < min_throughput_mbs:
                log(f"Throughput too low: {throughput} < {min_throughput_mbs} MB/s", "WARN")
                return 'PARTIAL'
        
        return 'SUCCESS'

class ResourceLimitStrategy(ValidationStrategy):
    """
    Validates ulimit and resource limit enforcement.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        combined = ctx.result['stdout'] + ctx.result['stderr']
        
        expect_hit_limit = ctx.config.get('expect_hit_limit', True)
        limit_keywords = ctx.config.get('limit_keywords', [])
        
        hit_limit = any(kw.lower() in combined.lower() for kw in limit_keywords)
        
        if expect_hit_limit:
            # Should hit resource limit
            if hit_limit or rc != 0:
                log("Resource limit properly enforced", "DEBUG")
                return 'SUCCESS'
            else:
                log("Resource limit not enforced - potential leak", "ERROR")
                return 'FAILURE'
        else:
            # Should not hit limit
            if rc == 0 and not hit_limit:
                return 'SUCCESS'
            else:
                return 'FAILURE'

class StabilityCheckStrategy(ValidationStrategy):
    """
    Validates system stability under stress.
    """
    def validate(self, ctx: ValidationContext) -> str:
        rc = ctx.result['return_code']
        duration = ctx.result['duration_s']
        stderr = ctx.result['stderr']
        
        expect_completion = ctx.config.get('expect_completion', True)
        max_duration_s = ctx.config.get('max_duration_s', 999)
        check_for_crashes = ctx.config.get('check_for_crashes', True)
        
        # Check for crashes
        crash_keywords = ['segmentation fault', 'core dumped', 'panic', 'oops']
        has_crash = any(kw in stderr.lower() for kw in crash_keywords)
        
        if check_for_crashes and has_crash:
            log("System crash detected during stress test", "ERROR")
            return 'FAILURE'
        
        # Check completion
        if expect_completion:
            if rc != 0:
                log(f"Stress test failed with rc={rc}", "ERROR")
                return 'FAILURE'
            
            if duration > max_duration_s:
                log(f"Stress test took too long: {duration}s > {max_duration_s}s", "WARN")
                return 'PARTIAL'
        
        log("Stability test passed", "DEBUG")
        return 'SUCCESS'

# --- Composite Strategy ---

class CompositeStrategy(ValidationStrategy):
    """Run multiple checks and aggregate results"""
    def validate(self, ctx: ValidationContext) -> str:
        checks = ctx.config.get('checks', [])
        if not checks:
            log("Composite validation with no checks - defaulting to FAILURE", "WARN")
            return 'FAILURE'
        
        results = []
        for check in checks:
            check_type = check.get('type')
            check_params = {k: v for k, v in check.items() if k != 'type'}
            
            strategy = STRATEGY_REGISTRY.get(check_type)
            if not strategy:
                log(f"Unknown check type: {check_type}", "ERROR")
                results.append('FAILURE')
                continue
            
            sub_ctx = ValidationContext(
                result=ctx.result,
                metrics=ctx.metrics,
                baseline=ctx.baseline,
                config=check_params,
                tool_name=ctx.tool_name,
                run_config=ctx.run_config
            )
            
            result = strategy.validate(sub_ctx)
            log(f"Composite check '{check_type}': {result}", "DEBUG")
            results.append(result)
        
        # Aggregate: ALL must succeed
        if all(r == 'SUCCESS' for r in results):
            return 'SUCCESS'
        elif any(r == 'FAILURE' for r in results):
            return 'FAILURE'
        else:
            return 'PARTIAL'

# --- Registry ---

STRATEGY_REGISTRY = {
    'standard': StandardExecutionStrategy(),
    'expect_fail': ExpectFailStrategy(),
    'kernel_version': KernelVersionStrategy(),
    'cmdline_leak': CmdlineLeakStrategy(),
    'network_sniffing': NetworkSniffingStrategy(),
    'network_behavior': NetworkBehaviorStrategy(),
    'containment_pids': ContainmentPidsStrategy(),
    'expect_oom': ExpectOOMStrategy(),
    'cpu_saturation': CPUSaturationStrategy(),
    'disk_exhaustion': DiskExhaustionStrategy(),
    'io_performance': IOPerformanceStrategy(),
    'resource_limit': ResourceLimitStrategy(),
    'stability_check': StabilityCheckStrategy(),
    'device_isolation': DeviceIsolationStrategy(),
    'capability_check': CapabilityCheckStrategy(),
    'sysctl_isolation': SysctlIsolationStrategy(),
    'ipc_isolation': IPCIsolationStrategy(),
    'uts_isolation': UTSIsolationStrategy(),
    'socket_isolation': SocketIsolationStrategy(),
    'composite': CompositeStrategy(),
}

# --- Main Validator ---

class TestValidator:
    """Factory for validation strategies"""
    
    @staticmethod
    def validate(validation_config: Dict[str, Any], result: Dict[str, Any], 
                 metrics: Dict[str, float], baseline: Dict[str, float],
                 tool_name: str = 'unknown', run_config: Dict[str, Any] = None) -> str:
        """
        Main entry point for validation.
        
        Args:
            validation_config: Dict with 'strategy' and optional 'params'
            result: Execution result from runner
            metrics: System metrics from monitor
            baseline: Baseline metrics
            tool_name: Which isolation tool (docker, gvisor, kata, etc)
            run_config: Full run configuration including config_type
            
        Returns:
            'SUCCESS', 'FAILURE', 'TIMEOUT', 'PARTIAL'
        """
        # Support both old format (string) and new format (dict)
        if isinstance(validation_config, str):
            strategy_name = validation_config
            params = {}
        else:
            strategy_name = validation_config.get('strategy', 'standard')
            params = validation_config.get('params', {})
        
        strategy = STRATEGY_REGISTRY.get(strategy_name)
        if not strategy:
            log(f"Unknown validation strategy: {strategy_name}, defaulting to 'standard'", "WARN")
            strategy = STRATEGY_REGISTRY['standard']
        
        ctx = ValidationContext(
            result=result,
            metrics=metrics,
            baseline=baseline,
            config=params,
            tool_name=tool_name,
            run_config=run_config or {}
        )
        
        final_status = strategy.validate(ctx)
        log(f"Validation strategy '{strategy_name}' → {final_status}", "DEBUG")
        
        return final_status
