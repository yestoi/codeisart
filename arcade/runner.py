"""The runner (spec 7.2): a fixed tick from sources to Sensed to the lobby or a game to the wall.

It owns what every game gets for free: the player lock, presence, the session rules (leave, inactivity, the cap
and the deliberate exit), the crash guard, the effects, and the two hard ceilings on every frame. One tick:

    read sources -> Sensed -> player, player2, present -> session rules -> update (skipped while fx.frozen)
    -> draw -> Juice.render -> overlays -> BrightnessLimiter.apply -> FlashGovernor.apply -> push

The governor runs last (owner Q11), so what it bounds is what the wall shows.
"""
from __future__ import annotations

import dataclasses
import logging
import math
import random
import time
import traceback
import zlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

import numpy as np

from arcade.brightness import BrightnessLimiter
from arcade.calibration import Calibration
from arcade.canvas import Canvas
from arcade.config import ArcadeConfig
from arcade.flash import FlashGovernor
from arcade.game import Game
from arcade.input import EPSILON, Hold, capture_grace
from arcade.juice import Juice
from arcade.look import is_real
from arcade.scores import Scores, SessionLog, _finite
from arcade.sensed import Audio, Blob, Body, Sensed
from show.display import Display
from show.font import CELL_H, Font

MAX_DT = 0.1                 # seconds: a tick's dt is clamped to this (spec 7.2)
CAMERA_STALE = 1.0           # seconds: an older camera result is empty and the camera unavailable (spec 10)
AUDIO_STALE = 0.5            # seconds: the same for audio
CLOCK_SLACK = 0.1            # seconds: a capture stamped further past the runner's clock is on another clock
MAX_CRASHES = 3              # a game that raises this many times is hidden until the dusk restart
CRASH_SECONDS = 0.5          # the crash icon fades over this, then the lobby
CRASH_RED = (96, 0, 0)       # the crash icon's colour: static and dim
PROMPT_SECONDS = 5.0         # "STILL PLAYING? HAND UP" shows this long before the session ends
PROMPT = "STILL PLAYING? HAND UP"
SWITCH_RATIO = 1.3           # a rival this much larger than the player ...
SWITCH_SECONDS = 1.0         # ... for this long takes the lock
REACQUIRE_DISTANCE = 0.25    # zone units: a new body this near the lost player's last place keeps the slot
BLOB_SPEED = 0.05            # frame widths a second: a slower in-zone light is a lamp, not a person (spec 7.2)
LOG_EVERY = 60.0             # seconds between two log lines about one failing thing
CAMERA_INPUTS = frozenset({"pose", "blobs", "motion"})
AUDIO_INPUTS = frozenset({"audio"})
LOBBY = "lobby"
RING = (160, 160, 160)       # the exit ring


@dataclass(frozen=True)
class SessionResult:
    """What the lobby's end card shows (spec 7.3): the session just ended and why."""

    game: str
    layout: str
    reason: str                  # one of scores.REASONS
    score: float | None          # the game's score as a finite float, else None (scores._finite)
    duration: float
    players: int
    best: float | None           # tonight's best after this session
    waiting: bool                # someone beyond the game's players stands in the zone
    new_best: bool = False       # tonight's best rose in this session: there was none at launch, or it is higher (C43)


class LobbyLike(Game, Protocol):
    """The lobby (the attract director, core Task 9): a Game plus a request the runner launches and three
    notices from the runner. The runner reads request after the lobby's tick and sets it to None; a request that
    cannot be read or set is a lobby that raised."""

    request: str | None

    def set_available(self, names: set[str]) -> None: ...
    def set_status(self, camera_ok: bool, mic_ok: bool, inputs: set[str], calibrated: bool) -> None: ...
    def end_session(self, result: SessionResult) -> None: ...


