from __future__ import annotations
from typing import Callable, Dict, Iterable
from kivy.clock import Clock
import threading


class ChannelStore:
    def __init__(self, size: int = 16):
        self._values = [0.0] * (size + 1)
        self._listeners: Dict[int, list[Callable[[int, float], None]]] = {}
        self._main_thread_id = threading.get_ident()
        self._pending: Dict[int, float] = {}
        self._flush_scheduled = False

    def size(self) -> int:
        return len(self._values) - 1

    def get(self, channel_id: int) -> float:
        if 0 < channel_id < len(self._values):
            return self._values[channel_id]
        return 0.0

    def set(self, channel_id: int, value: float):
        if not (0 < channel_id < len(self._values)):
            return
        if threading.get_ident() != self._main_thread_id:
            self._pending[channel_id] = value
            if not self._flush_scheduled:
                self._flush_scheduled = True
                Clock.schedule_once(self._flush, 0)
            return
        self._apply(channel_id, value)

    def _apply(self, channel_id: int, value: float):
        if self._values[channel_id] == value:
            return
        self._values[channel_id] = value
        for cb in self._listeners.get(channel_id, []):
            try:
                cb(channel_id, value)
            except Exception as e:
                print(f"ChannelStore listener error ch={channel_id}: {e}")

    def _flush(self, *_):
        for ch, val in list(self._pending.items()):
            self._apply(ch, val)
        self._pending.clear()
        self._flush_scheduled = False

    def add_listener(self, channel_id: int, callback: Callable[[int, float], None]):
        self._listeners.setdefault(channel_id, []).append(callback)

    def remove_listener(self, channel_id: int, callback: Callable[[int, float], None]):
        if channel_id in self._listeners:
            try:
                self._listeners[channel_id].remove(callback)
            except ValueError:
                pass

    def channels(self) -> Iterable[int]:
        return (i for i in range(1, len(self._values)))


channel_store = ChannelStore(size=32)
