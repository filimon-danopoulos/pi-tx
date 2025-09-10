from __future__ import annotations

import os
import pytest

# Use mock window to avoid needing a real display
os.environ.setdefault("KIVY_WINDOW", "mock")

try:
    from pi_tx.ui.components.channel_panel import ChannelPanel
except (
    BaseException
) as e:  # pragma: no cover - includes SystemExit from Kivy window init
    ChannelPanel = None  # type: ignore
    _import_error = e  # type: ignore
else:
    _import_error = None


def require_panel():
    if ChannelPanel is None:
        pytest.skip(f"ChannelPanel unavailable: {_import_error}")


def test_channel_panel_rebuild_empty():
    require_panel()
    panel = ChannelPanel()
    panel.rebuild({})
    assert panel.rows == {}
    # One child label with text 'No channels configured'
    assert len(panel.children) == 1
    assert hasattr(panel.children[0], "text")
    assert "No channels" in panel.children[0].text


def test_channel_panel_rebuild_and_virtual_detection():
    require_panel()
    mapping = {
        "1": {
            "device_path": "/dev/input/js0",
            "control_code": 5,
            "control_type": "unipolar",
        },
        # virtual due to missing device_path
        "2": {"device_path": None, "control_code": 6, "control_type": "unipolar"},
        # virtual due to non-digit control code
        "3": {
            "device_path": "/dev/input/js0",
            "control_code": "BTN_A",
            "control_type": "button",
        },
    }
    panel = ChannelPanel()
    panel.rebuild(mapping)
    assert set(panel.rows.keys()) == {1, 2, 3}
    # Channel types assigned
    assert panel.rows[1].channel_type == "unipolar"
    assert panel.rows[2].channel_type == "virtual"
    assert panel.rows[3].channel_type == "virtual"


def test_channel_panel_update_values():
    require_panel()
    mapping = {
        "1": {
            "device_path": "/dev/input/js0",
            "control_code": 5,
            "control_type": "bipolar",
        },
        "2": {
            "device_path": "/dev/input/js0",
            "control_code": 6,
            "control_type": "unipolar",
        },
        "3": {
            "device_path": "/dev/input/js0",
            "control_code": 7,
            "control_type": "unipolar",
        },
    }
    panel = ChannelPanel()
    panel.rebuild(mapping)
    snapshot = [0.25, 0.75, 0.0]
    panel.update_values(snapshot)
    assert panel.rows[1].bar.value == 0.25
    assert panel.rows[2].bar.value == 0.75
    assert panel.rows[3].bar.value == 0.0
    # Shorter snapshot: out of range channels should go to 0.0 (row 3 remains 0)
    panel.update_values([0.5])
    assert panel.rows[1].bar.value == 0.5
    assert (
        panel.rows[2].bar.value == 0.75
    )  # unchanged because method clamps but doesn't zero existing if snapshot index missing
    # We can assert behavior: missing indices keep old value (documented by code path)
