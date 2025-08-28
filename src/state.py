from kivy.event import EventDispatcher
from kivy.properties import DictProperty, NumericProperty  # noqa: F401
from kivy.clock import Clock
import threading


class ChannelState(EventDispatcher):
    """Centralized state management for channel values"""

    # Dictionary to store all channel values
    channels = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize all channels to 0
        self.channels = {i: 0.0 for i in range(1, 11)}
        # Record main thread id for thread-safety checks
        self._main_thread_id = threading.get_ident()
        # Simple buffer for coalescing background updates (channel -> latest value)
        self._pending = {}
        self._flush_scheduled = False

    def update_channel(self, channel: int, value: float):
        """Update the value of a specific channel

        Args:
            channel: Channel number (1-10)
            value: Normalized value (-1 to 1)
        """
        if not (1 <= channel <= 10):
            return

        # If we're not on the main thread, buffer and schedule a flush
        if threading.get_ident() != self._main_thread_id:
            self._pending[channel] = value
            if not self._flush_scheduled:
                self._flush_scheduled = True
                Clock.schedule_once(self._flush_pending, 0)
            return

        # Main thread: apply immediately
        self.channels[channel] = value

    def _flush_pending(self, *_):
        # Apply any pending buffered updates (main thread context)
        for ch, val in list(self._pending.items()):
            self.channels[ch] = val
        self._pending.clear()
        self._flush_scheduled = False

    def get_channel(self, channel: int) -> float:
        """Get the current value of a channel

        Args:
            channel: Channel number (1-10)

        Returns:
            The current value of the channel
        """
        return self.channels.get(channel, 0.0)


# Create a singleton instance
channel_state = ChannelState()
