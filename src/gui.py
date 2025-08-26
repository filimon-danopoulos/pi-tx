from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty


class AxisSlider(Widget):
    value = NumericProperty(0.0)
    axis_name = StringProperty("")


class ValueDisplay(BoxLayout):
    def update_channel(self, channel: int, value: float):
        """Update the value for a specific channel

        Args:
            channel: Channel number (1-10)
            value: Normalized value (-1 to 1)
        """
        if 1 <= channel <= 10:
            slider_id = f"ch{channel}"
            if slider_id in self.ids:
                self.ids[slider_id].value = value


class ControllerApp(App):
    def __init__(self, input_controller, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.display = None

    def build(self):
        Window.size = (800, 480)
        self.display = ValueDisplay()
        return self.display

    def on_start(self):
        # Start the input controller
        self.input_controller.start()

        # Channel mapping: channel_number: (device_path, event_code)
        channel_mapping = {
            1: ("/dev/input/event14", 0),  # CH1 - X axis
            2: ("/dev/input/event14", 1),  # CH2 - Y axis
            3: ("/dev/input/event14", 5),  # CH3 - Z axis
            4: ("/dev/input/event14", 6),  # CH4
            5: ("/dev/input/event14", 288),  # CH5
            6: ("/dev/input/event15", 0),  # CH1 - X axis
            7: ("/dev/input/event15", 1),  # CH2 - Y axis
            8: ("/dev/input/event15", 5),  # CH3 - Z axis
            9: ("/dev/input/event15", 6),  # CH4
            10: ("/dev/input/event15", 288),  # CH4
            # Add more mappings as needed, can use different device paths
        }

        # Register callbacks for all channels
        for channel, (device_path, event_code) in channel_mapping.items():

            def make_callback(ch):
                return lambda value: self.display.update_channel(ch, value)

            self.input_controller.register_callback(
                device_path, event_code, make_callback(channel)
            )

    def on_stop(self):
        # Stop the input controller
        self.input_controller.stop()


def create_gui(input_controller):
    """Create and run the GUI application"""
    app = ControllerApp(input_controller)
    return app
