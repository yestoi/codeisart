"""The show's loop and CLI (spec 4.6; daemon plan Task 14 as amended; it12 T-main).

Safety path (Q50): renderer, flash governor, push. The display is wrapped by the governor the moment it is made,
and the loop pushes only through that wrapper (`self.wall`): the show's frames, the static error frame and
--play's alike. No software brightness: the level is set once on the device at open.

Setup never exits: a failure is logged, named on a static error frame (governed like any other) and retried every
RETRY_S, while the loop keeps stepping and petting the watchdog.
"""
from __future__ import annotations

import argparse
import logging
import random
import signal
import sys
import textwrap
import time
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

import numpy as np

from show.audio import AudioCues
from show.config import PHOSPHORS, Config, load_config
from show.display import Display, make_display
from show.entries import load_entries, rescan
from show.font import CELL_H, CELL_W, Font
from show.input import PressQueue, make_buttons
from show.lights import make_lights
from show.pipeline import EntryPlayer
from show.renderer import NORMAL, draw_text, renderer_for
from show.state import Show
from show.terminal import Terminal
from show.wall import GovernedDisplay

log = logging.getLogger("show")

RESCAN_S = 30.0          # entries rescanned this often while the show runs (spec 4.6)
RETRY_S = 30.0           # a failed setup is tried again this often
PUSH_DARK_S = 10.0       # this long without a frame reaching the wall: all lights off (spec 4.5)
WATCHDOG_EVERY_S = 1.0   # WATCHDOG=1 at most this often (the unit's WatchdogSec is 15)
BLINK_HZ = 1.0           # the cursor's blink
FAILURE_LOG_EVERY = 300  # a run of push failures is logged at its first and every this many
FALLBACK_FPS = 20        # run's pace when cfg.fps is not an int of at least 2 (Config's default)
# A broken show.toml's own values for these still name the wall (config_from's fallback).
DISPLAY_KEYS = ("backend", "width", "height", "colorlight_iface", "ddp_host", "ddp_port")


class Sigterm:
    """SIGTERM's handler (systemctl stop): KeyboardInterrupt the first time, so run's finally darkens the wall and
    the lights; later ones only counted, so the close is never cut short. It never logs: main logs the count."""

    def __init__(self) -> None:
        self.seen = 0

    def __call__(self, signum: int, frame) -> None:
        self.seen += 1
        if self.seen == 1:
            raise KeyboardInterrupt


@contextmanager
def sigterm_raises() -> Iterator[None]:
    """Sigterm installed for the body, the previous handler back after it. Installed before the devices open, so
    SDL (the mixer) finds a handler and adds none of its own. Outside the main thread: a warning, nothing."""
    try:
        previous = signal.signal(signal.SIGTERM, Sigterm())
    except ValueError:
        log.warning("not the main thread: no SIGTERM handler, systemctl stop skips the close")
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous if previous is not None else signal.SIG_DFL)


