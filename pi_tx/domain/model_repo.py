from __future__ import annotations

import json
import os
from typing import List
from dataclasses import asdict

from .model_json import Model, parse_model_dict

MODELS_DIR_DEFAULT = "models"


class ModelRepository:
    def __init__(self, models_dir: str = MODELS_DIR_DEFAULT):
        self.models_dir = models_dir

    def list_models(self) -> List[str]:
        if not os.path.isdir(self.models_dir):
            return []
        return sorted(
            [f[:-5] for f in os.listdir(self.models_dir) if f.endswith(".json")]
        )

    def load_model(self, name: str) -> Model:
        path = os.path.join(self.models_dir, f"{name}.json")
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            return Model(name=name, channels={}, processors={})
        return parse_model_dict(name, data)

    def save_model(self, model: Model) -> None:
        """Save a model to JSON file."""
        os.makedirs(self.models_dir, exist_ok=True)
        path = os.path.join(self.models_dir, f"{model.name}.json")

        # Convert model to dict, but handle channels specially
        model_dict = {
            "name": model.name,
            "model_id": model.model_id,
            "rx_num": model.rx_num,
            "model_index": model.model_index,
            "bind_timestamp": model.bind_timestamp,
            "channels": {},
            "processors": model.processors,
        }

        # Convert channels to the expected JSON format using ch1 format
        for ch_id, channel in model.channels.items():
            channel_dict = {
                "control_type": channel.control_type,
                "device_path": channel.device_path,
                "control_code": channel.control_code,
            }

            # Include optional fields if they exist
            if channel.device_name:
                channel_dict["device_name"] = channel.device_name
            if channel.control_name:
                channel_dict["control_name"] = channel.control_name

            model_dict["channels"][f"ch{ch_id}"] = channel_dict

        with open(path, "w") as f:
            json.dump(model_dict, f, indent=2)
        print(f"Saved model to {path}")
