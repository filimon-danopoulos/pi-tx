"""
Top-level Model class for RC transmitter configuration.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Set, Union
from collections import defaultdict

from evdev import InputDevice, ecodes

from .channel import Channel
from .mixing import DifferentialMix, AggregateMix
from .virtual_control import VirtualControl
from ...logging_config import get_logger


@dataclass
class Model:
    """
    Complete RC model configuration.

    Defines all channels, mixing, and processing for a complete RC model.
    This is the top-level configuration object that gets loaded and used
    by the transmitter system.
    """

    name: str
    model_id: str
    channels: List[Channel]
    mixes: List[Union[DifferentialMix, AggregateMix]] = field(default_factory=list)
    rx_num: int = 0  # Receiver number (0-15)
    bind_timestamp: str = ""  # ISO timestamp

    def __post_init__(self):
        """Validate model configuration on creation."""
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

        # Check for duplicate channel names
        channel_names = [ch.name for ch in self.channels]
        if len(channel_names) != len(set(channel_names)):
            duplicates = [
                name for name in channel_names if channel_names.count(name) > 1
            ]
            errors.append(f"Duplicate channel names found: {set(duplicates)}")

        # Validate mix references
        valid_names = set(channel_names)

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

    def get_channel_by_name(self, channel_name: str) -> Optional[Channel]:
        """Get a channel by its name."""
        for ch in self.channels:
            if ch.name == channel_name:
                return ch
        return None

    def get_channel_by_control_name(self, control_name: str) -> Optional[Channel]:
        """Get a channel by its control's name."""
        for ch in self.channels:
            if ch.control.name == control_name:
                return ch
        return None

    async def listen(self, duration: Optional[float] = None):
        """
        Listen to all configured input devices and debug log any changes.

        Uses asyncio and evdev to monitor input events from all physical controls
        configured in the model. Virtual controls are skipped.

        Args:
            duration: Optional time limit in seconds. If None, runs until interrupted.

        Example:
            await model.listen()  # Run forever
            await model.listen(10)  # Run for 10 seconds
        """
        log = get_logger(f"{self.__class__.__name__}.listen")

        # Gather unique device paths from all channels (excluding virtual controls)
        device_paths: Set[str] = set()
        channel_map = defaultdict(list)  # device_path -> list of (channel, control)

        for channel in self.channels:
            if isinstance(channel.control, VirtualControl):
                continue

            # Get device_path from the control's device_path property
            device_path = channel.control.device_path
            if device_path:
                device_paths.add(device_path)
                channel_map[device_path].append((channel, channel.control))

        if not device_paths:
            log.warning("No physical input devices found in model configuration")
            return

        # Open all devices
        devices = []
        for path in device_paths:
            try:
                dev = InputDevice(path)
                devices.append(dev)
                log.info(f"Opened device: {dev.name} at {path}")
            except Exception as e:
                log.warning(f"Could not open device {path}: {e}")

        if not devices:
            log.error("No devices could be opened")
            return

        log.info(f"Listening to {len(devices)} device(s) for model '{self.name}'...")
        if duration:
            log.info(f"Will stop after {duration} seconds")

        # Track last values to detect changes
        last_values = {}
        # Rate limiting: 100Hz = 10ms minimum interval between processing
        min_interval = 0.01  # 10ms = 100Hz
        last_process_time = {}  # Track last process time per (device, code, type)

        try:
            # Create async tasks for each device
            async def monitor_device(device):
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

                    # Find matching channels for this event
                    matching_channels = [
                        (ch, ctrl)
                        for ch, ctrl in channel_map[device.path]
                        if hasattr(ctrl, "event_code")
                        and ctrl.event_code == event.code
                        and ctrl.event_type.value == event.type
                    ]

                    for channel, control in matching_channels:
                        # Create unique key for this control
                        key = channel.name

                        # Normalize the value
                        if hasattr(control, "normalize"):
                            # AxisControl
                            normalized = control.normalize(event.value)
                        else:
                            # ButtonControl
                            normalized = float(event.value)

                        # Check if value changed
                        if last_values.get(key) != normalized:
                            last_values[key] = normalized

                            # Apply channel processing
                            processed = normalized
                            if channel.reversed:
                                if control.control_type.value == "bipolar":
                                    processed = -processed
                                else:
                                    processed = 1.0 - processed

                            processed = channel.endpoint.clamp(processed)

                            log.debug(
                                f"{channel.name} ({control.name}): "
                                f"raw={event.value} norm={normalized:.3f} "
                                f"processed={processed:.3f}"
                            )

            # Run all device monitors concurrently
            tasks = [asyncio.create_task(monitor_device(dev)) for dev in devices]

            if duration:
                # Run for specified duration
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), timeout=duration
                    )
                except asyncio.CancelledError:
                    # Cancel all tasks when we're cancelled
                    for task in tasks:
                        task.cancel()
                    raise
            else:
                # Run until interrupted
                await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.TimeoutError:
            log.info(f"Listening stopped after {duration} seconds")
        except (KeyboardInterrupt, asyncio.CancelledError):
            log.info("Listening interrupted")
        finally:
            # Close all devices
            for dev in devices:
                dev.close()
            log.info("All devices closed")