class PlayerLock:
    """spec 7.2's player lock. update(bodies, t) returns (player, player2).

    player is the in-zone body with the largest scale. Once locked it stays until its body has been absent for
    more than lost_seconds, or another in-zone body has been SWITCH_RATIO times larger for SWITCH_SECONDS while the
    player is seen (the rival's time restarts when the player returns).
    While the locked body is absent, player is None and the slot is kept; a body with an id that was not there
    when it went missing, in the zone within REACQUIRE_DISTANCE of its last place, takes the slot (the tracker
    never reuses an id, so a re-detected player is a new id). player2 is the next in-zone body by scale.
    """

    def __init__(self, lost_seconds: float):
        self.lost_seconds = lost_seconds
        self.id: int | None = None
        self._seen = -math.inf
        self._place = (0.5, 0.5)
        self._known: set[int] = set()                 # ids present when the player went missing
        self._rival: int | None = None
        self._rival_since = -math.inf

    def reset(self) -> None:
        self.__init__(self.lost_seconds)

    def update(self, bodies: tuple[Body, ...], t: float) -> tuple[Body | None, Body | None]:
        inside = sorted((b for b in bodies if b.in_zone), key=lambda b: -b.scale)
        by_id = {b.id: b for b in inside}
        if self.id is not None and self.id not in by_id:
            if t - self._seen > self.lost_seconds + EPSILON:
                self.id = None
            else:
                new = [b for b in inside if b.id not in self._known and
                       math.hypot(b.zone_x - self._place[0], b.zone_y - self._place[1]) <= REACQUIRE_DISTANCE]
                if new:
                    self.id = min(new, key=lambda b: math.hypot(b.zone_x - self._place[0],
                                                                b.zone_y - self._place[1])).id
        if self.id is None and inside:
            self.id, self._rival = inside[0].id, None
        player = by_id.get(self.id)
        if player is None:                            # the rival's time counts only while the player is seen (C31)
            self._rival = None
        else:
            rival = next((b for b in inside if b.id != player.id and b.scale > SWITCH_RATIO * player.scale), None)
            if rival is None:
                self._rival = None
            elif rival.id != self._rival:
                self._rival, self._rival_since = rival.id, t
            elif t - self._rival_since >= SWITCH_SECONDS - EPSILON:
                self.id, player, self._rival = rival.id, rival, None
            self._seen, self._place = t, (player.zone_x, player.zone_y)
            self._known = {b.id for b in bodies}
        player2 = next((b for b in inside if b.id != self.id), None)
        return player, player2


class Presence:
    """spec 7.2's presence. update(evidence, t) returns present: true once evidence (an in-zone body or a moving
    in-zone blob) has lasted on_seconds, riding out dropouts of up to grace; false after off_seconds without any.
    last_seen is the time of the last evidence."""

    def __init__(self, on_seconds: float, off_seconds: float, grace: float):
        self.off_seconds = off_seconds
        self._on = Hold(on_seconds, grace=grace)
        self.present = False
        self.last_seen = -math.inf

    def update(self, evidence: bool, t: float) -> bool:
        if evidence:
            self.last_seen = t
        if self._on.update(evidence, t):
            self.present = True
        if self.present and t - self.last_seen >= self.off_seconds - EPSILON:
            self.present = False
            self._on.reset()
        return self.present


class _TitleCard:
    """The lobby after the real one raised: a built-in title card until the restart (spec 7.2)."""

    info = None
    request: str | None = None

    def reset(self, size, rng, fx=None) -> None:
        pass

    def update(self, sensed: Sensed, dt: float) -> None:
        pass

    def draw(self, canvas: Canvas) -> None:
        text = "ARCADE"
        canvas.text((canvas.width - canvas.text_width(text)) // 2, (canvas.height - CELL_H) // 2, text,
                    (120, 60, 0))

    def done(self) -> bool:
        return False

    def debug_state(self) -> dict:
        return {"title_card": True}

    def set_available(self, names) -> None:
        pass

    def set_status(self, camera_ok, mic_ok, inputs, calibrated) -> None:
        pass

    def end_session(self, result) -> None:
        pass


def moving_blob(before: tuple[Blob, ...], now: tuple[Blob, ...], seconds: float) -> bool:
    """True when a blob in now is in the zone and at least BLOB_SPEED from every blob in before, seconds earlier:
    spec 7.2's "moving in-zone blob". A light that appears counts on its first capture; a parked one never."""
    seconds = max(seconds, EPSILON)
    return any(b.in_zone and all(math.hypot(b.x - p.x, b.y - p.y) / seconds >= BLOB_SPEED for p in before)
               for b in now)


def _is_true(v) -> bool:
    """spec 7.1's active boolean: True or a numpy True. 1, "yes" and numpy ints are not booleans (plan review B1)."""
    return v is True or (isinstance(v, np.bool_) and bool(v))


