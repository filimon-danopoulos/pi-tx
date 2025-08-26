from controls import InputController
from gui import create_gui


def main():
    # Create the input controller
    input_controller = InputController(debug=False)

    # Create and run the GUI
    app = create_gui(input_controller)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        input_controller.stop()
        print("Shutdown complete")


if __name__ == "__main__":
    main()
