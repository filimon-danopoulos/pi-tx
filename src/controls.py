import threading
import time


class InputController:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the input controller thread."""
        if self._thread is not None and self._thread.is_alive():
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop the input controller thread."""
        if self._thread is None:
            return False

        self._stop_event.set()
        self._thread.join(timeout=2.0)
        return True

    def _input_loop(self):
        """Main input processing loop."""
        print("Input controller started")
        while not self._stop_event.is_set():
            # TODO: Implement actual input handling here
            time.sleep(0.1)  # Sleep to prevent CPU hogging
        print("Input controller stopped")