def _stamped(capture_t, now: float) -> bool:
    """Whether capture_t is a time on the runner's clock: finite, and at most CLOCK_SLACK past now.

    Sources stamp captures on the runner's monotonic clock, in seconds. On it a capture is never later than the
    moment latest() returns, a few microseconds after sense() reads now; 0.1 s leaves room for a slow thread and is
    3 camera frames at most. A capture stamped on another clock or in another unit (nanoseconds since boot, the
    wall clock's epoch) is off by hours or more, and would otherwise count as fresh for as long as it is repeated,
    holding a frozen body and a session (plan review R2-N2)."""
    return is_real(capture_t) and math.isfinite(capture_t) and capture_t <= now + CLOCK_SLACK


def _camera_result(got, now: float) -> tuple[float, tuple[Body, ...], tuple[Blob, ...], np.ndarray | None] | None:
    """A camera latest() result checked: None, or (capture_t, bodies, blobs, motion) with capture_t _stamped,
    Body and Blob items and motion None or a 2-D grid of bool, int, uint or float (the dtypes np.asarray(..., bool)
    and the resample take safely; C30b). Anything else raises, and sense() treats the source as failed."""
    if got is None:
        return None
    capture_t, bodies, blobs, motion = got
    bodies, blobs = tuple(bodies), tuple(blobs)
    if not (_stamped(capture_t, now) and all(isinstance(b, Body) for b in bodies)
            and all(isinstance(b, Blob) for b in blobs)
            and (motion is None or (isinstance(motion, np.ndarray) and motion.ndim == 2
                                    and motion.dtype.kind in "biuf"))):
        raise TypeError(f"camera latest() gave a malformed result: {got!r:.200}")
    return float(capture_t), bodies, blobs, motion


def _audio_result(got, now: float) -> tuple[float, Audio] | None:
    """An audio latest() result checked: None, or (capture_t, Audio) with capture_t _stamped. Anything else
    raises."""
    if got is None:
        return None
    capture_t, sound = got
    if not (_stamped(capture_t, now) and isinstance(sound, Audio)):
        raise TypeError(f"audio latest() gave a malformed result: {got!r:.200}")
    return float(capture_t), sound


def _take_request(lobby) -> str | None:
    """Read the lobby's request and clear it, so it launches once; the runner calls this inside _lobby_call, so
    a request that cannot be read or cleared is a lobby that raised (plan review R2-N4)."""
    request = getattr(lobby, "request", None)
    if request is not None:
        lobby.request = None
    return request


