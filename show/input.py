"""Station buttons: gpiozero presses land in a thread-safe queue the main loop drains."""
from __future__ import annotations

import logging
import threading

log = logging.getLogger(__name__)

BOUNCE_S = 0.05


class PressQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[int] = []

    def put(self, station: int) -> None:
        with self._lock:
            self._items.append(station)

    def drain(self) -> list[int]:
        with self._lock:
            items, self._items = self._items, []
        return items


class ButtonInput:
    def __init__(self, pins: list[int], presses: PressQueue) -> None:
        from gpiozero import Button

        self._buttons = []
        for index, pin in enumerate(pins):
            button = Button(pin, pull_up=True, bounce_time=BOUNCE_S)
            button.when_pressed = lambda station=index + 1: presses.put(station)
            self._buttons.append(button)

    def close(self) -> None:
        for button in self._buttons:
            try:
                button.close()
            except Exception:
                log.exception("closing a button failed")


def make_buttons(pins: list[int], presses: PressQueue) -> ButtonInput | None:
    try:
        return ButtonInput(pins, presses)
    except Exception:
        log.error("buttons unavailable, running without them", exc_info=True)
        return None
