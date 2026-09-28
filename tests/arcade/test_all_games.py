"""The generic tests every registered game inherits (spec 9.1, 9.2; core Task 20 and its amendment): a soak under
real noise and hostile input, the flash and pattern rules, the tick budget, the required scenarios and the bots.

Seeds are bots.seeds (zlib.crc32 of "name:layout:i"), printed in every message. The soak runs are shared by the
soak and flash tests through a cache of their measurements (never their frames)."""
import dataclasses
import functools
import os
import random
import time
from dataclasses import dataclass

import numpy as np
import pytest

from arcade.bots import Move, for_game, seeds
from arcade.calibration import Calibration
from arcade.flash import BUDGET, flash_area, square_flashes
from arcade.game import REQUIRED_SCENARIOS, reserved
from arcade.games import all_games
from arcade.headless import RecordingDisplay, run_headless
from arcade.pattern import PATTERN_AREA, pattern_area
from arcade.sensed import (LEFT_ANKLE, LEFT_ELBOW, LEFT_WRIST, MOTION_GRID, NOSE, RIGHT_ELBOW, RIGHT_HIP,
                           RIGHT_WRIST, Keypoint, place)
from arcade.sources.actors import (MAX_BLOBS, REAL_NOISE, TICK, Person, claps, degrade, motion_rect, moving_blob,
                                   scene, tempo)
from tests.arcade.helpers import make_cfg

BUDGET_MS = float(os.environ.get("ARCADE_TICK_BUDGET_MS", "2.0"))    # spec 9.2; 2.0 on the Mac (C36)
TICKS = 300
SEEDS = 5
EXTRA_LAYOUT = "96x48"
RAW_FLASH_AREA = 0.10                     # spec 7.6: a game's raw output may flash at most 10 percent of the wall
WARMUP_TICKS = 10


def _size(layout: str) -> tuple[int, int]:
    w, h = layout.split("x")
    return int(w), int(h)


CASES = [pytest.param(g, layout, id=f"{g.info.name}-{layout}")
         for g in all_games() for layout in sorted(g.info.layouts | {EXTRA_LAYOUT})]
GAMES = [pytest.param(g, id=g.info.name) for g in all_games()]


