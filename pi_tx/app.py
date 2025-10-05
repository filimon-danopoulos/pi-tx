import os, traceback
from .logging import get_logger

log = get_logger(__name__)

UART_SENDER = None
UART_INIT_ERROR = None  # store last init exception string
APP_INSTANCE = None  # store app instance for UART sampler
from .ui.main import create_app
from .domain.uart_tx import UartTx, MultiSerialTX


def run():
    global APP_INSTANCE
    app = create_app()
    APP_INSTANCE = app  # Store for UART sampler access

    def sample():
        # Get values from the current model
        if app.current_model:
            values = app.current_model.readValues()
            snap = [values.get(ch.name, 0.0) for ch in app.current_model.channels]
        else:
            snap = []

        # Pad to 16 channels
        if len(snap) < 16:
            snap = snap + [0.0] * (16 - len(snap))
        return snap[:16]

    port = os.environ.get("UART_PORT") or "/dev/null"
    uart = UartTx(port=port)
    log.info("Using UART on port: %s", port)
    if uart.open():

        tx = MultiSerialTX(uart, channel_count=16)
        tx.set_sampler(sample, normalized=True)  # -1..1 input expected
        tx.start()

        global UART_SENDER
        UART_SENDER = tx  # store tx for stop
    else:
        log.warning("UART not opened.")

    log.info("UART transmission started")

    def _shutdown(*_):
        try:
            UART_SENDER.stop()
        except Exception:
            pass

    try:
        app.bind(on_stop=_shutdown)
    except Exception:
        pass
    app.run()
