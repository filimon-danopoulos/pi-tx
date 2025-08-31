from __future__ import annotations

"""UART transmission of channel data to a MULTI / iRX4 style module (100000 baud 8E2) using pyserial.

Single class (MultiSerialTX) handles both frame construction and transmission.
Frame format: 16-channel V1 serial frame (26 bytes) per multiprotocol docs.

Backend: pyserial only (pigpio legacy removed).

Logging controls (environment variables):
    PI_TX_UART_DEBUG=1          force verbose frame logging
    PI_TX_UART_LOG_EVERY=N      log every Nth frame (N>0)
    PI_TX_UART_RAW_HEX=1        include full frame hex when debug enabled
    PI_TX_UART_DRIFT_INTERVAL=S seconds between rate/drift reports (default 1.0)
    PI_TX_UART_MAX_VALUE_LOG=M  number of channel values to show (default 8)

Binding:
    A timed bind window (start_bind()) or static bind flag causes the bind bit
    (byte1 bit7) to be asserted in every transmitted frame for the duration.
    Frames continue to flow; no transmission silence during bind.
    Env var PI_TX_UART_BIND_AT_START=1 triggers an automatic bind window at open
    (duration seconds from PI_TX_UART_BIND_SECONDS, default 2).

Usage:
    tx = MultiSerialTX(port='/dev/ttyS0')
        tx.open()
        tx.send_channels([0.0]*16)

Integrate by periodically calling send_channels(channel_store_snapshot) at ~50Hz.
"""
from typing import Sequence
import threading, time, platform, os

try:
    import serial  # type: ignore

    HAVE_PYSERIAL = True
except Exception:
    HAVE_PYSERIAL = False


"""Raspberry Pi detection with environment overrides.

Environment overrides:
  PI_TX_FORCE_PI=1      Force ON_PI True
  PI_TX_FORCE_NO_PI=1   Force ON_PI False
  PI_TX_UART_DETECT_DEBUG=1  Print detection reasoning at import time
"""


def _detect_raspberry_pi() -> tuple[bool, str]:
    # Order of checks; accumulate reasons
    force_pi = os.environ.get("PI_TX_FORCE_PI") == "1"
    force_no = os.environ.get("PI_TX_FORCE_NO_PI") == "1"
    if force_pi and force_no:
        return False, "Both PI_TX_FORCE_PI and PI_TX_FORCE_NO_PI set; treating as False"
    if force_pi:
        return True, "Forced True via PI_TX_FORCE_PI"
    if force_no:
        return False, "Forced False via PI_TX_FORCE_NO_PI"
    reasons = []
    try:
        node = platform.uname().nodename.lower()
        if "raspberry" in node:
            reasons.append(f"nodename contains 'raspberry' ({node})")
    except Exception as e:
        reasons.append(f"nodename check failed: {e!r}")
    detected = False
    # Device tree model
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = f.read().lower()
            if "raspberry pi" in model:
                reasons.append(f"model file contains 'raspberry pi' ({model.strip()})")
                detected = True
            else:
                reasons.append(
                    f"model file does not mention raspberry pi ({model.strip()})"
                )
    except Exception as e:
        reasons.append(f"model file read failed: {e!r}")
        # /proc/cpuinfo SoC hints
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read().lower()
            if "raspberry pi" in cpuinfo or "bcm27" in cpuinfo or "bcm28" in cpuinfo:
                reasons.append("cpuinfo contains raspberry/bcm27/bcm28")
                detected = True or detected
    except Exception as e:
        reasons.append(f"cpuinfo read failed: {e!r}")
    # OS release ID
    try:
        with open("/etc/os-release", "r") as f:
            osrel = f.read().lower()
            if "raspbian" in osrel or "debian" in osrel and "raspberry" in osrel:
                reasons.append("os-release suggests raspbian")
                detected = True or detected
    except Exception as e:
        reasons.append(f"os-release read failed: {e!r}")
    if not detected and any("nodename contains" in r for r in reasons):
        detected = True  # nodename heuristic
    return detected, "; ".join(reasons)


_ON_PI_RESULT = _detect_raspberry_pi()
ON_PI = _ON_PI_RESULT[0]
if os.environ.get("PI_TX_UART_DETECT_DEBUG") == "1":
    print(f"[UART DETECT] ON_PI={ON_PI} reasons: {_ON_PI_RESULT[1]}")

