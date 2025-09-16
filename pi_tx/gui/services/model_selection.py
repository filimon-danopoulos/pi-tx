from __future__ import annotations
from typing import Dict, Tuple, Optional, Callable
from .model_manager import ModelManager, Model


class ModelSelectionController:
    """Coordinates applying a model to runtime subsystems.

    Responsibilities moved out of the Kivy App:
      * Load model via ModelManager
      * Rebuild ChannelPanel rows
      * Re-map input controller channel bindings
      * Persist last model
      * Propagate RX / model identifiers to UART transmitter (if present)

    The GUI remains responsible only for updating UI properties & dispatching events.
    """

    def __init__(
        self,
        model_manager: ModelManager,
        input_controller,
        channel_panel=None,
        uart_resolver: Optional[Callable[[], object]] = None,
    ):
        self._model_manager = model_manager
        self._input = input_controller
        self._panel = channel_panel
        self._uart_resolver = uart_resolver or self._default_uart_resolver

    def set_channel_panel(self, panel):
        self._panel = panel

    # --- Public API -----------------------------------------------------
    def apply_selection(self, model_name: str) -> Tuple[Model, Dict[str, Dict]]:
        model, mapping = self._model_manager.load_and_apply(model_name)
        # UI channel rows
        if self._panel is not None:
            self._panel.rebuild(mapping)
        # Input re-mapping
        if self._input is not None:
            try:
                self._input.clear_values()
                for channel, cfg in mapping.items():
                    try:
                        ch_id = int(channel)
                        device_path = cfg.get("device_path")
                        code_raw = str(cfg.get("control_code", ""))
                        if not device_path or not code_raw.isdigit():  # virtual channel
                            continue
                        control_code = int(code_raw)
                        self._input.register_channel_mapping(
                            device_path, control_code, ch_id
                        )
                    except Exception as e:  # pragma: no cover (defensive per mapping)
                        print(f"Failed to register mapping for channel {channel}: {e}")
                self._input.start()
            except Exception as e:  # pragma: no cover
                print(f"Input mapping apply failed: {e}")
        # Persist selection
        self._model_manager.persist_last(model_name)
        # Propagate identifiers to UART transmitter if available
        self._apply_uart_metadata(model)
        return model, mapping

    # --- Internals ------------------------------------------------------
    def _apply_uart_metadata(self, model: Model):  # pragma: no cover (runtime/hardware)
        try:
            uart = self._uart_resolver()
            if not uart:
                return
            if hasattr(uart, "set_rx_num"):
                uart.set_rx_num(getattr(model, "rx_num", 0))
            if hasattr(uart, "set_model_id"):
                uart.set_model_id(getattr(model, "model_id", None))
        except Exception as e:
            print(f"Warning: could not apply rx_num/model_id to transmitter: {e}")

    @staticmethod
    def _default_uart_resolver():  # pragma: no cover
        try:
            from ... import app as app_mod  # local import to avoid cyclic UI deps

            return getattr(app_mod, "UART_SENDER", None)
        except Exception:
            return None
