import sys, types, importlib, time


def test_uart_serial_config(monkeypatch):
    # Prepare dummy serial module to intercept Serial creation
    called = {}

    class DummySerial:
        def __init__(
            self, *, port, baudrate, bytesize, parity, stopbits, timeout, write_timeout
        ):
            called.update(
                dict(
                    port=port,
                    baudrate=baudrate,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits,
                    timeout=timeout,
                    write_timeout=write_timeout,
                )
            )
            self.is_open = True

        def write(self, data: bytes):
            called["last_write_len"] = len(data)

        def flush(self):
            pass

        def close(self):
            self.is_open = False

    serial_mod = types.SimpleNamespace(Serial=DummySerial)
    monkeypatch.setitem(sys.modules, "serial", serial_mod)

    # Reload uart module so it picks up dummy serial
    import pi_tx.infrastructure.uart_tx as uart_tx

    importlib.reload(uart_tx)

    u = uart_tx.UartTx(port="TESTPORT")
    assert u.open() is True
    assert called["port"] == "TESTPORT"
    assert called["baudrate"] == 100000
    assert called["bytesize"] == 8
    assert called["parity"] == "E"
    assert called["stopbits"] == 2


def test_channel_value_clamp_and_encoding():
    from pi_tx.infrastructure.uart_tx import DebugUartTx, MultiSerialTX

    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=3)
    tx.set_channels([-100, 1024, 99999])  # extremes + mid
    frame = tx.get_frame_once()
    chan_bytes = frame[5:-1]
    decoded = []
    for i in range(0, len(chan_bytes), 2):
        lo = chan_bytes[i]
        hi = chan_bytes[i + 1] & 0x07
        decoded.append(lo | (hi << 8))
    assert decoded == [0, 1024, 2047]


def test_frame_rate_approximation():
    from pi_tx.infrastructure.uart_tx import DebugUartTx, MultiSerialTX

    dbg = DebugUartTx(max_frames=200)
    dbg.open()
    target_hz = 40.0
    tx = MultiSerialTX(dbg, channel_count=2, frame_rate_hz=target_hz)
    tx.start()
    dur = 0.25
    time.sleep(dur)
    tx.stop()
    frames = dbg.all_frames()
    # Expect at least 50% of ideal frames (allow for scheduling jitter)
    ideal = target_hz * dur
    assert (
        len(frames) >= ideal * 0.5
    ), f"Too few frames: got {len(frames)} expected >= {ideal*0.5}"
