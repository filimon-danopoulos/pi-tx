from kivymd.uix.toolbar import MDTopAppBar as MDToolbar
from kivy.metrics import dp


class TopBar(MDToolbar):
    def __init__(self, title, left_callback=None, right_action_items=None, **kwargs):
        super().__init__(title=title, **kwargs)
        # Left navigation icon (hamburger) to toggle settings drawer if provided
        if left_callback:
            self.left_action_items = [["menu", lambda *_: left_callback()]]
        # Right action items (empty by default)
        if right_action_items is None:
            right_action_items = []
        self.right_action_items = right_action_items
