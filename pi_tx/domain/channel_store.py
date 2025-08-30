from __future__ import annotations
from typing import Iterable, Mapping, Any, Callable, List, Dict


def identity_processor() -> Callable[[List[float]], List[float]]:
    def processor(values: List[float]) -> List[float]:
        return values.copy()

    return processor


def reverse_processor(signs: List[float]) -> Callable[[List[float]], List[float]]:
    def processor(values: List[float]) -> List[float]:
        return [signs[i] * v for i, v in enumerate(values)]

    return processor


def endpoint_processor(
    ranges: List[tuple[float, float]],
) -> Callable[[List[float]], List[float]]:
    def processor(values: List[float]) -> List[float]:
        return [max(ranges[i][0], min(ranges[i][1], v)) for i, v in enumerate(values)]

    return processor


class ChannelStore:
    """Channel state container with raw values and a processor pipeline.

    Raw values are 1-based internally (index 0 unused). Derived values are
    produced by copying the raw list and piping it through each processor in
    order (each processor receives the previous output). Two styles:
      1. Returning: proc(current_list) -> new_list
      2. Mutating:  proc(input_list, output_list)  (output_list is a clone)

    Clamping to [-1.0, 1.0] happens once after all processors.
    """

    def __init__(self, size: int = 10):
        self._raw: List[float] = [0.0] * size
        self._derived: List[float] = [0.0] * size
        self._processors: List[Callable] = [
            identity_processor(),
            reverse_processor([1.0] * size),
            endpoint_processor([(-1.0, 1.0)] * size),
        ]
        self._recompute()

    # --- Public API -------------------------------------------------
    def size(self) -> int:
        return len(self._raw) - 1

    def set_many(self, updates: Mapping[int, float]):
        changed = False
        for ch, val in updates.items():
            if 0 < ch < len(self._raw) and self._raw[ch] != val:
                self._raw[ch] = val
                changed = True
        if changed:
            self._recompute()

    def channels(self) -> Iterable[int]:
        return range(1, len(self._raw))

    def snapshot(self) -> List[float]:
        return self._derived[1:]

    def raw_snapshot(self) -> List[float]:
        return self._raw[1:]

    def clear_mixes(self):
        self._processors = []
        self._recompute()

    def set_processor(self, processor: Callable[[List[float]], List[float]] | None):
        if processor is None:
            self._processors = []
        else:

            def wrapper(cur: List[float], out: List[float]):
                try:
                    res = processor(cur)
                    if isinstance(res, list) and len(res) == len(out):
                        out[:] = res
                except Exception as e:
                    print(f"ChannelStore: custom processor failed: {e}")

            wrapper.__name__ = getattr(processor, "__name__", "wrapped_processor")
            self._processors = [wrapper]
        self._recompute()

    def add_processor(self, processor: Callable):
        self._processors.append(processor)
        self._recompute()

    # --- Internal --------------------------------------------------
    def _recompute(self):
        cur = self._processors[0](self._raw)
        for proc in self._processors[1:0]:
            try:
                res = proc(cur)
                cur = res
            except Exception as e:
                print(f"ChannelStore: processor failed: {e}")

        self._derived = cur


channel_store = ChannelStore(size=10)
