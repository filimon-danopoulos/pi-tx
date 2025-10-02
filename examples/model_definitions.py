"""Example model definitions demonstrating Python-based model configuration.

These examples show how to define models entirely in Python code,
without relying on JSON files.
"""
from pi_tx.domain.model_builder import ModelBuilder
from pi_tx.domain.model_json import Model
from pi_tx.domain.channel import (
    BipolarChannel,
    UnipolarChannel,
    LatchingButtonChannel,
    VirtualChannel,
)
from pi_tx.domain.processors import (
    ReverseProcessor,
    EndpointProcessor,
    DifferentialProcessor,
    DifferentialMix,
    AggregateProcessor,
    AggregateMix,
    AggregateChannel,
)


class D6TModel:
    """Example model based on the cat_d6t.json configuration.
    
    This demonstrates a dual-stick setup with differential mixing
    for tank steering and an aggregate channel for sound mixing.
    
    The model can be instantiated and customized:
        model = D6TModel().build()
        
    Or subclassed for variations:
        class MyD6T(D6TModel):
            def customize_builder(self, builder):
                super().customize_builder(builder)
                builder.set_rx_num(2)
                return builder
    """
    
    # Default device paths - can be overridden in subclasses
    STICK_1_PATH = "/dev/input/by-path/pci-0000:00:14.0-usb-0:3:1.0-event-joystick"
    STICK_2_PATH = "/dev/input/by-path/pci-0000:00:14.0-usb-0:2:1.0-event-joystick"
    DEVICE_NAME = "Thrustmaster T.16000M"
    
    def __init__(self):
        """Initialize the D6T model configuration."""
        self.name = "cat_d6t"
        self.model_id = "f2f9b6c8c2e44d3d8947e7d6b8c6e5ab"
        self.rx_num = 1
    
    def create_channels(self):
        """Create the channel configuration.
        
        Returns:
            List of Channel instances
        """
        return [
            # Stick 1 (right stick)
            BipolarChannel(
                channel_id=1,
                device_path=self.STICK_1_PATH,
                control_code="1",
                device_name=self.DEVICE_NAME,
                control_name="stick-y"
            ),
            BipolarChannel(
                channel_id=2,
                device_path=self.STICK_1_PATH,
                control_code="0",
                device_name=self.DEVICE_NAME,
                control_name="stick-x"
            ),
            # Stick 2 (left stick)
            BipolarChannel(
                channel_id=3,
                device_path=self.STICK_2_PATH,
                control_code="1",
                device_name=self.DEVICE_NAME,
                control_name="stick-y"
            ),
            BipolarChannel(
                channel_id=4,
                device_path=self.STICK_2_PATH,
                control_code="0",
                device_name=self.DEVICE_NAME,
                control_name="stick-x"
            ),
            # Hat switch
            BipolarChannel(
                channel_id=5,
                device_path=self.STICK_1_PATH,
                control_code="17",
                device_name=self.DEVICE_NAME,
                control_name="hat-y"
            ),
            # Button
            LatchingButtonChannel(
                channel_id=6,
                device_path=self.STICK_1_PATH,
                control_code="289",
                device_name=self.DEVICE_NAME,
                control_name="sb-2"
            ),
            # Virtual channel for sound mix
            VirtualChannel(
                channel_id=7,
                control_name="sound-mix",
                control_type="unipolar"
            ),
        ]
    
    def create_processors(self):
        """Create the processor configuration.
        
        Returns:
            List of Processor instances
        """
        return [
            # Reverse certain channels
            ReverseProcessor(channels={
                1: True,
                2: False,
                3: True,
                4: False,
                5: True,
                6: False,
                7: True,
                8: False,
            }),
            
            # Set endpoint ranges for specific channels
            EndpointProcessor(endpoints={
                1: (-0.80, 0.90),
                2: (-1.00, 1.00),
                3: (-0.50, 0.70),
                7: (0.00, 1.00),
            }),
            
            # Differential mixing for tank steering
            DifferentialProcessor(mixes=[
                DifferentialMix(left=2, right=1, inverse=True),
                DifferentialMix(left=4, right=3, inverse=False),
            ]),
            
            # Aggregate channels 1-4 into channel 7 (sound mix)
            AggregateProcessor(mixes=[
                AggregateMix(
                    channels=[
                        AggregateChannel(channel_id=1, weight=0.2),
                        AggregateChannel(channel_id=2, weight=0.2),
                        AggregateChannel(channel_id=3, weight=0.4),
                        AggregateChannel(channel_id=4, weight=0.4),
                    ],
                    target=7
                )
            ]),
        ]
    
    def customize_builder(self, builder: ModelBuilder) -> ModelBuilder:
        """Hook for subclasses to customize the builder.
        
        Args:
            builder: The ModelBuilder instance
            
        Returns:
            The modified builder (for chaining)
        """
        return builder
    
    def build(self) -> Model:
        """Build and return the Model instance.
        
        Returns:
            Configured Model instance
        """
        builder = ModelBuilder(self.name)
        builder.set_model_id(self.model_id)
        builder.set_rx_num(self.rx_num)
        
        # Add channels
        for channel in self.create_channels():
            builder.add_channel(channel)
        
        # Add processors
        for processor in self.create_processors():
            builder.add_processor(processor)
        
        # Allow customization
        builder = self.customize_builder(builder)
        
        return builder.build()


class SimpleModel:
    """A minimal example model with just two channels.
    
    Demonstrates the simplest possible model definition.
    """
    
    def __init__(self, name: str = "simple"):
        self.name = name
    
    def build(self) -> Model:
        """Build a simple 2-channel model."""
        return (ModelBuilder(self.name)
                .add_channel(BipolarChannel(
                    channel_id=1,
                    device_path="/dev/input/js0",
                    control_code="0",
                    device_name="Joystick",
                    control_name="X-axis"
                ))
                .add_channel(BipolarChannel(
                    channel_id=2,
                    device_path="/dev/input/js0",
                    control_code="1",
                    device_name="Joystick",
                    control_name="Y-axis"
                ))
                .set_rx_num(0)
                .build())


class CustomD6TModel(D6TModel):
    """Example of customizing the D6T model through subclassing.
    
    This variant uses different device paths and receiver number.
    """
    
    STICK_1_PATH = "/dev/input/by-id/usb-Thrustmaster_T.16000M-event-joystick"
    STICK_2_PATH = "/dev/input/by-id/usb-Thrustmaster_TWCS_Throttle-event-joystick"
    
    def __init__(self):
        super().__init__()
        self.name = "custom_d6t"
        self.rx_num = 2
    
    def customize_builder(self, builder: ModelBuilder) -> ModelBuilder:
        """Add an extra virtual channel."""
        builder = super().customize_builder(builder)
        builder.add_channel(VirtualChannel(
            channel_id=8,
            control_name="extra-virtual",
            control_type="unipolar"
        ))
        return builder
