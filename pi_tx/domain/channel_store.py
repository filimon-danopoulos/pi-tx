from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping
from ..logging_config import get_logger


class ChannelStore:
    def __init__(self, size: int = 10):
        self._raw: List[float] = [0.0] * size
        self._derived: List[float] = [0.0] * size
        self._reverse_flags: List[bool] = [False] * size
        self._channel_types: List[str] = ["unipolar"] * size
        self._endpoint_ranges: List[tuple[float, float]] = [(-1.0, 1.0)] * size
        self._differential_mixes: List[tuple[int, int, bool]] = []
        # aggregate mixes: list of ( [(ch_id, weight), ...], target_index_or_None )
        # Each mix aggregates abs(source)*weight (weights 0..1) and stores
        # clamped 0..1 result into target (or first source if no target).
        self._aggregates: List[tuple[List[tuple[int, float]], int | None]] = []
        self._log = get_logger(self.__class__.__name__)
        self._build_pipeline()

    def _build_pipeline(self):
        self._processors: List[Callable[[List[float]], List[float]]] = [
            self._identity_proc,
            self._differential_mix_proc,
            self._aggregate_proc,
            self._reverse_proc,
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
        for left_i, right_i, inv in self._differential_mixes:
            if not (0 <= left_i < size and 0 <= right_i < size):
                continue
            orig_left = out[left_i]
            orig_right = out[right_i]
            left_val = orig_left + orig_right
            right_val = orig_right - orig_left
            scale = max(1.0, abs(left_val), abs(right_val))

            out[right_i if inv else left_i] = left_val / scale
            out[left_i if inv else right_i] = right_val / scale
        return out

    def _aggregate_proc(self, values: List[float]) -> List[float]:
        """Compute configured aggregates (formerly sound mixes).

        For each configured sound mix group we:
          - Take abs of each source channel.
          - Multiply by its specific weight.
          - Sum and clamp to 0..1.
          - Write into target channel or first source if target absent.
        """
        if not self._aggregates:
            return values
        out = values[:]
        size = len(out)
        for chan_weights, target in self._aggregates:
            s = 0.0
            for ch_id, weight in chan_weights:
                idx = ch_id - 1
                if 0 <= idx < size:
                    s += abs(out[idx]) * weight
            if s > 1.0:
                s = 1.0
            tgt = (
                target
                if target is not None
                else (chan_weights[0][0] if chan_weights else None)
            )
            if tgt is not None:
                t_idx = tgt - 1
                if 0 <= t_idx < size:
                    out[t_idx] = s
        return out

    def configure_processors(self, processors_cfg: Dict[str, Any] | None):
        if not processors_cfg:
            return
        rev = processors_cfg.get("reverse") or {}
        for key, val in rev.items():
            try:
                # Expect ch1 format only
                if isinstance(key, str) and key.startswith("ch"):
                    idx = int(key[2:]) - 1
                    if 0 <= idx < len(self._reverse_flags) and isinstance(val, bool):
                        self._reverse_flags[idx] = val
                else:
                    self._log.debug("Invalid reverse key format", extra={"key": key})
            except Exception as e:
                self._log.debug(
                    "Bad reverse entry", extra={"key": key, "error": str(e)}
                )
        diff_cfg = processors_cfg.get("differential")
        if isinstance(diff_cfg, list):
            parsed: List[tuple[int, int, bool]] = []
            for m in diff_cfg:
                if not isinstance(m, dict):
                    continue
                try:
                    # Expect ch1 format only
                    left_raw = m.get("left")
                    right_raw = m.get("right")

                    if isinstance(left_raw, str) and left_raw.startswith("ch"):
                        left = int(left_raw[2:]) - 1
                    else:
                        raise ValueError(
                            f"Invalid left format {left_raw}, expected 'ch1' format"
                        )

                    if isinstance(right_raw, str) and right_raw.startswith("ch"):
                        right = int(right_raw[2:]) - 1
                    else:
                        raise ValueError(
                            f"Invalid right format {right_raw}, expected 'ch1' format"
                        )

                    inverse = bool(m.get("inverse", False))
                    parsed.append((left, right, inverse))
                except Exception:
                    continue
            self._differential_mixes = parsed
        # aggregate configuration supports per-channel weights; accepts legacy key 'sound_mix'
        sm_cfg = processors_cfg.get("aggregate") or processors_cfg.get("sound_mix")
        if isinstance(sm_cfg, list):
            sm_parsed: List[tuple[List[tuple[int, float]], int | None]] = []
            for m in sm_cfg:
                if not isinstance(m, dict):
                    continue
                try:
                    ch_entries = m.get("channels") or []
                    top_weight = m.get("value")  # legacy uniform multiplier
                    chan_weights: List[tuple[int, float]] = []
                    for entry in ch_entries:
                        if isinstance(entry, dict):
                            ch_id = (
                                entry.get("id")
                                or entry.get("ch")
                                or entry.get("channel")
                            )
                            if ch_id is None:
                                continue
                            # Expect ch1 format only
                            if isinstance(ch_id, str) and ch_id.startswith("ch"):
                                cid = int(ch_id[2:])
                            else:
                                raise ValueError(
                                    f"Invalid channel ID format {ch_id}, expected 'ch1' format"
                                )
                            if cid <= 0:
                                continue
                            w = entry.get("value")
                            weight = float(w) if w is not None else 1.0
                        else:
                            # Expect ch1 format only for direct entries
                            if isinstance(entry, str) and entry.startswith("ch"):
                                cid = int(entry[2:])
                            else:
                                raise ValueError(
                                    f"Invalid channel entry format {entry}, expected 'ch1' format"
                                )
                            if cid <= 0:
                                continue
                            weight = (
                                float(top_weight) if top_weight is not None else 1.0
                            )
                        if weight < 0.0:
                            weight = 0.0
                        if weight > 1.0:
                            weight = 1.0
                        chan_weights.append((cid, weight))
                    target_raw = m.get("target")
                    target_idx: int | None = None
                    if target_raw is not None:
                        # Expect ch1 format only for target
                        if isinstance(target_raw, str) and target_raw.startswith("ch"):
                            target_idx = int(target_raw[2:])
                        else:
                            raise ValueError(
                                f"Invalid target format {target_raw}, expected 'ch1' format"
                            )
                    if chan_weights:
                        sm_parsed.append((chan_weights, target_idx))
                except Exception:
                    continue
            self._aggregates = sm_parsed
        self._build_pipeline()

    def configure_differential_mixes(self, mixes: List[Dict[str, Any]]):
        parsed: List[tuple[int, int, bool]] = []
        for m in mixes:
            try:
                # Expect ch1 format only
                left_raw = m.get("left")
                right_raw = m.get("right")

                if isinstance(left_raw, str) and left_raw.startswith("ch"):
                    s = int(left_raw[2:]) - 1
                else:
                    raise ValueError(
                        f"Invalid left format {left_raw}, expected 'ch1' format"
                    )

                if isinstance(right_raw, str) and right_raw.startswith("ch"):
                    t = int(right_raw[2:]) - 1
                else:
                    raise ValueError(
                        f"Invalid right format {right_raw}, expected 'ch1' format"
                    )

                inv = bool(m.get("inverse", False))
                parsed.append((s, t, inv))
            except Exception as e:
                self._log.debug(
                    "Skipping differential mix",
                    extra={"mix": m, "error": str(e)},
                )
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

    # Note: earlier 'sound_mix_values' accessor removed; aggregate writes into target (or first source).

    def _recompute(self):
        cur = self._raw[:]
        for proc in self._processors:
            try:
                cur = proc(cur)
            except Exception as e:
                self._log.error(
                    "Processor failure",
                    extra={"processor": proc.__name__, "error": str(e)},
                )
        self._derived[:] = cur


channel_store = ChannelStore(size=10)
