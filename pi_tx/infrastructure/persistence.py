from . import __package__  # noqa: F401
from pathlib import Path
from ..config.settings import LAST_MODEL_FILE


def read_last_model() -> str | None:
    try:
        if LAST_MODEL_FILE.exists():
            return LAST_MODEL_FILE.read_text().strip() or None
    except Exception:
        pass
    return None


def write_last_model(name: str) -> None:
    try:
        LAST_MODEL_FILE.write_text(name.strip())
    except Exception as e:
        print(f"Warning: failed to persist last model: {e}")
