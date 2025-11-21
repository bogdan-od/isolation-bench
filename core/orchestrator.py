import os
import csv
import time
from typing import Dict, Any
import pandas as pd

# Modules
from core.logger import log, log_separator, log_output
from core.monitor import SystemMonitor
from core.reporter import ReportGenerator
from validators.rules import TestValidator
from runners.docker_runner import DockerRunner
from runners.qemu_runner import QemuRunner
from runners.nsjail_runner import NsjailRunner

class Orchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.monitor = SystemMonitor()
        self.csv_file = None
        self.writer = None
        
        self.runners_map = {
            'docker': DockerRunner,
            'gvisor': DockerRunner,
            'kata': DockerRunner,
            'qemu': QemuRunner,
            'nsjail': NsjailRunner
        }

    def setup(self):
        results_dir = self.config['global_settings']['results_dir']
        os.makedirs(results_dir, exist_ok=True)
        
        # Expanded fieldnames with new metrics
        fieldnames = [
            # Basic info
            'experiment_id', 'run_id', 'tool', 'config_type', 'validation_rule', 'status',
            'duration_s', 'return_code',
            
            # PIDs
            'baseline_pids', 'pids_start', 'pids_max', 'pids_min', 'pid_growth',
            
            # Threads
            'baseline_threads', 'threads_start', 'threads_max', 'threads_avg', 'thread_growth',
            
            # File Descriptors
            'baseline_fds', 'fds_start', 'fds_max', 'fds_avg', 'fd_growth',
            
            # CPU
            'baseline_cpu', 'cpu_avg', 'cpu_max', 'cpu_min',
            
            # Memory
            'baseline_mem', 'mem_start', 'mem_avg', 'mem_max', 'mem_min', 'mem_growth',
            
            # I/O
            'io_read_mb', 'io_write_mb',
            
            # Network
            'net_sent_mb', 'net_recv_mb',
            
            # Context Switches
            'ctx_switches_vol', 'ctx_switches_invol',
            
            # Output
            'stdout', 'stderr'
        ]
        
        csv_path = os.path.join(results_dir, 'summary.csv')
        self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.writer.writeheader()
        log(f"Results file initialized: {csv_path}", "SUCCESS")

    def execute_all(self):
        experiments = self.config.get('experiments', [])
        total = sum(len(e.get('runs', [])) for e in experiments)
        current = 0

        for exp in experiments:
            log_separator()
            log(f"BATTERY: {exp['id']} ({exp['description']})", "INFO")
            validation_rule = exp.get('validation', 'standard')
            
            for run_cfg in exp.get('runs', []):
                current += 1
                self._run_single_test(exp, run_cfg, validation_rule, current, total)
                
        self._finalize()

    def _run_single_test(self, exp, run_cfg, validation_config, current, total):
        tool_name = run_cfg['tool']
        log(f"\n[{current}/{total}] Test: {run_cfg['run_id']} [{tool_name}]", "INFO")
        
        runner_class = self.runners_map.get(tool_name)
        if not runner_class:
            log(f"Unknown tool: {tool_name}", "ERROR")
            return
            
        runner = runner_class(self.config)
        
        # 1. Measure Baseline (System at rest)
        baseline = self.monitor.measure_baseline(duration=2)
        log(f"Baseline: PIDs={baseline['pids_base']}, CPU={baseline['cpu_base']}%, "
            f"MEM={baseline['mem_base']}%, Threads={baseline['threads_base']}, "
            f"FDs={baseline['fds_base']}", "DEBUG")
        
        # 2. Start Monitor & Run Test
        self.monitor.start()
        raw_result = runner.run(
            run_config=run_cfg,
            payload_cmd=exp['payload_cmd'],
            timeout=self.config['global_settings']['default_timeout']
        )
        self.monitor.stop()
        
        # 3. Get Execution Metrics
        metrics = self.monitor.get_stats()
        
        # 4. Validate
        final_status = TestValidator.validate(
            validation_config, raw_result, metrics, baseline, 
            tool_name=run_cfg['tool'], run_config=run_cfg
        )
        
        # 5. Save & Report
        self._save_result(exp, run_cfg, raw_result, final_status, validation_config, metrics, baseline)
        
        status_level = "SUCCESS" if final_status == 'SUCCESS' else "FAILURE"
        if final_status == 'TIMEOUT': status_level = "TIMEOUT"
        
        # Enhanced logging with more metrics
        log(f"Result: {final_status} | Duration: {raw_result['duration_s']}s | "
            f"CPU: {metrics['cpu_avg']}% | MEM: {metrics['mem_avg']}% | "
            f"PIDs: {metrics['pids_max']} (+{metrics['pids_max'] - baseline['pids_base']}) | "
            f"FDs: {metrics['fds_max']} (+{metrics['fds_max'] - baseline['fds_base']})", 
            status_level)
            
        if final_status != 'SUCCESS':
            log_output(raw_result['stdout'], raw_result['stderr'], raw_result['return_code'])

        time.sleep(self.config['global_settings']['cooldown_period'])

    def _save_result(self, exp, run_cfg, raw, status, rule, metrics, baseline):
        row = {
            # Basic info
            'experiment_id': exp['id'],
            'run_id': run_cfg['run_id'],
            'tool': run_cfg['tool'],
            'config_type': run_cfg.get('config', 'unknown'),
            'validation_rule': rule if isinstance(rule, str) else rule.get('strategy', 'unknown'),
            'status': status,
            'duration_s': raw['duration_s'],
            'return_code': raw['return_code'],
            
            # PIDs
            'baseline_pids': baseline['pids_base'],
            'pids_start': metrics.get('pids_start', 0),
            'pids_max': metrics['pids_max'],
            'pids_min': metrics.get('pids_min', 0),
            'pid_growth': metrics['pids_max'] - baseline['pids_base'],
            
            # Threads
            'baseline_threads': baseline.get('threads_base', 0),
            'threads_start': metrics.get('threads_start', 0),
            'threads_max': metrics.get('threads_max', 0),
            'threads_avg': metrics.get('threads_avg', 0),
            'thread_growth': metrics.get('threads_max', 0) - baseline.get('threads_base', 0),
            
            # File Descriptors
            'baseline_fds': baseline.get('fds_base', 0),
            'fds_start': metrics.get('fds_start', 0),
            'fds_max': metrics.get('fds_max', 0),
            'fds_avg': metrics.get('fds_avg', 0),
            'fd_growth': metrics.get('fds_max', 0) - baseline.get('fds_base', 0),
            
            # CPU
            'baseline_cpu': baseline['cpu_base'],
            'cpu_avg': metrics['cpu_avg'],
            'cpu_max': metrics['cpu_max'],
            'cpu_min': metrics.get('cpu_min', 0),
            
            # Memory
            'baseline_mem': baseline.get('mem_base', 0),
            'mem_start': metrics.get('mem_start', 0),
            'mem_avg': metrics['mem_avg'],
            'mem_max': metrics['mem_max'],
            'mem_min': metrics.get('mem_min', 0),
            'mem_growth': metrics['mem_max'] - baseline.get('mem_base', 0),
            
            # I/O
            'io_read_mb': metrics.get('io_read_mb', 0),
            'io_write_mb': metrics.get('io_write_mb', 0),
            
            # Network
            'net_sent_mb': metrics.get('net_sent_mb', 0),
            'net_recv_mb': metrics.get('net_recv_mb', 0),
            
            # Context Switches
            'ctx_switches_vol': metrics.get('ctx_switches_vol', 0),
            'ctx_switches_invol': metrics.get('ctx_switches_invol', 0),
            
            # Output
            'stdout': raw['stdout'][:1000],
            'stderr': raw['stderr'][:1000]
        }
        self.writer.writerow(row)
        self.csv_file.flush()

    def _finalize(self):
        if self.csv_file:
            self.csv_file.close()
        
        log_separator()
        log("ALL TESTS COMPLETED", "SUCCESS")
        
        # Generate comprehensive reports
        try:
            res_dir = self.config['global_settings']['results_dir']
            reporter = ReportGenerator(res_dir)
            
            log("Generating reports...", "INFO")
            reporter.generate_all()
            reporter.generate_comparison_chart_data(pd.read_csv(os.path.join(res_dir, 'summary.csv')))
            
            log("All reports generated successfully", "SUCCESS")
            log(f"Reports location: {res_dir}/", "INFO")
            log("  - summary.md (high-level overview)", "INFO")
            log("  - detailed.md (full metrics)", "INFO")
            log("  - performance.md (performance analysis)", "INFO")
            log("  - security.md (security effectiveness)", "INFO")
            log("  - chart_data.json (visualization data)", "INFO")
            
        except Exception as e:
            log(f"Report generation failed: {e}", "ERROR")
            import traceback
            log(traceback.format_exc(), "DEBUG")
