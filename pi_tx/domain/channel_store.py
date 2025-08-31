from __future__ import annotations
from typing import Mapping, Any, Callable, List, Dict


class ChannelStore:
    """Channel state container with raw values and a processor pipeline (zero-based)."""

    def __init__(self, size: int = 10):
        self._raw: List[float] = [0.0] * size
        self._derived: List[float] = [0.0] * size
        self._reverse_flags: List[bool] = [False] * size
        self._channel_types: List[str] = ["unipolar"] * size
        self._endpoint_ranges: List[tuple[float, float]] = [(-1.0, 1.0)] * size
        self._differential_mixes: List[tuple[int, int]] = []
        self._build_pipeline()

    def _build_pipeline(self):
        self._processors: List[Callable[[List[float]], List[float]]] = [
            self._identity_proc,
            self._reverse_proc,
            self._differential_mix_proc,
            self._endpoint_proc,
        ]
        self._recompute()

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

    def _differential_mix_proc(self, values: List[float]) -> List[float]:
        if not self._differential_mixes:
            return values
        out = values[:]
        size = len(out)
        for left_i, right_i in self._differential_mixes:
            if not (0 <= left_i < size and 0 <= right_i < size):
                continue
            orig_left = out[left_i]
            orig_right = out[right_i]
            left_val = orig_left + orig_right
            right_val = orig_right - orig_left
            scale = max(1.0, abs(left_val), abs(right_val))
            left_val /= scale
            right_val /= scale
            out[left_i] = left_val
            out[right_i] = right_val
        return out

    def configure_processors(self, processors_cfg: Dict[str, Any] | None):
        if not processors_cfg:
            return
        rev = processors_cfg.get("reverse") or {}
        for key, val in rev.items():
            try:
                idx = int(key) - 1
                if 0 <= idx < len(self._reverse_flags) and isinstance(val, bool):
                    self._reverse_flags[idx] = val
            except Exception as e:
                print(f"ChannelStore: bad reverse entry {key}: {e}")
        diff_cfg = processors_cfg.get("differential")
        if isinstance(diff_cfg, list):
            parsed: List[tuple[int, int]] = []
            for m in diff_cfg:
                if not isinstance(m, dict):
                    continue
                try:
                    left = int(m.get("left")) - 1
                    right = int(m.get("right")) - 1
                    parsed.append((left, right))
                except Exception:
                    continue
            self._differential_mixes = parsed
        self._build_pipeline()

    def configure_differential_mixes(self, mixes: List[Dict[str, int]]):
        parsed: List[tuple[int, int]] = []
        for m in mixes:
            try:
                left = int(m.get("left")) - 1
                right = int(m.get("right")) - 1
                parsed.append((left, right))
            except Exception:
                continue
        self._differential_mixes = parsed
        self._build_pipeline()

    def configure_channel_types(self, channel_types: Dict[int, str]):
        for ch_id, t in channel_types.items():
            idx = ch_id - 1
            if 0 <= idx < len(self._channel_types):
                self._channel_types[idx] = t or "unipolar"

    def size(self) -> int:
        return len(self._raw)

    def set_many(self, updates: Mapping[int, float]):
        changed = False
        for ch, val in updates.items():
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

    def _recompute(self):
        cur = self._raw[:]
        for proc in self._processors:
            try:
                cur = proc(cur)
            except Exception as e:
                print(f"ChannelStore: processor failed: {e}")
        self._derived[:] = cur


channel_store = ChannelStore(size=10)
