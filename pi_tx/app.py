from .input.controls import InputController
from kivy.config import Config
import os, traceback
from .domain.channel_store import channel_store

UART_SENDER = None
UART_INIT_ERROR = None  # store last init exception string
from .input.controls import InputController
from .ui.gui import create_gui


def run():
    controller = InputController(debug=False)
    app = create_gui(controller)
    # Only enable UART on Raspberry Pi hardware
    try:
        from .infrastructure.uart_tx import ON_PI
    except Exception:
        ON_PI = False  # type: ignore

    if ON_PI:
        try:
            from .infrastructure.uart_tx import MultiSerialTX, PeriodicChannelSender

            # Show detection reasons if debug requested
            if os.environ.get("PI_TX_UART_DETECT_DEBUG") == "1":
                try:
                    from .infrastructure.uart_tx import _ON_PI_RESULT  # type: ignore

                    print(f"UART detection detail: {_ON_PI_RESULT[1]}")
                except Exception:
                    pass

            def sample():
                snap = channel_store.snapshot()
                if len(snap) < 16:
                    snap = snap + [0.0] * (16 - len(snap))
                return snap[:16]

            port = (
                os.environ.get("UART_PORT") or "/dev/serial0"
            )  # prefer real port on Pi
            debug = False  # suppress debug prints on real hardware by default
            tx = MultiSerialTX(port=port, debug_print=debug)
            sender = PeriodicChannelSender(tx, sample, rate_hz=50.0)
            sender.start()
            global UART_SENDER
            UART_SENDER = sender
            print("UART sender started")

            def _shutdown(*_):
                try:
                    sender.stop()
                except Exception:
                    pass
                try:
                    sender.tx.close()
                except Exception:
                    pass

            try:
                app.bind(on_stop=_shutdown)
            except Exception:
                pass
        except Exception as e:
            global UART_INIT_ERROR
            UART_INIT_ERROR = f"{type(e).__name__}: {e}"
            print(f"UART init failed: {UART_INIT_ERROR}")
            if os.environ.get("PI_TX_UART_TRACE") == "1":
                traceback.print_exc()
    else:
        print("UART disabled (not running on Raspberry Pi)")
    app.run()


def retry_uart_init():
    """Allow manual retry of UART initialization (can be wired to a UI button)."""
    global UART_SENDER, UART_INIT_ERROR
    if UART_SENDER:
        print("UART already active")
        return True
    try:
        from .infrastructure.uart_tx import ON_PI
    except Exception:
        print("UART retry: detection import failed")
        return False
    if not ON_PI:
        print(
            "UART retry: not detected as Raspberry Pi (set PI_TX_FORCE_PI=1 to override)"
        )
        return False
    try:
        from .infrastructure.uart_tx import MultiSerialTX, PeriodicChannelSender
        from .domain.channel_store import channel_store

        def sample():
            snap = channel_store.snapshot()
            if len(snap) < 16:
                snap = snap + [0.0] * (16 - len(snap))
            return snap[:16]

        port = os.environ.get("UART_PORT") or "/dev/serial0"
        tx = MultiSerialTX(port=port, debug_print=False)
        sender = PeriodicChannelSender(tx, sample, rate_hz=50.0)
        sender.start()
        UART_SENDER = sender
        UART_INIT_ERROR = None
        print("UART retry successful")
        return True
    except Exception as e:
        UART_INIT_ERROR = f"{type(e).__name__}: {e}"
        print(f"UART retry failed: {UART_INIT_ERROR}")
        if os.environ.get("PI_TX_UART_TRACE") == "1":
            traceback.print_exc()
        return False
