from __future__ import annotations
import os, json
from dataclasses import dataclass
from typing import Dict, List

MODELS_DIR_DEFAULT = "models"


@dataclass(frozen=True)
class ChannelConfig:
    channel_id: int
    control_type: str
    device_path: str
    control_code: int


@dataclass
class Model:
    name: str
    channels: Dict[int, ChannelConfig]


class ModelRepository:
    """Loads and validates model JSON files from a directory.

    A model file structure is expected:
    {
      "name": "plane1",
      "channels": {
         "1": {"device_path": "/dev/input/event0", "control_code": 3, "control_type": "bipolar"},
         ...
      }
    }
    """

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
            return Model(name=name, channels={})

        raw_channels = data.get("channels", {}) or {}
        parsed: Dict[int, ChannelConfig] = {}
        for key, cfg in raw_channels.items():
            try:
                ch_id = int(key)
                device_path = cfg["device_path"]
                control_code = int(cfg["control_code"])
                control_type = cfg.get("control_type") or cfg.get("type") or "unipolar"
                parsed[ch_id] = ChannelConfig(
                    channel_id=ch_id,
                    control_type=control_type,
                    device_path=device_path,
                    control_code=control_code,
                )
            except Exception as e:
                print(f"ModelRepository: skipping channel {key}: {e}")
        return Model(name=name, channels=parsed)
