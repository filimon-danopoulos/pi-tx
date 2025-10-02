"""Base classes for model processors.

Processors transform channel values through various operations like
reversing, clamping, differential mixing, and aggregation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


class Processor(ABC):
    """Base class for channel value processors.
    
    Processors can be chained to transform channel values in sequence.
    Each processor receives a list of channel values and returns a
    transformed list.
    """
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert processor configuration to dictionary format.
        
        Returns a dictionary that can be used in the processors configuration
        of a Model's processors field.
        """
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """Return the processor type identifier."""
        pass


@dataclass
class ReverseProcessor(Processor):
    """Reverses polarity of specified channels.
    
    For bipolar channels: value becomes -value
    For unipolar channels: value becomes 1.0 - value
    
    Attributes:
        channels: Dict mapping channel IDs to boolean reverse flags
    """
    channels: Dict[int, bool]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Model.processors['reverse']."""
        return {f"ch{ch_id}": reversed_flag 
                for ch_id, reversed_flag in self.channels.items()}
    
    def get_type(self) -> str:
        return "reverse"
    
    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> ReverseProcessor:
        """Create ReverseProcessor from dict with 'ch1', 'ch2', etc. keys."""
        channels = {}
        for key, val in data.items():
            if isinstance(key, str) and key.startswith("ch"):
                ch_id = int(key[2:])
                channels[ch_id] = bool(val)
        return cls(channels=channels)


@dataclass
class EndpointProcessor(Processor):
    """Clamps channel values to min/max ranges.
    
    Each channel can have custom min/max endpoints. Values are clamped
    to stay within the specified range.
    
    Attributes:
        endpoints: Dict mapping channel IDs to (min, max) tuples
    """
    endpoints: Dict[int, tuple[float, float]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Model.processors['endpoints']."""
        return {
            f"ch{ch_id}": {"min": min_val, "max": max_val}
            for ch_id, (min_val, max_val) in self.endpoints.items()
        }
    
    def get_type(self) -> str:
        return "endpoints"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, float]]) -> EndpointProcessor:
        """Create EndpointProcessor from dict with 'ch1': {'min': x, 'max': y} format."""
        endpoints = {}
        for key, rng in data.items():
            if isinstance(key, str) and key.startswith("ch") and isinstance(rng, dict):
                ch_id = int(key[2:])
                min_val = float(rng.get("min", -1.0))
                max_val = float(rng.get("max", 1.0))
                endpoints[ch_id] = (min_val, max_val)
        return cls(endpoints=endpoints)


@dataclass
class DifferentialMix:
    """Configuration for a single differential mix operation.
    
    Differential mixing combines two channels (left and right) to produce
    new left/right values that represent the sum and difference:
    - left_out = left + right
    - right_out = right - left
    Both values are scaled to prevent overflow.
    
    Attributes:
        left: Channel ID for left input
        right: Channel ID for right input
        inverse: If True, swap the output channels
    """
    left: int
    right: int
    inverse: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "left": f"ch{self.left}",
            "right": f"ch{self.right}",
            "inverse": self.inverse
        }


@dataclass
class DifferentialProcessor(Processor):
    """Applies differential mixing to channel pairs.
    
    Differential mixing is useful for converting stick inputs to
    differential drive outputs (like tank steering).
    
    Attributes:
        mixes: List of differential mix configurations
    """
    mixes: List[DifferentialMix]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Model.processors['differential']."""
        return [mix.to_dict() for mix in self.mixes]
    
    def get_type(self) -> str:
        return "differential"
    
    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> DifferentialProcessor:
        """Create DifferentialProcessor from list of mix configurations."""
        mixes = []
        for mix_cfg in data:
            if not isinstance(mix_cfg, dict):
                continue
            left_raw = mix_cfg.get("left")
            right_raw = mix_cfg.get("right")
            if isinstance(left_raw, str) and left_raw.startswith("ch"):
                left = int(left_raw[2:])
            else:
                continue
            if isinstance(right_raw, str) and right_raw.startswith("ch"):
                right = int(right_raw[2:])
            else:
                continue
            inverse = bool(mix_cfg.get("inverse", False))
            mixes.append(DifferentialMix(left=left, right=right, inverse=inverse))
        return cls(mixes=mixes)


@dataclass
class AggregateChannel:
    """Configuration for a single channel in an aggregate mix.
    
    Attributes:
        channel_id: The channel ID to read from
        weight: Weight factor (0.0 to 1.0) to apply to this channel's absolute value
    """
    channel_id: int
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": f"ch{self.channel_id}",
            "value": self.weight
        }


@dataclass
class AggregateMix:
    """Configuration for a single aggregate mix operation.
    
    Aggregate mixing takes absolute values from multiple channels,
    applies weights, sums them, and writes the clamped result (0..1)
    to a target channel.
    
    Attributes:
        channels: List of source channels with weights
        target: Target channel ID (if None, uses first source channel)
    """
    channels: List[AggregateChannel]
    target: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "channels": [ch.to_dict() for ch in self.channels]
        }
        if self.target is not None:
            result["target"] = f"ch{self.target}"
        return result


@dataclass
class AggregateProcessor(Processor):
    """Aggregates multiple channel values into target channels.
    
    Useful for creating composite channels, such as a sound mix that
    combines multiple input channels into a single output.
    
    Attributes:
        mixes: List of aggregate mix configurations
    """
    mixes: List[AggregateMix]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for Model.processors['aggregate']."""
        return [mix.to_dict() for mix in self.mixes]
    
    def get_type(self) -> str:
        return "aggregate"
    
    @classmethod
    def from_dict(cls, data: List[Dict[str, Any]]) -> AggregateProcessor:
        """Create AggregateProcessor from list of mix configurations."""
        mixes = []
        for mix_cfg in data:
            if not isinstance(mix_cfg, dict):
                continue
            ch_entries = mix_cfg.get("channels") or []
            channels = []
            for entry in ch_entries:
                if isinstance(entry, dict):
                    ch_id = entry.get("id") or entry.get("ch") or entry.get("channel")
                    if ch_id is None:
                        continue
                    if isinstance(ch_id, str) and ch_id.startswith("ch"):
                        cid = int(ch_id[2:])
                    else:
                        continue
                    weight = float(entry.get("value", 1.0))
                    weight = max(0.0, min(1.0, weight))  # Clamp to 0..1
                    channels.append(AggregateChannel(channel_id=cid, weight=weight))
            
            target_raw = mix_cfg.get("target")
            target: Optional[int] = None
            if target_raw is not None:
                if isinstance(target_raw, str) and target_raw.startswith("ch"):
                    target = int(target_raw[2:])
            
            if channels:
                mixes.append(AggregateMix(channels=channels, target=target))
        return cls(mixes=mixes)
