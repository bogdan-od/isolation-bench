from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseRunner(ABC):
    """
    Abstract base class that all isolation tools must implement.
    This ensures the framework is extensible.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def run(self, run_config: Dict, payload_cmd: str, timeout: int) -> Dict[str, Any]:
        """
        Execute the test payload.
        Must return dictionary with: status, return_code, stdout, stderr, duration_s.
        """
        pass

    @abstractmethod
    def cleanup(self):
        """
        Force cleanup of any leftover resources (containers, VMs, processes).
        """
        pass
