import json, uuid, os
from pi_tx.domain.model_json import parse_model_dict
from pi_tx.domain.model_repo import ModelRepository
from pi_tx.infrastructure.persistence import read_last_model, write_last_model


def test_parse_model_dict_basic_and_channel_skip(tmp_path):
    data = {
        "model_id": uuid.uuid4().hex,
        "rx_num": 20,  # will be clamped to 15
        "model_index": "3",
        "channels": {
            "1": {
                "control_type": "unipolar",
                "device_path": "/dev/js0",
                "control_code": 0,
            },
            "bad": {
                "control_type": "bipolar",
                "device_path": "x",
            },  # missing control_code -> skipped
            "2": {"type": "bipolar", "device_path": "/dev/js0", "control_code": "X"},
        },
        "processors": {"aggregate": [{"channels": [1, 2], "target": 2}]},
    }
    m = parse_model_dict("demo", data)
    assert m.name == "demo"
    assert m.rx_num == 15  # clamped
    assert m.model_index == 3
    # channel 1 and 2 present; 'bad' skipped
    assert set(m.channels.keys()) == {1, 2}
    assert m.channels[2].control_type == "bipolar"
    assert m.processors["aggregate"][0]["target"] == 2


def test_model_repository_list_and_load(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    cfg = {
        "channels": {
            "1": {"control_type": "unipolar", "device_path": "", "control_code": 0}
        },
        "processors": {},
    }
    with open(models_dir / "a.json", "w") as f:
        json.dump(cfg, f)
    with open(models_dir / "b.json", "w") as f:
        json.dump(cfg, f)
    repo = ModelRepository(str(models_dir))
    names = repo.list_models()
    assert names == ["a", "b"]
    m = repo.load_model("a")
    assert 1 in m.channels


def test_repository_missing_file_returns_empty(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    repo = ModelRepository(str(models_dir))
    m = repo.load_model("nope")
    assert m.name == "nope" and m.channels == {}


def test_persistence_round_trip(tmp_path, monkeypatch):
    # Redirect LAST_MODEL_FILE to tmp dir
    from pi_tx.config import settings
    import importlib
    from pi_tx.infrastructure import persistence as persistence_mod

    test_file = tmp_path / ".last_model"
    monkeypatch.setattr(settings, "LAST_MODEL_FILE", test_file, raising=False)
    # remove if any pre-existing file linked (safety)
    if test_file.exists():
        test_file.unlink()
    # Reload persistence so it sees patched settings
    importlib.reload(persistence_mod)
    assert read_last_model() is None
    write_last_model("model1")
    assert read_last_model() == "model1"
    # Overwrite with whitespace only -> should read back None
    test_file.write_text(" \n\n ")
    assert read_last_model() is None


def test_legacy_sound_mix_key_still_supported(tmp_path):
    # Ensure legacy key 'sound_mix' still parsed as aggregate
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    cfg = {
        "channels": {
            "1": {"control_type": "unipolar", "device_path": "", "control_code": 0}
        },
        "processors": {"sound_mix": [{"channels": [1], "value": 1.0}]},
    }
    with open(models_dir / "legacy.json", "w") as f:
        json.dump(cfg, f)
    repo = ModelRepository(str(models_dir))
    m = repo.load_model("legacy")
    assert "aggregate" in m.processors or "sound_mix" in m.processors