def _wrap(text: str, width: int, canvas: Canvas) -> list[str]:
    """text in lines that fit width at 1x, split between words."""
    lines: list[str] = []
    for word in text.split():
        if lines and canvas.text_width(lines[-1] + " " + word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


class Runner:
    """spec 7.2. tick(sensed, dt) runs one tick; loop(camera, audio) ticks at cfg.fps from the injected clock.

    games are the game classes the lobby may launch, keyed by info.name once here (the runner never calls
    all_games). scores and sessions default to in-memory ones; main passes the files in data_dir. local_clock
    is local time for the brightness limiter's night, never the monotonic clock; lux is the IMX500's lux
    callable or None. strict re-raises a game's exception instead of guarding it (the test harness default).
    runner.game is the last launched instance, kept after its session ends. raw_frames, when a list, gets a
    copy of every frame before the limiter; trace, when a list, gets state() after every tick. The Sensed that
    the lobby and games see has t set to the runner's t for the tick and camera_t moved by the same amount, so a
    game sees one clock live and headless, wherever a scenario starts. clock is the monotonic clock the sources
    stamp their captures on, in seconds.
    """

    def __init__(self, cfg: ArcadeConfig, display: Display, font: Font, lobby: LobbyLike, games: list[type],
                 seed: int = 0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, log: logging.Logger | None = None,
                 scores: Scores | None = None, sessions: SessionLog | None = None,
                 calibration: Calibration | None = None, strict: bool = False,
                 local_clock: Callable[[], datetime] = datetime.now, lux: Callable[[], Any] | None = None):
        self.cfg, self.display, self.lobby, self.seed = cfg, display, lobby, seed
        self.games: dict[str, type] = {g.info.name: g for g in games}
        self.clock, self.sleep, self.local_clock, self.strict = clock, sleep, local_clock, strict
        self.log = log or logging.getLogger("arcade")
        self.scores = scores if scores is not None else Scores(None, local_clock)
        self.sessions = sessions if sessions is not None else SessionLog(None)
        self.calibration = calibration or Calibration()
        self.canvas = Canvas(cfg.width, cfg.height, font)
        self.limiter = BrightnessLimiter(cfg, clock=local_clock, lux=lux)
        self.governor = FlashGovernor(cfg.height, cfg.width, cfg.gamma, fps=cfg.fps)
        self.grace = capture_grace(cfg.camera_fps)
        self.lock = PlayerLock(cfg.player_lost_seconds)
        self.presence = Presence(cfg.present_on_seconds, cfg.present_off_seconds, self.grace)
        self.t = 0.0
        self.running = True
        self.crashes: dict[str, int] = {}
        self.hidden: set[str] = set()
        self.last_error: str | None = None
        self.game: Game | None = None
        self.current: Any = lobby
        self.current_name = LOBBY
        self.fx: Juice | None = None
        self.raw_frames: list[np.ndarray] | None = None
        self.trace: list[dict] | None = None
        self.player: Body | None = None
        self.player2: Body | None = None
        self._state: dict = {}
        self._bodies: tuple[Body, ...] = ()
        self._blobs_before: tuple[float, tuple[Blob, ...]] | None = None  # (camera_t, blobs) of the last capture
        self._blob_moving = False
        self._evidence = False
        self._launches = 0
        self._exit = Hold(cfg.exit_seconds, grace=self.grace)
        self._blocked = False                         # after an exit, until the hands are down
        self._hands_seen = -math.inf
        self._crash: tuple[np.ndarray, float] | None = None  # (icon, since) while the crash icon shows
        self._session: dict = {}
        self._push_logged = self._governor_logged = -math.inf
        self._held_before = 0
        self._camera_seq, self._camera_capture = 0, None
        self._source_failed: dict[str, bool] = {}
        self.display.set_brightness(cfg.brightness)
        self._lobby_call(lambda: self.lobby.reset(cfg.size, random.Random(zlib.crc32(f"{seed}:lobby".encode()))))
        self._lobby_call(lambda: self.lobby.set_available(self.available()))

    # ----- the lobby and games -----

    def available(self) -> set[str]:
        """The games the lobby may offer: every game not hidden."""
        return set(self.games) - self.hidden

    def launch(self, name: str) -> bool:
        """Start a fresh instance of the game called name; False if it is unknown, hidden or crashed at start, or if
        a game is running: a launch comes from the lobby or during the crash icon, which it ends, so no session is
        dropped unlogged (plan review R2-N3)."""
        if self.current_name != LOBBY and self._crash is None:
            self.log.warning("not launching %r: %s is running", name, self.current_name)
            return False
        if not isinstance(name, str) or name not in self.games or name in self.hidden:
            hidden = isinstance(name, str) and name in self.hidden
            self.log.warning("not launching %r: %s", name, "hidden" if hidden else "unknown")
            return False
        self._launches += 1
        rng = random.Random(zlib.crc32(f"{self.seed}:{name}:{self._launches}".encode()))
        fx = Juice(random.Random(zlib.crc32(f"{self.seed}:{name}:{self._launches}:fx".encode())), self.cfg.size)
        self.current_name, self.fx, self._state, self._crash = name, fx, {}, None
        self._session = {"start": self.t, "local": self.local_clock(), "seen": self.t, "active": self.t,
                         "prompt": None, "players": 0, "best": self.scores.best(name, self.cfg.layout)}
        try:
            game = self.games[name]()
            self.game = game
            game.scores = self.scores.for_game(name, self.cfg.layout)
            game.reset(self.cfg.size, rng, fx)
        except Exception:
            self._crashed()
            return False
        self.current, self._state = game, {}
        self._exit.reset()                            # the caller rule (C27): a stale hold never fires at once
        return True

    def end_session(self, reason: str) -> SessionResult:
        """Log the session, tell the lobby, and return to it."""
        name, info = self.current_name, self.games[self.current_name].info
        s, state = self._session, self._state
        bodies = sum(b.in_zone for b in self._bodies)
        best, before = self.scores.best(name, self.cfg.layout), s["best"]
        result = SessionResult(game=name, layout=self.cfg.layout, reason=reason, score=_finite(state.get("score")),
                               duration=self.t - s["start"], players=s["players"], best=best,
                               waiting=bodies > info.players,
                               new_best=best is not None and (before is None or best > before))
        self.sessions.append(name, self.cfg.layout, s["local"], result.duration, result.players, result.score,
                             reason)
        self._lobby_call(lambda: self.lobby.end_session(result))
        self._to_lobby()
        if reason == "exit":
            self._blocked, self._hands_seen = True, self.t
        return result

    def _to_lobby(self) -> None:
        self.current, self.current_name, self.fx, self._crash = self.lobby, LOBBY, None, None
        self._state = {}

    def _crashed(self) -> None:
        """The crash guard (spec 7.2): log and keep the traceback, count, hide at MAX_CRASHES, show the icon."""
        if self.strict:
            raise
        name = self.current_name
        self.last_error = traceback.format_exc()
        self.log.exception("game %s crashed", name)
        self.crashes[name] = self.crashes.get(name, 0) + 1
        if self.crashes[name] >= MAX_CRASHES and name not in self.hidden:
            self.hidden.add(name)
            self._lobby_call(lambda: self.lobby.set_available(self.available()))
        result_icon = self.games[name].info.icon
        self.end_session("crash")
        self.current_name, self._crash = name, (result_icon, self.t)

    def _lobby_call(self, fn: Callable[[], Any]) -> Any:
        """Call into the lobby; if it raises, a built-in title card replaces it until restart."""
        try:
            return fn()
        except Exception:
            if self.strict:
                raise
            self.last_error = traceback.format_exc()
            self.log.exception("the lobby raised: showing the title card until restart")
            if self.current is self.lobby:
                self.current = _TitleCard()
            self.lobby = _TitleCard()
            return None

    # ----- one tick -----

    def tick(self, sensed: Sensed, dt: float) -> None:
        dt = min(MAX_DT, max(0.0, float(dt))) if is_real(dt) and math.isfinite(dt) else 0.0
        self.t += dt
        sensed = sensed.with_motion(self.cfg.size)
        self._bodies = sensed.bodies
        self.player, self.player2 = self.lock.update(sensed.bodies, self.t)
        self._evidence = any(b.in_zone for b in sensed.bodies) or self._moving(sensed)
        present = self.presence.update(self._evidence, self.t)
        sensed = dataclasses.replace(sensed, t=self.t, camera_t=sensed.camera_t + (self.t - sensed.t),
                                     player=self.player, player2=self.player2, present=present)
        hands_up = self.player is not None and self.player.both_hands_up
        exit_fired = self._exit.update(hands_up, self.t)             # every tick (C27), in the lobby too
        self.canvas.clear()
        if self._crash is not None and self._draw_crash():
            pass
        elif self.current_name == LOBBY:                              # also the tick the crash icon ends
            self._lobby_tick(sensed, dt)
        else:
            self._game_tick(sensed, dt, exit_fired)
        self._push()
        if self.trace is not None:
            self.trace.append(self.state())

    def _moving(self, sensed: Sensed) -> bool:
        """Whether a moving in-zone blob was in the last camera capture, judged on the tick it arrives (camera_fresh)
        against the capture before; seconds apart from camera_t, or one camera frame when that does not advance."""
        if sensed.camera_fresh:
            if self._blobs_before is None:
                self._blob_moving = any(b.in_zone for b in sensed.blobs)
            else:
                t0, before = self._blobs_before
                seconds = sensed.camera_t - t0 if sensed.camera_t > t0 else 1.0 / self.cfg.camera_fps
                self._blob_moving = moving_blob(before, sensed.blobs, seconds)
            self._blobs_before = (sensed.camera_t, sensed.blobs)
        return self._blob_moving

    def _lobby_tick(self, sensed: Sensed, dt: float) -> None:
        if self._blocked:
            if any(b.in_zone and b.raised_wrist is not None for b in sensed.bodies):
                self._hands_seen = self.t
            if self.t - self._hands_seen > self.grace + EPSILON:
                self._blocked = False
            else:
                sensed = dataclasses.replace(sensed, bodies=(), blobs=(), player=None, player2=None)
        lobby = self.current
        self._lobby_call(lambda: lobby.update(sensed, dt))
        self._lobby_call(lambda: self.current.draw(self.canvas))
        self._state = self._lobby_call(lambda: dict(self.current.debug_state())) or {}
        request = self._lobby_call(lambda: _take_request(self.current))
        if request is not None:
            self.launch(request)

    def _game_tick(self, sensed: Sensed, dt: float, exit_fired: bool) -> None:
        game, info, fx, s = self.current, self.games[self.current_name].info, self.fx, self._session
        inside = [b for b in sensed.bodies if b.in_zone]
        s["players"] = max(s["players"], min(len(inside), info.players))
        if self._evidence:                                          # the presence evidence: leave follows it
            s["seen"] = self.t
        if _is_true(self._state.get("active")):
            s["active"] = self.t
        reason = self._session_rule(sensed, info, exit_fired, len(inside))
        if reason is not None:
            self.end_session(reason)
            self._lobby_tick(sensed, 0.0)
            return
        game_sensed = dataclasses.replace(sensed, blobs=tuple(b for b in sensed.blobs if b.in_zone))
        try:
            if not fx.frozen:
                game.update(game_sensed, dt)
            game.draw(self.canvas)
            fx.render(self.canvas, self.player, self.player2)
            self._draw_overlays(info)
            fx.update(dt)
            self._state = dict(game.debug_state())
            if game.done():
                self.end_session("done")
        except Exception:
            self._crashed()
            self.canvas.clear()
            self._draw_crash()

    def _session_rule(self, sensed: Sensed, info, exit_fired: bool, inside: int) -> str | None:
        """The reason the session ends on this tick, from the rules of spec 7.2, or None."""
        s, cfg = self._session, self.cfg
        if exit_fired and info.exit_gesture:
            return "exit"
        leave = info.abandon_seconds if info.abandon_seconds is not None else cfg.leave_seconds
        if self.t - s["seen"] >= leave - EPSILON:
            return "left"
        if s["prompt"] is not None:
            if (self.player is not None and self.player.raised_wrist is not None) or s["active"] > s["prompt"]:
                s["prompt"], s["active"] = None, self.t
            elif self.t - s["prompt"] >= PROMPT_SECONDS - EPSILON:
                return "inactive"
        elif self.t - s["active"] >= cfg.inactive_seconds - EPSILON:
            s["prompt"] = self.t
        phase = self._state.get("phase", "play")      # a non-str phase counts as "play", as a missing key (C30a)
        if (self.t - s["start"] >= cfg.max_session_seconds - EPSILON and inside > info.players
                and isinstance(phase, str) and phase != "play"):
            return "capped"
        return None

    def _draw_overlays(self, info) -> None:
        c = self.canvas
        progress = self._exit.progress
        if info.exit_gesture and progress > 0.0 and self.player is not None:
            r = (1.0 - progress) * (min(c.width, c.height) / 2 - 2) + 1
            c.circle(self.player.zone_x * (c.width - 1), c.height / 2, r, RING)
        if self._session["prompt"] is not None:
            lines = _wrap(PROMPT, c.width - 2, c)
            top = (c.height - CELL_H * len(lines)) // 2
            c.fill_rect(0, top - 1, c.width, CELL_H * len(lines) + 1, (0, 0, 0))
            for i, line in enumerate(lines):
                c.text((c.width - c.text_width(line)) // 2, top + i * CELL_H, line, (255, 255, 255))

    def _draw_crash(self) -> bool:
        """Draw the fading crash icon; False once it has faded (and the runner is back in the lobby)."""
        icon, since = self._crash
        u = (self.t - since) / CRASH_SECONDS
        if u >= 1.0 - EPSILON:
            self._crash = None
            self._to_lobby()
            return False
        color = tuple(math.floor(v * (1.0 - u) + 0.5) for v in CRASH_RED)
        self.canvas.blit(icon, (self.canvas.width - icon.shape[1]) // 2, (self.canvas.height - icon.shape[0]) // 2,
                         color)
        return True

    def _push(self) -> None:
        if self.raw_frames is not None:
            self.raw_frames.append(self.canvas.frame.copy())
        try:
            out = self.governor.apply(self.limiter.apply(self.canvas.frame))
            self.display.push(out)
        except Exception:
            if self.t - self._push_logged >= LOG_EVERY:
                self._push_logged = self.t
                self.log.exception("display push failed (logged once a minute)")
        held = self.governor.held_ticks
        if held > self._held_before and self.t - self._governor_logged >= LOG_EVERY:
            self._governor_logged = self.t
            self.log.info("flash governor held frames of %s (%d ticks so far)", self.current_name, held)
        self._held_before = held

    # ----- sources and the loop -----

    def _source(self, name: str, source, check: Callable[[Any], Any]) -> tuple[Any, bool]:
        try:
            got, ok = check(source.latest()), bool(getattr(source, "available", True))
        except Exception:
            if not self._source_failed.get(name):
                self.log.exception("%s source failed", name)
            self._source_failed[name] = True
            return None, False
        self._source_failed[name] = False
        return got, ok

    def sense(self, camera, audio) -> Sensed:
        """A Sensed from the sources' latest() results (spec 5, 6): camera (capture_t, bodies, blobs, motion) or
        None, audio (capture_t, Audio), capture times on the injected clock in seconds. A result older than
        CAMERA_STALE or AUDIO_STALE is empty and its source unavailable (spec 10), as is a source whose latest()
        raises, gives another shape, or stamps a time that is not finite or is over CLOCK_SLACK ahead (logged once
        per run of failures). t and camera_t are on the runner's t before this tick's
        dt; tick() moves both to the tick's t. Tells the lobby the status."""
        now = self.clock()
        got, camera_ok = self._source("camera", camera, lambda got: _camera_result(got, now))
        bodies, blobs, motion, camera_t, fresh = (), (), None, 0.0, False
        if got is not None:
            capture_t, *rest = got
            if now - capture_t <= CAMERA_STALE:
                bodies, blobs, motion = rest
                camera_t = self.t - (now - capture_t)
                fresh = capture_t != self._camera_capture
                if fresh:
                    self._camera_capture, self._camera_seq = capture_t, self._camera_seq + 1
            else:
                camera_ok = False
        else:
            camera_ok = False
        heard, mic_ok = self._source("audio", audio, lambda got: _audio_result(got, now))
        sound = Audio()
        if heard is not None and now - heard[0] <= AUDIO_STALE:
            sound = heard[1]
        else:
            mic_ok = False
        inputs = (CAMERA_INPUTS if camera_ok else frozenset()) | (AUDIO_INPUTS if mic_ok else frozenset())
        self._lobby_call(lambda: self.lobby.set_status(camera_ok, mic_ok, set(inputs), self.calibration.calibrated))
        return Sensed(self.t, camera_t=camera_t, camera_fresh=fresh, camera_seq=self._camera_seq,
                      bodies=tuple(bodies), blobs=tuple(blobs), motion=motion, audio=sound).with_motion(self.cfg.size)

    def loop(self, camera, audio, max_ticks: int | None = None) -> None:
        """Tick at cfg.fps. A late tick runs at once and the schedule restarts from it: no burst of catch-up
        ticks (it04 forwarded: the governor's window leaves one frame of margin for one late tick)."""
        period = 1.0 / self.cfg.fps
        last = self.clock()
        deadline = last + period
        ticks = 0
        while self.running and (max_ticks is None or ticks < max_ticks):
            now = self.clock()
            dt, last = now - last, now
            self.tick(self.sense(camera, audio), dt)
            ticks += 1
            delay = deadline - self.clock()
            if delay > 0:
                self.sleep(delay)
                deadline += period
            else:
                deadline = self.clock() + period

    def state(self) -> dict:
        """The game's (or lobby's) debug_state, then the fx_* keys, then the runner's keys, which win (spec 7.2)."""
        crashed = self._crash is not None
        out = dict(self._state)
        if self.fx is not None and not crashed:
            out.update(self.fx.debug_state())
        out.update({"game": self.current_name, "t": round(self.t, 3),
                    "idle": 0.0 if self.presence.present else round(min(self.t, self.t - self.presence.last_seen), 3),
                    "attract": self.current_name == LOBBY and not self.presence.present,
                    "hidden": sorted(self.hidden), "crashes": dict(self.crashes), "glitch": crashed,
                    "flash_held_ticks": self.governor.held_ticks,
                    "player": None if self.player is None else self.player.id, "present": self.presence.present})
        return out
