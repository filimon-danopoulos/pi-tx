from kivy.event import EventDispatcher
from kivy.properties import DictProperty, NumericProperty


class ChannelState(EventDispatcher):
    """Centralized state management for channel values"""

    # Dictionary to store all channel values
    channels = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize all channels to 0
        self.channels = {i: 0.0 for i in range(1, 11)}

    def update_channel(self, channel: int, value: float):
        """Update the value of a specific channel

        Args:
            channel: Channel number (1-10)
            value: Normalized value (-1 to 1)
        """
        if 1 <= channel <= 10:
            self.channels[channel] = value

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
