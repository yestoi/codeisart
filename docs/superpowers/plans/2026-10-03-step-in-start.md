# Step-In Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With `--game NAME`, the arcade starts the game when the locked player has stood in the zone for two seconds, instead of on a raised hand.

**Architecture:** One flag on `Lobby` (`start_on_step_in`), set by `arcade/main.py` when `--game` is given. In `Lobby.update` the trigger that sets `fired` becomes a `Hold(STEP_IN_SECONDS)` on "a player is locked" instead of the raised-wrist `Edge`, primed at the same two places (a new player id, the end of a card). The invite pictogram is not drawn in this mode. Nothing else moves.

**Tech Stack:** Python, the arcade's `Hold` (`arcade/input.py`), pytest with the headless runner and `Person` scripts (`tests/arcade/test_lobby.py`'s helpers).

**Spec:** `docs/superpowers/specs/2026-10-03-step-in-start-design.md` (context: promptviz `docs/superpowers/specs/2026-10-03-night-one-menu-design.md`)

## Global Constraints

- Without `--game` nothing changes: every existing lobby test passes unchanged.
- No new drawing: the pictogram is dropped in the new mode, the mirror figure is unchanged. The lobby has no rows 60 to 63 test and its figure lights those rows today at 128x64 (roadmap, the it20 note); nothing is added here. `test_mirror_under_real_noise_keeps_the_area_rule` (the degraded mover, default lobby) runs unchanged.
- The suite's command: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_lobby.py` for the task; the full suite once before the commit is pushed (the Mac is shared; a time over the limit is read once more).
- No Pi, no card, no change under `deploy/`.

## Review Focus

1. A player who steps in, leaves at one second and returns must start the count again, not inherit the first second; pinned by `test_step_in_count_restarts_after_leaving` (Task 1).
2. A player who stays on the square after the card must get the game again after two more seconds, not at once; pinned by `test_after_the_card_the_count_starts_again` (Task 1).
3. A raised hand in this mode must do nothing by itself (the guest was told nothing about hands); pinned by `test_raised_hand_does_not_start_in_step_in_mode` (Task 1).
4. A passer-by crossing the zone in under two seconds must not start the game; pinned by `test_a_crossing_does_not_start` (Task 1).
5. Two bodies in the zone: the lock's player counts, not the sum; the existing lock rules apply, and `test_second_body_does_not_shorten_the_count` (Task 1) pins it.

---

### Task 1: `start_on_step_in` in the lobby, behind `--game`

**Files:**
- Modify: `arcade/attract/lobby.py` (module docstring, constants, `Lobby.__init__`, `reset`, `update`, `mode`, `_place_pictogram` call sites, `_prime`)
- Modify: `arcade/main.py:233-252` (the `--game` branch and the help text)
- Test: `tests/arcade/test_lobby.py` (append)

