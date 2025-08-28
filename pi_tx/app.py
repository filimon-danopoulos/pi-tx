from .input.controls import InputController
from .ui.gui import create_gui


def run():
    controller = InputController(debug=False)
    app = create_gui(controller)
    app.run()
