from .input.controls import InputController
from kivy.config import Config
import os
from .domain.channel_store import channel_store

UART_SENDER = None
from .input.controls import InputController
from .ui.gui import create_gui


def run():
    controller = InputController(debug=False)
    app = create_gui(controller)
    # UART integration (real port if UART_PORT set, else loopback with console print)
    try:
        from .infrastructure.uart_tx import MultiSerialTX, PeriodicChannelSender

        def sample():
            snap = channel_store.snapshot()  # index 0 -> channel 1
            # Ensure length at least 16
            if len(snap) < 16:
                snap = snap + [0.0] * (16 - len(snap))
            return snap[:16]

        port = os.environ.get("UART_PORT") or "loop://"  # pyserial loopback URL
        debug = not os.environ.get("UART_PORT")  # only print when using loopback
        tx = MultiSerialTX(port=port, debug_print=debug)
        sender = PeriodicChannelSender(tx, sample, rate_hz=50.0)
        sender.start()
        global UART_SENDER
        UART_SENDER = sender

        # Register a shutdown hook so the sender is stopped and serial closed
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
            # If binding fails for any reason, attempt to ensure cleanup at exit
            pass
    except Exception as e:
        print(f"UART init failed: {e}")
    app.run()
