from __future__ import annotations

import os
from typing import List
from pathlib import Path

from .model_json import Model, parse_model_dict
from ..infrastructure.file_cache import load_json, save_json
from ..logging_config import get_logger

MODELS_DIR_DEFAULT = "models"


class ModelRepository:
    def __init__(self, models_dir: str = MODELS_DIR_DEFAULT):
        self.models_dir = models_dir
        self._log = get_logger(self.__class__.__name__)

    def list_models(self) -> List[str]:
        if not os.path.isdir(self.models_dir):
            return []
        return sorted(
            [f[:-5] for f in os.listdir(self.models_dir) if f.endswith(".json")]
        )

    def load_model(self, name: str) -> Model:
        path = os.path.join(self.models_dir, f"{name}.json")

        # Use file cache to load model data
        data = load_json(path, default_value={})

        # If file doesn't exist, return default model
        if not data:
            return Model(name=name, channels={}, processors={})

        return parse_model_dict(name, data)

    def save_model(self, model: Model) -> None:
        """Save a model to JSON file using file cache."""
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

        # Use file cache to save model
        save_json(path, model_dict)
        self._log.info(
            "Saved model",
            extra={"path": path, "channels": len(model.channels)},
        )
