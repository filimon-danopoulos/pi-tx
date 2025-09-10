from __future__ import annotations

from pi_tx.ui.services.input_event_pump import InputEventPump


class FakeInput:
    def __init__(self, events=None, raise_on=False):
        self._events = events or []
        self._started = False
        self._raise = raise_on

    def pop_events(self):
        if self._raise:
            raise RuntimeError("boom")
        # simulate queue drain
        evs, self._events = self._events, []
        return evs

    def start(self):  # pragma: no cover (not used directly here)
        self._started = True


def test_input_event_pump_no_events(monkeypatch):
    fake = FakeInput([])
    called = {}

    def set_many(d):
        called.update(d)

    pump = InputEventPump(fake, set_many)
    pump.tick()
    assert called == {}


def test_input_event_pump_aggregates_latest():
    # Two events for same channel; last wins
    fake = FakeInput([(1, 0.1), (2, 0.2), (1, 0.5)])
    captured = {}

    def set_many(d):
        captured.update(d)

    pump = InputEventPump(fake, set_many)
    pump.tick()
    assert captured == {1: 0.5, 2: 0.2}
    # second tick should see nothing new
    pump.tick()
    assert captured == {1: 0.5, 2: 0.2}


def test_input_event_pump_exception_safe():
    fake = FakeInput(raise_on=True)
    pump = InputEventPump(fake, lambda d: (_ for _ in ()).throw(ValueError()))
    # Should not raise
    pump.tick()
