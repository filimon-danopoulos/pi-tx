from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window


class ValueDisplay(BoxLayout):
    def update_x(self, value):
        """Update X axis value"""
        self.ids.x_value.text = f"{value:.3f}"

    def update_y(self, value):
        """Update Y axis value"""
        self.ids.y_value.text = f"{value:.3f}"

    def update_z(self, value):
        """Update Z axis value"""
        self.ids.z_value.text = f"{value:.3f}"


class ControllerApp(App):
    def __init__(self, input_controller, **kwargs):
        super().__init__(**kwargs)
        self.input_controller = input_controller
        self.display = None

    def build(self):
        Window.size = (800, 480)  # Set a small window size
        self.display = ValueDisplay()
        return self.display

    def on_start(self):
        # Start the input controller
        self.input_controller.start()

        # Register callback for event code 0
        def value_callback(value):
            self.display.update_value(value)

        self.input_controller.register_callback(
            "/dev/input/event14", 0, lambda v: self.display.update_x(v)
        )
        self.input_controller.register_callback(
            "/dev/input/event14", 1, lambda v: self.display.update_y(v)
        )
        self.input_controller.register_callback(
            "/dev/input/event14", 5, lambda v: self.display.update_z(v)
        )

    def on_stop(self):
        # Stop the input controller
        self.input_controller.stop()


def create_gui(input_controller):
    """Create and run the GUI application"""
    app = ControllerApp(input_controller)
    return app
