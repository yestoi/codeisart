# it18 plan review (adversarial, fresh context)

Plan: docs/superpowers/plans/2026-10-01-it18-suite-time-dodge.md at 0c45b44. Probes ran in a detached scratch
checkout of 0c45b44 with 16dbb91 reverted by `--no-commit`. The checkout was removed afterwards, and the main checkout
is clean.

## Verdict: BLOCKED

The design holds: the facts about the code, the pool, the tests and the counts are right, and I reproduced them (see
below). The one blocker is O2's commit message. It is a one-line fix and needs no new probe.

## Blocking findings

1. **O2 and its fallback commit without the trailers that the plan requires.**
   - **Plan lines:** 152 and 155 (`revert --no-edit 16dbb91`, "The revert's message is git's own") and 158 (the
     fallback `revert --no-edit <the revert's sha>`).
   - **The constraint:** Global Constraints lines 16-18 require the `Co-Authored-By: <the committing model's own
     name>` and `Claude-Session: ...` trailers on every commit, and O2 is the orchestrator's commit.
   - **What happens:** `--no-edit` writes git's default message (`Revert "Revert "Merge G2: Dodge (it15)""`, plus
     "This reverts commit 16dbb91..."). That message carries no trailers and gives no reason. Nothing adds the
     trailers later: `.git/hooks` has no active hook, and `scripts/operator/guard_bash.py` has no rule on commit
     messages.
   - **Precedent:** 16dbb91 had a written message with its reason (the cut order and the 334.84 s) and a
     `Co-Authored-By` trailer. The fallback revert would also lose the reason that made it.
   - **Smallest fix:** use `git -C /Users/trey/dev/codeisart revert --no-commit 16dbb91`, then
     `git -C /Users/trey/dev/codeisart commit` with a subject, one line on why (it18 O2: the suite after T-pool) and
     the two trailers in the last paragraph. Do the same for the fallback, with the two suite times in its message.
     The checks that follow (`show --stat HEAD`: 4 files, 991 insertions; empty diff against 83fe13a) stay as they
     are.

## Notes (non-blocking)

- **Line 104, "its seven existing tests":** at BASE, `test_oracle.py` has 5 test functions and 5 items (7 items with
  Dodge). The intent is clear: keep every existing test and assert word for word.
- **`n < 2` is silent (fill step 2):**
  - On a host where `os.cpu_count()` is 1, the fill starts nothing and gives no warning.
  - `test_the_pool_made_every_missing_play` then fails without any text.
  - Both failure tests also fail there, because with `workers=2` they need n = 2 to start a worker.
  - The Mac (8) and the Pi 5 (4) are fine.
- **`WORKER_TIMEOUT_S = 300.0`:**
  - A hung pool plus the in-process fallback makes the suite about 630 s. That is over the 600 s Bash limit and the
    plan's "no command over 10 minutes".
  - Only a hang reaches it, because a play is bounded by MAX_PLAY_SECONDS.
  - The 180 plays took 32.7 s here, so 120 s would still be about 4x.
- **`main` (line 101), "pickles the dict of 5":** this reads as "step 5's dict" (`{"arcade", "plays"}`). Worth
  rewording so nobody looks for five keys.
- **The "under ROOT" check (step 5):** in the main checkout, `.claude/worktrees/*/arcade` is also "under ROOT".
  `Path(arcade.__file__).resolve().parents[1] == ROOT` is exact. With `cwd=ROOT` the loose check cannot be fooled, so
  this is taste.
- **The 380 s gate is sound, with about 11 s to spare.** After the pool, Dodge adds about 29 s:
  - its 53 tests, about 20 s (45.2 s measured minus its 25.07 s report);
  - its canonical, 2.5 s;
  - 45 pooled plays, about 25 s of CPU over 4 workers, so about 6 s.

  So 380 + 29 is about 409 s, under 420. The twice-over-420 fallback covers a noisy run.
- **`children_of_this_process()` returns 0 when pgrep is missing** (OSError). On such a host that check would pass
  without testing anything, but pgrep is on both the Mac and the Pi.
- **`cannot-start` replaces the Popen of every module:** `mp.setattr(pooled.subprocess, "Popen", raiser)` makes
  `subprocess.Popen is raiser` true for every module, `tools.show_soak` included (I checked this inside the context).
  So the plan's scoping is both required and enough: the children are counted after the context ends.