**Interfaces:**
- Consumes: `arcade.input.Hold(seconds, grace)` with `update(value, t) -> bool` (fires once per hold) and `reset()`; `Lobby.featured()`; `Runner` reads `lobby.request`.
- Produces: `Lobby(games, cfg, start_on_step_in: bool = False)`; `STEP_IN_SECONDS = 2.0`; `Lobby.start_on_step_in` attribute; `debug_state()["step_in"]` (the hold's progress, 0..1, in this mode; absent otherwise).

- [ ] **Step 1: Write the failing tests**

Append to `tests/arcade/test_lobby.py`:

```python
# ----- step-in start (docs/superpowers/specs/2026-10-03-step-in-start-design.md) -----

from arcade.attract.lobby import STEP_IN_SECONDS


def step_in_run(font, persons, seconds, size=(128, 64)):
    """The lobby with --game's flag over a scene, through the real runner. The one game is a spy called pong
    that ends 30 updates (1 s) after it starts, so its card follows and the count can start again."""
    games = [spy("pong", finish_after=30)]
    return lobby_run(font, games, persons, seconds, size=size,
                     setup=lambda lobby: setattr(lobby, "start_on_step_in", True))


def test_step_in_starts_the_game_after_two_seconds(font5x7):
    _, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(1.0)], 4.0)
    starts = launches(runner)
    assert len(starts) == 1 and starts[0][1] == "pong"
    at = starts[0][0] * TICK
    assert 1.0 + STEP_IN_SECONDS - 0.1 <= at <= 1.0 + STEP_IN_SECONDS + 0.2, at


def test_a_crossing_does_not_start(font5x7):
    """Review Focus 4: in the zone for 1.5 s and out again."""
    person = Person(0.5, id=1).arrive(1.0).leave(2.5)
    _, runner = step_in_run(font5x7, [person], 5.0)
    assert launches(runner) == []


def test_step_in_count_restarts_after_leaving(font5x7):
    """Review Focus 1: in at 1.0, out at 2.0, back at 3.0 as a new track id (the tracker never reuses one, and a
    Person has one arrive and one leave): the game starts near 5.0, not 4.0."""
    persons = [Person(0.5, id=1).arrive(1.0).leave(2.0), Person(0.5, id=2).arrive(3.0)]
    _, runner = step_in_run(font5x7, persons, 7.0)
    starts = launches(runner)
    assert len(starts) == 1
    at = starts[0][0] * TICK
    assert at >= 3.0 + STEP_IN_SECONDS - 0.1, at


def test_raised_hand_does_not_start_in_step_in_mode(font5x7):
    """Review Focus 3: a hand up at 1.2 s for half a second, with the player gone by 1.9 s."""
    person = Person(0.5, id=1).arrive(1.0).raise_hand(at=1.2, seconds=0.5).leave(1.9)
    _, runner = step_in_run(font5x7, [person], 4.0)
    assert launches(runner) == []


def test_after_the_card_the_count_starts_again(font5x7):
    """Review Focus 2: the player stays; the second game starts two seconds after the card ends, not at once."""
    _, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 12.0)
    starts = launches(runner)
    assert len(starts) >= 2, starts
    card_start, card_len = card_run(runner)
    card_end = card_start + card_len
    assert starts[1][0] - card_end >= round(STEP_IN_SECONDS / TICK) - 3, (starts, card_end)


def test_second_body_does_not_shorten_the_count(font5x7):
    """Review Focus 5: a second body arriving at 2.0 s does not start the game before the player's two seconds."""
    _, runner = step_in_run(font5x7, [Person(0.4, id=1).arrive(1.5), Person(0.6, id=2, height=0.5).arrive(2.0)], 5.0)
    starts = launches(runner)
    assert len(starts) == 1 and starts[0][0] * TICK >= 1.5 + STEP_IN_SECONDS - 0.1


def test_no_pictogram_in_step_in_mode(font5x7):
    """Also the spec's 1.9 s: a player present 1.4 s (0.5 to 1.9) has not started the game."""
    lobby, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 1.9)
    assert all(s.get("pictogram") in (None, False) for s in runner.trace)
    assert all(s.get("mode") != "invite" for s in runner.trace)
    assert launches(runner) == []


def test_without_the_flag_nothing_changes(font5x7):
    _, runner = lobby_run(font5x7, [spy("pong", finish_after=30)], [Person(0.5, id=1).arrive(1.0)], 6.0)
    assert launches(runner) == [], "standing still never starts a game in the default lobby"


def test_step_in_debug_state_has_progress(font5x7):
    lobby, runner = step_in_run(font5x7, [Person(0.5, id=1).arrive(0.5)], 1.5)
    last = runner.trace[-1]
    assert 0.0 < last["step_in"] < 1.0
```

The scripted `Person` helpers used (`arrive`, `leave`, `raise_hand`) exist in `arcade/sources/actors.py`; `spy`, `launches`, `card_run`, `lobby_run`, `TICK` and `font5x7` are already imported or defined at the top of `tests/arcade/test_lobby.py`. The existing `KEYS` equality assertions (`test_debug_keys_are_not_reserved` and the one near line 329) run the default lobby, where `debug_state` has no `step_in` key, so they stay as they are.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_lobby.py -k "step_in or crossing or raised_hand_does_not or after_the_card or second_body or no_pictogram or without_the_flag"`
Expected: FAIL with `ImportError: cannot import name 'STEP_IN_SECONDS'`

- [ ] **Step 3: Change `arcade/attract/lobby.py`**

Constants, after `MODES = (...)`:

```python
STEP_IN_SECONDS = 2.0        # start_on_step_in: a locked player this long starts the featured game (2026-10-03 spec)
```

Constructor:

```python
    def __init__(self, games: Sequence[type], cfg: ArcadeConfig, start_on_step_in: bool = False):
        self.games = {g.info.name: g for g in games}
        self.cfg = cfg
        self.grace = capture_grace(cfg.camera_fps)
        self.start_on_step_in = start_on_step_in     # --game: a player standing in the zone starts it, not a hand
        self.request: str | None = None
        self._available: set[str] = set()
        self._inputs: set[str] = set(INPUTS)         # every input until set_status: headless runs never sense()
        self.reset(cfg.size, None)
```

In `reset`, after `self._edge = Edge(self.grace)`:

```python
        self._step_in = Hold(STEP_IN_SECONDS, grace=self.grace)
```

In `update`, replace the block from `self._hold.update(player is not None, t)` to `self._place_pictogram(t)` with:

```python
        self._hold.update(player is not None, t)
        if self.start_on_step_in:
            if player is not None and player.id != self._player_id:
                self._player_id = player.id
                self._step_in.reset()                         # a new player: the count starts now
            elif card_ended:
                self._step_in.reset()                         # "again" needs two more seconds on the square
            fired = self._step_in.update(player is not None, t)
            self._edge.update(raised, t)                      # kept armed, never read in this mode
        else:
            if player is not None and player.id != self._player_id:
                self._player_id = player.id
                fired = self._prime(raised, t)
            elif card_ended:
                fired = self._prime(raised, t)
            else:
                fired = self._edge.update(raised, t)
        if fired and self.mode in ("mirror", "invite"):
            self.request = self.featured()
        if not self.start_on_step_in:
            self._place_pictogram(t)
```

In `mode` (the property that returns `"invite" if self._hold.fired else "mirror"`), make the invite impossible in this mode:

```python
        return "invite" if self._hold.fired and not self.start_on_step_in else "mirror"
```

In `debug_state`, add to the returned dict:

```python
                **({"step_in": round(self._step_in.progress, 3)} if self.start_on_step_in else {}),
```

Module docstring: add one paragraph after the raised-hand paragraph:

```
With start_on_step_in (`arcade run --game NAME`, the 2026-10-03 step-in spec) the trigger is a locked player
present for STEP_IN_SECONDS, counted from the lock and again from the end of each card; the pictogram is not
drawn and a raised hand does nothing by itself.
```

- [ ] **Step 4: Change `arcade/main.py`**

At line 252, pass the flag (the call becomes three lines):

```python
            runner = Runner(cfg, display, font, Lobby(games, cfg, start_on_step_in=args.game is not None), games,
                            scores=Scores(data_dir / "scores.json"), sessions=SessionLog(data_dir / "sessions.jsonl"),
                            calibration=calibration, local_clock=datetime.now, lux=None)
```

At line 229, `run()`'s docstring says "--game offers that one game only: a raised hand starts it"; change it to "--game offers that one game only: a player standing in the zone for 2 s starts it". At line 280, the help text:

```python
    r.add_argument("--game", metavar="NAME", help="offer only this game: a player standing in the zone for 2 s starts it")
```

- [ ] **Step 5: Run the lobby tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_lobby.py`
Expected: every test passes, the nine new ones included. The spy game ends 30 updates after it starts (reason "done"), its card runs 3 s, and the second launch follows about 2 s after the card; the 12 s scene holds all of it.

- [ ] **Step 6: Run the lobby and runner tests, then the full suite once**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_lobby.py tests/arcade/test_runner.py`
Expected: pass. Then the full suite: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: the collected count before the change (`pytest --collect-only -q | tail -1`, taken before Step 3) plus 9, under the 540 s limit (a time over it is read once more: the Mac is shared).

- [ ] **Step 7: Commit**

```bash
git add arcade/attract/lobby.py arcade/main.py tests/arcade/test_lobby.py
git commit -m "feat(lobby): with --game, a player standing in the zone for 2 s starts the game (no raised hand)"
```
