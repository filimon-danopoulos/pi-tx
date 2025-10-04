"""
Main UI application for pi-tx.

Loads a hardcoded model (cat_d6t) and displays live channel values
updated at 30Hz.
"""

import sys
import asyncio
import threading
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle

# Import the cat_d6t model
sys.path.insert(0, str(Path(__file__).parent.parent))
from examples.cat_d6t_example import cat_d6t
from pi_tx.logging_config import init_logging


class ChannelDisplay(BoxLayout):
    """Widget to display a single channel's value."""

    def __init__(self, channel_name: str, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=60, padding=10, spacing=5, **kwargs)
        self.channel_name = channel_name

        # Channel name label
        self.name_label = Label(
            text=channel_name,
            size_hint_y=None,
            height=20,
            font_size='14sp',
            bold=True,
            color=(0.8, 0.8, 0.8, 1)
        )
        self.add_widget(self.name_label)

        # Value label
        self.value_label = Label(
            text='0.000',
            size_hint_y=None,
            height=25,
            font_size='18sp',
            font_name='RobotoMono-Regular',
            halign='right',
            color=(0.5, 0.5, 0.5, 1)
        )
        self.add_widget(self.value_label)

        # Background
        with self.canvas.before:
            Color(0.17, 0.17, 0.17, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[5])

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        """Update background rectangle on size/position change."""
        self.rect.pos = self.pos
        self.rect.size = self.size

    def update_value(self, value: float):
        """Update the displayed value."""
        self.value_label.text = f'{value:7.3f}'

        # Color code based on value
        if abs(value) < 0.1:
            color = (0.5, 0.5, 0.5, 1)  # Gray for neutral
        elif value > 0:
            color = (0.3, 0.69, 0.31, 1)  # Green for positive
        else:
            color = (0.96, 0.26, 0.21, 1)  # Red for negative

        self.value_label.color = color


class MainScreen(BoxLayout):
    """Main screen layout."""

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)

        # Title
        title = Label(
            text='CAT D6T - Live Channel Values',
            size_hint_y=None,
            height=40,
            font_size='20sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(title)

        # Model info
        info = Label(
            text=f'Model: {cat_d6t.name} | RX: {cat_d6t.rx_num} | Channels: {len(cat_d6t.channels)}',
            size_hint_y=None,
            height=25,
            font_size='12sp',
            color=(0.6, 0.6, 0.6, 1)
        )
        self.add_widget(info)

        # ScrollView for channels
        scroll = ScrollView(size_hint=(1, 1))
        channel_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, padding=(0, 10))
        channel_layout.bind(minimum_height=channel_layout.setter('height'))

        # Create channel displays
        self.channel_displays = {}
        for channel in cat_d6t.channels:
            display = ChannelDisplay(channel.name)
            self.channel_displays[channel.name] = display
            channel_layout.add_widget(display)

        scroll.add_widget(channel_layout)
        self.add_widget(scroll)

    def update_values(self):
        """Update all channel displays with current values."""
        try:
            # Get current processed values from the model
            values = cat_d6t.readValues()

            # Update each display
            for channel_name, display in self.channel_displays.items():
                value = values.get(channel_name, 0.0)
                display.update_value(value)

        except Exception as e:
            print(f"Error updating values: {e}")


class PiTxApp(App):
    """Main Kivy application."""

    def build(self):
        """Build the application."""
        # Set window properties
        Window.clearcolor = (0.12, 0.12, 0.12, 1)
        Window.size = (400, 600)

        # Create main screen
        self.main_screen = MainScreen()

        # Schedule updates at 30Hz (~33ms)
        Clock.schedule_interval(lambda dt: self.main_screen.update_values(), 1/30)

        # Start listening to input in background thread
        self.start_listening()

        return self.main_screen

    def start_listening(self):
        """Start the model.listen() method in a background thread."""
        def run_listen():
            # Create a new event loop for this thread
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            # Run listen indefinitely
            try:
                event_loop.run_until_complete(cat_d6t.listen())
            except Exception as e:
                print(f"Listen thread error: {e}")
            finally:
                event_loop.close()

        listen_thread = threading.Thread(target=run_listen, daemon=True)
        listen_thread.start()

    def on_stop(self):
        """Clean up when application stops."""
        # The daemon thread will automatically stop when the main thread exits
        return True


def main():
    """Run the UI application."""
    # Initialize logging
    init_logging(level="INFO")

    # Run the Kivy app
    PiTxApp().run()


if __name__ == "__main__":
    main()
