import threading
from typing import Tuple, Optional

class DiagnosticsManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DiagnosticsManager, cls).__new__(cls)
                    cls._instance._error_state = False
                    cls._instance._error_message = None
        return cls._instance

    def set_global_error_state(self, is_error: bool, message: Optional[str] = None):
        with self._lock:
            self._error_state = is_error
            if message:
                self._error_message = message

    def get_global_error_state(self) -> Tuple[bool, Optional[str]]:
        with self._lock:
            return self._error_state, self._error_message

    def reset(self):
        with self._lock:
            self._error_state = False
            self._error_message = None

global_diagnostics = DiagnosticsManager()
