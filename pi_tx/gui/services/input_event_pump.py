from __future__ import annotations
from typing import Callable, Dict, Iterable, Tuple
from ...domain.value_store import value_store
from ...logging_config import get_logger


class InputEventPump:
    """Polls the InputController queue and batches updates to the channel store.

    Decouples input draining from the Kivy App so it can be unit-tested and
    potentially replaced (e.g. alternate scheduling or headless mode).
    """

    def __init__(
        self,
        input_controller,
        set_many: Callable[[Dict[int, float]], None],
    ):
        self._input = input_controller
        self._set_many = set_many
        self._log = get_logger(__name__)

    def tick(self, *_):
        """Drain queued input events, keeping only latest per channel, then update store."""
        if not self._input:
            return
        last: Dict[int, float] = {}
        try:
            for (
                ch_id,
                value,
            ) in self._input.pop_events():  # expects iterable of (int,float)
                last[ch_id] = value
        except Exception as e:  # pragma: no cover (defensive)
            self._log.warning("Failed reading events: %s", e)
            return
        if not last:
            return
        try:
            # Update both channel_store and value_store in batch
            # (both stores already implement efficient batching internally)
            self._set_many(last)
            value_store.set_many(last)
        except Exception as e:  # pragma: no cover
            self._log.warning("Failed applying events: %s", e)

    def start_input(self):  # convenience passthrough
        try:
            if self._input:
                self._input.start()
        except Exception as e:  # pragma: no cover
            self._log.warning("Failed to start input controller: %s", e)
