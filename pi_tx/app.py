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
    # Only enable UART on Raspberry Pi hardware
    try:
        from .infrastructure.uart_tx import ON_PI
    except Exception:
        ON_PI = False  # type: ignore

    if ON_PI:
        try:
            from .infrastructure.uart_tx import MultiSerialTX, PeriodicChannelSender

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
            print(f"UART init failed: {e}")
    else:
        print("UART disabled (not running on Raspberry Pi)")
    app.run()
