from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple
from ...domain.model_repo import ModelRepository, Model
from ...domain.channel_store import channel_store
from ...config.settings import MODELS_DIR, LAST_MODEL_FILE


class ModelManager:
    """Encapsulates model repository access and applying model configuration.

    Responsibilities:
    - Listing and loading models.
    - Applying channel types & processors to channel_store.
    - Preparing a lightweight mapping structure for UI & input registration.
    - Persisting and restoring last selected model.
    """

    def __init__(self, models_dir=MODELS_DIR, last_model_file=LAST_MODEL_FILE):
        self._repo = ModelRepository(models_dir)
        self._last_model_file = last_model_file

    def list_models(self):
        return self._repo.list_models()

    def load_and_apply(self, model_name: str) -> Tuple[Model, Dict[str, Dict]]:
        model = self._repo.load_model(model_name)
        # Configure channel types first
        try:
            types_map = {
                ch_id: cfg.control_type for ch_id, cfg in model.channels.items()
            }
            channel_store.configure_channel_types(types_map)
        except Exception as e:  # pragma: no cover (defensive)
            print(f"Warning: failed to configure channel types: {e}")
        # Processors
        try:
            channel_store.configure_processors(model.processors)
        except Exception as e:  # pragma: no cover
            print(
                f"Warning: failed to configure processors for model {model_name}: {e}"
            )
        mapping = {
            str(k): {
                "device_path": v.device_path,
                "control_code": v.control_code,
                "control_type": v.control_type,
            }
            for k, v in model.channels.items()
        }
        return model, mapping

    def persist_last(self, model_name: str):
        try:
            with open(self._last_model_file, "w") as f:
                f.write(model_name.strip())
        except Exception as e:  # pragma: no cover
            print(f"Warning: couldn't persist last model: {e}")

    def autoload_last(self):
        try:
            if self._last_model_file.exists():
                name = self._last_model_file.read_text().strip()
                if name and name in self.list_models():
                    return name
        except Exception as e:  # pragma: no cover
            print(f"Warning: failed to read last model: {e}")
        return None
