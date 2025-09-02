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
            from .infrastructure.uart_tx import UartTx, MultiSerialTX

            def sample():
                snap = channel_store.snapshot()
                if len(snap) < 16:
                    snap = snap + [0.0] * (16 - len(snap))
                return snap[:16]

            port = os.environ.get("UART_PORT") or "/dev/serial0"
            uart = UartTx(port=port)
            if not uart.open():
                raise Exception(f"Failed to open UART port: {port}")

            tx = MultiSerialTX(uart, channel_count=16)
            tx.set_sampler(sample, normalized=True)  # -1..1 input expected
            tx.start()

            global UART_SENDER
            UART_SENDER = tx  # store tx for stop
            print("UART transmission started (internal sampler)")

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
        from .infrastructure.uart_tx import UartTx, MultiSerialTX

        def sample():
            snap = channel_store.snapshot()
            if len(snap) < 16:
                snap = snap + [0.0] * (16 - len(snap))
            return snap[:16]

        port = os.environ.get("UART_PORT") or "/dev/serial0"
        uart = UartTx(port=port)
        if not uart.open():
            raise Exception(f"Failed to open UART port: {port}")

        tx = MultiSerialTX(uart, channel_count=16)
        tx.set_sampler(sample, normalized=True)
        tx.start()

        UART_SENDER = tx
        UART_INIT_ERROR = None
        print("UART retry successful (internal sampler)")
        return True
    except Exception as e:
        UART_INIT_ERROR = f"{type(e).__name__}: {e}"
        print(f"UART retry failed: {UART_INIT_ERROR}")
        if os.environ.get("PI_TX_UART_TRACE") == "1":
            traceback.print_exc()
        return False