## What I checked and found right

- **The memo (attack 1):**
  - `feel._bot_plays` passes the game's own `won`, which is the same function object `for_game` returns. It uses
    the default seconds, no `keep_frames`, and the project font from `bots._font`, so every play it asks for is
    plain.
  - The key is (game name, bot class name, seed, layout). Because the game name is part of the key, Pong's `Good`
    and Quickdraw's `Good` cannot collide.
  - `Play` holds no font. Pong's font-keyed mask cache is per instance and affects drawing only.
- **The purity of a play:**
  - `run_headless` keeps Scores and SessionLog in memory and fixes the local clock at OPENING_NIGHT.
  - The monotonic clock is used only in `sense` and `loop`, never in `tick`.
  - Nothing in `arcade/` uses the global `random` or `np.random`; each rng comes from a crc32 seed.
  - `Calibration()` is pure.
  - A play writes nothing to disk and reads only the font.
- **Probe 1, the pool (my `pooled.py`, written to the plan's interface):**
  - 4 plain `python -m tests.arcade.pooled` workers with `cwd=ROOT` made all 180 plays of pong, quickdraw and dodge
    in 32.7 s at load 3.3, with no warning.
  - The workers imported the checkout's `arcade`. `sys.path[0]` is the physical `/private/tmp/...` path from
    `getcwd()`, which matches the resolved ROOT. The editable finder is appended to `meta_path`, so the cwd wins.
  - `children_of_this_process()` was 0 after the fill.
  - Pooled plays equalled in-process plays, field by field, in two checks: 18 plays made after the parent had first
    played other seeds, and 41 good plays (all 20 seeds of quickdraw and dodge, plus Pong's seed 19).
  - Across all 180 states, every value is None, bool, float, int, str or tuple, and every float is finite, so no NaN
    breaks `==` after the pickle.
  - A worker imports neither pytest nor pygame, and it runs without the SDL variables.
- **Probe 2, the two failure tests as specified (`MonkeyPatch.context` inside `pytest.warns`):** both warn once per
  worker, return `set()`, leave `store` as `{}`, take 0.02 s, and leave 0 children.
- **Packaging (attack 2):** `tests/__init__.py` and `tests/arcade/__init__.py` exist and are empty. `pooled.py` is not
  collected under the default `python_files`. The only plugin is pytest 9.1.1 itself: no randomizer, no xdist.
- **Order (attacks 3 and 4):**
  - `tests/arcade/` is collected before `tests/test_*.py`.
  - Before the oracle, only `test_dodge.py` (after O2) stores report keys: 15 of them, seeds 0 to 4, through
    `played`.
  - `test_quickdraw.py`'s `played` and `test_pong.py`'s `bot_play` run after the oracle. `bot_play` only reads
    `PLAYS` and never stores, so "Pong's 60 keys are among them" holds whatever the file order.
  - No test plays seed index 19 before the fill.
  - `test_feel.py` patches `bots.play` at function scope. `test_arcade_evidence.py` never touches `PLAYS`.
  - Every subprocess in the earlier `tests/arcade` modules is a waited `subprocess.run`, so 0 children holds at the
    end of the oracle module.
  - The timing tests are in earlier modules (`test_headless.py`, `test_all_games.py`), and the fill runs
    synchronously inside a module fixture.
  - `shared_plays` yielding `real` changes nothing for the fixtures that take it.
- **O2 (attack 5):**
  - The revert applies cleanly on 0c45b44: 4 files, 991 insertions, and an empty diff against 83fe13a.
  - No code changed between 86f0607 and 0c45b44.
  - Since 83fe13a, `arcade/` changed only in `__main__.py`, `main.py` and `quickdraw.py`, none of them on Dodge's
    headless path, so Dodge's evidence should match it15's.
  - MENU_ORDER names dodge, and `all_games()` returns pong, quickdraw, dodge.
  - No test hard-codes the game count; `test_game.py:236` already names dodge.
  - The counts are right: 1809 + 6 = 1815; 1862 - 1809 = 53 measured; 1815 + 53 + 1 = 1869.
- **The rules (attack 7):**
  - No assert, band, seed count or test command changes.
  - No safety file is touched (rule 4).
  - `helpers.py` is imported, not edited (rule 6).
  - The plan is 210 lines (rule 1).
