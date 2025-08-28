from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
LAST_MODEL_FILE = BASE_DIR / ".last_model"
MAPPINGS_DIR = BASE_DIR / "pi_tx" / "input" / "mappings"
STICK_MAPPING_FILE = MAPPINGS_DIR / "stick_mapping.json"
