"""
Tests for the strongly-typed model classes.
"""

import pytest
from pi_tx.domain.models import (
    Endpoint,
    Channel,
    VirtualControl,
    DifferentialMix,
    AggregateSource,
    AggregateMix,
    Model,
)
from pi_tx.input.mappings.stick_mapping import (
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


class TestChannel:
    """Tests for Channel dataclass."""

    def test_create_basic_channel(self):
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
        ch = Channel(
            id=1,
            control=control,
        )
        assert ch.id == 1
        assert ch.control.name == "stick-y"
        assert ch.control.control_type == ControlType.BIPOLAR
        assert ch.reversed is False
        assert ch.endpoint.min == -1.0
        assert ch.endpoint.max == 1.0

    def test_create_channel_with_all_fields(self):
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
        ch = Channel(
            id=2,
            control=control,
            reversed=True,
            endpoint=Endpoint(min=0.0, max=1.0),
        )
        assert ch.control.name == "throttle"
        assert ch.reversed is True
        assert ch.endpoint.min == 0.0

    def test_invalid_channel_id(self):
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
        with pytest.raises(ValueError, match="Channel ID must be positive"):
            Channel(
                id=0,
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
            Channel(
                id=1,
                control=control,
                endpoint=Endpoint(min=1.0, max=-1.0),
            )


class TestDifferentialMix:
    """Tests for DifferentialMix dataclass."""

    def test_create_differential_mix(self):
        mix = DifferentialMix(left_channel=1, right_channel=2)
        assert mix.left_channel == 1
        assert mix.right_channel == 2
        assert mix.inverse is False

    def test_create_differential_mix_with_inverse(self):
        mix = DifferentialMix(left_channel=1, right_channel=2, inverse=True)
        assert mix.inverse is True

    def test_same_channel_raises_error(self):
        with pytest.raises(ValueError, match="cannot be the same"):
            DifferentialMix(left_channel=1, right_channel=1)

    def test_invalid_left_channel(self):
        with pytest.raises(ValueError, match="left_channel must be positive"):
            DifferentialMix(left_channel=0, right_channel=2)


class TestAggregateSource:
    """Tests for AggregateSource dataclass."""

    def test_create_aggregate_source(self):
        src = AggregateSource(channel_id=1)
        assert src.channel_id == 1
        assert src.weight == 1.0

    def test_create_aggregate_source_with_weight(self):
        src = AggregateSource(channel_id=2, weight=0.5)
        assert src.weight == 0.5

    def test_invalid_weight_too_high(self):
        with pytest.raises(ValueError, match="weight must be in range"):
            AggregateSource(channel_id=1, weight=1.5)

    def test_invalid_weight_negative(self):
        with pytest.raises(ValueError, match="weight must be in range"):
            AggregateSource(channel_id=1, weight=-0.1)


class TestAggregateMix:
    """Tests for AggregateMix dataclass."""

    def test_create_aggregate_mix(self):
        mix = AggregateMix(
            sources=[
                AggregateSource(channel_id=1, weight=0.5),
                AggregateSource(channel_id=2, weight=0.5),
            ]
        )
        assert len(mix.sources) == 2
        assert mix.target_channel is None

    def test_create_aggregate_mix_with_target(self):
        mix = AggregateMix(
            sources=[AggregateSource(channel_id=1)],
            target_channel=3,
        )
        assert mix.target_channel == 3

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
            channels=[
                Channel(
                    id=1,
                    control=control,
                )
            ],
        )
        assert model.name == "test_model"
        assert model.model_id == "abc123"
        assert len(model.channels) == 1
        assert len(model.differential_mixes) == 0
        assert len(model.aggregate_mixes) == 0
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
            channels=[
                Channel(id=1, control=control1),
                Channel(id=2, control=control2),
                Channel(id=3, control=control3),
            ],
            differential_mixes=[
                DifferentialMix(left_channel=1, right_channel=2),
            ],
            aggregate_mixes=[
                AggregateMix(
                    sources=[
                        AggregateSource(channel_id=1, weight=0.5),
                        AggregateSource(channel_id=2, weight=0.5),
                    ],
                    target_channel=3,
                )
            ],
            rx_num=1,
        )
        assert len(model.differential_mixes) == 1
        assert len(model.aggregate_mixes) == 1
        assert model.rx_num == 1

    def test_duplicate_channel_ids_raises_error(self):
        control1 = AxisControl(
            event_code=1, event_type=EventType.ABS, name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        control2 = AxisControl(
            event_code=0, event_type=EventType.ABS, name="stick-x",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        with pytest.raises(ValueError, match="Duplicate channel IDs"):
            Model(
                name="test_model",
                model_id="abc123",
                channels=[
                    Channel(id=1, control=control1),
                    Channel(id=1, control=control2),
                ],
            )

    def test_invalid_differential_mix_reference(self):
        control = AxisControl(
            event_code=1, event_type=EventType.ABS, name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        with pytest.raises(ValueError, match="references invalid channel"):
            Model(
                name="test_model",
                model_id="abc123",
                channels=[
                    Channel(id=1, control=control),
                ],
                differential_mixes=[
                    DifferentialMix(left_channel=1, right_channel=99),
                ],
            )

    def test_invalid_aggregate_source_reference(self):
        control = AxisControl(
            event_code=1, event_type=EventType.ABS, name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        with pytest.raises(ValueError, match="references invalid channel"):
            Model(
                name="test_model",
                model_id="abc123",
                channels=[
                    Channel(id=1, control=control),
                ],
                aggregate_mixes=[
                    AggregateMix(
                        sources=[AggregateSource(channel_id=99)],
                    )
                ],
            )

    def test_invalid_aggregate_target_reference(self):
        control = AxisControl(
            event_code=1, event_type=EventType.ABS, name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        with pytest.raises(ValueError, match="target channel.*is invalid"):
            Model(
                name="test_model",
                model_id="abc123",
                channels=[
                    Channel(id=1, control=control),
                ],
                aggregate_mixes=[
                    AggregateMix(
                        sources=[AggregateSource(channel_id=1)],
                        target_channel=99,
                    )
                ],
            )

    def test_invalid_rx_num(self):
        control = AxisControl(
            event_code=1, event_type=EventType.ABS, name="stick-y",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        with pytest.raises(ValueError, match="rx_num must be in range"):
            Model(
                name="test_model",
                model_id="abc123",
                channels=[
                    Channel(id=1, control=control),
                ],
                rx_num=99,
            )

    def test_get_channel_by_id(self):
        control1 = AxisControl(
            event_code=1, event_type=EventType.ABS, name="elevator",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        control2 = AxisControl(
            event_code=0, event_type=EventType.ABS, name="aileron",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            channels=[
                Channel(id=1, control=control1),
                Channel(id=2, control=control2),
            ],
        )
        ch = model.get_channel_by_id(2)
        assert ch is not None
        assert ch.id == 2
        assert ch.control.name == "aileron"

        ch_not_found = model.get_channel_by_id(99)
        assert ch_not_found is None

    def test_get_channel_by_name(self):
        control1 = AxisControl(
            event_code=1, event_type=EventType.ABS, name="elevator",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        control2 = AxisControl(
            event_code=0, event_type=EventType.ABS, name="aileron",
            control_type=ControlType.BIPOLAR,
            min_value=0, max_value=255, fuzz=0, flat=15,
        )
        model = Model(
            name="test_model",
            model_id="abc123",
            channels=[
                Channel(id=1, control=control1),
                Channel(id=2, control=control2),
            ],
        )
        ch = model.get_channel_by_name("aileron")
        assert ch is not None
        assert ch.id == 2

        ch_not_found = model.get_channel_by_name("nonexistent")
        assert ch_not_found is None
