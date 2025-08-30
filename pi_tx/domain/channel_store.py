from __future__ import annotations
from typing import Iterable, Mapping, Any, Callable, List, Dict


class ChannelStore:
    """Channel state container with raw values and a processor pipeline (zero-based).

    All internal lists are standard zero-based arrays. Processors are pure
    functions returning new lists (identity, reverse, clamp).
    """

    def __init__(self, size: int = 10):
        self._raw: List[float] = [0.0] * size
        self._derived: List[float] = [0.0] * size
        # Reverse flags now booleans (True means apply channel-type dependent inversion)
        self._reverse_flags: List[bool] = [False] * size
        # Channel types: 'bipolar', 'unipolar', 'button', etc. Used for reversal logic
        self._channel_types: List[str] = ["unipolar"] * size
        self._endpoint_ranges: List[tuple[float, float]] = [(-1.0, 1.0)] * size
        self._build_pipeline()

    def _build_pipeline(self):
        self._processors: List[Callable] = [
            self._identity_proc,
            self._reverse_proc,
            self._endpoint_proc,
        ]
        self._recompute()

    # Processor methods ---------------------------------------------
    def _identity_proc(self, values: List[float]) -> List[float]:
        return values[:]

    def _reverse_proc(self, values: List[float]) -> List[float]:

        def reverse_value(i: int, value: float) -> float:
            if not self._reverse_flags[i]:
                return value
            if self._channel_types[i] == "bipolar":
                return -value
            return 1.0 - value

        return [reverse_value(i, value) for i, value in enumerate(values)]

    def _endpoint_proc(self, values: List[float]) -> List[float]:
        return [
            max(
                self._endpoint_ranges[i][0], min(self._endpoint_ranges[i][1], values[i])
            )
            for i in range(len(values))
        ]

    def configure_processors(self, processors_cfg: Dict[str, Any] | None):
        if not processors_cfg:
            return
        rev = processors_cfg.get("reverse") or {}
        for key, val in rev.items():
            try:
                # Reverse mapping channels are 1-based booleans; convert to 0-based index
                idx = int(key) - 1
                if 0 <= idx < len(self._reverse_flags):
                    if isinstance(val, bool):
                        self._reverse_flags[idx] = val
                    else:
                        print(
                            f"ChannelStore: reverse value for channel {key} must be boolean, got {type(val).__name__}; ignoring"
                        )
            except Exception as e:
                print(f"ChannelStore: bad reverse entry {key}: {e}")
        self._build_pipeline()

    def configure_channel_types(self, channel_types: Dict[int, str]):
        """Configure channel types using 1-based channel ids.

        Types influence reversal behavior:
          bipolar: value -> -value when reversed
          unipolar: value (0..1) -> 1 - value when reversed
          button: 0/1 -> 1 - value when reversed
        """
        for ch_id, t in channel_types.items():
            idx = ch_id - 1
            if 0 <= idx < len(self._channel_types):
                self._channel_types[idx] = t or "unipolar"
        # No pipeline rebuild needed (types only consulted during reverse)

    # --- Public API -------------------------------------------------
    def size(self) -> int:
        return len(self._raw)

    def set_many(self, updates: Mapping[int, float]):
        changed = False
        for ch, val in updates.items():
            # Incoming channels are 1-based; internal storage is 0-based
            idx = ch - 1
            if 1 <= ch <= len(self._raw) and self._raw[idx] != val:
                self._raw[idx] = val
                changed = True
        if changed:
            self._recompute()

    def snapshot(self) -> List[float]:
        return self._derived[:]

    def raw_snapshot(self) -> List[float]:
        return self._raw[:]

    def clear_mixes(self):
        self._processors = []
        self._recompute()

    # --- Internal --------------------------------------------------
    def _recompute(self):
        cur = self._raw[:]
        for proc in self._processors:
            try:
                cur = proc(cur)
            except Exception as e:
                print(f"ChannelStore: processor failed: {e}")
        # Assign derived
        self._derived[:] = cur


channel_store = ChannelStore(size=10)
