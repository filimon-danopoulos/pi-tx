from controls import InputController
from gui import create_gui
from state import channel_state


def setup_controls(input_controller, app):
    """Setup the control mappings and callbacks

    Args:
        input_controller: The input controller instance
        app: The GUI application instance
    """
    # Channel mapping: channel_number: (device_path, event_code)
    control_mapping = {
        1: ("/dev/input/event14", 0),  # Left stick X
        2: ("/dev/input/event14", 1),  # Left stick Y
        3: ("/dev/input/event14", 5),  # Right stick X
        4: ("/dev/input/event14", 6),  # Right stick Y
        5: ("/dev/input/event14", 288),  # Left throttle
        6: ("/dev/input/event15", 0),  # Right throttle
        7: ("/dev/input/event15", 1),  # Rudder
        8: ("/dev/input/event15", 5),  # Aux 1
        9: ("/dev/input/event15", 6),  # Aux 2
        10: ("/dev/input/event15", 288),  # Aux 3
    }

    # Register callbacks for all controls
    for control_id, (device_path, event_code) in control_mapping.items():

        def make_callback(ctrl_id):
            return lambda value: app.update_value(ctrl_id, value)

        input_controller.register_callback(
            device_path, event_code, make_callback(control_id)
        )

    # Start the input controller
    input_controller.start()


def main():
    # Create the input controller
    input_controller = InputController(debug=False)

    # Create the GUI application
    app = create_gui(input_controller)

    # Setup control mappings and callbacks
    setup_controls(input_controller, app)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        input_controller.stop()
        print("Shutdown complete")


if __name__ == "__main__":
    main()
