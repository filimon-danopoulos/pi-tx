import json, uuid
from pi_tx.domain.model_repo import ModelRepository


def test_model_loads_or_generates_id_and_rx_num(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    legacy = {"name": "legacy", "channels": {}, "processors": {}}
    with open(models_dir / "legacy.json", "w") as f:
        json.dump(legacy, f)
    mid = uuid.uuid4().hex
    modern = {
        "name": "modern",
        "model_id": mid,
        "rx_num": 7,
        "channels": {},
        "processors": {},
    }
    with open(models_dir / "modern.json", "w") as f:
        json.dump(modern, f)
    repo = ModelRepository(str(models_dir))
    m1 = repo.load_model("legacy")
    m2 = repo.load_model("modern")
    assert m1.model_id and len(m1.model_id) >= 32
    assert m1.rx_num == 0
    assert m2.model_id == mid
    assert m2.rx_num == 7