def error_frame(width: int, height: int, phosphor: tuple[int, int, int], font: Font | None,
                lines: list[str]) -> np.ndarray:
    """A static frame naming what failed: a lit border (never black, even with no font or no lines) and the lines
    wrapped to the wall, in the phosphor at normal text level."""
    color = tuple(int(c * NORMAL) for c in phosphor)
    frame = np.zeros((height, width, 3), np.uint8)
    frame[0, :] = frame[-1, :] = color
    frame[:, 0] = frame[:, -1] = color
    if font is not None:
        fits = max(1, (width - 2) // CELL_W)
        x, y = (width - fits * CELL_W) // 2, 2
        for text in lines:
            for part in textwrap.wrap(text, fits) or [""]:
                if y + CELL_H > height - 1:
                    break
                draw_text(frame, x, y, part, font, color)
                y += CELL_H
    frame.flags.writeable = False
    return frame


class ShowLoop:
    def __init__(self, cfg: Config, *, display: Display | None = None, player_factory: Callable = EntryPlayer,
                 notify: Callable[[str], None] | None = None, rng: random.Random | None = None,
                 config_error: str | None = None):
        self.cfg = cfg
        self.player_factory, self.rng = player_factory, rng
        self.presses = PressQueue()
        self.wall: GovernedDisplay | None = None
        self.show: Show | None = None
        self.lights = None
        self.buttons = None
        self.audio = None
        self.font: Font | None = None
        self.renderer = None
        self.errors: list[str] = []
        self.rendered: np.ndarray | None = None           # the last frame before the governor
        self.notify = notify if notify is not None else _systemd_notify()
        self.clock: Callable[[], float] = time.monotonic   # run's clock and sleep (tests give fakes)
        self.sleep: Callable[[float], None] = time.sleep
        self._display = display
        self._fixed: list[str] = [config_error] if config_error else []   # errors no retry can mend
        self._static = config_error is not None    # the error frame only, never a show
        self._wall_retry = True                    # the display may be opened (again)
        self._devices = False                      # lights, buttons and audio made
        self._next_retry = self._next_rescan = 0.0
        self._last_pet: float | None = None
        self._push_failed = False                  # the last push raised: the last governed frame goes again
        self._failures = 0
        self._fail_since: float | None = None      # the first of this run of failures (or of no wall)
        self._dark = False                         # lights all off until a push is good again
        self._error_key: tuple[str, ...] | None = None
        self._error: np.ndarray | None = None

    # -- setup ---------------------------------------------------------------------------------------------------

    def start(self, now: float) -> None:
        """Setup, the show's start, READY=1. Pushes nothing; never raises."""
        try:
            self._setup(now)
        except Exception:
            log.exception("setup failed")
        self._tell("READY=1")

    def _setup(self, now: float) -> None:
        cfg, failed = self.cfg, []
        if self.wall is None and self._wall_retry:
            error = self._open_wall()
            if error is not None:
                failed.append(error)
        if not self._devices:
            self._devices = True
            self._make_devices()
        if self.font is None:
            try:
                self.font = Font.load(cfg.font_path)
            except Exception as exc:
                failed.append(f"font: {exc}")
        if self.show is None and not self._static:
            try:
                entries = load_entries(cfg.entries_dir)
            except Exception as exc:
                failed.append(f"entries: {exc}")
                entries = None
            if entries is not None and self.font is not None:
                try:
                    renderer = renderer_for(cfg, self.font)
                    show = Show(cfg, entries, Terminal(cfg.columns, cfg.rows - 1), self.lights, self.audio,
                                self.player_factory, self.rng)
                    show.start(now)
                    self.renderer, self.show = renderer, show
                    self._next_rescan = now + RESCAN_S
                except Exception as exc:
                    log.exception("the show could not be built")
                    failed.append(f"show: {exc}")
        for error in failed:
            log.error("setup: %s", error)
        self.errors = self._fixed + failed
        self._next_retry = now + RETRY_S
        if self.wall is None and self._fail_since is None:
            self._fail_since = now

    def _open_wall(self) -> str | None:
        """The display, wrapped by the governor at birth; the error when the display cannot be made (retried)."""
        cfg, raw = self.cfg, None
        try:
            self.wall = GovernedDisplay((raw := self._display if self._display is not None else make_display(
                cfg, on_key=lambda i: self.presses.put(i + 1))), cfg.height, cfg.width, cfg.fps, cfg.gamma)
        except Exception as exc:
            if raw is None:
                log.exception("the display could not be opened")
                return f"display: {exc}"
            # The governor refuses the config: the module's defaults govern a static frame naming it, no show.
            log.exception("the flash governor refused the config; the error frame only")
            self._static, self._wall_retry = True, False
            self._fixed.append(f"flash governor: {exc}")
            try:
                self.wall = GovernedDisplay(raw, cfg.height, cfg.width)
            except Exception as exc2:
                log.exception("no flash governor can be built; the display is closed and the wall stays dark")
                self._fixed.append(f"flash governor (defaults): {exc2}")
                try:
                    raw.close()
                except Exception:
                    log.exception("closing the ungoverned display failed")
                return None
        level = cfg.effective_brightness
        if cfg.backend == "ddp":
            log.warning("ddp sends pixels unscaled: Falcon Player's output brightness must hold %.2f "
                        "(show.toml's brightness, capped at brightness_cap %.2f)", level, cfg.brightness_cap)
        try:
            self.wall.set_brightness(level)
        except Exception:
            log.exception("setting the brightness on the device failed")
        return None

    def _make_devices(self) -> None:
        cfg = self.cfg
        try:
            self.lights = make_lights(cfg.light_pins, cfg.lightbox_pins)
        except Exception:
            log.exception("lights unavailable")
        try:
            self.buttons = make_buttons(cfg.button_pins, self.presses)
        except Exception:
            log.exception("buttons unavailable")
        try:
            self.audio = AudioCues(cfg.audio_dir, cfg.volume, cfg.quiet_hours)
        except Exception:
            log.exception("audio unavailable")

    # -- the step ------------------------------------------------------------------------------------------------

    def step(self, now: float) -> None:
        """Presses, tick, lights, rescan, render, push, watchdog. Never raises (but KeyboardInterrupt: the window
        was closed)."""
        try:
            if now >= self._next_retry and ((self.show is None and not self._static)
                                            or (self.wall is None and self._wall_retry)):
                self._setup(now)
            self._advance(now)
            frame = self._render(now)
            self._push(frame, now)
        except Exception:
            log.exception("the step failed")
        self._pet(now)

    def _advance(self, now: float) -> None:
        show, presses = self.show, self.presses.drain()
        if show is not None:
            for station in presses:
                try:
                    show.press(station, now)
                except Exception:
                    log.exception("press on station %d failed; attract", station)
                    self._abort(now)
            try:
                show.tick(now)
            except Exception:
                log.exception("the show's tick failed; attract")
                self._abort(now)
        if self.lights is not None:
            try:
                if self._dark:
                    self.lights.all_off()             # the show may have lit one since: the wall is still dark
                self.lights.tick(now)
            except Exception:
                log.exception("the lights' tick failed")
        if show is not None and now >= self._next_rescan:
            self._next_rescan = now + RESCAN_S
            try:
                show.set_entries(rescan(self.cfg.entries_dir, show.entries), now)
            except Exception:
                log.exception("the rescan failed")

    def _render(self, now: float) -> np.ndarray | None:
        cfg = self.cfg
        if self.show is None:
            key = tuple(self.errors)
            if self._error is None or key != self._error_key:
                phosphor = PHOSPHORS.get(cfg.phosphor, PHOSPHORS["green"])
                self._error = error_frame(cfg.width, cfg.height, phosphor, self.font, self.errors)
                self._error_key = key
            frame = self._error
        else:
            show = self.show
            try:
                frame = self.renderer.render(show.term.screen, cursor_on=int(now * 2 * BLINK_HZ) % 2 == 0,
                                             strip=show.strip(now), full_screen=show.full_screen,
                                             strip_visible=show.strip_visible(now))
            except Exception:
                log.exception("the render failed; the last frame again, and attract")
                self._abort(now)
                frame = self.rendered
        self.rendered = frame
        return frame

    def _push(self, frame: np.ndarray | None, now: float) -> None:
        if self.wall is None:
            self._failing(now)
            return
        if frame is None:
            return
        try:
            if self._push_failed:
                self.wall.repush()                    # the frame the governor counted, before the next
            self.wall.push(frame)
        except Exception:
            self._push_failed = True
            self._failures += 1
            if self._failures == 1 or self._failures % FAILURE_LOG_EVERY == 0:
                log.exception("the push failed (%d in a row); the show goes on", self._failures)
            self._failing(now)
            return
        if self._failures:
            log.info("the push works again after %d failures", self._failures)
        self._push_failed, self._failures, self._fail_since = False, 0, None
        if self._dark:
            self._dark = False
            if self.show is not None:
                try:
                    self.show.relight()
                except Exception:
                    log.exception("relighting failed")

    def _failing(self, now: float) -> None:
        if self._fail_since is None:
            self._fail_since = now
        if not self._dark and now - self._fail_since >= PUSH_DARK_S:
            log.error("no frame has reached the wall for %.0f s: all lights off", now - self._fail_since)
            self._dark = True
            if self.lights is not None:
                try:
                    self.lights.all_off()
                except Exception:
                    log.exception("lights: all off failed")

    def _abort(self, now: float) -> None:
        try:
            self.show.abort(now)
        except Exception:
            log.exception("the abort failed")

    def _pet(self, now: float) -> None:
        if self._last_pet is None or now - self._last_pet >= WATCHDOG_EVERY_S:
            self._last_pet = now
            self._tell("WATCHDOG=1")

    def _tell(self, state: str) -> None:
        try:
            self.notify(state)
        except Exception:
            log.exception("notify %s failed", state)

    # -- run -----------------------------------------------------------------------------------------------------

    def run(self, play: str | None = None) -> int:
        """Step at most cfg.fps times a second, no catch-up after a stall. 0 on Ctrl-C, the window's close and
        --play's end; with --play, 2 for a slug the show does not have and 1 when no show could be set up."""
        pace = self.cfg.fps
        if isinstance(pace, bool) or not isinstance(pace, int) or pace < 2:
            # A Config built in code skips load_config's check; the wall's refusal names this fps on its frame.
            log.error("fps %r is not an int of at least 2: run steps at %d fps", pace, FALLBACK_FPS)
            pace = FALLBACK_FPS
        period = 1.0 / pace
        try:
            now = self.clock()
            self.start(now)
            log.info("the show runs at %d fps", pace)
            pressed = False
            if play is not None:
                if self.show is None:
                    log.error("--play %s: no show could be set up: %s", play, self.errors)
                    return 1
                stations = [s for s, e in self.show.entries.items() if e.slug == play]
                if not stations:
                    log.error("no entry with slug %r", play)
                    return 2
                self.presses.put(stations[0])
            due = now
            while True:
                now = self.clock()
                if now < due:
                    self.sleep(due - now)
                    now = self.clock()
                self.step(now)
                due = now + period
                if play is not None:
                    if pressed and not self.show.playing:     # the press was taken a step ago: the entry is over
                        return 0
                    pressed = True
        except KeyboardInterrupt:
            return 0
        finally:
            self._close()

    def _close(self) -> None:
        log.info("closing: the wall goes black, the lights off")
        if self.show is not None:
            try:
                self.show.abort(self.clock())
            except Exception:
                log.exception("closing: the abort failed")
        if self.buttons is not None:
            try:
                self.buttons.close()
            except Exception:
                log.exception("closing the buttons failed")
        if self.lights is not None:
            try:
                self.lights.all_off()
                self.lights.tick(self.clock())                # all_off sets the modes; the tick writes them
            except Exception:
                log.exception("closing: the lights off failed")
        close = getattr(self.lights, "close", None)
        if close is not None:
            try:
                close()
            except Exception:
                log.exception("closing the lights failed")
        if self.wall is not None:
            try:
                self.wall.close()
            except Exception:
                log.exception("closing the wall failed")


def _systemd_notify() -> Callable[[str], None]:
    """sdnotify's notifier (a no-op outside systemd); a no-op if it cannot be had."""
    try:
        import sdnotify
        return sdnotify.SystemdNotifier().notify
    except Exception:
        log.exception("sdnotify unavailable: no READY or WATCHDOG to systemd")
        return lambda state: None


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="show", description="Code is Art LED wall show")
    p.add_argument("--config", type=Path, default=Path("show.toml"))
    p.add_argument("--backend", default=None, help="override the display backend")
    p.add_argument("--play", default=None, metavar="SLUG", help="play one entry and exit")
    p.add_argument("--capture", action="store_true", help="record fallback.cast for entries lacking one")
    return p.parse_args(argv)


