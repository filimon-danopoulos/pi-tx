from __future__ import annotations

from pi_tx.ui.services.model_manager import ModelManager


class FakeChannelCfg:
    def __init__(
        self,
        control_type: str,
        device_path: str = "/dev/input/js0",
        control_code: int = 5,
    ):
        self.control_type = control_type
        self.device_path = device_path
        self.control_code = control_code


class FakeModel:
    def __init__(self, name="fake_model"):
        self.name = name
        self.channels = {
            1: FakeChannelCfg("unipolar"),
            2: FakeChannelCfg("bipolar"),
        }
        self.processors = [
            {"type": "reverse", "channels": [2]},
        ]
        self.rx_num = 7
        self.model_id = 55


class FakeRepo:
    def __init__(self, model: FakeModel):
        self._model = model
        self.listed = [model.name]
        self.loaded = []

    def list_models(self):
        return list(self.listed)

    def load_model(self, name: str):  # name ignored
        self.loaded.append(name)
        return self._model


def test_model_manager_load_and_apply(monkeypatch, tmp_path):
    model = FakeModel()
    repo = FakeRepo(model)
    captured_types = {}
    captured_processors = None

    def fake_configure_channel_types(mapping):
        captured_types.update(mapping)

    def fake_configure_processors(specs):
        nonlocal captured_processors
        captured_processors = specs

    mm = ModelManager(models_dir=tmp_path, last_model_file=tmp_path / "last.txt")
    mm._repo = repo  # type: ignore[attr-defined]

    import pi_tx.ui.services.model_manager as mm_mod

    monkeypatch.setattr(
        mm_mod.channel_store, "configure_channel_types", fake_configure_channel_types
    )
    monkeypatch.setattr(
        mm_mod.channel_store, "configure_processors", fake_configure_processors
    )

    loaded_model, mapping = mm.load_and_apply(model.name)
    assert loaded_model is model
    assert set(mapping.keys()) == {"1", "2"}
    assert captured_types == {1: "unipolar", 2: "bipolar"}
    assert captured_processors == model.processors


def test_model_manager_persist_and_autoload(tmp_path):
    model = FakeModel()
    repo = FakeRepo(model)
    last_file = tmp_path / "last_model.txt"
    mm = ModelManager(models_dir=tmp_path, last_model_file=last_file)
    mm._repo = repo  # type: ignore[attr-defined]
    assert mm.autoload_last() is None
    mm.persist_last(model.name)
    assert last_file.read_text().strip() == model.name
    assert mm.autoload_last() == model.name