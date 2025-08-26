from controls import InputController
import time


def main():
    # Create and start the input controller
    input_controller = InputController()

    right_stick_path = "/dev/input/event14"
    input_controller.register_callback(
        right_stick_path, 0, lambda v: print(f"The X-axis recieved the value {v}")
    )
    input_controller.register_callback(
        right_stick_path, 1, lambda v: print(f"The Y-axis recieved the value {v}")
    )
    input_controller.register_callback(
        right_stick_path, 5, lambda v: print(f"The Z-axis recieved the value {v}")
    )

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
