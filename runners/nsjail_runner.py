import subprocess
import time
import os
import signal
from typing import Dict, Any
from runners.base import BaseRunner
from core.logger import log, log_output

class NsjailRunner(BaseRunner):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.nsjail_path = self.config['tools']['nsjail']['path']
        self.rootfs = self.config['tools']['nsjail']['rootfs']
        self.current_proc = None

    def run(self, run_config: Dict, payload_cmd: str, timeout: int) -> Dict[str, Any]:
        params = run_config['params']
        
        # Using your exact working command structure
        cmd = (
            f"sudo {self.nsjail_path} -Mo "
            f"--chroot {self.rootfs} "
            f"{params} -- "
            f"/bin/sh -c \"{payload_cmd}\""
        )
        
        log(f"Nsjail CMD: {cmd}", "DEBUG")
        
        start_time = time.monotonic()
        result = {'stdout': '', 'stderr': '', 'return_code': -1, 'duration_s': 0, 'status': 'ERROR'}
        
        try:
            # Using preexec_fn=os.setsid for process group management (as discussed previously)
            self.current_proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
            
            stdout, stderr = self.current_proc.communicate(timeout=timeout)
            result['return_code'] = self.current_proc.returncode
            result['stdout'] = stdout.strip()
            result['stderr'] = stderr.strip()
            result['status'] = 'EXECUTED'

        except subprocess.TimeoutExpired:
            log(f"Timeout ({timeout}s)! Nsjail process killing...", "TIMEOUT")
            result['status'] = 'TIMEOUT'
            result['stderr'] += "\n[NSJAIL KILLED - TIMEOUT]"
        
        except Exception as e:
            log(f"Nsjail Error: {e}", "ERROR")
            result['stderr'] = str(e)

        finally:
            self.cleanup()
            result['duration_s'] = round(time.monotonic() - start_time, 2)
            
        return result

    def cleanup(self):
        if self.current_proc:
            try:
                # Kill the whole process group
                os.killpg(os.getpgid(self.current_proc.pid), signal.SIGKILL)
                self.current_proc.wait(timeout=2)
            except:
                pass
            
            # Backup cleanup via pkill
            try:
                subprocess.run(['sudo', 'pkill', '-9', '-f', 'nsjail'], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
