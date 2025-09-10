from __future__ import annotations

from pi_tx.ui.services.model_selection import ModelSelectionController


class FakeModel:
    def __init__(self, name="m1", rx_num=3, model_id=42):
        self.name = name
        self.rx_num = rx_num
        self.model_id = model_id
        # channels attribute shape mimics real Model for types mapping
        self.channels = {}
        self.processors = []


class FakeModelManager:
    def __init__(self):
        self.persisted = None
        # Provide deterministic mapping: ch1 real, ch2 virtual (no device), ch3 non-digit code (virtual)
        self._mapping = {
            "1": {
                "device_path": "/dev/input/js0",
                "control_code": 5,
                "control_type": "unipolar",
            },
            "2": {"device_path": None, "control_code": 6, "control_type": "unipolar"},
            "3": {
                "device_path": "/dev/input/js0",
                "control_code": "BTN_A",
                "control_type": "button",
            },
        }
        model = FakeModel()
        # Populate channels to exercise channel type configuration path
        for ch_id, cfg in {1: "unipolar", 2: "unipolar", 3: "button"}.items():

            class Cfg:
                def __init__(self, control_type):
                    self.control_type = control_type
                    self.device_path = "/dev/input/js0"
                    self.control_code = 5

            model.channels[ch_id] = Cfg(cfg)
        self._model = model

    def load_and_apply(self, name):  # name ignored for simplicity
        return self._model, self._mapping

    def persist_last(self, name):
        self.persisted = name


class FakeInputController:
    def __init__(self):
        self.cleared = False
        self.mappings = []
        self.started = False

    def clear_values(self):
        self.cleared = True

    def register_channel_mapping(self, device_path, code, ch_id):
        self.mappings.append((device_path, code, ch_id))

    def start(self):
        self.started = True


class FakePanel:
    def __init__(self):
        self.last_mapping = None

    def rebuild(self, mapping):
        self.last_mapping = mapping


class FakeTx:
    def __init__(self):
        self.rx_num = None
        self.model_id = None

    def set_rx_num(self, v):
        self.rx_num = v

    def set_model_id(self, v):
        self.model_id = v


def test_model_selection_applies_and_filters_virtual():
    mgr = FakeModelManager()
    ic = FakeInputController()
    panel = FakePanel()
    tx = FakeTx()

    selector = ModelSelectionController(mgr, ic, panel, uart_resolver=lambda: tx)
    model, mapping = selector.apply_selection("ignored")

    # Panel got full mapping
    assert panel.last_mapping is mapping
    # Input controller only got real channel 1
    assert ic.cleared is True
    assert ic.started is True
    assert ic.mappings == [("/dev/input/js0", 5, 1)]
    # Persistence
    # Persisted value should match the selection argument (controller uses the provided name)
    assert mgr.persisted == "ignored"
    # UART propagation
    assert tx.rx_num == model.rx_num
    assert tx.model_id == model.model_id


def test_model_selection_without_panel():
    mgr = FakeModelManager()
    ic = FakeInputController()
    selector = ModelSelectionController(mgr, ic, None, uart_resolver=lambda: None)
    model, mapping = selector.apply_selection("ignored")
    # Still mapped input
    assert ic.mappings and ic.mappings[0][2] == 1
    # Panel absent so nothing blew up
    assert mapping is not None
