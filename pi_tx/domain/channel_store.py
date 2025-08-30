from __future__ import annotations
from typing import Dict, Iterable, Mapping


class ChannelStore:
    def __init__(self, size: int = 10):
        self._values = [0.0] * (size + 1)

    def size(self) -> int:
        return len(self._values) - 1

    def _apply(self, channel_id: int, value: float):
        if self._values[channel_id] != value:
            self._values[channel_id] = value

    # No listener dispatch; UI polls; no threading queue now

    # --- Batch API -------------------------------------------------
    def set_many(self, updates: Mapping[int, float]):
        """Apply a batch of channel updates (synchronous, single-thread use)."""
        for ch, val in updates.items():
            if 0 < ch < len(self._values):
                self._apply(ch, val)

    # Listener management removed (polling model)

    def channels(self) -> Iterable[int]:
        return (i for i in range(1, len(self._values)))

    def snapshot(self) -> list[float]:
        """Return channel values as a list in channel order (channel 1 at index 0)."""
        return self._values[1:]


channel_store = ChannelStore(size=10)
