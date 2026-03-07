import threading


class SystemState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemState, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.shutdown_event = threading.Event()

    def request_shutdown(self):
        """Signal that the system should shut down."""
        self.shutdown_event.set()

    def is_shutdown_requested(self) -> bool:
        """Check if a shutdown has been requested."""
        return self.shutdown_event.is_set()

    def clear_shutdown_request(self):
        """Reset the shutdown request (though typically you'd not use this after a shutdown)."""
        self.shutdown_event.clear()


# This ensures that any import of system_state will have access to the same instance
system_state = SystemState()
