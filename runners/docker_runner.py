import subprocess
import time
import uuid
from typing import Dict, Any
from runners.base import BaseRunner
from core.logger import log, log_output

class DockerRunner(BaseRunner):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.image = self.config['tools']['docker']['image']
        self.container_name = None

    def _generate_name(self):
        return f"isolationbench_{uuid.uuid4().hex[:8]}"

    def run(self, run_config: Dict, payload_cmd: str, timeout: int) -> Dict[str, Any]:
        self.container_name = self._generate_name()
        
        runtime = ""
        tool_variant = run_config['tool'] # docker, gvisor, kata
        
        if tool_variant == 'gvisor':
            runtime = f"--runtime={self.config['tools']['docker']['runtime_gvisor']}"
        elif tool_variant == 'kata':
            runtime = f"--runtime={self.config['tools']['docker']['runtime_kata']}"

        params = run_config['params']
        
        # Construct command exactly as in your working code
        cmd = f"docker run --name {self.container_name} --rm {runtime} {params} {self.image} /bin/sh -c \"{payload_cmd}\""
        
        log(f"Docker CMD ({tool_variant}): {cmd}", "DEBUG")
        
        start_time = time.monotonic()
        result = {'stdout': '', 'stderr': '', 'return_code': -1, 'duration_s': 0, 'status': 'ERROR'}
        proc = None
        
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, text=True)
            
            stdout, stderr = proc.communicate(timeout=timeout)
            result['return_code'] = proc.returncode
            result['stdout'] = stdout.strip()
            result['stderr'] = stderr.strip()
            
            # Note: Status determination is moved to Validator, here we just report execution success
            result['status'] = 'EXECUTED' 

        except subprocess.TimeoutExpired:
            log(f"Timeout ({timeout}s)! Docker container will be killed.", "TIMEOUT")
            try:
                stdout, stderr = proc.communicate(timeout=1)
                result['stdout'] = stdout.strip() if stdout else ''
                result['stderr'] = stderr.strip() if stderr else ''
            except:
                pass
            result['status'] = 'TIMEOUT'
            result['stderr'] += "\n[DOCKER CONTAINER KILLED - TIMEOUT]"

        except Exception as e:
            log(f"Critical Docker Error: {e}", "ERROR")
            result['stderr'] = str(e)
        
        finally:
            self.cleanup()
            result['duration_s'] = round(time.monotonic() - start_time, 2)

        return result

    def cleanup(self):
        """Guaranteed cleanup using docker rm -f"""
        if self.container_name:
            # log(f"Cleaning up container: {self.container_name}", "CLEANUP")
            try:
                subprocess.run(['docker', 'rm', '-f', self.container_name], 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            except Exception as e:
                log(f"Error cleaning up docker: {e}", "WARN")
