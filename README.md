# IsolationBench

**A comprehensive security and performance benchmarking framework for container and virtualization isolation technologies**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Supported Technologies](#supported-technologies)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Extending the Framework](#extending-the-framework)
- [Test Categories](#test-categories)
- [Understanding Results](#understanding-results)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**IsolationBench** is an advanced, extensible benchmarking framework designed to rigorously evaluate the security isolation, resource containment, and performance characteristics of container runtimes, sandboxes, and virtualization technologies.

Built with a modular architecture, IsolationBench enables security researchers, system administrators, and DevOps engineers to:

- **Assess security boundaries** through adversarial testing
- **Measure performance overhead** of isolation mechanisms
- **Compare technologies** side-by-side with comprehensive metrics
- **Validate configurations** against real-world attack scenarios

### Why IsolationBench?

Modern cloud infrastructure relies on isolation technologies, but their effectiveness varies significantly. IsolationBench provides:

- ✅ **Standardized evaluation** across diverse isolation technologies
- ✅ **Real attack scenarios** including fork bombs, memory exhaustion, kernel exploits
- ✅ **Detailed metrics** covering CPU, memory, I/O, network, and process behavior
- ✅ **Extensible design** for adding custom tests and runners
- ✅ **Automated reporting** with actionable insights

---

## ✨ Features

### Security Testing
- **Filesystem Isolation**: Device access, mount escapes, read-only validation
- **Kernel Isolation**: /proc leaks, kernel module loading, syscall filtering
- **Network Isolation**: Packet sniffing, port scanning, raw socket creation
- **IPC Isolation**: Shared memory, Unix sockets, namespace boundaries
- **Privilege Escalation**: Capability checks, cgroup escapes, chroot breakouts

### Resource Testing
- **PID Exhaustion**: Fork bombs with containment validation
- **Memory Limits**: OOM killer effectiveness
- **CPU Throttling**: Saturation tests and quota enforcement
- **Disk Quotas**: Storage exhaustion protection
- **File Descriptor Limits**: ulimit enforcement

### Performance Benchmarking
- **CPU Performance**: Computational workload baseline
- **I/O Throughput**: Disk read/write performance
- **Network Latency**: Packet capture overhead
- **Context Switching**: Scheduler behavior under load

### System Monitoring
- Real-time metrics collection during test execution
- Baseline vs. execution comparison
- Comprehensive resource tracking:
  - CPU usage (avg, max, min)
  - Memory consumption and growth
  - Process and thread counts
  - File descriptor utilization
  - I/O operations (read/write MB)
  - Network traffic (sent/received MB)
  - Context switches (voluntary/involuntary)

### Reporting
- **Summary Reports**: High-level overview with success rates
- **Detailed Reports**: Complete metrics for all tests
- **Performance Reports**: Overhead analysis and comparison
- **Security Reports**: Effectiveness matrix by category
- **Chart Data**: JSON export for visualization tools

---

## 🏗️ Architecture

IsolationBench follows a clean, modular architecture:

```
IsolationBench/
│
├── core/
│   ├── logger.py          # Colored logging system
│   ├── monitor.py         # Real-time system metrics collector
│   ├── orchestrator.py    # Test execution coordinator
│   └── reporter.py        # Multi-format report generator
│
├── runners/
│   ├── base.py            # Abstract runner interface
│   ├── docker_runner.py   # Docker/gVisor/Kata support
│   ├── qemu_runner.py     # QEMU VM runner
│   └── nsjail_runner.py   # NsJail sandbox runner
│
├── validators/
│   └── rules.py           # Validation strategies (20+ built-in)
│
├── payloads/
│   └── *.c                # Attack simulation binaries
│
├── config.yaml            # Test suite configuration
├── Dockerfile             # Test environment container
└── main.py                # Entry point
```

### Design Principles

1. **Extensibility**: Add new tests, technologies, or validation logic without core changes
2. **Separation of Concerns**: Runners handle execution, validators interpret results
3. **Context-Aware Validation**: Same payload evaluated differently based on configuration
4. **Comprehensive Metrics**: System state captured before, during, and after tests

---

## 🔧 Supported Technologies

| Technology | Type | Security Focus | Performance Focus |
|------------|------|----------------|-------------------|
| **Docker** | Container | Namespace/cgroup isolation | Native performance |
| **gVisor (runsc)** | Sandboxed Container | Application kernel | CPU/syscall overhead |
| **Kata Containers** | VM-based Container | Hardware virtualization | Boot time, memory |
| **QEMU** | Full Virtualization | Complete isolation | Emulation overhead |
| **NsJail** | Lightweight Sandbox | Namespace-based | Minimal overhead |

---

## 📦 Prerequisites

### System Requirements
- **OS**: Linux (kernel 4.14+)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 20GB free space
- **Root Access**: Required for most tests

### Software Dependencies
```bash
# Core tools
Python 3.8+
Docker 20.10+
QEMU 4.2+

# Optional (for specific runners)
gVisor (runsc)
Kata Containers
NsJail

# Python packages
pyyaml
pandas
psutil
paramiko
```

---

## 🚀 Installation

### 1. Clone Repository
```bash
git clone https://github.com/bogdan-od/IsolationBench.git
cd IsolationBench
```

### 2. Build Test Environment
```bash
# Download sysbench source
wget https://github.com/akopytov/sysbench/archive/refs/tags/1.0.20.tar.gz

# Build Docker image with test payloads
docker build -t isolation_env:latest .
```

### 3. Set Up Python Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Compile Test Payloads
```bash
cd payloads
./compile_all.sh  # Compiles all C programs
cd ..
```

### 5. Configure Test Suite
Edit `config.yaml` to match your environment:
```yaml
tools:
  qemu:
    image_path: "/path/to/your/vm.qcow2"
    ssh_port: 2222
    ssh_user: "your_user"
    ssh_pass: "your_password"
  
  nsjail:
    path: "/usr/local/bin/nsjail"
    rootfs: "/path/to/nsjail/rootfs"
```

---

## ⚡ Quick Start

### Run Complete Test Suite
```bash
sudo python3 main.py
```

### Run Specific Test Categories
Edit `config.yaml` to enable only desired experiments, or filter by ID:
```yaml
experiments:
  # Comment out unwanted tests
  - id: "T0.1_CPU_Perf"
    ...
  # - id: "T1.1_Fork_Bomb"  # Disabled
```

### View Results
```bash
# Results are saved in results/ directory
ls -lh results/

# View reports
cat results/summary.md
cat results/security.md
cat results/performance.md
```

---

## ⚙️ Configuration

### Test Definition Structure

Each test in `config.yaml` follows this pattern:

```yaml
- id: "T1.1_Fork_Bomb"
  description: "Fork bomb - PID namespace isolation"
  payload_cmd: "sleep 1 && /bin/fork_bomb"
  
  validation:
    strategy: "containment_pids"
    params:
      max_pid_growth: 200
      timeout_pid_threshold: 200
      strict_mode: false
  
  runs:
    - run_id: "docker_weak"
      tool: "docker"
      config: "weak"
      params: "--pid=host"
    
    - run_id: "docker_strong"
      tool: "docker"
      config: "strong"
      params: "--pids-limit=100"
```

### Global Settings
```yaml
global_settings:
  default_timeout: 30           # Test timeout in seconds
  cooldown_period: 2            # Seconds between tests
  results_dir: "results"        # Output directory
```

---

## 🔨 Extending the Framework

IsolationBench is designed for extensibility. Here's how to add new components:

### Adding a New Test

**To add a new test, simply extend `config.yaml`** - no code changes needed!

1. **Write the payload** (if needed):
```c
// payloads/my_exploit.c
#include <stdio.h>
int main() {
    printf("Attempting exploit...\n");
    // Your test logic here
    return 0;
}
```

2. **Compile the payload**:
```bash
gcc -static -o payloads/my_exploit payloads/my_exploit.c
```

3. **Add to config.yaml**:
```yaml
- id: "TX.Y_My_Test"
  description: "Description of what this tests"
  payload_cmd: "/bin/my_exploit"
  validation:
    strategy: "expect_fail"  # Or another strategy
    params:
      allowed_errors: ["Permission denied"]
  runs:
    - { run_id: "test_1", tool: "docker", config: "strong", params: "" }
```

### Adding a New Validation Strategy

**To add new validation logic, update `validators/rules.py`:**

```python
class MyCustomStrategy(ValidationStrategy):
    """Custom validation logic"""
    
    def validate(self, ctx: ValidationContext) -> str:
        # Access test results
        rc = ctx.result['return_code']
        output = ctx.result['stdout']
        
        # Access metrics
        cpu_avg = ctx.metrics['cpu_avg']
        
        # Access baseline
        baseline_pids = ctx.baseline['pids_base']
        
        # Your validation logic
        if rc == 0 and "success" in output:
            return 'SUCCESS'
        else:
            return 'FAILURE'

# Register the strategy
STRATEGY_REGISTRY['my_custom'] = MyCustomStrategy()
```

Use in config:
```yaml
validation:
  strategy: "my_custom"
  params:
    custom_param: "value"
```

### Adding a New Runner

**To add support for a new isolation technology, create a new runner:**

Create `runners/my_runner.py`:

```python
from runners.base import BaseRunner
from typing import Dict, Any
import time

class MyRunner(BaseRunner):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize your runner
    
    def run(self, run_config: Dict, payload_cmd: str, timeout: int) -> Dict[str, Any]:
        start_time = time.monotonic()
        
        # Execute the payload using your technology
        # ...
        
        return {
            'stdout': stdout,
            'stderr': stderr,
            'return_code': rc,
            'duration_s': time.monotonic() - start_time,
            'status': 'EXECUTED'
        }
    
    def cleanup(self):
        # Clean up resources
        pass
```

Register in `core/orchestrator.py`:
```python
self.runners_map = {
    'docker': DockerRunner,
    'qemu': QemuRunner,
    'nsjail': NsjailRunner,
    'my_tech': MyRunner,  # Add here
}
```

---

## 📊 Test Categories

### T0: Performance Baseline
- **T0.1**: CPU performance (sysbench prime calculation)
- **T0.2**: Disk I/O throughput (dd benchmark)

### T1: Resource Exhaustion
- **T1.1**: Fork bomb (PID limits)
- **T1.2**: Memory exhaustion (OOM killer)
- **T1.3**: CPU saturation (multi-threaded burn)
- **T1.4**: Disk space exhaustion

### T2: Filesystem Isolation
- **T2.1**: /sys write attempts
- **T2.2**: Sensitive device access (/dev/mem, /dev/kmem)
- **T2.3**: Root filesystem modification
- **T2.4**: Mount escape attempts

### T3: Kernel & Proc Isolation
- **T3.1**: /proc/version info leak
- **T3.2**: Host process cmdline exposure
- **T3.3**: Kernel module loading
- **T3.4**: Sysctl parameter access

### T4: Network Isolation
- **T4.1**: Host network packet sniffing
- **T4.2**: Port scanning
- **T4.3**: Raw socket creation
- **T4.4**: ARP spoofing

### T5: IPC & Namespace Isolation
- **T5.1**: Shared memory segment access
- **T5.2**: UTS namespace (hostname isolation)
- **T5.3**: Unix socket escape (Docker socket)

### T6: Syscall & Seccomp
- **T6.1**: Reboot syscall blocking
- **T6.2**: System time modification
- **T6.3**: Ptrace attach to host processes

### T7: Advanced Escape Attempts
- **T7.1**: Classic chroot escape
- **T7.2**: Cgroup limit modification
- **T7.3**: CVE-2022-0492 style cgroup escape

### T8: Stress & Stability
- **T8.1**: Rapid process spawn/destroy
- **T8.2**: File descriptor exhaustion
- **T8.3**: Signal flood stress test

---

## 📈 Understanding Results

### Status Codes

- **SUCCESS** ✅: Test passed (attack blocked or baseline completed)
- **FAILURE** ❌: Test failed (attack succeeded or isolation breached)
- **TIMEOUT** ⏱️: Test exceeded time limit
- **PARTIAL** ⚠️: Partial success (e.g., contained but not completely blocked)

### Report Files

- **summary.csv**: Raw data with all metrics
- **summary.md**: High-level overview with success rates
- **detailed.md**: Complete metrics for every test
- **performance.md**: Overhead analysis and comparisons
- **security.md**: Security effectiveness matrix
- **chart_data.json**: Structured data for visualization

### Interpreting Security Results

The security report shows an effectiveness matrix:

```
| Test Category         | Docker | gVisor | Kata | NsJail |
|-----------------------|--------|--------|------|--------|
| T2_Filesystem         | ✅     | ✅     | ✅   | ✅     |
| T3_Kernel_Proc        | ❌     | ✅     | ✅   | ⚠️     |
| T4_Network            | ⚠️     | ✅     | ✅   | ✅     |
```

- More ✅ = Better isolation
- ❌ indicates potential security concerns
- ⚠️ suggests partial protection

### Interpreting Performance Results

Performance overhead is normalized to Docker baseline:

```
Tool      | CPU Overhead | Memory Overhead | I/O Throughput
----------|--------------|-----------------|---------------
Docker    | 1.0x         | 1.0x            | 100%
gVisor    | 1.3x         | 1.2x            | 65%
Kata      | 1.1x         | 2.5x            | 85%
NsJail    | 1.02x        | 1.05x           | 95%
```

---

## 🤝 Contributing

Contributions are welcome! Here are ways to help:

### Bug Reports
Open an issue with:
- Your environment (OS, kernel version, tool versions)
- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs from `results/`

### Feature Requests
- Describe the use case
- Explain why it's valuable
- Suggest implementation approach (optional)

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit with clear messages
7. Push and open a PR

### Adding Test Payloads
If contributing new attack scenarios:
- Ensure code is safe and ethical
- Include comments explaining the technique
- Add corresponding test configuration
- Document expected behavior

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

### Why GPLv3?

- ✅ **Freedom to use**: Run IsolationBench for any purpose
- ✅ **Freedom to study**: Examine and understand how it works
- ✅ **Freedom to modify**: Adapt to your needs
- ✅ **Freedom to share**: Distribute copies and improvements
- ⚠️ **Copyleft**: Derivatives must be open source under GPLv3

---

## 🙏 Acknowledgments

- **sysbench** for CPU benchmarking capabilities
- **Docker**, **gVisor**, **Kata Containers**, **QEMU**, **NsJail** communities
- Security researchers documenting container escape techniques
- Python ecosystem (psutil, pandas, paramiko)

---

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/bogdan-od/IsolationBench/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bogdan-od/IsolationBench/discussions)

---

## ⚠️ Disclaimer

**IsolationBench is designed for legitimate security research, testing, and evaluation purposes only.**

- Always obtain proper authorization before testing systems you don't own
- Some tests may cause system instability (fork bombs, resource exhaustion)
- Use in isolated test environments, not production
- The authors assume no liability for misuse or damage

**Use responsibly and ethically.**

---

## 🗺️ Roadmap

- [ ] Web-based dashboard for result visualization
- [ ] Support for Firecracker and Cloud Hypervisor
- [ ] Automated CVE testing framework
- [ ] Container image vulnerability correlation
- [ ] Kubernetes pod security policy testing
- [ ] Windows container support
- [ ] Performance regression tracking

---

**Built with ❤️ for the security research community**