def random_mix(rng: random.Random, needs: frozenset[str], ticks: int = TICKS):
    """The draft's mix (core Task 20): up to two walkers raising a hand and jumping, up to two moving blobs,
    claps, a tempo or silence; plus motion rectangles when the game needs motion."""
    persons = [Person(rng.uniform(0.1, 0.9), 0.55, rng.uniform(0.4, 0.8), id=i)
               .walk(rng.uniform(0.1, 0.9), rng.uniform(1, 5))
               .raise_hand(at=rng.uniform(0, 5), seconds=1.0)
               .jump(at=rng.uniform(0, 8), height=0.2)
               for i in range(rng.randint(0, 2))]
    blobs = [moving_blob(rng.random(), rng.random(), rng.random(), rng.random(), rng.uniform(1, 6),
                         color=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
             for _ in range(rng.randint(0, 2))]
    motion = []
    if "motion" in needs:
        for _ in range(rng.randint(1, 3)):
            x0, y0 = rng.uniform(0, 0.8), rng.uniform(0, 0.8)
            motion.append(motion_rect(x0, y0, x0 + rng.uniform(0.05, 0.2), y0 + rng.uniform(0.05, 0.2),
                                      start=rng.uniform(0, 8), seconds=rng.uniform(0.5, 3)))
    audio = rng.choice([claps([1.0, 2.5, 4.0]), tempo(120), None])
    return scene(persons=persons, blobs=blobs, motion=motion, audio=audio, ticks=ticks)


def hostile_mix(rng: random.Random, ticks: int = TICKS):
    """Five bodies, eight blobs, keypoints at 0 and 1, confidence-0 limbs, flickering presence and short
    both-hands-up (under the exit hold), with claps and motion."""
    persons = []
    for i in range(5):
        p = Person(rng.uniform(0.1, 0.9), rng.uniform(0.45, 0.65), rng.uniform(0.3, 0.9), id=i + 1)
        p.walk(rng.choice([0.0, 1.0, rng.random()]), rng.uniform(0.5, 3)).walk(rng.random(), rng.uniform(0.5, 3))
        p.raise_hand(at=rng.uniform(0, 8), seconds=rng.uniform(0.1, 1.0), hand=rng.choice(["left", "right"]))
        p.both_hands_up(at=rng.uniform(0, 9), seconds=rng.uniform(0.1, 0.8))
        p.jump(at=rng.uniform(0, 9), height=0.3)
        persons.append(p)
    blobs = [moving_blob(rng.choice([0.0, 1.0, rng.random()]), rng.choice([0.0, 1.0, rng.random()]),
                         rng.random(), rng.random(), rng.uniform(0.5, 8), start=rng.uniform(0, 3),
                         color=rng.choice([(255, 255, 255), (255, 120, 0), (0, 200, 0), (255, 0, 0)]))
             for _ in range(MAX_BLOBS)]
    x0, y0 = rng.uniform(0, 0.5), rng.uniform(0, 0.5)
    motion = [motion_rect(x0, y0, x0 + 0.5, y0 + 0.5, start=rng.uniform(0, 3), seconds=rng.uniform(1, 6))]
    audio = claps(sorted(rng.uniform(0, ticks * TICK) for _ in range(20)))
    cal = Calibration()
    for i, s in enumerate(scene(persons=persons, blobs=blobs, motion=motion, audio=audio, ticks=ticks)):
        bodies = []
        for b in s.bodies:
            if (i // 2 + b.id) % 3 == 0:                      # flickering: gone two ticks in every six
                continue
            limb, edges = (i + b.id) % 4 == 0, (i + b.id) % 5 == 0
            if limb or edges:
                kps = list(b.keypoints)
                if limb:                                      # a limb at confidence 0
                    for j in ((LEFT_ELBOW, LEFT_WRIST) if b.id % 2 else (RIGHT_ELBOW, RIGHT_WRIST)):
                        kps[j] = Keypoint(kps[j].x, kps[j].y, 0.0)
                if edges:                                     # keypoints on the frame's edges
                    kps[NOSE], kps[LEFT_ANKLE] = Keypoint(0.0, 0.0), Keypoint(1.0, 1.0)
                    kps[RIGHT_WRIST], kps[RIGHT_HIP] = Keypoint(1.0, 0.0), Keypoint(0.0, 1.0)
                b = place(dataclasses.replace(b, keypoints=tuple(kps)), cal)
            bodies.append(b)
        bodies.sort(key=lambda b: -b.scale)
        yield dataclasses.replace(s, bodies=tuple(bodies))


def strobe_mix(ticks: int = TICKS):
    """spec 7.6's strobe inputs plus a person: claps at 12 Hz, tempo(180), the whole motion grid on and off on
    alternate ticks, and one player walking and raising a hand."""
    clapping, beat = claps([k / 12 for k in range(int(ticks * TICK * 12) + 1)]), tempo(180)

    def audio(t):
        a, b = clapping(t), beat(t)
        return dataclasses.replace(b, level=max(a.level, b.level), level_smooth=max(a.level_smooth, b.level_smooth),
                                   peak=max(a.peak, b.peak), clap=a.clap, onset=a.onset or b.onset)

    w, h = MOTION_GRID
    grid = np.ones((h, w), bool)

    def motion(t):
        return grid if round(t / TICK) % 2 == 0 else None

    person = Person(0.4, id=1).walk(0.6, 3.0).walk(0.4, 3.0).raise_hand(at=1.0, seconds=1.5).jump(at=5.0)
    return scene(persons=[person], motion=[motion], audio=audio, ticks=ticks)


@dataclass(frozen=True)
class Soak:
    """What one soak run measured: its seed and mix; lit, a non-black pushed frame; the traced phases; the game's
    debug_state keys; the pushed frames' square_flashes and pattern_area; error, what the run raised."""

    seed: int
    mix: str
    lit: bool = False
    phases: frozenset = frozenset()
    keys: frozenset = frozenset()
    squares: int = 0
    pattern: float = 0.0
    error: BaseException | None = None

    def check(self, where: str) -> None:
        if self.error is not None:
            raise AssertionError(f"{where}: the game raised {self.error!r}") from self.error


def _watched(records, name: str, keys: set):
    """A callable feed of records that reads the game's debug_state() keys between ticks, while it runs."""
    def feed(runner):
        for s in records:
            yield s
            if runner.current_name == name and runner.game is not None:
                keys.update(runner.game.debug_state())
    return feed


@functools.lru_cache(maxsize=None)
def soak(game_cls, layout: str, i: int, mix: str, font) -> Soak:
    seed = seeds(game_cls, layout, SEEDS)[i]
    name, rng = game_cls.info.name, random.Random(seed)
    records = (degrade(random_mix(rng, game_cls.info.needs), **REAL_NOISE) if mix == "random_mix"
               else hostile_mix(rng))
    keys: set = set()
    try:
        frames, runner = run_headless(make_cfg(_size(layout)), font, game_cls, _watched(records, name, keys),
                                      seed=seed, trace=True, raw=True)
    except Exception as e:                                    # strict: a game's exception reaches here
        return Soak(seed, mix, error=e)
    phases = frozenset(s["phase"] for s in runner.trace if s["game"] == name and "phase" in s)
    return Soak(seed, mix, lit=any(f.any() for f in frames), phases=phases, keys=frozenset(keys),
                squares=square_flashes(frames), pattern=pattern_area(frames))


def soaks(game_cls, layout: str, font) -> list[Soak]:
    return [soak(game_cls, layout, i, mix, font) for i in range(SEEDS) for mix in ("random_mix", "hostile_mix")]


@pytest.mark.parametrize("game_cls, layout", CASES)
def test_every_game_soaks_without_error(game_cls, layout, font5x7):
    name = game_cls.info.name
    for run in soaks(game_cls, layout, font5x7):
        where = f"{name} {layout} seed {run.seed} {run.mix}"
        run.check(where)
        assert run.lit, f"{where}: every pushed frame was black"
        assert run.phases <= set(game_cls.PHASES), f"{where}: phases {sorted(map(str, run.phases))} not all in " \
                                                   f"PHASES {game_cls.PHASES}"
        bad = sorted(k for k in run.keys if reserved(k))
        assert not bad, f"{where}: debug_state uses reserved keys {bad}"


@pytest.mark.parametrize("game_cls, layout", CASES)
def test_every_game_keeps_the_flash_rule_in_the_soak(game_cls, layout, font5x7):
    name = game_cls.info.name
    for run in soaks(game_cls, layout, font5x7):
        where = f"{name} {layout} seed {run.seed} {run.mix}"
        run.check(where)
        assert run.squares <= BUDGET, f"{where}: pushed square_flashes {run.squares} > {BUDGET}"
        assert run.pattern <= PATTERN_AREA, f"{where}: pushed pattern_area {run.pattern:.3f} > {PATTERN_AREA}"
    seed = seeds(game_cls, layout, 1)[0]
    _, runner = run_headless(make_cfg(_size(layout)), font5x7, game_cls, strobe_mix(), seed=seed, raw=True)
    raw = flash_area(runner.raw_frames)
    assert raw <= RAW_FLASH_AREA, f"{name} {layout} seed {seed} strobe inputs: raw flash_area {raw:.3f} > " \
                                  f"{RAW_FLASH_AREA}"


def _timed(records, stamps: list):
    for s in records:
        stamps.append(time.thread_time())
        yield s
    stamps.append(time.thread_time())


@pytest.mark.perf
@pytest.mark.parametrize("game_cls, layout", CASES)
def test_every_game_fits_the_tick_budget(game_cls, layout, font5x7):
    # The whole runner.tick on the thread's CPU clock (C36): the code's cost, not the machine's load.
    seed = seeds(game_cls, layout, 1)[0]
    records = list(hostile_mix(random.Random(seed)))
    stamps: list = []
    run_headless(make_cfg(_size(layout)), font5x7, game_cls, _timed(records, stamps), seed=seed,
                 display=RecordingDisplay(keep_all=False))
    ticks = np.diff(stamps)[WARMUP_TICKS:] * 1000
    assert len(ticks) == TICKS - WARMUP_TICKS
    mean, p95 = float(ticks.mean()), float(np.percentile(ticks, 95))
    report = f"{game_cls.info.name} {layout} seed {seed}: tick mean {mean:.3f} ms, p95 {p95:.3f} ms"
    assert mean < BUDGET_MS and p95 < 2 * BUDGET_MS, f"{report} (budget {BUDGET_MS} ms)"


@pytest.mark.parametrize("game_cls", GAMES)
def test_every_game_declares_the_required_scenarios(game_cls):
    scenarios = game_cls.SCENARIOS
    missing = [n for n in REQUIRED_SCENARIOS if n not in scenarios]
    assert not missing, f"{game_cls.info.name}: SCENARIOS lacks {missing} (has {sorted(scenarios)})"
    assert all(callable(scenarios[n]) for n in REQUIRED_SCENARIOS)


@pytest.mark.parametrize("game_cls", GAMES)
def test_every_game_has_good_and_lazy_bots(game_cls):
    name = game_cls.info.name
    bots, won = for_game(game_cls)
    assert {"good", "lazy"} <= set(bots), f"{name}: BOTS has {sorted(bots)}"
    assert callable(won), f"{name}: won is not callable"
    for key, factory in bots.items():
        bot = factory()
        assert isinstance(bot.reaction_ticks, int) and bot.reaction_ticks >= 0, (name, key, bot.reaction_ticks)
        assert isinstance(bot.noise, (int, float)) and bot.noise >= 0, (name, key, bot.noise)
        move = bot({}, 0.0)                                   # play() hands {} before the first state
        assert move is None or isinstance(move, Move), (name, key, move)
