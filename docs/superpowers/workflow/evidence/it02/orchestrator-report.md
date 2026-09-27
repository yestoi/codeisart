# Iteration 2 orchestrator report

Plan: `docs/superpowers/plans/2026-09-27-it02-carried-sensed-actors.md`. Range: b93e767..3017693, on main, not pushed.

## Completed

- Task 1, display hardening (C1-C3, C7, C8): done, task review clean. Suite at that commit: 85 passed, 0 skipped.
- Task 2, config range checks and per-key calibration validation (C5, C6): done, task review clean. 123 passed, 0 skipped.
- Task 3, anchored `.gitignore`, `within()` and the `probe_pose` timeout (C9): done, task review clean. 134 passed, 0 skipped. The doctor exits 0 for `--require pose` (`pose    ok  mediapipe 1.0.0: landmarker ran in ... ms`), 1 with `--timeout 0.01` (`pose    UNAVAILABLE  pose landmarker did not finish within 0.01 s`) and 2 for `--require ""` (`names no source`).
- Task 4, the Sensed record (`arcade/sensed.py`, `arcade/sources/mirror.py`): done, task review clean. 153 passed, 0 skipped.
- Task 5, actors, poses and exact event ticks (`arcade/poses.py`, `arcade/sources/actors.py`): done, task review clean. 169 passed, 0 skipped.
- Task 6, `degrade`, `REAL_NOISE` and festival scenes: done, task review clean. 183 passed, 0 skipped. The `actors.py` change is additions only on top of Task 5's file.
- Every production and test file is byte-identical to the plan's code block. I checked this with `cmp` after each task, and the final reviewer checked all 22 files again on its own.
- Implementers were sonnet, one fresh one per task. Task reviewers were sonnet. The final whole-branch review was opus.
- I ran all 7 Iteration verify steps myself, and all pass:
  1. `pytest --collect-only -q | tail -1` prints `183 tests collected`.
  2. `pytest -q -rs` prints `183 passed`, 0 skipped, with per-module counts matching the plan (table below).
  3. `git diff 7697d01 -- tests/ | grep '^-[^-]'` prints exactly the 5 expected lines, none of them an assert:
     - `from arcade.main import doctor, main`
     - the two lines of the old `from show.display.colorlight import (DST_MAC, ...` import
     - the old 3-entry `@pytest.mark.parametrize("width,height", ...)`
     - the old `Recorder.__init__(self, width, height, iface, sock=None)`
  4. Doctor exit codes are 0, 1 and 2, as in Task 3 above.
  5. `git check-ignore --no-index -v tests/arcade/fixtures/data/x.jsonl.gz` prints only `exit 1`.
  6. Importing `arcade.sources.actors` and `arcade.sensed` loads none of cv2, mediapipe, sounddevice or pygame (`[]`).
  7. `git log --oneline -6` shows the six commit messages in order. `git status --short` shows only ` M docs/superpowers/workflow/state.md`, which was never staged.
- `arcade/games/__init__.py` does not exist. Nothing was pushed or deployed. The only file I created under `docs/superpowers/workflow/` is this report, at the team lead's request.
- Final whole-branch review (opus): 0 implementation deviations, 0 Critical findings. It raised 1 Important and 5 Minor findings, all plan defects (see Deviations). Its verdict was "Ready to merge: with fixes", and the fix it means is the Important plan defect.

### Rulings I made

1. **Implementers copied the plan's code instead of retyping it.** They copied pre-extracted plan code blocks into place and then diffed them against the brief. Why: the plan requires a verbatim copy, and a mechanical copy removes transcription risk. Cost if wrong: none beyond a possible extraction bug, and `cmp` plus the reviewers would catch that.
2. **I rejected a Task 5 review finding.** The reviewer said `level_ramp` divides by zero on equal timestamps. Ruling: the code stands, because the `ta <= t < tb` guard is false when `ta == tb`, so the division never runs. Correction: the ledger first recorded `level_ramp([(1, .5), (1, .9)])(1.0)` as returning 0.9. I re-checked and it returns 0.5, with no error. The ruling itself is unchanged. Cost if wrong: none; this is an untested authoring utility.
3. **I ran no fix wave for the final-review findings.** Every one is a plan defect, and the team lead's rules say plan defects are listed for the operator, not fixed. Cost if wrong: the keyword-only fix for `Sensed` and `Audio` lands one iteration later.

