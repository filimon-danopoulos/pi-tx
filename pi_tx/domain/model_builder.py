"""Model builder for programmatic model creation.

The ModelBuilder provides a fluent API for constructing models entirely
in Python code, without relying on JSON files.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from .model_json import Model, ChannelConfig
from .channel import Channel
from .processors import (
    Processor,
    ReverseProcessor,
    EndpointProcessor,
    DifferentialProcessor,
    AggregateProcessor,
)


class ModelBuilder:
    """Fluent builder for creating Model instances programmatically.
    
    Example:
        model = (ModelBuilder("my_model")
                .set_rx_num(1)
                .add_channel(BipolarChannel(1, "/dev/input/js0", "0", "Stick", "X"))
                .add_channel(BipolarChannel(2, "/dev/input/js0", "1", "Stick", "Y"))
                .add_processor(ReverseProcessor({1: True}))
                .build())
    """
    
    def __init__(self, name: str):
        """Initialize a new ModelBuilder.
        
        Args:
            name: The model name
        """
        self._name = name
        self._channels: Dict[int, Channel] = {}
        self._processors: List[Processor] = []
        self._rx_num: int = 0
        self._model_id: Optional[str] = None
        self._bind_timestamp: str = ""
    
    def add_channel(self, channel: Channel) -> ModelBuilder:
        """Add a channel to the model.
        
        Args:
            channel: Channel instance to add
            
        Returns:
            Self for method chaining
        """
        self._channels[channel.channel_id] = channel
        return self
    
    def add_channels(self, *channels: Channel) -> ModelBuilder:
        """Add multiple channels to the model.
        
        Args:
            *channels: Variable number of Channel instances
            
        Returns:
            Self for method chaining
        """
        for channel in channels:
            self._channels[channel.channel_id] = channel
        return self
    
    def add_processor(self, processor: Processor) -> ModelBuilder:
        """Add a processor to the model.
        
        Args:
            processor: Processor instance to add
            
        Returns:
            Self for method chaining
        """
        self._processors.append(processor)
        return self
    
    def set_rx_num(self, rx_num: int) -> ModelBuilder:
        """Set the receiver number (0-15).
        
        Args:
            rx_num: Receiver number
            
        Returns:
            Self for method chaining
        """
        self._rx_num = max(0, min(15, rx_num))
        return self
    
    def set_model_id(self, model_id: str) -> ModelBuilder:
        """Set the model ID.
        
        Args:
            model_id: Unique model identifier
            
        Returns:
            Self for method chaining
        """
        self._model_id = model_id
        return self
    
    def set_bind_timestamp(self, timestamp: str) -> ModelBuilder:
        """Set the bind timestamp.
        
        Args:
            timestamp: ISO format timestamp
            
        Returns:
            Self for method chaining
        """
        self._bind_timestamp = timestamp
        return self
    
    def build(self) -> Model:
        """Build and return the Model instance.
        
        Converts all channels and processors to the format expected by
        the Model dataclass.
        
        Returns:
            Configured Model instance
        """
        # Convert channels to ChannelConfig instances
        channels_dict: Dict[int, ChannelConfig] = {}
        for ch_id, channel in self._channels.items():
            channels_dict[ch_id] = ChannelConfig(
                channel_id=ch_id,
                control_type=channel.get_control_type(),
                device_path=channel.device_path,
                control_code=channel.control_code,
                device_name=channel.device_name,
                control_name=channel.control_name,
            )
        
        # Convert processors to dict format
        processors_dict: Dict[str, Any] = {}
        for processor in self._processors:
            proc_type = processor.get_type()
            proc_data = processor.to_dict()
            
            # Some processor types expect a dict (reverse, endpoints)
            # Others expect a list (differential, aggregate)
            if proc_type in ("reverse", "endpoints"):
                processors_dict[proc_type] = proc_data
            else:
                processors_dict[proc_type] = proc_data
        
        return Model(
            name=self._name,
            channels=channels_dict,
            processors=processors_dict,
            model_id=self._model_id or uuid.uuid4().hex,
            rx_num=self._rx_num,
            bind_timestamp=self._bind_timestamp,
        )
    
    @classmethod
    def from_model(cls, model: Model) -> ModelBuilder:
        """Create a ModelBuilder from an existing Model.
        
        Useful for modifying existing models.
        
        Args:
            model: Existing Model instance
            
        Returns:
            ModelBuilder initialized with the model's data
        """
        builder = cls(model.name)
        builder._rx_num = model.rx_num
        builder._model_id = model.model_id
        builder._bind_timestamp = model.bind_timestamp
        
        # Reconstruct channels (as generic Channel instances)
        from .channel import (
            BipolarChannel, UnipolarChannel, ButtonChannel,
            LatchingButtonChannel, VirtualChannel
        )
        
        for ch_id, ch_cfg in model.channels.items():
            # Determine channel class based on control_type
            channel_cls = Channel
            if ch_cfg.control_type == "bipolar":
                channel_cls = BipolarChannel
            elif ch_cfg.control_type == "unipolar":
                channel_cls = UnipolarChannel
            elif ch_cfg.control_type == "button":
                channel_cls = ButtonChannel
            elif ch_cfg.control_type == "latching-button":
                channel_cls = LatchingButtonChannel
            
            if ch_cfg.device_path == "" and ch_cfg.control_code == "virtual":
                channel = VirtualChannel(
                    channel_id=ch_id,
                    control_name=ch_cfg.control_name,
                    control_type=ch_cfg.control_type
                )
            else:
                channel = channel_cls(
                    channel_id=ch_id,
                    device_path=ch_cfg.device_path,
                    control_code=ch_cfg.control_code,
                    device_name=ch_cfg.device_name,
                    control_name=ch_cfg.control_name,
                )
            builder._channels[ch_id] = channel
        
        # Reconstruct processors
        processors = model.processors or {}
        if "reverse" in processors:
            builder._processors.append(
                ReverseProcessor.from_dict(processors["reverse"])
            )
        if "endpoints" in processors:
            builder._processors.append(
                EndpointProcessor.from_dict(processors["endpoints"])
            )
        if "differential" in processors:
            builder._processors.append(
                DifferentialProcessor.from_dict(processors["differential"])
            )
        if "aggregate" in processors:
            builder._processors.append(
                AggregateProcessor.from_dict(processors["aggregate"])
            )
        
        return builder
