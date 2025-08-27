from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty
from state import channel_state
import json


class AxisSlider(Widget):
    value = NumericProperty(0.0)
    axis_name = StringProperty("")
    control_name = StringProperty("")


class ValueDisplay(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = channel_state
        # Bind to state changes
        self.state.bind(channels=self.on_state_change)
        self.create_channel_sliders()

    def create_channel_sliders(self):
        """Create sliders based on the model mapping configuration"""
        try:
            with open("model_mapping.json", "r") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            print("No model mapping found!")
            return

        grid = self.ids.channel_grid
        for channel, config in sorted(mapping["channels"].items()):
            slider = AxisSlider()
            slider.id = f"ch{channel}"
            slider.axis_name = f"CH{channel}"
            slider.control_name = config["control_name"]
            grid.add_widget(slider)
            self.ids[slider.id] = slider

    def on_state_change(self, instance, value):
        """Called when channel_values changes in state"""
        for channel, val in value.items():
            slider_id = f"ch{channel}"
            if slider_id in self.ids:
                self.ids[slider_id].value = val

    def update_channel(self, channel: int, value: float):
        """Update the value for a specific channel

        Args:
            channel: Channel number (1-10)
            value: Normalized value (-1 to 1)
        """
        if 1 <= channel <= 10:
            self.state.update_channel(channel, value)


class ControllerApp(App):
    def __init__(self, input_controller, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.display = None
        self.state = channel_state

    def build(self):
        Window.size = (800, 480)
        self.display = ValueDisplay()
        return self.display

    def update_value(self, control_id: int, value: float):
        """Update a control value in the display

        Args:
            control_id: The control ID (1-10)
            value: The normalized value for the control
        """
        if self.display:
            self.display.update_channel(control_id, value)


def create_gui(input_controller):
    """Create and run the GUI application"""
    app = ControllerApp(input_controller)
    return app
