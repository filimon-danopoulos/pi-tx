from controls import InputController
from gui import create_gui


def main():
    input_controller = InputController(debug=False)
    app = create_gui(input_controller)

    # GUI now handles control setup internally on model selection.
    app.run()


if __name__ == "__main__":
    main()
