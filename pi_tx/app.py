# Configure Kivy window size for 800x480 screen BEFORE importing any Kivy modules
from kivy.config import Config

Config.set("graphics", "width", "800")
Config.set("graphics", "height", "480")
Config.set("graphics", "resizable", "0")  # Disable resizing for embedded display

import os, traceback
from .logging_config import get_logger

log = get_logger(__name__)
from .domain.channel_store import channel_store

UART_SENDER = None
UART_INIT_ERROR = None  # store last init exception string
from .ui.main import create_app


def run():
    app = create_app()
    # Enable UART on Raspberry Pi hardware OR when debug mode is explicitly requested
    try:
        from .infrastructure.uart_tx import ON_PI
    except Exception:
        ON_PI = False  # type: ignore

    # Allow debug UART mode even when not on Pi
    debug_mode = bool(os.environ.get("PI_TX_DEBUG_UART"))
    enable_uart = ON_PI or debug_mode

    if enable_uart:
        try:
            from .infrastructure.uart_tx import UartTx, MultiSerialTX, DebugUartTx

            def sample():
                snap = channel_store.snapshot()
                if len(snap) < 16:
                    snap = snap + [0.0] * (16 - len(snap))
                return snap[:16]

            port = os.environ.get("UART_PORT") or "/dev/serial0"
            verbose_uart_logging = bool(os.environ.get("PI_TX_UART_VERBOSE"))
            if debug_mode:
                uart = DebugUartTx(verbose_logging=verbose_uart_logging)
                log.info("Using Debug UART (no real hardware needed)")
                if verbose_uart_logging:
                    log.info("Verbose UART logging enabled - frame details logged")
            else:
                uart = UartTx(port=port)
                log.info("Using real UART on port: %s", port)
            if not uart.open():
                raise Exception(f"Failed to open UART port: {port}")

            tx = MultiSerialTX(uart, channel_count=16)
            tx.set_sampler(sample, normalized=True)  # -1..1 input expected
            tx.start()

            global UART_SENDER
            UART_SENDER = tx  # store tx for stop
            if debug_mode:
                log.info(
                    "UART debug transmission started (frames captured in DebugUartTx)"
                )
            else:
                log.info("UART transmission started (internal sampler)")

            def _shutdown(*_):
                try:
                    UART_SENDER.stop()
                except Exception:
                    pass

            try:
                app.bind(on_stop=_shutdown)
            except Exception:
                pass
        except Exception as e:
            global UART_INIT_ERROR
            UART_INIT_ERROR = f"{type(e).__name__}: {e}"
            log.error("UART init failed: %s", UART_INIT_ERROR)
            if os.environ.get("PI_TX_UART_TRACE") == "1":
                traceback.print_exc()
    else:
        if ON_PI:
            log.info("UART disabled (not running on Raspberry Pi)")
        else:
            log.info("UART disabled (set PI_TX_DEBUG_UART=1 to enable debug mode)")
    app.run()


def retry_uart_init():
    """Allow manual retry of UART initialization (can be wired to a UI button)."""
    global UART_SENDER, UART_INIT_ERROR
    if UART_SENDER:
        log.info("UART already active")
        return True
    try:
        from .infrastructure.uart_tx import ON_PI
    except Exception:
        log.warning("UART retry: detection import failed")
        return False
    if not ON_PI:
        log.warning(
            "UART retry: not detected as Raspberry Pi (set PI_TX_FORCE_PI=1 to override)"
        )
        return False
    try:
        from .infrastructure.uart_tx import UartTx, MultiSerialTX, DebugUartTx

        def sample():
            snap = channel_store.snapshot()
            if len(snap) < 16:
                snap = snap + [0.0] * (16 - len(snap))
            return snap[:16]

        port = os.environ.get("UART_PORT") or "/dev/serial0"
        debug_mode = bool(os.environ.get("PI_TX_DEBUG_UART"))
        if debug_mode:
            uart = DebugUartTx()
        else:
            uart = UartTx(port=port)
        if not uart.open():
            raise Exception(f"Failed to open UART port: {port}")

        tx = MultiSerialTX(uart, channel_count=16)
        tx.set_sampler(sample, normalized=True)
        tx.start()

        UART_SENDER = tx
        UART_INIT_ERROR = None
        if debug_mode:
            log.info("UART retry successful (debug mode, frames captured)")
        else:
            log.info("UART retry successful (internal sampler)")
        return True
    except Exception as e:
        UART_INIT_ERROR = f"{type(e).__name__}: {e}"
        log.error("UART retry failed: %s", UART_INIT_ERROR)
        if os.environ.get("PI_TX_UART_TRACE") == "1":
            traceback.print_exc()
        return False


def dump_debug_frames(limit: int = 5):
    """Print most recent captured frames when running with PI_TX_DEBUG_UART=1."""
    tx = globals().get("UART_SENDER")
    if not tx:
        log.info("No UART sender active")
        return
    debug_uart = getattr(tx, "_uart", None)
    if not debug_uart or not hasattr(debug_uart, "all_frames"):
        log.info("Not in debug UART mode or no frames captured")
        return
    frames = debug_uart.all_frames()
    if not frames:
        log.info("No frames captured yet")
        return
    for i, f in enumerate(frames[-limit:], 1):
        parsed = f.get("parsed", {})
        chans = parsed.get("channels", [])
        log.info(
            "[%d] proto=%s sub=%s bind=%s rx=%s chans=%s total=%d",
            i,
            parsed.get("protocol"),
            parsed.get("sub_protocol"),
            parsed.get("bind"),
            parsed.get("rx_num"),
            chans[:10],
            len(chans),
        )
