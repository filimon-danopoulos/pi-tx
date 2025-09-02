from __future__ import annotations
import os, json, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any

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
    processors: Dict[str, Any] = field(default_factory=dict)
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rx_num: int = 0  # 0..15 slot used by MULTI/IRX module
    model_index: int = 0  # Sequential human-friendly ID


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

        raw = data.get("channels", {}) or {}
        processors_cfg = data.get("processors", {}) or {}
        model_id = data.get("model_id") or uuid.uuid4().hex
        model_index = data.get("model_index")
        try:
            model_index = int(model_index)
        except Exception:
            model_index = 0
        rx_num = data.get("rx_num")
        try:
            rx_num = int(rx_num)
        except Exception:
            rx_num = 0
        # clamp rx_num
        if rx_num < 0:
            rx_num = 0
        if rx_num > 15:
            rx_num = 15
        parsed: Dict[int, ChannelConfig] = {}
        for key, cfg in raw.items():
            try:
                ch_id = int(key)
                parsed[ch_id] = ChannelConfig(
                    channel_id=ch_id,
                    control_type=cfg.get("control_type")
                    or cfg.get("type")
                    or "unipolar",
                    device_path=cfg["device_path"],
                    control_code=int(cfg["control_code"]),
                )
            except Exception as e:
                print(f"ModelRepository: skipping channel {key}: {e}")
        return Model(
            name=name,
            channels=parsed,
            processors=processors_cfg,
            model_id=model_id,
            rx_num=rx_num,
            model_index=model_index,
        )
