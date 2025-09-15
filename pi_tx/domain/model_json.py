from __future__ import annotations

import uuid
from typing import Any, Dict
from dataclasses import dataclass, field

# Core data structures kept here so parsing module can be imported standalone


@dataclass(frozen=True)
class ChannelConfig:
    channel_id: int
    control_type: str
    device_path: str
    control_code: str  # may be numeric string or symbolic (e.g. 'virtual')
    device_name: str = ""  # Human-readable device name
    control_name: str = ""  # Human-readable control name


@dataclass
class Model:
    name: str
    channels: Dict[int, ChannelConfig]
    processors: Dict[str, Any] = field(default_factory=dict)
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    rx_num: int = 0
    model_index: int = 0
    bind_timestamp: str = ""  # ISO timestamp when model was last bound


def parse_model_dict(name: str, data: Dict[str, Any]) -> Model:
    """Create a Model from raw loaded JSON dict.

    Tolerant of missing/invalid fields; silently skips bad channels.
    """
    raw = data.get("channels", {}) or {}
    processors_cfg = data.get("processors", {}) or {}
    model_id = data.get("model_id") or uuid.uuid4().hex
    bind_timestamp = data.get("bind_timestamp", "")
    # model_index & rx_num normalization
    model_index_raw = data.get("model_index")
    try:
        model_index = int(model_index_raw)
    except Exception:
        model_index = 0
    rx_raw = data.get("rx_num")
    try:
        rx_num = int(rx_raw)
    except Exception:
        rx_num = 0
    if rx_num < 0:
        rx_num = 0
    if rx_num > 15:
        rx_num = 15

    parsed: Dict[int, ChannelConfig] = {}
    for key, cfg in raw.items():
        try:
            # Expect ch1 format only
            if isinstance(key, str) and key.startswith("ch"):
                ch_id = int(key[2:])
            else:
                raise ValueError(
                    f"Invalid channel key format {key}, expected 'ch1' format"
                )
            ctrl_code_raw = cfg.get("control_code")
            if ctrl_code_raw is None:
                raise ValueError("missing control_code")
            parsed[ch_id] = ChannelConfig(
                channel_id=ch_id,
                control_type=cfg.get("control_type") or cfg.get("type") or "unipolar",
                device_path=cfg.get("device_path", ""),
                control_code=str(ctrl_code_raw),
                device_name=cfg.get("device_name", ""),
                control_name=cfg.get("control_name", ""),
            )
        except Exception as e:
            print(f"ModelParser: skipping channel {key}: {e}")
    return Model(
        name=name,
        channels=parsed,
        processors=processors_cfg,
        model_id=model_id,
        rx_num=rx_num,
        model_index=model_index,
        bind_timestamp=bind_timestamp,
    )