## Deviations

### Implementation deviations

None.

### Plan defect, Important

**1. `Sensed` and `Audio` accept positional arguments, so the core plan's revision-2 calls would bind values to the wrong fields without any error.**
- Where: `arcade/sensed.py:253-264` (`Audio`) and `arcade/sensed.py:300-312` (`Sensed`).
- The new field order is `Sensed(t, camera_t, camera_fresh, camera_seq, bodies, ...)` and `Audio(level, level_smooth, peak, voice_db, ...)`.
- The core plan (`docs/superpowers/plans/2026-09-26-wall-arcade-core.md`) still calls them positionally in these places:
  - Task 8 runner `sense()`, line 2884: `Sensed(self.t, tuple(bodies), tuple(blobs), motion, a)`
  - Task 12 `decode`, lines 3659 and 3661
  - Task 14, line 4157
  - Task 18 `record`, line 5267
- Evidence (I confirmed this myself): `Sensed(1.0, (), (), None, Audio())` builds with no error. It gives `camera_t` a tuple, sets `camera_seq=None` and sets `bodies` to an `Audio` object. The final reviewer also showed that `Audio(0.8, 1.0, True, False, None)` gives `peak=True`, `voice_db=False` and `floor_db=None`, again with no error.
- The plan's "Forwarded to later amendments" note that covers `decode` (plan line 56) is addressed to core Task 7. But `decode` is in core Task 12; Task 7 is the game protocol. The note is also not in the roadmap's carried fixes, so it could be lost.
- Suggested fix:
  - Make every field after `t` in `Sensed` keyword-only (`_: dataclasses.KW_ONLY` right after `t`), and all fields of `Audio` keyword-only. Every call in the repo already uses keywords, so no test changes.
  - Re-address the forwarded note to core Task 12 and carry it on the roadmap (for example as C12).
  - Point the note at the Task 8, 14 and 18 calls as well, and have it say that `decode` must call `place()` (see Minor 4).

### Plan defect, Minor

**1. Calibration has to be passed three times.**
- `scene`, `degrade` and `shake` (`arcade/sources/actors.py:250, 342, 357`) each take `calibration=None` and fall back to the default zone.
- If you pass the calibration to `scene` but not to `degrade`, every capture is re-placed against the wrong zone.
- Evidence: with `Calibration(zone=(0.5, 0.2, 1.0, 0.8))` and `Person(0.85)`:
  - `scene` gives `in_zone=True`.
  - `degrade` without the calibration gives `False`.
  - `degrade` with it gives `True`.
- `shake` has a test for this; `degrade` has none.
- Suggested fix: add a test, or have `scene` carry the calibration forward.

**2. With one shoulder and no hips, the raise line drops to shoulder height.**
- Where: `arcade/sensed.py:144-170`. `torso` is 0 because `shoulder_width` needs both shoulders.
- As a result:
  - `raise_line` equals the shoulder y, so a wrist 0.005 above the shoulder counts as raised.
  - `scale` is 0.
  - `reach` falls back to the box.
- This is rare with actors (about 0.6% of captures under spec 6.4 noise), but it is real for someone close to a low camera.
- Suggested fix: use the nose raise line when `torso == 0`.

**3. Actor body ids can collide.**
- `crowd` hard-codes ids `100 + i` (`arcade/sources/actors.py:286`), and `scene` does not check for duplicates.
- `scene([Person(), *crowd(2), *crowd(2)])` gives ids `[0, 100, 101, 100, 101]`.
- Duplicate ids get identical `degrade` noise, and they would confuse core Task 8's `PlayerLock` when it re-acquires the player.
- Suggested fix: have `scene` raise on duplicate ids, or give `crowd` an id base.

**4. `in_zone` defaults to True.**
- Where: `Body.in_zone` at `arcade/sensed.py:79` and `Blob.in_zone` at `arcade/sensed.py:250`.
- Any producer that skips `place()` treats every body as in-zone, crowd included, so a crowd body can take the player slot.
- Core Task 12's revision-2 `decode` builds `Body` without calling `place()`.
- The plan-literal `test_body_defaults_and_measured_scale` pins this default, so the cheaper fix is the forwarded note in Important 1.

