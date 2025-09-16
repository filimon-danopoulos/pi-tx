"""Value store for storing input values with reversing support.

Similar to channel_store but simplified to only support reversing functionality.
Configuration is loaded from system_values.json file.
"""

import json
import os
from typing import List, Dict, Any, Mapping


class ValueStore:
    """A store for input values that supports reversing.

    Values can be stored and retrieved with optional reversing applied.
    Configuration is loaded from system_values.json.
    """

    def __init__(self, size: int = 32, config_path: str = None):
        """Initialize the value store.

        Args:
            size: Number of values to store
            config_path: Path to configuration file (defaults to system_values.json)
        """
        self._size = size
        self._raw: List[float] = [0.0] * size
        self._derived: List[float] = [0.0] * size
        self._reverse_flags: List[bool] = [False] * size
        self._channel_types: List[str] = ["unipolar"] * size  # Missing initialization
        self._channel_values: Dict[int, Dict[str, Any]] = (
            {}
        )  # Channel value definitions
        self._stick_mapping: Dict[str, Any] = {}  # Stick mapping data

        # Default config path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "system_values.json"
            )
        self._config_path = config_path

        # Stick mapping path
        self._stick_mapping_path = os.path.join(
            os.path.dirname(__file__), "..", "input", "mappings", "stick_mapping.json"
        )

        # Load configuration
        self._load_stick_mapping()
        self._load_configuration()

    def _reverse_proc(self, values: List[float]) -> List[float]:
        """Apply reversing to values based on channel types and reverse flags.

        Args:
            values: Input values to process

        Returns:
            Values with reversing applied
        """
        out = values[:]
        for i, (val, reverse, ch_type) in enumerate(
            zip(out, self._reverse_flags, self._channel_types)
        ):
            if reverse:
                if ch_type == "bipolar":
                    out[i] = -val
                else:  # unipolar
                    out[i] = 1.0 - val
        return out

    def _load_configuration(self):
        """Load configuration from system_values.json file."""
        if not os.path.exists(self._config_path):
            # Create default configuration file
            self._create_default_config()
            return

        try:
            with open(self._config_path, "r") as f:
                config = json.load(f)

            # Load reverse flags
            reverse_cfg = config.get("reverse", {})
            for key, val in reverse_cfg.items():
                try:
                    # Expect var1 format only
                    if isinstance(key, str) and key.startswith("var"):
                        ch_num = int(key[3:])  # Extract number from "var1", "var2", etc.
                        idx = ch_num - 1
                    else:
                        raise ValueError(f"Invalid reverse key format {key}, expected 'var1' format")
                    
                    if 0 <= idx < len(self._reverse_flags) and isinstance(val, bool):
                        self._reverse_flags[idx] = val
                except (ValueError, TypeError) as e:
                    print(f"ValueStore: bad reverse entry {key}: {e}")

            # Load channel value definitions
            values_cfg = config.get("values", {})
            for key, val in values_cfg.items():
                try:
                    # Expect var1 format only
                    if isinstance(key, str) and key.startswith("var"):
                        ch_num = int(key[3:])  # Extract number from "var1", "var2", etc.
                    else:
                        raise ValueError(f"Invalid values key format {key}, expected 'var1' format")
                        
                    if isinstance(val, dict):
                        self._channel_values[ch_num] = val
                except (ValueError, TypeError) as e:
                    print(f"ValueStore: bad values entry {key}: {e}")

        except (json.JSONDecodeError, IOError) as e:
            print(f"ValueStore: failed to load config from {self._config_path}: {e}")
            self._create_default_config()

    def _load_stick_mapping(self):
        """Load stick mapping from stick_mapping.json file."""
        if not os.path.exists(self._stick_mapping_path):
            print(f"ValueStore: stick mapping not found at {self._stick_mapping_path}")
            return

        try:
            with open(self._stick_mapping_path, "r") as f:
                self._stick_mapping = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(
                f"ValueStore: failed to load stick mapping from {self._stick_mapping_path}: {e}"
            )

    def _create_default_config(self):
        """Create a default configuration file."""
        default_config = {"reverse": {}, "values": {}}

        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(default_config, f, indent=2)
        except IOError as e:
            print(f"ValueStore: failed to create default config: {e}")

    def save_configuration(self):
        """Save current configuration to system_values.json file."""
        config = {"reverse": {}, "values": {}}

        # Save reverse flags (only non-default values) using var prefix
        for i, reverse in enumerate(self._reverse_flags):
            if reverse:
                config["reverse"][f"var{i + 1}"] = True

        # Save channel values using var prefix
        for ch_num, ch_data in self._channel_values.items():
            config["values"][f"var{ch_num}"] = ch_data

        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"ValueStore: failed to save config: {e}")

    def configure_reverse(self, reverse_config: Dict[str, bool]):
        """Configure reverse flags for specific channels.

        Args:
            reverse_config: Dict mapping channel identifiers (var1, var2, etc.) to reverse flags
        """
        for key, val in reverse_config.items():
            try:
                # Expect var1 format only
                if isinstance(key, str) and key.startswith("var"):
                    ch_num = int(key[3:])  # Extract number from "var1", "var2", etc.
                    idx = ch_num - 1
                else:
                    raise ValueError(f"Invalid reverse key format {key}, expected 'var1' format")
                    
                if 0 <= idx < len(self._reverse_flags) and isinstance(val, bool):
                    self._reverse_flags[idx] = val
            except (ValueError, TypeError) as e:
                print(f"ValueStore: bad reverse entry {key}: {e}")
        self._recompute()

    def configure_channel_types(self, channel_types: Dict[str, str]):
        """Configure channel types for specific channels.

        Args:
            channel_types: Dict mapping channel identifiers (var1, var2, etc.) to types
        """
        for key, val in channel_types.items():
            try:
                # Expect var1 format only
                if isinstance(key, str) and key.startswith("var"):
                    ch_num = int(key[3:])  # Extract number from "var1", "var2", etc.
                    idx = ch_num - 1
                else:
                    raise ValueError(f"Invalid channel_types key format {key}, expected 'var1' format")
                    
                if 0 <= idx < len(self._channel_types) and isinstance(val, str):
                    if val in ["bipolar", "unipolar"]:
                        self._channel_types[idx] = val
            except (ValueError, TypeError) as e:
                print(f"ValueStore: bad channel_type entry {key}: {e}")
        self._recompute()

    def set_reverse(self, channel: int, reverse: bool):
        """Set reverse flag for a specific channel.

        Args:
            channel: Channel number (1-based)
            reverse: Whether to reverse the channel
        """
        idx = channel - 1
        if 0 <= idx < len(self._reverse_flags):
            self._reverse_flags[idx] = reverse
            self._recompute()

    def set_channel_type(self, channel: int, ch_type: str):
        """Set channel type for a specific channel.

        Args:
            channel: Channel number (1-based)
            ch_type: Channel type ("bipolar" or "unipolar")
        """
        idx = channel - 1
        if 0 <= idx < len(self._channel_types) and ch_type in ["bipolar", "unipolar"]:
            self._channel_types[idx] = ch_type
            self._recompute()

    def size(self) -> int:
        """Get the size of the value store."""
        return self._size

    def set_value(self, channel: int, value: float):
        """Set a single value.

        Args:
            channel: Channel number (1-based)
            value: Value to set
        """
        idx = channel - 1
        if 0 <= idx < len(self._raw) and self._raw[idx] != value:
            self._raw[idx] = value
            self._recompute()

    def set_many(self, updates: Mapping[int, float]):
        """Set multiple values at once.

        Args:
            updates: Dict mapping channel numbers (1-based) to values
        """
        changed = False
        for ch, val in updates.items():
            idx = ch - 1
            if 0 <= idx < len(self._raw) and self._raw[idx] != val:
                self._raw[idx] = val
                changed = True
        if changed:
            self._recompute()

    def get_value(self, channel: int) -> float:
        """Get a processed value.

        Args:
            channel: Channel number (1-based)

        Returns:
            Processed value with reversing applied
        """
        idx = channel - 1
        if 0 <= idx < len(self._derived):
            return self._derived[idx]
        return 0.0

    def get_raw_value(self, channel: int) -> float:
        """Get a raw value (before processing).

        Args:
            channel: Channel number (1-based)

        Returns:
            Raw value before reversing
        """
        idx = channel - 1
        if 0 <= idx < len(self._raw):
            return self._raw[idx]
        return 0.0

    def snapshot(self) -> List[float]:
        """Get a snapshot of all processed values."""
        return self._derived[:]

    def raw_snapshot(self) -> List[float]:
        """Get a snapshot of all raw values."""
        return self._raw[:]

    def is_reversed(self, channel: int) -> bool:
        """Check if a channel is reversed.

        Args:
            channel: Channel number (1-based)

        Returns:
            True if channel is reversed
        """
        idx = channel - 1
        if 0 <= idx < len(self._reverse_flags):
            return self._reverse_flags[idx]
        return False

    def get_channel_type(self, channel: int) -> str:
        """Get channel type.

        Args:
            channel: Channel number (1-based)

        Returns:
            Channel type ("bipolar" or "unipolar")
        """
        if channel in self._channel_values:
            return self._channel_values[channel].get("control_type", "unipolar")
        return "unipolar"

    def get_device_name(self, channel: int) -> str:
        """Get device name for a channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            Device name or "Input" if not configured
        """
        if channel not in self._channel_values:
            return "Input"

        channel_info = self._channel_values[channel]
        device_path = channel_info.get("device_path", "")

        if device_path in self._stick_mapping:
            return self._stick_mapping[device_path].get("name", "Input")

        return "Input"

    def get_control_name(self, channel: int) -> str:
        """Get control name for a channel.

        Args:
            channel: Channel number (1-based)

        Returns:
            Control name or empty string if not configured
        """
        if channel not in self._channel_values:
            return ""

        channel_info = self._channel_values[channel]
        device_path = channel_info.get("device_path", "")
        control_code = channel_info.get("control_code", "")

        if device_path in self._stick_mapping:
            controls = self._stick_mapping[device_path].get("controls", {})
            if control_code in controls:
                return controls[control_code].get("name", "")

        return ""

    def get_channel_info(self, channel: int) -> Dict[str, Any]:
        """Get full channel information.

        Args:
            channel: Channel number (1-based)

        Returns:
            Dictionary with channel information or empty dict if not configured
        """
        return self._channel_values.get(channel, {})

    def _recompute(self):
        """Recompute derived values with reversing applied."""
        self._derived[:] = self._reverse_proc(self._raw[:])


# Global instance for use throughout the application
value_store = ValueStore(size=32)
