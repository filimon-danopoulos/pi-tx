from __future__ import annotations

import json
import os
from typing import List

from .model_json import Model, parse_model_dict

MODELS_DIR_DEFAULT = "models"


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
        return parse_model_dict(name, data)
