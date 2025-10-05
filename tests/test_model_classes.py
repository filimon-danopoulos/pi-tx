"""
Tests for the strongly-typed model classes.
"""

import pytest
from pi_tx.domain import (
    Channels,
    Endpoint,
    Value,
    VirtualControl,
    DifferentialMix,
    AggregateSource,
    AggregateMix,
    Model,
)
from pi_tx.domain.stick_mapping import (
    AxisControl,
    ButtonControl,
    EventType,
    ControlType,
)


class TestEndpoint:
    """Tests for Endpoint class."""

    def test_create_default_endpoint(self):
        ep = Endpoint()
        assert ep.min == -1.0
        assert ep.max == 1.0

    def test_create_custom_endpoint(self):
        ep = Endpoint(min=0.0, max=1.0)
        assert ep.min == 0.0
        assert ep.max == 1.0

    def test_invalid_endpoint_range(self):
        with pytest.raises(ValueError, match="min.*must be less than max"):
            Endpoint(min=1.0, max=-1.0)

    def test_clamp_value(self):
        ep = Endpoint(min=-0.5, max=0.5)
        assert ep.clamp(-1.0) == -0.5  # Below min
        assert ep.clamp(1.0) == 0.5  # Above max
        assert ep.clamp(0.0) == 0.0  # Within range


class TestControlType:
    """Tests for ControlType enum."""

    def test_control_type_values(self):
        assert ControlType.UNIPOLAR.value == "unipolar"
        assert ControlType.BIPOLAR.value == "bipolar"
        assert ControlType.BUTTON.value == "button"