**5. Type protocol mismatch (cosmetic).**
- `DisplayConfig` declares `iface: str` (`show/display/__init__.py:21`), but `show.config.Config` has only `colorlight_iface`. A static type checker would reject `make_display(Config(...))`. The docstring explains the fallback.
- Separately, `test_make_display_starts_at_the_configured_brightness` uses a `SimpleNamespace` in place of `ArcadeConfig`. A case with a real `ArcadeConfig(backend="colorlight")` would pin the actual type.

### Note for M3 (not a defect in this iteration)

- Under spec 6.4 noise, a person holding both hands up reads `both_hands_up` on only 70.9% of 299 captures, because both wrists must be confident.
- In 30 s there were 3 runs of 3 or more missed captures, each longer than `Hold(grace=0.25)`. So a 3 s `exit_seconds` hold will often reset under `degrade`.
- `raised_wrist` holds on 97.7% of captures, with no such runs.
- The M3 plan should size the exit grace per capture and test it under `degrade`, alongside C10.

### Deferred minors from the task reviews

The final reviewer triaged these, and none must be fixed before acceptance. All are plan-mandated.
- Task 1: the Colorlight bind error message uses a `e.strerror or e` fallback, on an error path no test reaches.
- Task 2: the calibration `static_mask` x, y and radius share one error label.
- Task 2: the calibration missing/unknown warning prints empty lists (cosmetic).
- Task 4: `sensed._clean` repeats the clamp inline instead of calling `_clamp01`.
- Task 5: `test_actors` puts several behaviours in one test function (style).
- Task 6: `degrade` reuses the local name `shot` for two things (style).

### Reviewed and left alone by the final reviewer

These are out of this plan's scope or already carried:
- `inf` is accepted for `*_seconds` and `night_lux`; `max_session_seconds = inf` has a reasonable meaning (no cap).
- `ddp_port` has no range check, `camera_index` can be negative, and width and height have no upper bound. These are outside C5's list.
- `Body.box` is not cleaned for NaN or out-of-range values; `place` and `reach` already degrade without raising.
- `shake` wrapped around an already-degraded stream would jitter every tick instead of every capture; its docstring says it wraps a scene.
- Degraded bodies keep the scene's `box`, `scale`, `vx` and `vy`; the spec says those come from the tracker, which is later work.
- `Blob` has no id or velocity: already carried as C11.
- The cursor flipping between hands: already carried as C10.

## Test status (command + counts)

Command, run from the repo root at HEAD 3017693:
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`

Result: **183 passed, 0 skipped.** Collect-only reports `183 tests collected`.

Running totals after each task match the plan: 85, 123, 134, 153, 169, 183.

| Module | Tests |
|---|---|
| `tests/arcade/test_actors.py` | 16 |
| `tests/arcade/test_calibration.py` | 23 |
| `tests/arcade/test_config.py` | 42 |
| `tests/arcade/test_doctor.py` | 10 |
| `tests/arcade/test_festival.py` | 14 |
| `tests/arcade/test_mirror.py` | 2 |
| `tests/arcade/test_sensed.py` | 17 |
| `tests/test_colorlight.py` | 29 |
| `tests/test_config.py` | 5 |
| `tests/test_ddp.py` | 8 |
| `tests/test_display.py` | 4 |
| `tests/test_font.py` | 7 |
| `tests/test_gitignore.py` | 6 |

## Commits (sha + subject)

Every commit ends with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

- 26f684f fix(show): Colorlight safe start brightness and periodic resend, uint8 frame checks, clear iface and CAP_NET_RAW errors (it01 C1-C3, C7, C8)
- 13ca20a fix(arcade): config range checks, per-key calibration validation, fsync the directory (it01 C5, C6)
- 62a4fe6 fix(arcade): anchor the runtime ignores, doctor --require '' exits 2, probe_pose honours its timeout (it01 C9)
- a6d957c feat(arcade): Sensed record per spec 5 with raise line, reach box, place() and mirroring (core Task 3)
- f84700f feat(arcade): actors with exact event ticks, wrist ramps, poses, motion and level scripts (core Task 4, part 1)
- 3017693 feat(arcade): degrade, REAL_NOISE and festival scenes (core Task 4, part 2)

The ledger, briefs, per-task implementer reports and review packages are kept in `/Users/trey/dev/codeisart/.superpowers/sdd/2026-09-27-it02-carried-sensed-actors/`, which is git-ignored.
