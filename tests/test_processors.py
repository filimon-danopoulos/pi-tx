"""Tests for processor classes."""
import pytest
from pi_tx.domain.processors import (
    ReverseProcessor,
    EndpointProcessor,
    DifferentialProcessor,
    DifferentialMix,
    AggregateProcessor,
    AggregateMix,
    AggregateChannel,
)


def test_reverse_processor_to_dict():
    """Test ReverseProcessor converts to dict format correctly."""
    proc = ReverseProcessor(channels={1: True, 2: False, 5: True})
    result = proc.to_dict()
    
    assert result == {"ch1": True, "ch2": False, "ch5": True}
    assert proc.get_type() == "reverse"


def test_reverse_processor_from_dict():
    """Test ReverseProcessor can be created from dict."""
    data = {"ch1": True, "ch2": False, "ch5": True}
    proc = ReverseProcessor.from_dict(data)
    
    assert proc.channels == {1: True, 2: False, 5: True}


def test_endpoint_processor_to_dict():
    """Test EndpointProcessor converts to dict format correctly."""
    proc = EndpointProcessor(endpoints={
        1: (-0.8, 0.9),
        2: (-1.0, 1.0),
        7: (0.0, 1.0),
    })
    result = proc.to_dict()
    
    assert result == {
        "ch1": {"min": -0.8, "max": 0.9},
        "ch2": {"min": -1.0, "max": 1.0},
        "ch7": {"min": 0.0, "max": 1.0},
    }
    assert proc.get_type() == "endpoints"


def test_endpoint_processor_from_dict():
    """Test EndpointProcessor can be created from dict."""
    data = {
        "ch1": {"min": -0.8, "max": 0.9},
        "ch2": {"min": -1.0, "max": 1.0},
    }
    proc = EndpointProcessor.from_dict(data)
    
    assert proc.endpoints[1] == (-0.8, 0.9)
    assert proc.endpoints[2] == (-1.0, 1.0)


def test_differential_mix_to_dict():
    """Test DifferentialMix converts to dict correctly."""
    mix = DifferentialMix(left=2, right=1, inverse=True)
    result = mix.to_dict()
    
    assert result == {"left": "ch2", "right": "ch1", "inverse": True}


def test_differential_processor_to_dict():
    """Test DifferentialProcessor converts to dict format correctly."""
    proc = DifferentialProcessor(mixes=[
        DifferentialMix(left=2, right=1, inverse=True),
        DifferentialMix(left=4, right=3, inverse=False),
    ])
    result = proc.to_dict()
    
    assert len(result) == 2
    assert result[0] == {"left": "ch2", "right": "ch1", "inverse": True}
    assert result[1] == {"left": "ch4", "right": "ch3", "inverse": False}
    assert proc.get_type() == "differential"


def test_differential_processor_from_dict():
    """Test DifferentialProcessor can be created from dict."""
    data = [
        {"left": "ch2", "right": "ch1", "inverse": True},
        {"left": "ch4", "right": "ch3", "inverse": False},
    ]
    proc = DifferentialProcessor.from_dict(data)
    
    assert len(proc.mixes) == 2
    assert proc.mixes[0].left == 2
    assert proc.mixes[0].right == 1
    assert proc.mixes[0].inverse is True
    assert proc.mixes[1].left == 4
    assert proc.mixes[1].right == 3
    assert proc.mixes[1].inverse is False


def test_aggregate_channel_to_dict():
    """Test AggregateChannel converts to dict correctly."""
    ch = AggregateChannel(channel_id=1, weight=0.5)
    result = ch.to_dict()
    
    assert result == {"id": "ch1", "value": 0.5}


def test_aggregate_mix_to_dict():
    """Test AggregateMix converts to dict correctly."""
    mix = AggregateMix(
        channels=[
            AggregateChannel(channel_id=1, weight=0.2),
            AggregateChannel(channel_id=2, weight=0.3),
        ],
        target=7
    )
    result = mix.to_dict()
    
    assert result["target"] == "ch7"
    assert len(result["channels"]) == 2
    assert result["channels"][0] == {"id": "ch1", "value": 0.2}
    assert result["channels"][1] == {"id": "ch2", "value": 0.3}


def test_aggregate_mix_no_target():
    """Test AggregateMix without explicit target."""
    mix = AggregateMix(
        channels=[AggregateChannel(channel_id=1, weight=0.5)]
    )
    result = mix.to_dict()
    
    assert "target" not in result
    assert len(result["channels"]) == 1


def test_aggregate_processor_to_dict():
    """Test AggregateProcessor converts to dict format correctly."""
    proc = AggregateProcessor(mixes=[
        AggregateMix(
            channels=[
                AggregateChannel(channel_id=1, weight=0.2),
                AggregateChannel(channel_id=2, weight=0.2),
            ],
            target=7
        )
    ])
    result = proc.to_dict()
    
    assert len(result) == 1
    assert result[0]["target"] == "ch7"
    assert len(result[0]["channels"]) == 2
    assert proc.get_type() == "aggregate"


def test_aggregate_processor_from_dict():
    """Test AggregateProcessor can be created from dict."""
    data = [
        {
            "channels": [
                {"id": "ch1", "value": 0.2},
                {"id": "ch2", "value": 0.3},
            ],
            "target": "ch7"
        }
    ]
    proc = AggregateProcessor.from_dict(data)
    
    assert len(proc.mixes) == 1
    assert len(proc.mixes[0].channels) == 2
    assert proc.mixes[0].channels[0].channel_id == 1
    assert proc.mixes[0].channels[0].weight == 0.2
    assert proc.mixes[0].channels[1].channel_id == 2
    assert proc.mixes[0].channels[1].weight == 0.3
    assert proc.mixes[0].target == 7


def test_aggregate_processor_weight_clamping():
    """Test that weights are clamped to 0..1 range."""
    data = [
        {
            "channels": [
                {"id": "ch1", "value": -0.5},  # Should clamp to 0.0
                {"id": "ch2", "value": 1.5},   # Should clamp to 1.0
            ],
            "target": "ch7"
        }
    ]
    proc = AggregateProcessor.from_dict(data)
    
    assert proc.mixes[0].channels[0].weight == 0.0
    assert proc.mixes[0].channels[1].weight == 1.0
