"""
Top-level Model class for RC transmitter configuration.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Union
from collections import defaultdict

from evdev import InputDevice, ecodes

from .value import Value
from .mixing import DifferentialMix, AggregateMix
from .virtual_control import VirtualControl
from ..logging import get_logger


class ModelIcon(str, Enum):
    """Available Material Design icons for RC models."""
    
    BULLDOZER = "bulldozer"
    CAR_PICKUP = "car-pickup"
    DUMP_TRUCK = "dump-truck"
    EXCAVATOR = "excavator"
    FIRE_TRUCK = "fire-truck"
    FORKLIFT = "forklift"
    TOW_TRUCK = "tow-truck"
    TRACTOR = "tractor"
    TRACTOR_VARIANT = "tractor-variant"
    TRUCK = "truck"
    TRUCK_FLATBED = "truck-flatbed"
    VAN_UTILITY = "van-utility"


@dataclass
class Channels:
    """
    Channel mapping for AFHDS2A protocol (14 channels max).
    
    Maps value names to specific channel positions (1-14).
    Any unmapped channels will be set to neutral (0.0).
    """
    ch_1: Optional[str] = None
    ch_2: Optional[str] = None
    ch_3: Optional[str] = None
    ch_4: Optional[str] = None
    ch_5: Optional[str] = None
    ch_6: Optional[str] = None
    ch_7: Optional[str] = None
    ch_8: Optional[str] = None
    ch_9: Optional[str] = None
    ch_10: Optional[str] = None
    ch_11: Optional[str] = None
    ch_12: Optional[str] = None
    ch_13: Optional[str] = None
    ch_14: Optional[str] = None


@dataclass
class Model:
    """
    Complete RC model configuration.

    Defines all values, mixing, and processing for a complete RC model.
    This is the top-level configuration object that gets loaded and used
    by the transmitter system.
    """

    name: str
    model_id: str
    values: List[Value]
    channels: Channels
    mixes: List[Union[DifferentialMix, AggregateMix]] = field(default_factory=list)
    rx_num: int = 0  # Receiver number (0-15)
    bind_timestamp: str = ""  # ISO timestamp
    icon: ModelIcon = ModelIcon.EXCAVATOR  # Material Design icon name for the model

    def __post_init__(self):
        """Validate model configuration on creation."""
        # Initialize value storage fields
        self.raw_values: dict[str, float] = {}
        self.processed_values: dict[str, float] = {}

        # Initialize connection state
        self._devices: List[InputDevice] = []
        self._tasks: List[asyncio.Task] = []
        self._is_connected = False
        self._log = get_logger(f"{self.__class__.__name__}")

        errors = self.validate()
        if errors:
            raise ValueError(
                f"Invalid model configuration for '{self.name}':\n"
                + "\n".join(f"  - {err}" for err in errors)
            )

    def validate(self) -> List[str]:
        """
        Validate model configuration and return list of errors.

        Returns:
            List of error messages. Empty list means valid configuration.
        """
        errors = []

        # Check for duplicate value names
        value_names = [v.name for v in self.values]
        if len(value_names) != len(set(value_names)):
            duplicates = [
                name for name in value_names if value_names.count(name) > 1
            ]
            errors.append(f"Duplicate value names found: {set(duplicates)}")

        # Validate mix references
        valid_names = set(value_names)

        for i, mix in enumerate(self.mixes):
            if isinstance(mix, DifferentialMix):
                if mix.left_channel not in valid_names:
                    errors.append(
                        f"Differential mix {i}: references invalid channel '{mix.left_channel}'"
                    )
                if mix.right_channel not in valid_names:
                    errors.append(
                        f"Differential mix {i}: references invalid channel '{mix.right_channel}'"
                    )
            elif isinstance(mix, AggregateMix):
                for j, src in enumerate(mix.sources):
                    if src.channel_name not in valid_names:
                        errors.append(
                            f"Aggregate mix {i}, source {j}: "
                            f"references invalid channel '{src.channel_name}'"
                        )
                if mix.target_channel and mix.target_channel not in valid_names:
                    errors.append(
                        f"Aggregate mix {i}: target channel '{mix.target_channel}' is invalid"
                    )

        # Validate rx_num range
        if not (0 <= self.rx_num <= 15):
            errors.append(f"rx_num must be in range [0, 15], got {self.rx_num}")

        return errors

    def get_value_by_name(self, value_name: str) -> Optional[Value]:
        """Get a value by its name."""
        for v in self.values:
            if v.name == value_name:
                return v
        return None

    def get_value_by_control_name(self, control_name: str) -> Optional[Value]:
        """Get a value by its control's name."""
        for v in self.values:
            if v.control.name == control_name:
                return v
        return None

    def readValues(self) -> dict[str, float]:
        self._process()
        self._postProcess()
        return self.processed_values.copy()

    def getChannels(self) -> List[float]:
        """
        Get channel values mapped according to the channels configuration.
        
        Returns a list of 14 float values (one per AFHDS2A channel).
        Maps value names to specific channel positions as defined in the channels field.
        Unmapped channels default to 0.0 (neutral).
        
        Returns:
            List of 14 floats representing channel values.
        """
        # Get processed values
        values_dict = self.readValues()
        
        # Initialize all 14 channels to neutral (0.0)
        channel_list = [0.0] * 14
        
        # Use channel mapping
        channel_fields = [
            self.channels.ch_1, self.channels.ch_2, self.channels.ch_3,
            self.channels.ch_4, self.channels.ch_5, self.channels.ch_6,
            self.channels.ch_7, self.channels.ch_8, self.channels.ch_9,
            self.channels.ch_10, self.channels.ch_11, self.channels.ch_12,
            self.channels.ch_13, self.channels.ch_14
        ]
        
        for i, value_name in enumerate(channel_fields):
            if value_name is not None:
                channel_list[i] = values_dict.get(value_name, 0.0)
        
        return channel_list

    def _process(self):
        # Start with a copy of raw values
        values = dict(self.raw_values)

        # Apply all mixes
        for mix in self.mixes:
            # Each mix computes its output and we update values
            mixed = mix.compute(values)
            values.update(mixed)

        # Store the mixed values
        self.processed_values = values

    def _postProcess(self):
        for value_obj in self.values:
            # Get the value (post-mixing or original)
            value = self.processed_values.get(value_obj.name, 0.0)

            # Apply value post-processing
            value = value_obj.postProcess(value)

            # Update the processed value
            self.processed_values[value_obj.name] = value

    async def connect(self):
        """
        Connect to all configured input devices and start collecting normalized values.

        This method opens input devices and starts monitoring for events,
        storing normalized raw values in self.raw_values. It does NOT apply
        mixes, reversing, or endpoints. Call readValues() to process the collected values.

        Uses asyncio and evdev to monitor input events from all physical controls
        configured in the model. Virtual controls are skipped.

        Call disconnect() to gracefully stop listening and close devices.

        Example:
            await model.connect()  # Start listening in background
            # ... do other work ...
            await model.disconnect()  # Stop listening
        """
        if self._is_connected:
            self._log.warning(f"Model '{self.name}' is already connected")
            return

        # Gather unique device paths from all values (excluding virtual controls)
        device_paths: Set[str] = set()
        value_map = defaultdict(list)  # device_path -> list of (value, control)

        for value_obj in self.values:
            if isinstance(value_obj.control, VirtualControl):
                continue

            # Get device_path from the control's device_path property
            device_path = value_obj.control.device_path
            if device_path:
                device_paths.add(device_path)
                value_map[device_path].append((value_obj, value_obj.control))

        if not device_paths:
            self._log.warning("No physical input devices found in model configuration")
            return

        # Open all devices
        self._devices = []
        for path in device_paths:
            try:
                dev = InputDevice(path)
                self._devices.append(dev)
                self._log.info(f"Opened device: {dev.name} at {path}")
            except Exception as e:
                self._log.warning(f"Could not open device {path}: {e}")

        if not self._devices:
            self._log.error("No devices could be opened")
            return

        self._log.info(
            f"Listening to {len(self._devices)} device(s) for model '{self.name}'..."
        )

        # Track last values to detect changes
        last_values = {}
        # Rate limiting: 100Hz = 10ms minimum interval between processing
        min_interval = 0.01  # 10ms = 100Hz
        last_process_time = {}  # Track last process time per (device, code, type)

        # Create async tasks for each device
        async def monitor_device(device):
            try:
                async for event in device.async_read_loop():
                    # Skip sync and misc events
                    if event.type in (ecodes.EV_SYN, ecodes.EV_MSC):
                        continue

                    # Rate limiting check
                    event_key = (device.path, event.code, event.type)
                    current_time = asyncio.get_event_loop().time()
                    last_time = last_process_time.get(event_key, 0)

                    if current_time - last_time < min_interval:
                        # Skip processing if below 100Hz threshold
                        continue

                    last_process_time[event_key] = current_time

                    # Find matching values for this event
                    matching_values = [
                        (v, ctrl)
                        for v, ctrl in value_map[device.path]
                        if hasattr(ctrl, "event_code")
                        and ctrl.event_code == event.code
                        and ctrl.event_type.value == event.type
                    ]

                    for value_obj, control in matching_values:
                        # Normalize the value
                        if hasattr(control, "normalize"):
                            # AxisControl
                            normalized = control.normalize(event.value)
                        else:
                            # ButtonControl
                            normalized = float(event.value)

                        # Apply pre-processing (latching)
                        preprocessed = value_obj.preProcess(normalized)

                        # Check if value changed and store in raw_values
                        if last_values.get(value_obj.name) != preprocessed:
                            last_values[value_obj.name] = preprocessed
                            self.raw_values[value_obj.name] = preprocessed

                            self._log.debug(
                                f"{value_obj.name} ({control.name}): "
                                f"raw={event.value} norm={normalized:.3f} pre={preprocessed:.3f}"
                            )
            except asyncio.CancelledError:
                self._log.debug(f"Monitor task cancelled for device {device.path}")
                raise
            except Exception as e:
                self._log.error(
                    f"Error monitoring device {device.path}: {e}", exc_info=True
                )

        # Run all device monitors concurrently
        self._tasks = [
            asyncio.create_task(monitor_device(dev)) for dev in self._devices
        ]
        self._is_connected = True
        self._log.info(f"Model '{self.name}' connected successfully")

    async def disconnect(self):
        """
        Disconnect from all input devices and stop collecting values.

        Cancels all monitoring tasks and closes all open devices gracefully.
        After disconnection, the model can be reconnected by calling connect() again.
        """
        if not self._is_connected:
            self._log.debug(f"Model '{self.name}' is not connected")
            return

        self._log.info(f"Disconnecting model '{self.name}'...")

        # Cancel all monitoring tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete/cancel
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close all devices
        for dev in self._devices:
            try:
                dev.close()
                self._log.debug(f"Closed device: {dev.path}")
            except Exception as e:
                self._log.warning(f"Error closing device {dev.path}: {e}")

        # Clear state
        self._devices = []
        self._tasks = []
        self._is_connected = False
        self._log.info(f"Model '{self.name}' disconnected successfully")

    async def listen(self, duration: Optional[float] = None):
        """
        Legacy method: Connect and listen for a specified duration.

        This is a compatibility wrapper around connect()/disconnect().
        For new code, prefer using connect() and disconnect() directly.

        Args:
            duration: Optional time limit in seconds. If None, runs until interrupted.
        """
        await self.connect()

        if duration:
            try:
                await asyncio.sleep(duration)
            except asyncio.CancelledError:
                pass
            finally:
                await self.disconnect()
        else:
            # Run until interrupted
            try:
                await asyncio.Event().wait()  # Wait forever
            except (KeyboardInterrupt, asyncio.CancelledError):
                await self.disconnect()
