from controls import InputController
import time


def main():
    # Create and start the input controller
    input_controller = InputController()
    input_controller.start()

    try:
        # Main program loop
        while True:
            # TODO: Add main program logic here
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        input_controller.stop()
        print("Shutdown complete")


if __name__ == "__main__":
    main()
