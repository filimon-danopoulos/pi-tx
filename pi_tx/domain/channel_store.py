from __future__ import annotations
from typing import Iterable, Mapping, Any, Callable, List, Dict


class ChannelStore:
    """Channel state container with raw values and a processor pipeline.

    Raw values are stored as 1-based (index 0 unused) for ergonomic mapping to
    external channel numbers. Derived values are produced by copying the raw
    list (identity) and then applying each processor in order. Processors may
    either mutate the derived list in-place (signature (raw, derived)) or
    return a replacement list (signature (raw) -> list[float]). Clamping to
    [-1.0, 1.0] occurs once after all processors run.
    """

    def __init__(self, size: int = 10):
        self._raw: List[float] = [0.0] * (size + 1)
        self._derived: List[float] = [0.0] * (size + 1)
        self._processors: List[Callable] = []
        self._recompute()

    # --- Public API -------------------------------------------------
    def size(self) -> int:
        return len(self._raw) - 1

    def set_many(self, updates: Mapping[int, float]):
        """Batch update raw channel values then recompute derived state."""
        changed = False
        for ch, val in updates.items():
            if 0 < ch < len(self._raw):
                if self._raw[ch] != val:
                    self._raw[ch] = val
                    changed = True
        if changed:
            self._recompute()

    def channels(self) -> Iterable[int]:
        return (i for i in range(1, len(self._raw)))

    def snapshot(self) -> List[float]:
        return self._derived[1:]

    def raw_snapshot(self) -> List[float]:
        return self._raw[1:]

    # --- Mixing / processors ---------------------------------------
    def configure_mixes(self, mix_configurations: Dict[int | str, Any]):
        """Compile mix rules into a single processor and install it.

        mix_configurations format:
            { target_channel: { 'offset': float,
                                'sources': [ { 'channel': int, 'weight': float }, ... ] } }
        Empty dict removes existing mix processor.
        """
        self._processors = [
            p for p in self._processors if not getattr(p, "__mix_processor__", False)
        ]
        if not mix_configurations:
            self._recompute()
            return

        rules: List[tuple[int, float, list[tuple[int, float]]]] = []
        for target_key, cfg in mix_configurations.items():
            try:
                tgt_idx = int(target_key) - 1
                offset = float(cfg.get("offset", 0.0))
                srcs: list[tuple[int, float]] = []
                for s in cfg.get("sources", []):
                    try:
                        src_idx = int(s.get("channel")) - 1
                        weight = float(s.get("weight", 0.0))
                        srcs.append((src_idx, weight))
                    except Exception as e:
                        print(f"ChannelStore: invalid mix source for {target_key}: {e}")
                rules.append((tgt_idx, offset, srcs))
            except Exception as e:
                print(f"ChannelStore: invalid mix entry {target_key}: {e}")

        def mix_proc(raw_list: List[float], derived_list: List[float]):
            length = len(derived_list)
            for tgt_idx, offset, srcs in rules:
                if not (0 <= tgt_idx < length):
                    continue
                val = offset
                for src_idx, weight in srcs:
                    if 0 <= src_idx < length:
                        val += raw_list[src_idx] * weight
                derived_list[tgt_idx] = val

        setattr(mix_proc, "__mix_processor__", True)
        self._processors.append(mix_proc)
        self._recompute()

    def clear_mixes(self):
        self._processors = [
            p for p in self._processors if not getattr(p, "__mix_processor__", False)
        ]
        self._recompute()

    def set_processor(self, processor: Callable[[List[float]], List[float]] | None):
        """Replace current processors with a single legacy-style processor or none."""
        if processor is None:
            self._processors = []
        else:

            def wrapper(raw_list: List[float], derived_list: List[float]):
                try:
                    result = processor(raw_list)
                    if isinstance(result, list) and len(result) == len(derived_list):
                        for i, v in enumerate(result):
                            derived_list[i] = v
                except Exception as e:
                    print(f"ChannelStore: custom processor failed: {e}")

            wrapper.__name__ = getattr(processor, "__name__", "wrapped_processor")
            self._processors = [wrapper]
        self._recompute()

    def add_processor(self, processor: Callable):
        """Append a processor to the pipeline (mutating or returning style)."""
        self._processors.append(processor)
        self._recompute()

    # --- Internal --------------------------------------------------
    def _recompute(self):
        raw_zero = self._raw[1:]
        derived = raw_zero.copy()
        for proc in self._processors:
            try:
                argcount = getattr(getattr(proc, "__code__", None), "co_argcount", None)
                if argcount and argcount >= 2:
                    proc(raw_zero, derived)
                else:
                    result = proc(raw_zero)
                    if isinstance(result, list) and len(result) == len(derived):
                        derived = result
            except Exception as e:
                print(f"ChannelStore: processor failed: {e}")
        for i, v in enumerate(derived):
            if v > 1.0:
                derived[i] = 1.0
            elif v < -1.0:
                derived[i] = -1.0
        for idx, value in enumerate(derived, start=1):
            self._derived[idx] = value


channel_store = ChannelStore(size=10)