# Protocol constants (numeric IDs as used by MULTI serial spec).
# AFHDS2A protocol ID = 28 (decimal) / 0x1C
PROTOCOL_AFHDS2A: int = 28
SUBP_AFHDS2A_PWM_IBUS = 0
SUBP_AFHDS2A_PPM_IBUS = 1
SUBP_AFHDS2A_PWM_SBUS = 2
SUBP_AFHDS2A_PPM_SBUS = 3
SUBP_AFHDS2A_GYRO_OFF = 4
SUBP_AFHDS2A_GYRO_ON = 5
SUBP_AFHDS2A_GYRO_ON_REV = 6
PROTOCOL_AFHDS2A: int | None = None  # set the correct integer ID for AFHDS2A
_PROTOCOL_NAME_MAP: dict[str, str] = {
    "afhds2a": "AFHDS2A",
}


class MultiSerialTX:
    def __init__(
        self,
        port: str,
        *,
        protocol: int = PROTOCOL_AFHDS2A,  # default FS-iA10B (AFHDS2A)
        sub_protocol: int = SUBP_AFHDS2A_PWM_IBUS,  # PWM/iBUS output
        rx_num: int = 0,
        option: int = 0,
        power_low: bool = False,
        autobind: bool = False,
        bind: bool = False,
        range_check: bool = False,
        debug_print: bool = False,
        disabled: bool = False,
    ):
        # Configuration
        self.port_name = port
        self.protocol = protocol
        self.sub_protocol = sub_protocol
        self.rx_num = rx_num
        self.option = option
        self.power_low = power_low
        self.autobind = autobind
        self.bind = bind
        self.range_check = range_check
        self.debug_print = debug_print
        self.disabled = disabled
        # Runtime state
        self._lock = threading.Lock()
        self._last_error_print = 0.0
        self._error_count = 0
        self._serial = None
        self._baud = 100000
        # Logging state
        self._frame_counter = 0
        self._log_every = int(os.environ.get("PI_TX_UART_LOG_EVERY", "0"))
        if os.environ.get("PI_TX_UART_DEBUG") == "1":
            self.debug_print = True
        self._max_value_log = int(os.environ.get("PI_TX_UART_MAX_VALUE_LOG", "8"))
        # Timed bind window end timestamp (epoch seconds); 0 => inactive
        self._bind_until = 0.0
        # legacy suppression log removed (we keep frames flowing during bind)
        # Environment overrides for protocol selection
        # 1. Explicit numeric override
        env_pid = os.environ.get("PI_TX_PROTOCOL_ID")
        if env_pid:
            try:
                self.protocol = int(env_pid, 0)
            except ValueError:
                pass
        # Channel count heuristic: FS-iA10B uses 10 primary channels (set 10 by default for AFHDS2A)
        self.max_channels = 10 if self.protocol == PROTOCOL_AFHDS2A else 16
        # 2. Name-based mapping (currently only AFHDS2A placeholder)
        env_pname = os.environ.get("PI_TX_PROTOCOL_NAME", "").lower()
        if env_pname:
            if env_pname in _PROTOCOL_NAME_MAP:
                if env_pname == "afhds2a":
                    self.protocol = PROTOCOL_AFHDS2A
        # Ensure cap
        if self.max_channels > 16:
            self.max_channels = 16
        env_sp = os.environ.get("PI_TX_SUB_PROTOCOL")
        if env_sp:
            try:
                self.sub_protocol = int(env_sp, 0) & 0x1F
            except ValueError:
                pass
        # Sub protocol name override (afhds2a only)
        env_sp_name = os.environ.get("PI_TX_SUB_PROTOCOL_NAME", "").lower()
        if env_sp_name:
            afhds2a_subs = {
                "pwm_ibus": SUBP_AFHDS2A_PWM_IBUS,
                "ppm_ibus": SUBP_AFHDS2A_PPM_IBUS,
                "pwm_sbus": SUBP_AFHDS2A_PWM_SBUS,
                "ppm_sbus": SUBP_AFHDS2A_PPM_SBUS,
                "gyro_off": SUBP_AFHDS2A_GYRO_OFF,
                "gyro_on": SUBP_AFHDS2A_GYRO_ON,
                "gyro_on_rev": SUBP_AFHDS2A_GYRO_ON_REV,
            }
            if env_sp_name in afhds2a_subs:
                self.sub_protocol = afhds2a_subs[env_sp_name]
        # Channel count heuristic: default 16, AFHDS2A typical 14 / 10; allow env override
        self.max_channels = 16
        env_mc = os.environ.get("PI_TX_MAX_CHANNELS")
        if env_mc:
            try:
                self.max_channels = max(1, min(16, int(env_mc)))
            except ValueError:
                pass
        else:
            if (
                PROTOCOL_AFHDS2A is not None and self.protocol == PROTOCOL_AFHDS2A
            ) and self.max_channels > 10:
                self.max_channels = 10  # typical receiver channel count
                self.max_channels = 10  # FS-iA10B typical active channels

    def _now_parts(self):
        now = time.time()
        int_part = int(now)
        ms = int((now - int_part) * 1000)
        ts = time.strftime("%H:%M:%S", time.localtime(int_part))
        return ts, ms

    def _log(self, msg: str):
        ts, ms = self._now_parts()
        print(f"[UART {ts}.{ms:03d}] {msg}")

    def open(self):
        if self.disabled:
            return
        if self._serial is not None:
            return
        if not ON_PI:
            raise RuntimeError("UART enabled only on Raspberry Pi in this build")
        if not HAVE_PYSERIAL:
            raise RuntimeError("pyserial module not available; pip install pyserial")
        try:
            self._log("Opening pyserial port")
            candidates = [self.port_name]
            if self.port_name == "/dev/serial0":
                candidates.extend(["/dev/ttyAMA0", "/dev/ttyS0"])  # typical Pi names
            ser = None
            first_err = None
            for p in candidates:
                try:
                    ser = serial.Serial(
                        port=p,
                        baudrate=self._baud,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_EVEN,
                        stopbits=serial.STOPBITS_TWO,
                        timeout=0,
                        write_timeout=0.05,
                        exclusive=True,
                    )
                    self.port_name = p
                    break
                except Exception as e:
                    if first_err is None:
                        first_err = e
            if ser is None:
                diag = [
                    f"open failed starting from {self.port_name} first_error={first_err}",
                ]
                for p in candidates:
                    try:
                        st = os.stat(p)
                        diag.append(
                            f"{p}:exists mode={oct(st.st_mode & 0o777)} uid={st.st_uid} gid={st.st_gid}"
                        )
                    except FileNotFoundError:
                        diag.append(f"{p}:missing")
                    except Exception as es:
                        diag.append(f"{p}:stat_err={es}")
                self._log(" | ".join(diag))
                raise RuntimeError("UART open failed (pyserial)")
            self._serial = ser
            self._log(
                f"Opened port={self.port_name} baud={self._baud} 8E2 via pyserial"
            )
            # Optional automatic bind at startup
            if os.environ.get("PI_TX_UART_BIND_AT_START") == "1":
                sec = float(os.environ.get("PI_TX_UART_BIND_SECONDS", "2"))
                self.start_bind(sec)
        except Exception:
            # Ensure cleanup
            try:
                if self._serial:
                    self._serial.close()
            except Exception:
                pass
            self._serial = None
            raise

    def close(self):
        try:
            if self._serial:
                self._log("Closing serial port")
                try:
                    self._serial.flush()
                except Exception:
                    pass
                self._serial.close()
        except Exception:
            pass
        finally:
            self._serial = None

    def build_frame(self, ch_values: Sequence[float]) -> bytes:
        # Expect up to max_channels (pad to 16 for packing)
        mc = getattr(self, "max_channels", 16)
        vals = list(ch_values[:mc]) + [0.0] * (mc - len(ch_values))
        # Always extend to 16 for the wire format (unused channels zeroed)
        if len(vals) < 16:
            vals.extend([0.0] * (16 - len(vals)))

        # Convert to 0..2047 range (approx mapping from -1..+1)
        def to_raw(v: float) -> int:
            v = max(-1.0, min(1.0, v))
            raw = int(round((v * 0.5 + 0.5) * 2047))
            return max(0, min(2047, raw))

        raws = [to_raw(v) for v in vals]
        header = 0x55 if self.protocol < 32 else 0x54  # we keep protocol <32 now
        byte1 = self.protocol & 0x1F
        if self.autobind:
            byte1 |= 0x20
        if self.range_check:
            byte1 |= 0x40
        # Determine whether bind flag active (static or timed window)
        active_bind = self.bind or (time.time() < self._bind_until)
        if self.debug_print and self._frame_counter % 25 == 0:
            self._log(
                f"bind_state active={active_bind} static={self.bind} until={self._bind_until:.2f} now={time.time():.2f}"
            )
        if active_bind:
            byte1 |= 0x80
        byte2 = (self.rx_num & 0x0F) | ((self.sub_protocol & 0x07) << 4)
        if self.power_low:
            byte2 |= 0x80
        frame = bytearray(26)
        frame[0] = header
        frame[1] = byte1
        frame[2] = byte2
        frame[3] = (self.option + 256) % 256
        # Pack 16 * 11 bits starting at frame[4]
        bit_pos = 0
        for raw in raws:
            for i in range(11):
                if raw & (1 << i):
                    byte_index = 4 + (bit_pos // 8)
                    bit_in_byte = bit_pos % 8
                    frame[byte_index] |= 1 << bit_in_byte
                bit_pos += 1
        frame_bytes = bytes(frame)
        self._frame_counter += 1
        if self.debug_print or (
            self._log_every and (self._frame_counter % self._log_every == 0)
        ):
            preview_vals = ",".join(f"{v:+.2f}" for v in vals[: self._max_value_log])
            self._log(
                f"frame#{self._frame_counter} hdr={header:02X},{byte1:02X},{byte2:02X},{frame[3]:02X} first8={frame_bytes[:8].hex()} vals={preview_vals}"
            )
        return frame_bytes

    def start_bind(self, seconds: float = 2.0):
        if seconds <= 0:
            return
        self._bind_until = time.time() + seconds
        self._log(
            f"Bind window started for {seconds:.2f}s (until {self._bind_until:.2f})"
        )
        # Log an immediate frame preview with bind bit expectation
        try:
            self._log("Bind flag will be set in outgoing frames during window")
        except Exception:
            pass

    @property
    def bind_active(self) -> bool:
        return self.bind or (time.time() < self._bind_until)

    def _drain_loopback(self):
        # No loopback handling
        return

    def send_frame(self, frame: bytes):
        if self.disabled:
            return
        with self._lock:
            try:
                if not self._serial:
                    raise RuntimeError("serial not open")
                self._serial.write(frame)
                if self.debug_print and os.environ.get("PI_TX_UART_RAW_HEX") == "1":
                    self._log(f"raw={frame.hex()}")
            except Exception as e:
                self._error_count += 1
                now = time.time()
                if now - self._last_error_print > 2.0:
                    self._log(
                        f"WRITE ERROR count={self._error_count} type={type(e).__name__} detail={e!r}"
                    )
                    self._last_error_print = now
                try:
                    self.close()
                    self.open()
                    self._error_count = 0
                except Exception:
                    pass

    def send_channels(self, ch_values: Sequence[float]):
        frame = self.build_frame(ch_values)
        self.send_frame(frame)


class PeriodicChannelSender:
    def __init__(self, tx: MultiSerialTX, sampler, rate_hz: float = 50.0):
        self.tx = tx
        self.sampler = sampler  # callable returning sequence of channel floats
        self.interval = 1.0 / rate_hz
        self._thread = None
        self._stop = threading.Event()

    # no file logging when using console debug

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.tx.open()
        # no file logging setup
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._thread:
            return
        self._stop.set()
        self._thread.join(timeout=2)
        self._thread = None

    # nothing to close for console logging

    def _loop(self):
        monotonic = time.monotonic
        start = monotonic()
        frame_index = 0
        interval = self.interval
        last_report = start
        drift_interval = float(os.environ.get("PI_TX_UART_DRIFT_INTERVAL", "1.0"))
        while not self._stop.is_set():
            target = start + frame_index * interval
            now = monotonic()
            if now - last_report >= drift_interval:
                actual_rate = frame_index / (now - start) if frame_index else 0.0
                try:
                    self.tx._log(
                        f"rate={actual_rate:.2f}Hz frames={frame_index} drift={(now - target):+.4f}s"
                    )
                except Exception:
                    pass
                last_report = now
            # Sleep until the target time
            if now < target:
                to_sleep = target - now
                # Cap very large sleep in case interval changed
                if to_sleep > interval:
                    to_sleep = interval
                time.sleep(to_sleep)
                continue
            # If we are late by more than one interval, skip ahead to avoid drift
            if now - target > interval:
                frame_index = int((now - start) / interval)
                target = start + frame_index * interval
            try:
                values = self.sampler()
                frame = self.tx.build_frame(values)
                self.tx.send_frame(frame)
            except Exception as e:
                try:
                    self.tx._log(f"LOOP ERROR: {e!r}")
                except Exception:
                    print(f"Periodic sender error: {e}")
            frame_index += 1

    # End of PeriodicChannelSender