class TestValue:
    """Tests for Value dataclass."""

    def test_create_basic_value(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        value = Value(
            name="elevator",
            control=control,
        )
        assert value.name == "elevator"
        assert value.control.name == "stick-y"
        assert value.control.control_type == ControlType.BIPOLAR
        assert value.reversed is False
        assert value.endpoint.min == -1.0
        assert value.endpoint.max == 1.0

    def test_create_value_with_all_fields(self):
        control = AxisControl(
            event_code=0,
            event_type=EventType.ABS,
            name="throttle",
            control_type=ControlType.UNIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        value = Value(
            name="throttle_channel",
            control=control,
            reversed=True,
            endpoint=Endpoint(min=0.0, max=1.0),
        )
        assert value.control.name == "throttle"
        assert value.reversed is True
        assert value.endpoint.min == 0.0

    def test_invalid_value_name(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="Value name must be a non-empty string"):
            Value(
                name="",
                control=control,
            )

    def test_invalid_endpoint(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="min.*must be less than max"):
            Value(
                id=1,
                control=control,
                endpoint=Endpoint(min=1.0, max=-1.0),
            )


class TestDifferentialMix:
    """Tests for DifferentialMix dataclass."""

    def test_create_differential_mix(self):
        mix = DifferentialMix(left_channel="left", right_channel="right")
        assert mix.left_channel == "left"
        assert mix.right_channel == "right"
        assert mix.inverse is False

    def test_create_differential_mix_with_inverse(self):
        mix = DifferentialMix(left_channel="left", right_channel="right", inverse=True)
        assert mix.inverse is True

    def test_same_channel_raises_error(self):
        with pytest.raises(ValueError, match="cannot be the same"):
            DifferentialMix(left_channel="same", right_channel="same")

    def test_invalid_left_value(self):
        with pytest.raises(ValueError, match="left_channel must be a non-empty string"):
            DifferentialMix(left_channel="", right_channel="right")


class TestAggregateSource:
    """Tests for AggregateSource dataclass."""

    def test_create_aggregate_source(self):
        src = AggregateSource(channel_name="ch1")
        assert src.channel_name == "ch1"
        assert src.weight == 1.0

    def test_create_aggregate_source_with_weight(self):
        src = AggregateSource(channel_name="ch2", weight=0.5)
        assert src.weight == 0.5

    def test_invalid_weight_too_high(self):
        with pytest.raises(ValueError, match="weight must be in range"):
            AggregateSource(channel_name="ch1", weight=1.5)

    def test_invalid_weight_negative(self):
        with pytest.raises(ValueError, match="weight must be in range"):
            AggregateSource(channel_name="ch1", weight=-0.1)


class TestAggregateMix:
    """Tests for AggregateMix dataclass."""

    def test_create_aggregate_mix(self):
        mix = AggregateMix(
            sources=[
                AggregateSource(channel_name="ch1", weight=0.5),
                AggregateSource(channel_name="ch2", weight=0.5),
            ]
        )
        assert len(mix.sources) == 2
        assert mix.target_channel is None

    def test_create_aggregate_mix_with_target(self):
        mix = AggregateMix(
            sources=[AggregateSource(channel_name="ch1")],
            target_channel="ch3",
        )
        assert mix.target_channel == "ch3"

    def test_empty_sources_raises_error(self):
        with pytest.raises(ValueError, match="must have at least one source"):
            AggregateMix(sources=[])


class TestModel:
    """Tests for Model dataclass."""

    def test_create_simple_model(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            values=[
                Value(
                    name="ch1",
                    control=control,
                )
            ],
            channels=Channels(),
        )
        assert model.name == "test_model"
        assert model.model_id == "abc123"
        assert len(model.values) == 1
        assert len(model.mixes) == 0
        assert model.rx_num == 0

    def test_create_model_with_mixes(self):
        control1 = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        control2 = AxisControl(
            event_code=0,
            event_type=EventType.ABS,
            name="stick-x",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        control3 = VirtualControl(
            name="virtual",
            control_type=ControlType.UNIPOLAR,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            values=[
                Value(name="ch1", control=control1),
                Value(name="ch2", control=control2),
                Value(name="ch3", control=control3),
            ],
            mixes=[
                DifferentialMix(left_channel="ch1", right_channel="ch2"),
                AggregateMix(
                    sources=[
                        AggregateSource(channel_name="ch1", weight=0.5),
                        AggregateSource(channel_name="ch2", weight=0.5),
                    ],
                    target_channel="ch3",
                ),
            ],
            rx_num=1,
            channels=Channels(),
        )
        assert len(model.mixes) == 2
        assert isinstance(model.mixes[0], DifferentialMix)
        assert isinstance(model.mixes[1], AggregateMix)
        assert model.rx_num == 1

    def test_duplicate_value_names_raises_error(self):
        control1 = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        control2 = AxisControl(
            event_code=0,
            event_type=EventType.ABS,
            name="stick-x",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="Duplicate value names"):
            Model(
                name="test_model",
                model_id="abc123",
                values=[
                    Value(name="duplicate", control=control1),
                    Value(name="duplicate", control=control2),
                ],
                channels=Channels(),
            )

    def test_invalid_differential_mix_reference(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="references invalid channel"):
            Model(
                name="test_model",
                model_id="abc123",
                values=[
                    Value(name="ch1", control=control),
                ],
                channels=Channels(),
                mixes=[
                    DifferentialMix(left_channel="ch1", right_channel="ch99"),
                ],
            )

    def test_invalid_aggregate_source_reference(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="references invalid channel"):
            Model(
                name="test_model",
                model_id="abc123",
                values=[
                    Value(name="ch1", control=control),
                ],
                channels=Channels(),
                mixes=[
                    AggregateMix(
                        sources=[AggregateSource(channel_name="ch99")],
                    ),
                ],
            )

    def test_invalid_aggregate_target_reference(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="target channel.*is invalid"):
            Model(
                name="test_model",
                model_id="abc123",
                values=[
                    Value(name="ch1", control=control),
                ],
                channels=Channels(),
                mixes=[
                    AggregateMix(
                        sources=[AggregateSource(channel_name="ch1")],
                        target_channel="ch99",
                    ),
                ],
            )

    def test_invalid_rx_num(self):
        control = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        with pytest.raises(ValueError, match="rx_num must be in range"):
            Model(
                name="test_model",
                model_id="abc123",
                values=[
                    Value(name="ch1", control=control),
                ],
                rx_num=99,
                channels=Channels(),
            )

    def test_get_value_by_name(self):
        control1 = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="elevator",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        control2 = AxisControl(
            event_code=0,
            event_type=EventType.ABS,
            name="aileron",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            values=[
                Value(name="ch1", control=control1),
                Value(name="ch2", control=control2),
            ],
            channels=Channels(),
        )
        value = model.get_value_by_name("ch2")
        assert value is not None
        assert value.name == "ch2"
        assert value.control.name == "aileron"

        value_not_found = model.get_value_by_name("ch99")
        assert value_not_found is None

    def test_get_value_by_control_name(self):
        control1 = AxisControl(
            event_code=1,
            event_type=EventType.ABS,
            name="elevator",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        control2 = AxisControl(
            event_code=0,
            event_type=EventType.ABS,
            name="aileron",
            control_type=ControlType.BIPOLAR,
            min_value=0,
            max_value=255,
            fuzz=0,
            flat=15,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            values=[
                Value(name="ch1", control=control1),
                Value(name="ch2", control=control2),
            ],
            channels=Channels(),
        )
        value = model.get_value_by_control_name("aileron")
        assert value is not None
        assert value.name == "ch2"

        value_not_found = model.get_value_by_control_name("nonexistent")
        assert value_not_found is None
