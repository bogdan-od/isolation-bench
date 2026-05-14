import threading
import time
import psutil
import statistics
from typing import Dict, List, Tuple
from core.logger import log

class SystemMonitor:
    """
    Enhanced background thread to monitor comprehensive system resources.
    Captures baseline (idle) stats and detailed test execution stats.
    """
    def __init__(self):
        self.stop_event = threading.Event()
        self.metrics = {
            'cpu': [],
            'mem': [],
            'pids': [],
            'threads': [],
            'fds': [],    
            'io_read': [],
            'io_write': [],
            'net_sent': [],
            'net_recv': [],
            'ctx_switches_vol': [], # Voluntary context switches
            'ctx_switches_invol': [] # Involuntary context switches
        }
        self.thread = None
        self.baseline_io = None     # For delta calculation
        self.baseline_net = None    # For delta calculation

    def measure_baseline(self, duration: int = 2) -> Dict[str, float]:
        """
        Measures system state for 'duration' seconds to establish a baseline.
        Returns dict with average metrics.
        """
        log(f"Measuring system baseline ({duration}s)...", "DEBUG")
        
        samples = {
            'cpu': [],
            'mem': [],
            'pids': [],
            'threads': [],
            'fds': []
        }
        
        # Get initial I/O and network counters
        try:
            io_start = psutil.disk_io_counters()
            net_start = psutil.net_io_counters()
        except:
            io_start = None
            net_start = None
        
        # Collect samples
        for _ in range(duration * 5):  # 5 samples per second
            try:
                samples['cpu'].append(psutil.cpu_percent(interval=None))
                samples['mem'].append(psutil.virtual_memory().percent)
                samples['pids'].append(len(psutil.pids()))
                
                # Count total threads across all processes
                total_threads = sum(p.num_threads() for p in psutil.process_iter(['num_threads']) 
                                   if p.info['num_threads'])
                samples['threads'].append(total_threads)
                
                # Count total file descriptors
                total_fds = 0
                for p in psutil.process_iter(['num_fds']):
                    try:
                        if hasattr(p, 'num_fds'):
                            total_fds += p.num_fds()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                samples['fds'].append(total_fds)
                
            except Exception as e:
                log(f"Baseline sampling error: {e}", "DEBUG")
            
            time.sleep(0.2)
        
        # Calculate averages
        baseline = {
            'cpu_base': round(statistics.mean(samples['cpu']), 2) if samples['cpu'] else 0,
            'mem_base': round(statistics.mean(samples['mem']), 2) if samples['mem'] else 0,
            'pids_base': int(statistics.mean(samples['pids'])) if samples['pids'] else 0,
            'threads_base': int(statistics.mean(samples['threads'])) if samples['threads'] else 0,
            'fds_base': int(statistics.mean(samples['fds'])) if samples['fds'] else 0
        }
        
        # Store baseline I/O and network for delta calculation
        self.baseline_io = io_start
        self.baseline_net = net_start
        
        log(f"Baseline: CPU={baseline['cpu_base']}%, MEM={baseline['mem_base']}%, "
            f"PIDs={baseline['pids_base']}, Threads={baseline['threads_base']}, "
            f"FDs={baseline['fds_base']}", "DEBUG")
        
        return baseline

    def start(self):
        """Start monitoring thread"""
        self.metrics = {
            'cpu': [], 'mem': [], 'pids': [], 'threads': [], 'fds': [],
            'io_read': [], 'io_write': [],
            'net_sent': [], 'net_recv': [],
            'ctx_switches_vol': [], 'ctx_switches_invol': []
        }
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring thread"""
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=2)

    def get_stats(self) -> Dict[str, float]:
        """Returns aggregated stats for the session."""
        if not self.metrics['cpu']:
            return self._empty_stats()

        stats = {
            # CPU
            'cpu_avg': round(statistics.mean(self.metrics['cpu']), 2),
            'cpu_max': round(max(self.metrics['cpu']), 2),
            'cpu_min': round(min(self.metrics['cpu']), 2),
            
            # Memory
            'mem_start': round(self.metrics['mem'][0], 2) if self.metrics['mem'] else 0,
            'mem_avg': round(statistics.mean(self.metrics['mem']), 2),
            'mem_max': round(max(self.metrics['mem']), 2),
            'mem_min': round(min(self.metrics['mem']), 2),
            
            # PIDs
            'pids_start': self.metrics['pids'][0] if self.metrics['pids'] else 0,
            'pids_max': max(self.metrics['pids']) if self.metrics['pids'] else 0,
            'pids_min': min(self.metrics['pids']) if self.metrics['pids'] else 0,
            
            # Threads
            'threads_start': self.metrics['threads'][0] if self.metrics['threads'] else 0,
            'threads_max': max(self.metrics['threads']) if self.metrics['threads'] else 0,
            'threads_avg': int(statistics.mean(self.metrics['threads'])) if self.metrics['threads'] else 0,
            
            # File Descriptors
            'fds_start': self.metrics['fds'][0] if self.metrics['fds'] else 0,
            'fds_max': max(self.metrics['fds']) if self.metrics['fds'] else 0,
            'fds_avg': int(statistics.mean(self.metrics['fds'])) if self.metrics['fds'] else 0,
            
            # I/O (deltas from baseline)
            'io_read_mb': round(sum(self.metrics['io_read']) / (1024 * 1024), 2),
            'io_write_mb': round(sum(self.metrics['io_write']) / (1024 * 1024), 2),
            
            # Network (deltas from baseline)
            'net_sent_mb': round(sum(self.metrics['net_sent']) / (1024 * 1024), 2),
            'net_recv_mb': round(sum(self.metrics['net_recv']) / (1024 * 1024), 2),
            
            # Context Switches
            'ctx_switches_vol': sum(self.metrics['ctx_switches_vol']),
            'ctx_switches_invol': sum(self.metrics['ctx_switches_invol'])
        }
        
        return stats

    def _empty_stats(self) -> Dict[str, float]:
        """Returns empty stats structure"""
        return {
            'cpu_avg': 0, 'cpu_max': 0, 'cpu_min': 0,
            'mem_start': 0, 'mem_avg': 0, 'mem_max': 0, 'mem_min': 0,
            'pids_start': 0, 'pids_max': 0, 'pids_min': 0,
            'threads_start': 0, 'threads_max': 0, 'threads_avg': 0,
            'fds_start': 0, 'fds_max': 0, 'fds_avg': 0,
            'io_read_mb': 0, 'io_write_mb': 0,
            'net_sent_mb': 0, 'net_recv_mb': 0,
            'ctx_switches_vol': 0, 'ctx_switches_invol': 0
        }

    def _monitor_loop(self):
        """Main monitoring loop running in background thread"""
        prev_io = self.baseline_io
        prev_net = self.baseline_net
        
        while not self.stop_event.is_set():
            try:
                # CPU and Memory
                self.metrics['cpu'].append(psutil.cpu_percent(interval=None))
                self.metrics['mem'].append(psutil.virtual_memory().percent)
                
                # PIDs
                self.metrics['pids'].append(len(psutil.pids()))
                
                # Threads
                total_threads = 0
                for p in psutil.process_iter(['num_threads']):
                    try:
                        total_threads += p.info['num_threads'] or 0
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self.metrics['threads'].append(total_threads)
                
                # File Descriptors
                total_fds = 0
                for p in psutil.process_iter(['num_fds']):
                    try:
                        if hasattr(p, 'num_fds'):
                            total_fds += p.num_fds()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self.metrics['fds'].append(total_fds)
                
                # I/O Counters (delta from previous sample)
                try:
                    io_curr = psutil.disk_io_counters()
                    if prev_io and io_curr:
                        self.metrics['io_read'].append(io_curr.read_bytes - prev_io.read_bytes)
                        self.metrics['io_write'].append(io_curr.write_bytes - prev_io.write_bytes)
                        prev_io = io_curr
                except:
                    pass
                
                # Network Counters (delta from previous sample)
                try:
                    net_curr = psutil.net_io_counters()
                    if prev_net and net_curr:
                        self.metrics['net_sent'].append(net_curr.bytes_sent - prev_net.bytes_sent)
                        self.metrics['net_recv'].append(net_curr.bytes_recv - prev_net.bytes_recv)
                        prev_net = net_curr
                except:
                    pass
                
                # Context Switches (aggregate across all processes)
                ctx_vol_total = 0
                ctx_invol_total = 0
                for p in psutil.process_iter(['num_ctx_switches']):
                    try:
                        ctx = p.info['num_ctx_switches']
                        if ctx:
                            ctx_vol_total += ctx.voluntary
                            ctx_invol_total += ctx.involuntary
                    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                        pass
                
                self.metrics['ctx_switches_vol'].append(ctx_vol_total)
                self.metrics['ctx_switches_invol'].append(ctx_invol_total)
                
            except Exception as e:
                # Silently continue on errors
                pass
            
            time.sleep(0.2)
