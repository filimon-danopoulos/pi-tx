import json, uuid
from pi_tx.tools import create_model as cm
from pi_tx.config.settings import MODELS_DIR


def test_allocate_model_index_sequential(tmp_path, monkeypatch):
    # Redirect MODELS_DIR to tmp_path/models
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(cm, "MODELS_DIR", models_dir)

    # Create three models with non-sequential existing indices (1,2,4)
    existing = [
        {
            "name": "m1",
            "model_id": uuid.uuid4().hex,
            "rx_num": 0,
            "model_index": 1,
            "channels": {},
        },
        {
            "name": "m2",
            "model_id": uuid.uuid4().hex,
            "rx_num": 1,
            "model_index": 2,
            "channels": {},
        },
        {
            "name": "m3",
            "model_id": uuid.uuid4().hex,
            "rx_num": 2,
            "model_index": 4,
            "channels": {},
        },
    ]
    for m in existing:
        with open(models_dir / f"{m['name']}.json", "w") as f:
            json.dump(m, f)

    names = [m["name"] for m in existing]
    next_idx = cm.allocate_model_index(names)
    assert next_idx == 3  # should fill the gap

    # Add model with index 3 and expect next index 5
    with open(models_dir / "m4.json", "w") as f:
        json.dump(
            {
                "name": "m4",
                "model_id": uuid.uuid4().hex,
                "rx_num": 3,
                "model_index": 3,
                "channels": {},
            },
            f,
        )
    names.append("m4")
    assert cm.allocate_model_index(names) == 5