from controls import InputController
from gui import create_gui
from setup import setup_controls


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