def config_from(args: argparse.Namespace) -> tuple[Config, str | None]:
    """The config and None; if load_config raises, the fallback and the error (the error frame names it).
    --backend and --capture apply either way."""
    try:
        cfg, error = load_config(args.config), None
    except Exception as exc:
        log.error("config %s: %s; the defaults run and the wall names the error", args.config, exc)
        cfg, error = _fallback(args.config), f"config: {exc}"
    if args.backend:
        cfg.backend = args.backend
    if args.capture:
        cfg.capture = True
    return cfg, error


def _fallback(path: Path) -> Config:
    """Config() with the file's DISPLAY_KEYS (when it parses as TOML and a value has the default's type, never a
    bool for an int), so the wall it names shows the error; its brightness and brightness_cap only as a level 0 to
    1 and never above Config()'s, which is the only level known otherwise. Never gamma or fps."""
    cfg = Config()
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return cfg
    for key in DISPLAY_KEYS:
        if type(data.get(key)) is type(getattr(cfg, key)):
            setattr(cfg, key, data[key])
    for key in ("brightness", "brightness_cap"):
        value = data.get(key)
        if not isinstance(value, bool) and isinstance(value, (int, float)) and 0.0 <= value <= 1.0:   # not nan
            setattr(cfg, key, min(value, getattr(cfg, key)))
    return cfg


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    cfg, error = config_from(args)
    if args.play is not None:
        try:
            slugs = sorted(e.slug for e in load_entries(cfg.entries_dir).values())
        except Exception as exc:
            log.error("--play: %s", exc)
            slugs = []
        if args.play not in slugs:
            log.error("no entry with slug %r (have %s)", args.play, slugs)
            return 2
    with sigterm_raises():
        try:
            return ShowLoop(cfg, config_error=error).run(play=args.play)
        finally:
            handler = signal.getsignal(signal.SIGTERM)
            if isinstance(handler, Sigterm) and handler.seen:
                log.info("stopped by SIGTERM, seen %d times (the later ones ignored)", handler.seen)


if __name__ == "__main__":
    sys.exit(main())
