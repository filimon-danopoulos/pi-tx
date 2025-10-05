"""
UART communication with MULTI module for RC transmitter functionality.
Supports AFHDS2A protocol (compatible with FS-iA10B receiver).
"""

import logging
import threading
import time
import os
from typing import Callable, Optional, Sequence, Iterable
import serial


class UartTx:
    """
    Simple serial port wrapper for MULTI module communication.
    Handles opening, closing, and sending bytes over serial.
    """

    def __init__(self, port: str, baud: int = 100000):
        self.port = port
        self.baud = baud
        self._serial = None

    def open(self) -> bool:
        """Open the serial connection."""

        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=8,
                parity="E",  # Even parity
                stopbits=2,  # 2 stop bits (8E2)
                timeout=0.1,
                write_timeout=0.1,
            )
            logging.info(f"Opened UART: {self.port} at {self.baud} baud (8E2)")
            return True
        except Exception as e:
            logging.error(f"Failed to open UART {self.port}: {e}")
            return False

    def close(self):
        """Close the serial connection."""
        if self._serial:
            try:
                self._serial.close()
                logging.info("Closed UART port")
            except Exception as e:
                logging.error(f"Error closing UART: {e}")
            finally:
                self._serial = None

    def send_bytes(self, data: bytes) -> bool:
        """Send bytes over the serial connection."""
        if not self._serial or not self._serial.is_open:
            logging.warning("UART not open, cannot send data")
            return False

        try:
            self._serial.write(data)
            self._serial.flush()
            return True
        except Exception as e:
            logging.error(f"Error sending UART data: {e}")
            return False


