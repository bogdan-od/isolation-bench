import subprocess
import time
import paramiko
from typing import Dict, Any
from runners.base import BaseRunner
from core.logger import log, log_output
import logging

logging.getLogger("paramiko").setLevel(logging.CRITICAL)

class QemuRunner(BaseRunner):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.qemu_img = self.config['tools']['qemu']['image_path']
        self.ssh_port = self.config['tools']['qemu']['ssh_port']
        self.ssh_user = self.config['tools']['qemu']['ssh_user']
        self.ssh_pass = self.config['tools']['qemu']['ssh_pass']
        self.qemu_proc = None
        self.ssh_client = None

    def run(self, run_config: Dict, payload_cmd: str, timeout: int) -> Dict[str, Any]:
        mem = run_config['mem']
        vcpus = run_config['vcpus']

        # Your specific QEMU command
        qemu_cmd = (
            f"qemu-system-x86_64 -m {mem} -smp {vcpus} -enable-kvm -cpu host "
            f"-hda {self.qemu_img} -daemonize -display none "
            f"-net nic -net user,hostfwd=tcp::{self.ssh_port}-:22"
        )
        
        log(f"Starting QEMU VM...", "DEBUG")
        start_time = time.monotonic()
        result = {'stdout': '', 'stderr': '', 'return_code': -1, 'status': 'ERROR', 'duration_s': 0}
        
        try:
            self.qemu_proc = subprocess.Popen(qemu_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for boot and SSH
            time.sleep(20) 
            if not self._wait_for_ssh():
                raise Exception("SSH Connection failed after retries")
            
            log(f"VM Ready. Executing: {payload_cmd}", "DEBUG")
            
            cmd_start = time.monotonic()
            stdin, stdout, stderr = self.ssh_client.exec_command(f"/bin/sh -c \"{payload_cmd}\"", timeout=timeout)
            
            result['stdout'] = stdout.read().decode().strip()
            result['stderr'] = stderr.read().decode().strip()
            result['return_code'] = stdout.channel.recv_exit_status()
            result['status'] = 'EXECUTED'
            result['duration_s'] = round(time.monotonic() - cmd_start, 2)

        except Exception as e:
            log(f"QEMU/SSH Error: {e}", "ERROR")
            result['stderr'] = str(e)
            if result['duration_s'] == 0:
                result['duration_s'] = round(time.monotonic() - start_time, 2)
        
        finally:
            self.cleanup()

        return result

    def _wait_for_ssh(self):
        for i in range(10):
            try:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect('localhost', port=self.ssh_port, username=self.ssh_user, 
                                   password=self.ssh_pass, timeout=5)
                return True
            except:
                time.sleep(3)
        return False

    def cleanup(self):
        if self.ssh_client:
            try: self.ssh_client.close()
            except: pass
        
        # Hard cleanup of QEMU
        try:
            subprocess.run(['pkill', '-9', 'qemu-system-x86'], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
