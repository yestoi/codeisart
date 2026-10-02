"""The game registry (spec 4.1): MENU_ORDER and guarded discovery.

A game is the module arcade/games/<name>.py with a GAME attribute, the game class, whose info.name is <name>.
Nothing else registers a game: adding one means creating its module and, if it is new to the spec, adding its
name to MENU_ORDER in its place. This file changes in no other way.
"""
from __future__ import annotations

import importlib
import logging

from arcade.game import GameInfo

log = logging.getLogger("arcade")

MENU_ORDER = ("copyme", "pong", "paint", "quickdraw", "dodge", "tug", "flap", "swat", "jump", "freeze")


def _load(name: str) -> type | None:
    """arcade.games.<name>'s GAME, or None: silently when the module does not exist yet, with a log line when
    it fails to import (any exception, a missing dependency included) or its GAME is not a game called name."""
    module_name = f"{__name__}.{name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name == module_name:
            return None
        log.exception("game %s skipped: its module failed to import", name)
        return None
    except Exception:
        log.exception("game %s skipped: its module failed to import", name)
        return None
    game = getattr(module, "GAME", None)
    info = getattr(game, "info", None)
    if not isinstance(game, type) or not isinstance(info, GameInfo) or info.name != name:
        log.error("game %s skipped: GAME must be a class whose info is a GameInfo named %r", name, name)
        return None
    return game


def all_games() -> list[type]:
    """Every game that imports cleanly, in MENU_ORDER."""
    return [game for game in map(_load, MENU_ORDER) if game is not None]


def get_game(name: str) -> type:
    """The game called name; KeyError if it is not in MENU_ORDER or did not load."""
    for game in all_games():
        if game.info.name == name:
            return game
    raise KeyError(name)