class MultiSerialTX:
    """
    Streams one MULTI-serial control frame continuously (~45 Hz).
    Binding is controlled by a flag bit inside the frame (no separate bind packet).

    Frame layout (common V2-style used by MULTI serial):
      [0]  0x55
      [1]  protocol_id                  (e.g., AFHDS2A = 28)
      [2]  flags = (subproto & 0x1F) | (bind<<7) | (range<<6) | (autobind<<5)
      [3]  option (fine-tune / signed -32..+31, stored as 0..255)
      [4]  rx_num (0..15)
      [5..] channels (11-bit each, little-endian: lo, hi)
      [last] XOR checksum over bytes [1..last-1] (exclude 0x55)

    Keep sending this frame; toggle bind flag for a few seconds to bind.
    """

    # ---- Protocol IDs (from Multiprotocol.h snippet you shared) ----
    PROTO_AFHDS2A = 28  # 0x1C

    # ---- AFHDS2A sub-protocols (lower 5 bits of flags) ----
    AFHDS2A_PWM_IBUS = 0
    AFHDS2A_PPM_IBUS = 1
    AFHDS2A_PWM_SBUS = 2
    AFHDS2A_PPM_SBUS = 3
    AFHDS2A_GYRO_OFF = 4
    AFHDS2A_GYRO_ON = 5
    AFHDS2A_GYRO_ON_REV = 6

    def __init__(
        self,
        uart: UartTx,
        protocol_id: int = PROTO_AFHDS2A,
        sub_protocol: int = AFHDS2A_PWM_IBUS,
        rx_num: int = 0,
        option: int = 0,
        channel_count: int = 10,
        frame_rate_hz: float = 45.0,
    ):
        self._uart = uart
        self._protocol_id = protocol_id
        self._sub_protocol = sub_protocol & 0x1F
        self._rx_num = rx_num
        self._option = option
        self._frame_rate_hz = frame_rate_hz

        # Channels
        self._num_channels = channel_count
        self._channels = [1024] * self._num_channels

        # Flags
        self._bind_mode = False
        self._range_check = False
        self._autobind = False

        # Threading / sampler
        self._stop_flag = False
        self._sender_thread = None
        self._sampler = None
        self._sampler_normalized = True
        self._last_sampler_error_log = 0.0
        self._sampler_error_suppression_s = 2.0

        # Model identity (external metadata)
        self._model_id = None  # filled via set_model_id

    # ---- Model identity (not part of protocol frame) ----
    def set_model_id(self, model_id: str | None):
        self._model_id = model_id

    def get_model_id(self) -> Optional[str]:  # pragma: no cover (trivial)
        return self._model_id

    # Internal sampler update extracted for reuse in tests
    def _update_channels_from_sampler(self):
        if not self._sampler:
            return
        try:
            raw_values = self._sampler()
            converted: list[int] = []
            for i, v in enumerate(raw_values):
                if i >= self._num_channels:
                    break
                if v is None or not isinstance(v, (int, float)):
                    converted.append(1024)
                    continue
                if self._sampler_normalized:
                    nv = max(-1.0, min(1.0, float(v)))
                    ch = int((nv + 1.0) * 1023.5)
                else:
                    fv = float(v)
                    if 900 <= fv <= 2100 and fv > 200:
                        ch = int((fv - 1000.0) * 2047.0 / 1000.0)
                    else:
                        ch = int(fv)
                converted.append(max(0, min(2047, ch)))
            if converted:
                self.set_channels(converted)
        except Exception as se:
            now = time.time()
            if now - self._last_sampler_error_log > self._sampler_error_suppression_s:
                logging.error(f"Sampler error: {se}")
                self._last_sampler_error_log = now

    # ---- Channel setters ----
    def set_channel(self, ch_index: int, value: int):
        """
        Set a single channel to an 11-bit value [0..2047].
        1500 = neutral for PWM.
        """
        if 0 <= ch_index < self._num_channels:
            # Clamp to 11-bit range
            self._channels[ch_index] = max(0, min(2047, int(value)))

    def set_channels(self, values):
        """
        Set multiple channels. values can be a list/tuple of ints.
        Automatically clamps to [0..2047].
        """
        for i, val in enumerate(values):
            if i >= self._num_channels:
                break
            self.set_channel(i, val)

    # ---- Sampler registration ----
    def set_sampler(
        self, sampler: Callable[[], Sequence[float]], *, normalized: bool = True
    ):
        """Register a sampler callback invoked each frame before building.

        sampler: callable returning a sequence of channel values.
        If normalized=True (default) values are assumed in -1.0..1.0 and converted
        to 0..2047. Otherwise values are treated as already scaled (ints or floats
        in 0..2047) and simply clamped.
        """
        self._sampler = sampler
        self._sampler_normalized = normalized

    # ---- Frame building ----
    def _build_frame(self) -> bytes:
        """
        Build the MULTI-serial frame with current settings.
        Returns bytes ready to send over serial.
        """
        # Convert signed option (-32..+31) to byte (0..255)
        option_byte = (self._option + 32) & 0xFF

        # Build flags byte: [7=bind][6=range][5=auto][4:0=subproto]
        flags = self._sub_protocol & 0x1F
        if self._bind_mode:
            flags |= 0x80  # bit 7
        if self._range_check:
            flags |= 0x40  # bit 6
        if self._autobind:
            flags |= 0x20  # bit 5

        # Frame starts with: header, protocol, flags, option, rx_num
        frame = bytearray([0x55, self._protocol_id, flags, option_byte, self._rx_num])

        # Add channels (11-bit each, little-endian)
        for ch_val in self._channels:
            # Clamp to 11-bit just in case
            val = max(0, min(2047, ch_val))
            lo = val & 0xFF
            hi = (val >> 8) & 0x07
            frame.extend([lo, hi])

        # XOR checksum over bytes [1..last] (exclude the 0x55 header)
        checksum = 0
        for b in frame[1:]:
            checksum ^= b
        frame.append(checksum)

        return bytes(frame)

    # ---- Periodic transmission ----
    def start(self):
        """Start the periodic frame transmission thread."""
        if self._sender_thread and self._sender_thread.is_alive():
            return  # already running

        self._stop_flag = False
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()

    def stop(self):
        """Stop the periodic frame transmission."""
        self._stop_flag = True
        if self._sender_thread:
            self._sender_thread.join(timeout=1.0)
            self._sender_thread = None

    def _sender_loop(self):
        """
        Main transmission loop. Sends frames at ~frame_rate_hz.
        """
        if self._frame_rate_hz <= 0:
            self._frame_rate_hz = 45.0
        interval = 1.0 / self._frame_rate_hz
        # Use perf_counter for better monotonic timing
        perf = time.perf_counter
        next_send = perf()
        drift_resets = 0
        while not self._stop_flag:
            now = perf()
            # Sleep until scheduled send time with drift correction
            remaining = next_send - now
            if remaining > 0.0008:  # more than ~0.8ms: coarse sleep then fine spin
                # Leave ~0.3ms for spin to reduce oversleep
                coarse = remaining - 0.0003
                if coarse > 0:
                    time.sleep(coarse)
            # Fine wait (spin/yield) until deadline or stop
            while not self._stop_flag and perf() < next_send:
                # brief yield to OS
                time.sleep(0)
            # Build & send frame
            try:
                if self._sampler:
                    self._update_channels_from_sampler()
                frame = self._build_frame()
                if hasattr(self._uart, "send_bytes"):
                    self._uart.send_bytes(frame)
            except Exception as e:
                logging.error(f"MultiSerialTX frame send error: {e}")
            # Schedule next send; correct drift accumulation
            next_send += interval
            # If we fell behind by more than one interval, fast-forward
            behind = perf() - next_send
            if behind > interval * 0.5:
                # resync to current time + interval
                next_send = perf() + interval
                drift_resets += 1

    def __del__(self):
        """Cleanup: stop the sender thread."""
        self.stop()
