# Iteration 18: the oracle's plays in worker processes, then Dodge returns
BASE: the operator's commit of this plan (code head at the plan: 86f0607). Roadmap note "it18 (the suite's time and
Dodge's return; from it17)", the note "it15 (every plan; before M7a's next game)", owner decision Q81 (after D5 only
the suite's time and Dodge's return; no new game). Thin plan. NOT a safety slice (rule 4): nothing under `arcade/`
changes in O1 and T-pool; O2 restores Dodge's four files exactly as it15 built and reviewed them (c49d902, merged as
83fe13a). The evidence tool (`tools/arcade_evidence.py`), `arcade/feel.py`, `arcade/bots.py`, every seed count, every
assert and every band stay as they are; the test command does not change.

## Global Constraints
- Test command, from the root (a worktree's root in a worktree): `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
  /Users/trey/dev/codeisart/.venv/bin/python -m pytest -q -rs`. At 86f0607: 1806 passed, 3 skipped, 1809 collected,
  325.84 s (`evidence/it18/orient-durations.txt`); with 16dbb91 reverted: 1859 passed and 3 skipped expected in the main
  checkout (1858 and 4 in the scratch checkout without `models/`), 371.06 s (`orient-durations-dodge.txt`). Limit 420 s
  (Q81). A worktree's extra skip (the pose test, no model in git) is expected.
- Test-first; only your files; never `cd` (in a worktree plain git, one command a call); `git add` by name; no stash,
  push, or command over 10 minutes; `tmp_path`; every child process waited for or killed before the function that
  started it returns. Trailers `Co-Authored-By: <the committing model's own name> <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_018YqFKnchNWHcsKuxWkeYQ1`. No rulings: a gap is reported.
- No assert is removed or weakened, no band or budget changes, no seed count changes (spec 9.3's 20 stays in the suite
  and in the evidence tool). The reviewer lists every changed assert in `git diff BASE..HEAD -- tests/`; the plan
  expects none outside the new tests (the existing tests of `test_oracle.py` keep their asserts word for word).
- The wall is 128x64 (Q82): every report and play is at 128x64, as today. No new game (Q81). Nothing under `deploy/`;
  no ssh, no Pi.

## Where the time goes (the plan writer's probes, the Mac shared, load 2 to 6)
- A report is a canonical run and 60 bot plays. Canonical (with its probes and presence runs): pong 2.66 s, quickdraw
  2.20 s, dodge 2.17 s. One play, good / lazy / Nobody: pong 1.37 / 1.52 / 0.11 s, quickdraw 0.44 / 0.64 / 0.12 s,
  dodge 0.91 / 0.62 / 0.11 s. So the plays are 95% of a report: pong about 60 s, quickdraw 24 s, dodge 33 s (15 of its
  60 are already made by `test_dodge.py`, which sorts before the oracle and stores them in `PLAYS` through `played`).
- `bots.Play` pickles and the round trip is equal (`==`) for 3 seeds x 3 bots of each game; its `state` holds only
  None, bool, float, int, str, tuple.
- All 180 plays of the three games in 4 workers: 32.4 s with a spawn `ProcessPoolExecutor`, 32.5 s with 4 plain
  `python -m` subprocesses dealt round robin (the four ended within 0.2 s of each other); 3 workers 40.8 s. CPU sum
  about 125 s. Starting the 4 spawn workers and their imports took 0.11 s; the subprocess run took the same total, so
  a worker's start is under 1% of its share. The first seed of each bot of each game played in process equals the
  pooled play (`==`); the workers' `hash("pong")` differed (each its own hash seed). Under `python -m pytest` a spawn
  pool ran and its workers imported the rootdir's `arcade` (probe 3).
- The decider, probe 4a: a spawn pool, after `shutdown`, leaves the resource tracker alive as a child of the parent for
  the parent's life (`pgrep -P` lists it). In the suite's process that child is counted by `tools/show_soak.py`'s
  `children_of_this_process()`, and `tests/test_show_soak.py:67, 76, 135` assert `failures(report) == []`, which
  includes `children_left`: a multiprocessing pool (spawn or forkserver) in the pytest process would fail them. Fork
  starts no tracker but forks a process with threads (pygame, earlier tests) and is unsafe on macOS. So the workers are
  plain subprocesses, as `show/display/colorlight.py:98-99` decided for the same reason; probe 4b left no child.

## Lanes
- O1 (orchestrator, before any task): nothing to build; the orient files are the "before" measurement.
- GROUP 1, one task from BASE, `isolation: "worktree"`: T-pool (opus). Merge it (`--no-ff`), then the full suite once
  with `--durations=20` added (the measurement; the test command is otherwise unchanged), then O2. O2 only if that
  suite reads at most 380 s (measured once more when over, Q83); else Dodge waits and the journal says why.
- O2 (orchestrator, main checkout, after T-pool's merge and its suite): Dodge returns, then the full suite with
  `--durations=20` added.
- Owners. T-pool: `tests/arcade/pooled.py` (new), `tests/arcade/test_oracle.py`. O2: the four files of 16dbb91
  (`arcade/games/dodge.py`, `arcade/games/dodge_bots.py`, `arcade/games/dodge_feel.toml`, `tests/arcade/test_dodge.py`)
  by the revert only. Nobody: `tests/arcade/helpers.py` (imported, not edited), `tests/arcade/test_all_games.py`,
  `tests/arcade/test_pong.py`, `tests/arcade/test_quickdraw.py`, `tests/arcade/test_feel.py`, `arcade/` (but O2's
  revert), `tools/`, `tests/conftest.py`, `tests/arcade/conftest.py`, `pyproject.toml`, `deploy/`, the safety files.

## T-pool (opus): the oracle's plain plays made by worker processes before its reports
The oracle's memo (`tests/arcade/test_oracle.py:22-40`, `shared_plays`) already returns a plain play from
`tests.arcade.helpers.PLAYS` by `play_key(game, bot class name, seed, layout)`, and `feel._bot_plays` asks for exactly
plain plays (the game's own `won`, the default seconds, no frames, the project font). T-pool fills `PLAYS` with every
report's 60 plays from worker processes before the first report, so each `feel.report` finds them and runs only its
canonical part. A play is a pure function of (game, bot, seed, layout) (`helpers.py:36-39`); the workers run the real
`bots.play` with its defaults, never the memo.
```
# tests/arcade/pooled.py (new)
PLAY_WORKERS = 4                  # worker processes at most: the Pi 5 has 4 cores, the shared Mac 4 fast ones (Q97)
WORKER_TIMEOUT_S = 300.0          # from the first worker's start to the last's end; past it the rest are killed
ROLES = ("good", "lazy", "none")  # feel._bot_plays' three bots, in its order; "none" is bots.Nobody
ROOT = Path(__file__).resolve().parents[2]   # the checkout this file is in (a worktree's own): the workers' cwd
PYTHON = sys.executable           # the workers' interpreter (a module constant so a test can replace it)
Job = tuple[str, str, int, str]   # (game name, role, seed, layout): plain data across the process boundary
Key = tuple[str, str, int, str]   # helpers.play_key's

def bot_for(game_cls, role: str) -> bots.Bot           # a fresh bot: Nobody() for "none", else for_game()[0][role]()
def jobs(reports: Sequence[tuple[type, str, Sequence[int]]]) -> list[Job]
    # for each (game_cls, layout, seeds) in order, for each role in ROLES, for each seed in order: one job
def play_job(job: Job) -> bots.Play                    # the worker's play: get_game(name), bot_for(game, role),
                                                       # bots.play(game, bot, seed, layout) with every other default
def fill(reports, plays: dict = PLAYS, workers: int = PLAY_WORKERS) -> set[Key]
def main(argv: list[str] | None = None) -> int         # the worker: argv [jobs.json, out.pickle]
```
`fill`, so two implementers write the same function:
1. `todo`: the jobs of `jobs(reports)` whose key is not in `plays` (an earlier test's play is kept and not remade). The
   key is `play_key(game_cls, type(bot_for(game_cls, role)).__name__, seed, layout)`, the memo's key for that play.
2. `n = min(workers, os.cpu_count() or 1, len(todo))`. With `n < 2` it starts nothing and returns `set()`.
3. In a `tempfile.TemporaryDirectory()`: worker k's share is `todo[k::n]` (round robin: each worker gets a mix of the
   games and bots), written as JSON; worker k is `subprocess.Popen([PYTHON, "-m", "tests.arcade.pooled", <jobs-k.json>,
   <out-k.pickle>], cwd=ROOT, stdout=DEVNULL, stderr=<err-k.txt in the directory>)`, the environment inherited (the
   conftests' SDL dummies are set by then). `-m` with `cwd=ROOT`, never by path: by path a script imports the main
   checkout's `arcade` through the venv's editable `.pth` (config.md rule 6). Not `multiprocessing` (probe 4a).
4. It waits for every worker against the deadline `WORKER_TIMEOUT_S` from the first start. In a `finally`, any worker
   still running is killed and waited for: no worker outlives `fill`, on any path (a raise, a timeout, Ctrl-C).
5. A worker that exited 0 and wrote its file: the file holds `{"arcade": <the worker's arcade.__file__>, "plays":
   [bots.Play, ...]}` in its share's order. Its share is stored (`plays[key] = play`, the key added to the returned
   set) only when the list has the share's length and that path is under `ROOT`.
6. Any other outcome for a worker (Popen raised OSError, a non-zero exit, the deadline, a missing or short file, an
   `arcade` outside ROOT): one `warnings.warn(..., RuntimeWarning)` naming the worker, its exit code and the last 20
   lines of its stderr; its share is not stored, so the memo makes those plays in this process as today (a game's own
   exception then raises there, with its traceback, where it raises today). Returns the keys it stored.
`main`: reads the jobs, `play_job` each in order, pickles the dict of 5 to the out path, returns 0; an exception is not
caught (exit 1, the traceback in the worker's stderr file). `if __name__ == "__main__": sys.exit(main())`.

`tests/arcade/test_oracle.py` changes (its seven existing tests and their asserts stay word for word):
```
REPORT_PLAYS: list[tuple[type, str, list[int]]]   # [(Pong, LAYOUT, SEEDS)] + for each game of OTHER_GAMES
                                                  # (game, bots._layout(game, None), bots.seeds(game, that, 20))
shared_plays   # unchanged, but yields `real` (the unpatched bots.play) instead of None
pooled_plays(shared_plays) -> tuple[set[Key], set[Key]]   # module fixture: (the report keys already in PLAYS, the
                                                  # keys pooled.fill(REPORT_PLAYS) stored); fill runs once a module
pong_report(shared_plays, pooled_plays); game_report(shared_plays, pooled_plays)   # game_report reads its layout and
                                                  # seeds from REPORT_PLAYS (one table, so the pool and the report
                                                  # cannot disagree on a key)
```
The module docstring says the reports' plays come from worker processes first (`tests/arcade/pooled.py`).
`test_evidence_package_for_pong` keeps no new fixture (run alone, it starts no worker). The new tests go after it, at
the end of the module, so the first test to set up `pooled_plays` is `test_feel_pong_meets_its_budgets`, as today's
first report. The fixture is module-scoped: its workers are gone before the first report runs, and every timing test
(`tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share` and the test at `test_headless.py:236`,
`tests/arcade/test_all_games.py::test_every_game_fits_the_tick_budget`, on the thread's CPU clock) is in another
module and never runs while a worker lives.

New tests, `tests/arcade/test_oracle.py`:
- `test_jobs_name_every_report_play` (no worker): `pooled.jobs([(Pong, LAYOUT, SEEDS)])` is 60 jobs, the 20 seeds in
  order for `good`, then `lazy`, then `none`, each `("pong", role, seed, "128x64")`; every field is a str or an int,
  and a JSON round trip gives the same values.
- `test_the_pool_made_every_missing_play(pooled_plays)`: every key of every job of `REPORT_PLAYS` is in `PLAYS`; the
  keys the fill stored are exactly the report keys that were not there before it (no fallback happened: a lost
  saving fails here, with the warning's text in the summary); Pong's 60 keys are among them (no test before the
  oracle plays Pong); `tools.show_soak.children_of_this_process() == 0` (the count `test_show_soak.py` relies on).
- `test_pooled_plays_are_the_in_process_plays[<game>]`, one per game of `REPORT_PLAYS` (pong and quickdraw; dodge
  after O2): the good bot on the report's LAST seed (index 19: never one of the 5 seeds a game's own tests play first,
  so a worker made it); its key is among the keys the fill stored; `PLAYS[key]` equals `real(game,
  pooled.bot_for(game, "good"), seed, layout)` for each field of `dataclasses.fields(bots.Play)` (`seed, ticks,
  seconds, done, won, state, phases, frames`), each compared alone so a failure names the field, the game and the
  seed. `real` is `shared_plays`' unpatched `bots.play`: the memo would hand back the `PLAYS` entry itself and the test
  would pass vacuously. A game whose play depends on the hash seed (a set iterated) or on what its process played
  before fails here.
- `test_fill_warns_and_stores_nothing_when_its_workers_fail[cannot-start]` and `[exit-1]` (no play is made, under 0.1 s
  each): `cannot-start` replaces `subprocess.Popen` (through `pooled.subprocess`) with one that raises `OSError`;
  `exit-1` sets `pooled.PYTHON` to `shutil.which("false")` (the worker exits 1 and writes no file). Each replacement is
  scoped to the fill call (`pytest.MonkeyPatch.context()`): `children_of_this_process()` runs `pgrep` through
  `subprocess`, and under a raising Popen it would return 0 whatever is left. Each: under
  `pytest.warns(RuntimeWarning)`, `pooled.fill([(Pong, LAYOUT, SEEDS[:1])], plays=store, workers=2)` with `store = {}`
  returns `set()`, `store` stays `{}`; after the context, `children_of_this_process() == 0`.
Stay green unchanged: the rest of `tests/arcade/` (`test_pong.py`'s `bot_play` and `test_quickdraw.py`'s `played` read
the pooled plays from `PLAYS` as they read the in-process ones today; `test_feel.py::test_good_plays_are_reused`
patches `bots.play` in its own module), `tests/test_show_soak.py` (no child is left), `tests/test_colorlight_*.py`.
New items: 6 (5 calls under 3 s together, the pong comparison about 1.4 s).

## O2 (orchestrator, main checkout, after T-pool's merge and suite): Dodge returns
`git -C /Users/trey/dev/codeisart revert --no-edit 16dbb91` (16dbb91 reverts the merge 83fe13a; its branch is already
in main's history, so only this brings Dodge back). Check `git -C /Users/trey/dev/codeisart show --stat HEAD`: exactly
the four files, 991 lines added, none removed, and `git -C /Users/trey/dev/codeisart diff 83fe13a HEAD -- <the four
files>` empty (Dodge as it15 reviewed it). The revert's message is git's own (`--no-edit`); the journal names it.
Nothing else in the commit: `REPORT_PLAYS` and the comparison test pick Dodge up from `all_games()` (MENU_ORDER already
names `dodge`). Then the full suite with `--durations=20` added. A suite over 420 s is measured once more (Q83); over
twice, Dodge goes back out by `git -C /Users/trey/dev/codeisart revert --no-edit <the revert's sha>` and the journal
says why.

## Expected counts and times (the Mac, the load noted beside each run)
| step | collected | passed | skipped | suite | `test_oracle.py` |
| --- | --- | --- | --- | --- | --- |
| BASE (86f0607, measured) | 1809 | 1806 | 3 | 325.84 s | 88 s |
| after T-pool | 1815 | 1812 | 3 | about 270 s | about 32 s |
| after O2 (Dodge) | 1869 | 1866 | 3 | about 300 s | about 45 s |
O2 adds Dodge's 53 tests and one comparison case. In `--durations=20` after T-pool: the setup of
`test_feel_pong_meets_its_budgets` (the fill for pong and quickdraw, 120 plays, and Pong's canonical) about 25 s, was
59.80 s; `test_feel_meets_its_budgets[quickdraw]` about 2.5 s, was 24.95 s. After O2: that setup about 33 s (165
plays: Dodge's first 5 seeds come from `test_dodge.py`), `[quickdraw]` and `[dodge]` about 2.5 s each (dodge was
25.07 s). The pool's share grows with the load on the other cores: the 4 workers made the 180 plays in 32.5 s at a
load of 2 to 6. Below these numbers is fine; the orchestrator writes each run's head-of-durations, totals and `uptime`
into `evidence/it18/durations-after-pool.txt` and `durations-after-dodge.txt` (the "before" is the orient files).

## Operator, after the review (inline, not implementers); E = `docs/superpowers/workflow/evidence/it18`
1. The full suite twice at the code head on the idle Mac (the other session idle, `uptime` written beside each):
   1869 collected, 1866 passed, 3 skipped expected, under 420 s; the two times in the journal.
2. Dodge's evidence from a clean detached checkout of the code head in the scratchpad (it15's way,
   `evidence/it15/dodge-83fe13a/arcade.txt`; `git status --porcelain` clean before and after): `python -m
   tools.arcade_evidence --iteration 18 --games dodge --seeds 20 --out arcade` (its feel row at 128x64, the sheets,
   the GIF, the trace) and `python -m tools.arcade_shot dodge --lobby small --scenario canonical --raw-vs-pushed --out
   it18-dodge`, both copied to `E/dodge/`. The feel row is read beside it15's (`evidence/it15/dodge-83fe13a/games.md`,
   `feel.json`): the same code, so the same numbers are expected; a difference is reported, not judged here. The
   operator reads `feel.json` first, then the sheets and the GIF with the Read tool (verify checklist item 7).
3. The roadmap's M7a line: Dodge is on main (it18, the revert's sha; evidence/it18/dodge/); the suite's time note
   "it15 (every plan; before M7a's next game)" closed with the it18 numbers (the oracle's plays in 4 workers, about
   60 s saved; each further pose game adds about 25 s: its own tests, its soaks, its canonical, its share of the pool).

## Decisions taken (the owner's questions go to decisions.md from Q97)
- The saving is the operator's proposal: the oracle's plain plays made in worker processes, stored in `PLAYS` before
  the reports. Not taken: fewer seeds in the suite and 20 in the evidence tool (it changes what the suite asserts; not
  needed: the pool saves about 60 s), or a marker (the loop's command would run it anyway).
- Plain `python -m` subprocesses, not `multiprocessing` (probe 4a: the resource tracker outlives the pool and fails the
  soak's `children_left`), so the start method question does not arise: each worker is a fresh interpreter on the Mac
  and on the Pi alike, its own hash seed (the comparison test is the guard), importing only `tests.arcade.pooled` and
  what `bots.play` needs. The game and the bot cross the boundary by name (`get_game(name)`, the role in `BOTS` or
  `none`), the `Play` comes back by pickle. 4 workers, capped by the core count and the jobs (Q97).
- A worker that cannot start or fails gives a warning and leaves its plays to the memo (today's path, the same plays);
  `test_the_pool_made_every_missing_play` then fails, so a lost saving is never silent.
- Left alone: `test_all_games.py`'s soaks (19 s, 26 s with Dodge, in 3 to 6 s cases, in the module that holds the tick
  budget test) and Dodge's own 15 plays (7 s; they return unchanged by the revert and the oracle already reuses them).
  A later game's plan may take them.

## Risks
- Another session on the Mac (Q83): the 4 workers compete for its cores; a suite over 420 s or a timing failure is
  measured once more before anything is decided on it.
- A future game whose `debug_state()` holds something that does not pickle fails the worker (warning, the test above
  fails, its plays made in process): the fix is in that game, not here.
- Not probed: the workers on the Pi 5 (no Pi in this plan). Nothing there is Mac-only (`sys.executable`, `-m`,
  `pgrep`, `false` are on both); the operator's Pi subsets do not run `tests/arcade/test_oracle.py` today.
