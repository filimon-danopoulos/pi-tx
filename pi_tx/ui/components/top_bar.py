from kivymd.uix.toolbar import MDTopAppBar as MDToolbar
from kivy.metrics import dp


class TopBar(MDToolbar):
    def __init__(self, title, right_action_items, **kwargs):
        super().__init__(title=title, **kwargs)
        self.right_action_items = right_action_items
