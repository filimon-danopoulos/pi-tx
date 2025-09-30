from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivy.uix.widget import Widget


class AggregateEditDialog:
    """Placeholder dialog for editing an aggregate processor.

    (Future) Expected fields:
      - Target channel selector
      - Source channel multi-select with weights
    """

    def __init__(self, on_close=None):
        self.on_close = on_close
        self.on_delete = None
        self.dialog: MDDialog | None = None
        self._delete_confirm_dialog: MDDialog | None = None

    def show(
        self,
        target: str,
        sources: str,
        can_delete: bool = False,
        on_delete=None,
    ):
        if self.dialog and self.dialog.parent:
            return
        self.on_delete = on_delete if can_delete else None
        text = (
            "Edit Aggregate (placeholder)\n\n"
            f"Target: {target}\nSources: {sources or '-'}\n\n"
            "Future: add/remove source channels & weights, pick target channel."
        )
        buttons = []
        if self.on_delete:
            btn_delete = MDFlatButton(
                text="DELETE",
                on_release=lambda *_: self._open_delete_confirm(),
            )
            try:  # pragma: no cover - UI styling
                btn_delete.theme_text_color = "Custom"
                btn_delete.text_color = (1, 0.2, 0.2, 1)
            except Exception:
                pass
            buttons.append(btn_delete)
            buttons.append(Widget(size_hint_x=1))
        buttons.append(MDFlatButton(text="CLOSE", on_release=lambda *_: self.close()))
        # Keep APPLY for future real edit (currently just closes)
        buttons.append(
            MDRaisedButton(text="APPLY", on_release=lambda *_: self._apply())
        )
        self.dialog = MDDialog(
            title="Edit Aggregate",
            text=text,
            buttons=buttons,
        )
        self.dialog.open()

    def _apply(self):  # pragma: no cover - placeholder
        self.close()

    def _open_delete_confirm(self):  # pragma: no cover - placeholder
        if self._delete_confirm_dialog and self._delete_confirm_dialog.parent:
            return
        self._delete_confirm_dialog = MDDialog(
            title="Confirm Delete",
            text="Delete this aggregate processor? This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL", on_release=lambda *_: self._dismiss_delete_confirm()
                ),
                MDRaisedButton(
                    text="DELETE",
                    md_bg_color=(0.9, 0.3, 0.3, 1),
                    on_release=lambda *_: self._perform_delete(),
                ),
            ],
        )
        self._delete_confirm_dialog.open()

    def _dismiss_delete_confirm(self):  # pragma: no cover
        if self._delete_confirm_dialog:
            try:
                self._delete_confirm_dialog.dismiss()
            except Exception:
                pass
            self._delete_confirm_dialog = None

    def _perform_delete(self):  # pragma: no cover
        try:
            if self.on_delete:
                self.on_delete()
        except Exception:
            pass
        self._dismiss_delete_confirm()
        self.close()

    def close(self):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
        self._dismiss_delete_confirm()
        if self.on_close:
            self.on_close()
