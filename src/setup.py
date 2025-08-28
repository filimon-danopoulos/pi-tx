import json
from state import channel_state


def setup_controls(input_controller, app):
    """Setup the control mappings and callbacks using model_mapping.json

    Args:
        input_controller: The input controller instance
        app: The GUI application instance
    """
    try:
        with open("model_mapping.json", "r") as f:
            model_mapping = json.load(f)
    except FileNotFoundError:
        print("Error: model_mapping.json not found!")
        return

    # Register callbacks for mapped channels
    for channel, mapping in model_mapping["channels"].items():

        def make_callback(channel_id):
            return lambda value: channel_state.update_channel(int(channel_id), value)

        device_path = mapping["device_path"]
        control_code = int(mapping["control_code"])

        input_controller.register_callback(
            device_path, control_code, make_callback(channel)
        )

    # Start the input controller
    input_controller.start()
