from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton


class AggregateEditDialog:
    """Placeholder dialog for editing an aggregate processor.

    (Future) Expected fields:
      - Target channel selector
      - Source channel multi-select with weights
    """

    def __init__(self, on_close=None):
        self.on_close = on_close
        self.dialog: MDDialog | None = None

    def show(self, target: str, sources: str):
        if self.dialog and self.dialog.parent:
            return
        text = (
            "Edit Aggregate (placeholder)\n\n"
            f"Target: {target}\nSources: {sources or '-'}\n\n"
            "Future: add/remove source channels & weights, pick target channel."
        )
        self.dialog = MDDialog(
            title="Edit Aggregate",
            text=text,
            buttons=[
                MDFlatButton(text="CLOSE", on_release=lambda *_: self.close()),
            ],
        )
        self.dialog.open()

    def close(self):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
        if self.on_close:
            self.on_close()
