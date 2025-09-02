import time
import math

from pi_tx.infrastructure.uart_tx import DebugUartTx, MultiSerialTX


def xor_checksum(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c


def test_frame_basic_structure():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=6)
    frame = tx.get_frame_once()
    # header
    assert frame[0] == 0x55
    # length should be 5 + 2*N + 1
    expected_len = 5 + 2 * 6 + 1
    assert len(frame) == expected_len
    # checksum
    assert xor_checksum(frame[1:-1]) == frame[-1]


def test_channel_packing_roundtrip():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=5)
    vals = [0, 1, 1023, 1024, 2047]
    tx.set_channels(vals)
    frame = tx.get_frame_once()
    chan_bytes = frame[5:-1]
    out = []
    for i in range(0, len(chan_bytes), 2):
        lo = chan_bytes[i]
        hi = chan_bytes[i + 1] & 0x07
        out.append(lo | (hi << 8))
    assert out == vals


def test_flag_bits():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=2)
    # baseline flags (no bind/range/auto)
    f0 = tx.get_frame_once()[2]
    assert (f0 & 0xE0) == 0
    tx.set_bind_mode(True)
    bind_flags = tx.get_frame_once()[2]
    assert (bind_flags & 0x80) != 0
    tx.set_range_check(True)
    range_flags = tx.get_frame_once()[2]
    assert (range_flags & 0xC0) == 0xC0  # bind + range bits
    tx.set_autobind(True)
    auto_flags = tx.get_frame_once()[2]
    assert (auto_flags & 0xE0) == 0xE0  # all three bits


def test_option_mapping():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg)
    for val in [-40, -32, -1, 0, 31, 40]:
        tx.set_option(val)
        frame = tx.get_frame_once()
        stored = frame[3]
        # Recover signed: (stored-32), original clamped to -32..31
        clamped = max(-32, min(31, val))
        recovered = ((stored & 0xFF) - 32) if stored < 128 else stored - 256 - 32
        assert recovered == clamped, (val, stored, recovered)


def test_sampler_normalized_scaling():
    dbg = DebugUartTx()
    dbg.open()
    seqs = [[-1.0, 0.0, 1.0], [0.5, -0.5, 0.0]]
    out_sets = []
    tx = MultiSerialTX(dbg, channel_count=3)

    def sampler_gen():
        for s in seqs:
            yield s

    gen = sampler_gen()

    def sampler():
        return next(gen)

    tx.set_sampler(sampler, normalized=True)
    # First sample
    tx.sample_once()
    c1 = tx.get_channels()
    # Second sample
    tx.sample_once()
    c2 = tx.get_channels()
    out_sets.append(c1)
    out_sets.append(c2)
    # Check boundaries
    assert c1[0] == 0 and c1[1] in (1023, 1024) and c1[2] >= 2046
    # Monotonic mapping check for second set (-0.5 < 0.0 < 0.5)
    assert c2[1] < c2[2]
    assert 0 <= min(c1 + c2) and max(c1 + c2) <= 2047


def test_debug_capture_frames():
    dbg = DebugUartTx(max_frames=3)
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=2, frame_rate_hz=20)
    tx.start()
    time.sleep(0.2)  # allow several frames
    tx.stop()
    frames = dbg.all_frames()
    assert 1 <= len(frames) <= 3  # ring buffer capped
    last = frames[-1]
    assert "parsed" in last and "channels" in last["parsed"]


def test_thread_start_stop_idempotent():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=1, frame_rate_hz=10)
    tx.start()
    tx.start()
    time.sleep(0.05)
    tx.stop()
    tx.stop()  # should not raise
    # ensure at least one frame captured
    assert dbg.latest() is not None


def test_sampler_exception_suppression():
    dbg = DebugUartTx()
    dbg.open()
    calls = {"n": 0}

    def bad_sampler():
        calls["n"] += 1
        raise RuntimeError("boom")

    tx = MultiSerialTX(dbg, channel_count=1, frame_rate_hz=25)
    tx.set_sampler(bad_sampler)
    tx.start()
    time.sleep(0.12)
    tx.stop()
    # sampler was invoked several times but errors were suppressed (no crash)
    assert calls["n"] >= 2


def test_rx_num_clamp_and_encoding():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=1)
    for val in [-5, 0, 7, 15, 99]:
        tx.set_rx_num(val)
        frame = tx.get_frame_once()
        encoded = frame[4]
        clamped = min(15, max(0, val))
        assert encoded == clamped


def test_sub_protocol_masking():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=1)
    for sub in [0, 1, 0x1F, 0x3A]:
        tx.set_sub_protocol(sub)
        frame = tx.get_frame_once()
        flags = frame[2]
        assert (flags & 0x1F) == (sub & 0x1F)


def test_frame_length_formula_various_channel_counts():
    dbg = DebugUartTx()
    dbg.open()
    for ch in [1, 2, 8, 10, 16]:
        tx = MultiSerialTX(dbg, channel_count=ch)
        frame = tx.get_frame_once()
        assert len(frame) == 5 + 2 * ch + 1


def test_checksum_error_detection_in_debug_parser():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=3)
    frame = bytearray(tx.get_frame_once())
    # Corrupt one channel byte
    frame[6] ^= 0xFF
    dbg.send_bytes(bytes(frame))
    parsed = dbg.latest()["parsed"]
    assert parsed.get("error") == "checksum"


def test_bind_for_seconds_sets_and_clears_flag():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=1, frame_rate_hz=30)
    # monkey patch set_bind_mode to observe transitions
    transitions = []
    real_set = tx.set_bind_mode

    def tracking_set(v):
        transitions.append(v)
        real_set(v)

    tx.set_bind_mode = tracking_set  # type: ignore
    start = time.time()
    tx.bind_for_seconds(0.15)
    dur = time.time() - start
    assert dur >= 0.14  # approximate
    assert transitions[0] is True and transitions[-1] is False


def test_channel_count_overflow_ignored():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=4)
    tx.set_channels([0, 100, 200, 300, 400, 500])  # extra values ignored
    frame = tx.get_frame_once()
    chan_bytes = frame[5:-1]
    decoded = []
    for i in range(0, len(chan_bytes), 2):
        lo = chan_bytes[i]
        hi = chan_bytes[i + 1] & 0x07
        decoded.append(lo | (hi << 8))
    assert decoded == [0, 100, 200, 300]


def test_model_id_attached_to_debug_frames():
    dbg = DebugUartTx()
    dbg.open()
    tx = MultiSerialTX(dbg, channel_count=2, frame_rate_hz=25)
    tx.set_model_id("abc123")
    tx.start()
    time.sleep(0.08)
    tx.stop()
    frames = dbg.all_frames()
    assert frames, "No frames captured"
    # Find a frame with meta.model_id
    meta_ids = [f.get("meta", {}).get("model_id") for f in frames]
    assert "abc123" in meta_ids
