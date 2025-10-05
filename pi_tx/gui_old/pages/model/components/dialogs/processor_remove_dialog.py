from __future__ import annotations

from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton


class ProcessorRemoveDialog:
    """Placeholder dialog for confirming processor removal."""

    def __init__(self, on_confirm=None, on_cancel=None):
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.dialog: MDDialog | None = None

    def show(self, ptype: str, targets: str, sources: str):
        if self.dialog and self.dialog.parent:
            return
        text = (
            f"Are you sure you want to remove this {ptype} processor?\n\n"
            f"Targets: {targets or '-'}\nSources: {sources or '-'}\n\n"
            "This action will update the model configuration."
        )
        self.dialog = MDDialog(
            title=f"Remove {ptype}",
            text=text,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self._cancel()),
                MDRaisedButton(
                    text="REMOVE",
                    md_bg_color=(0.9, 0.3, 0.3, 1),
                    on_release=lambda *_: self._confirm(),
                ),
            ],
        )
        self.dialog.open()

    def _confirm(self):
        if self.on_confirm:
            self.on_confirm()
        self.close()

    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.close()

    def close(self):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
