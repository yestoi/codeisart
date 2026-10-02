# Adversarial review: the arcade on the wall, stage 1 plan

Date: 2026-10-02, 10:35 CDT. Reviewer: a fresh-context agent. Plan:
`docs/superpowers/plans/2026-10-02-arcade-on-the-wall-stage1.md` (untracked). Spec:
`docs/superpowers/specs/2026-10-02-arcade-on-the-wall-design.md` (ee5ab0d). Repo at ee5ab0d.

Counts: 1 Critical, 4 Important, 9 Minor.

How it was checked: Tasks 1 to 5 and Task 8b's code were pasted verbatim (cut from the plan by line number)
onto a scratch copy of `arcade/`, `show/`, `tools/`, `tests/arcade/` in the session scratchpad and run with the
repo's `.venv/bin/python`. Task 7's edits were applied to a scratch copy of the workflow files and
`scripts/operator/reinject.py --fresh` was run on it. The full suite was not run. No repo file was edited but
this one. Nothing was run on the Pi; the picamera2 and IMX500 points come from the picamera2 docs (Context7,
`/raspberrypi/picamera2`) and from what I know, and are marked where they are not verified.

## Critical

### 1. Task 9 step 2: the gamma check's mapping is the reverse of the code's, and its guard can never pass

Evidence:
- `arcade/look.py:65-68`: the light table is `v ** (MONITOR_GAMMA / gamma)`, not `(byte / 255) ** gamma`.
  `light_lut` docstring, `look.py:74-75`: "With gamma 2.2 the card sends bytes as they are and the light is
  linear in the byte; with 1.0 the card applies gamma and the light is (byte / 255) ** 2.2."
- Run: `light_lut(2.2)[128] = 0.502`, `light_lut(2.2)[186] = 0.729`; `light_lut(1.0)[128] = 0.22`,
  `light_lut(1.0)[186] = 0.5`.
- `tools/wall_pattern.py:84-87`, the text the tool itself prints during the run: "The checker matches the LEFT
  patch: the card sends bytes as they are, keep gamma = 2.2 in arcade.toml. It matches the RIGHT patch: the card
  applies gamma, set gamma = 1.0." `arcade/config.py:107` and `show/wall.py:31` say the same.
- The plan says the opposite: "right": `gamma = 2.2` stands; "left": `arcade.pi.toml` gains `gamma = 1.0`.

What happens as written: the step tells the executor to confirm the formula is `(byte / 255) ** gamma` and to
change nothing if it is not. It is not, so the step can never set `gamma`, and the spec's item 4 ("`gamma`
follows the wall session's gamma check") is not met. If the executor reads the guard loosely and follows the
bullets: on a wall that is linear in the bytes (checker matches the left block) `gamma = 1.0` makes the limiter
and the flash governor model byte 128 as 0.22 of full light where the wall emits 0.50
(`arcade/brightness.py:30`, `arcade/flash.py:36`, `arcade/runner.py:304`): both under-read the light, the APL
cap lets through more than the supplies are sized for. That is the one step in the plan that changes what the
governor and the limiter do. The third bullet is wrong the same way: with the card at 2.8
(`evidence/hardware.md:227, 329, 354`) the nearest allowed value is 1.0 (the model reads `v ** 2.2`, still over
the wall's `v ** 2.8`, the safe side), not 2.2 (the model reads `v`, 0.50 for a grey the wall shows at 0.15: safe,
but the limiter dims far more than it needs to).

Smallest fix: replace the three bullets and the guard with the tool's own mapping:
- guard: `light_lut` is `(byte / 255) ** (2.2 / gamma)` (`look.py:68`);
- "left" (128): the wall is linear in the bytes; `gamma = 2.2` stands, nothing changes;
- "right" (186): the card applies 2.2; `arcade.pi.toml` gains `gamma = 1.0`;
- "neither, the checker is brighter than the right block": the card's curve is steeper than 2.2;
  `arcade.pi.toml` gains `gamma = 1.0`, the nearest value allowed (the model still reads mid greys brighter than
  the wall shows them: the safe side), recorded as an owner item;
- "neither, the checker is darker than the left block" or anything else: nothing changes, recorded.

## Important

### 2. Runbook section 4 and Task 9: the early stop cannot get the Pi's lock while a run holds it

Evidence: Global Constraints: "Every Pi command is one ssh call whose whole remote command starts with
`flock -w 300 /tmp/pi5.lock `". A run is `flock ... sudo systemd-run --pipe --wait ...`: `--wait` keeps
`systemd-run`, and so `flock`, alive for the whole run (up to 300 s). The stop, `sudo systemctl kill -s INT
arcade-wall`, sent as the rule says under the same `flock -w 300`, waits for that lock until the run has ended
by itself; it then finds no unit. `evidence/it16/wall-session.md` shows no earlier session stopped a run early
under the lock (run 7 used `timeout`, lines 98-104), so this path has never been exercised. At the wall this is
the only stop the plan gives for a picture that must come down now.

Smallest fix, one of:
- the runbook and Task 9 name the stop as the one Pi command sent without the lock, at the owner's word
  (`ssh trey@codeisart.local 'sudo systemctl kill -s INT --kill-whom=main arcade-wall'`); the operator's guard is
  inert in this session (`_common.is_operator`), the rule is the owner's to bend; or
- start runs without `--pipe --wait` (the call returns, the lock is free), read the run with
  `journalctl -u arcade-wall` under the lock afterwards. This changes the proven form of 2026-10-01, so the
  first is smaller.

The signal itself is right: `systemctl kill` reaches python once; the sender child ignores SIGINT
(`show/display/colorlight_sender.py:415`); `run` closes the display on it (`arcade/main.py:180-186`; checked in
the scratch copy: one SIGINT 4 s into a run, `display.close()` called once, exit 0).

### 3. Task 2: `capture_array("main")` has no timeout, so Review Focus 3 does not hold on the real camera

Evidence: picamera2 docs (Context7, `api-reference/job.md`): "Synchronous (default, wait=None): frame =
camera.capture_array()  # Blocks until capture complete"; "frame = camera.capture_array(wait=5.0)  # Wait max 5
seconds" raises `TimeoutError`. When frames stop (the ribbon works loose) the call does not raise, it blocks.
So `read()` never returns `(False, None)`, and:
- the camera thread never ends; `ThreadedCamera.close()` gives up after 2 s and leaves the device open
  (`arcade/sources/camera.py:338-341`). The arcade itself goes on: `latest()` goes stale
  (`camera.py:330`);
- `arcade doctor --capture picamera2` and `run --require camera` hang for good in `_first_frame`: the camera
  probe is not under `within` (`arcade/main.py:138`), and "no frames in 5 s (is the ribbon seated...)" is never
  printed for picamera2.
The plan's test only covers a fake that raises.

Smallest fix: `self._cam.capture_array("main", wait=READ_TIMEOUT)` with `READ_TIMEOUT = 2.0`; `FakeCam`'s
`capture_array(self, name, wait=None)`; the first test's last assert unchanged. `TimeoutError` is then caught by
`read()`'s `except` and becomes `(False, None)`. Check on the Pi in Task 8 step 5 that 0.3.37 takes `wait=` as a
number. Side note: `read()` uses `log.exception`, so a probe whose reads fail prints a traceback per read
(every 0.05 s for the timeout), against Review Focus 5's "no traceback"; `log.warning` once is enough.

### 4. Task 8 step 7: the check reads log lines the arcade does not write

Evidence: `arcade/runner.py` logs only a refused launch (351, 355), a crash (403, 420), a failed push (565), a
governor hold (569) and a failed source (584). Run in the scratch copy: `arcade run --script walkup --seconds 6
-v` printed one line, `INFO arcade.main: wall 128x64, backend fake`, through a walk-up, a lock and a launch.
There are no "session lines" and nothing says a player was locked. With `backend = "fake"` there is no picture
either, so the step passes on an arcade that sees nobody: the last check before the card would not catch a pose
pipeline that opens and tracks nothing. The same holds for Task 9's "checked to have started (its first log
lines)": one line.

Smallest fix: make step 7 read a fact. Either the owner raises a hand in the 30 s and the call ends with
`tail -1 data/sessions.jsonl` (a session of `copyme` with today's time), or the step is a stdin script in step
5's form: `make_sources(load_config(...), ...)`, then once a second for 10 s print
`len(camera.latest()[1])` (the bodies), then `camera.close()`.

### 5. Task 8 step 4, and the runbook's start line in the `sh -c` form: the nested quotes break

Evidence: Task 8 says every command is the remote part of
`ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sh -c '<script>'"`. Step 4's script holds double quotes
(`sed -i "s/..."`, `-e ".[pi,dev]"`, `python -c "..."`), which end the outer string. `shlex.split` of the
assembled line gives `... sh -c 'cd ~/codeisart && sed -i s/^include-system-site-packages`, `=`,
`false/include-system-site-packages`, `=`, `true/ .venv/pyvenv.cfg && ...`: the remote `sed` gets a cut script
and fails (nothing is changed; it fails safe), and zsh on the Mac globs the bare `.[pi,dev]`. The start line's
`-p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE'` breaks inside `sh -c '...'` too: run locally,
`sh -c 'printf "[%s]\n" systemd-run -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/x'`
prints `[systemd-run] [-p] [AmbientCapabilities=CAP_NET_RAW]` and drops the rest.

Smallest fix: say which form each command takes. The start line goes as one command in double quotes, the form
of 2026-10-01 (`ssh trey@codeisart.local "flock -w 300 /tmp/pi5.lock sudo systemd-run ... -p
AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' ..."`). Step 4's script is written with no double quotes inside
(`sed -i s/^include-system-site-packages\ =\ false/include-system-site-packages\ =\ true/`, `-e .[pi,dev]`
inside the single quotes, and the python check as a stdin script in step 5's form).

## Minor

### 6. Stated red-run results are wrong in three places

- Task 1 step 2 says 2 failed. Run: `1 failed, 1 passed`. `test_capture_rejects_another_value` passes before
  the implementation: `unknown config keys: ['capture']` matches `match="capture"`. Fix: say so, or match
  `"capture must be one of"`.
- Task 3 step 2 says 6 failed. Run: `6 failed, 2 passed`: `-k "capture or picamera2"` also selects the existing
  `test_capture_stamped_on_the_injected_clock_in_seconds` and `test_tap_gets_one_raw_record_per_due_capture`.
  In that red run `test_without_picamera2_...` opens the Mac's real camera 0 (5 s, the camera light) because
  `open_capture` still ignores the kind. Harmless; say it.
- Task 5 step 2 says FAIL. Run: `1 failed, 1 passed` (the gamma-bound test passes on a missing file).

### 7. Task 7: the loop will take M8, but five things it reads still name the old plan

The edited files parse: on the scratch copy `state_phase` gives `gated`, `agent_in_flight` False, each of
`phase`, `milestone`, `plan` matches one line, the M8 and M7b lines are each unique, `reinject.py --fresh` runs.
`state.md`'s three lines and Q181 are explicit, and roadmap line 10 ("the first unchecked `M` line whose needs
are met") then gives M8 after M5. Still pointing at Paint and Tug:
- the last journal entry, which `reinject.py` prints at every start: "Iteration 22: the suite's room for two
  more games (the soaks in workers), C57, then M7b's Paint and Tug" (`journal.md`, the end of Iteration 21);
- `roadmap.md:109`, the sentence right above where the Q181 paragraph goes: "Iteration 22: the suite's room
  (the soaks in workers), C57, then M7b's Paint and Tug";
- `config.md:17`: "in the roadmap's order: ... M5 (no audio source, Q99), M7b, M8, M6";
- `roadmap.md:129`, C57: "the first task in `arcade/games/jump.py` in it22's plan";
- `gate.md`'s own "Default" paragraph and its "The plan review" row, under the inserted ANSWERED note, until
  the owner deletes the file; and `state.md`'s `decisions:` line, which ends at Q180.
Fix: one clause in the roadmap paragraph ("this replaces line 109's 'Iteration 22: ...' and config.md's order
M7b, M8"), Q181 added to `state.md`'s `decisions:` line, and Q181 saying where M8's writer puts its report:
`evidence/it22/plan-writer-report.md` exists (the Paint and Tug writer's) and the Plan writer prompt
(`config.md:156-158`) would write over it.
Also: step 2 calls the target "the 'After iteration 9' section's last paragraph"; it is the one before last
(the last is "Iteration 15 is done", `roadmap.md:113`). The ending text is unique, so the edit lands.
Also: step 6's `test_hooks.sh` builds its own files under `mktemp` (`test_hooks.sh:7, 19, 36`) and never reads
the real `state.md`: it says nothing about the edit. A real check is
`OPERATOR=1 CLAUDE_PROJECT_DIR=$PWD python3 scripts/operator/reinject.py --fresh </dev/null` and reading what
the loop will be shown.

### 8. Task 7 steps 8 and 9, and the plan's header: main is already pushed

Evidence: `git reflog show origin/main --date=iso`: `600bc3c ... 2026-10-02 10:01:30: update by push`;
`git rev-list --count origin/main..main` is 1 (ee5ab0d, the spec). The plan says the Pi's 56e585d is
origin/main, "the Mac's main is 86 commits ahead and not pushed", "about 90 commits ahead of origin". The push
will carry about nine commits, and the Pi can already pull iteration 21's code. (The range already pushed holds
no image: `git diff --name-only 56e585d..600bc3c -- '*.png' '*.jpg' '*.jpeg' '*.gif' '*.mp4'` is empty.)
Step 8 expects a clean tree, but no step commits the plan file itself (`git status`: `?? docs/superpowers/
plans/2026-10-02-arcade-on-the-wall-stage1.md`) or this review. Fix: correct the numbers; add both files to
Task 7's commit.

### 9. Task 8 steps 1 and 2: the order, and what the packages can change (not verified on the Pi)

Step 1 expects its result "after the packages and a boot", which is step 2, and then says "Nothing below starts
until a camera is listed": read in order, step 2 never runs. As far as I know the kernel's `imx500` driver and
its overlay ship with the kernel, and `imx500-all` brings the two firmware files the sensor needs to stream,
models and tools, not the detection: "the kernel log names no sensor" with `camera_auto_detect=1` points at the
ribbon or at no camera attached (MEMORY, 2026-10-01: "everything connected but the camera"), which no package
changes. Fix: step 2 first (the packages are needed anyway), then step 1's check; and before the reboot ladder,
ask the owner whether the camera is plugged in.

### 10. Task 8 step 4: the venv that gets `include-system-site-packages = true` is the show's too

Evidence: `deploy/README.md` step 4 and `deploy/show.service` run the show from the same `.venv`. apt's
`python3-picamera2` brings `python3-numpy`, `python3-pil` and others into `/usr/lib/python3/dist-packages`; the
venv's own copies stay in front, so I expect no change, and the venv is the system's Python 3.13 (`python3 -m
venv`), which apt's compiled modules need. The step prints `numpy.__file__` only. Fix: print the paths of
`cv2`, `PIL`, `pygame` and `mediapipe` as well and expect all inside `.venv`.

### 11. The first time picamera2 opens inside the transient unit is with the card live

Task 8 steps 5 to 7 open the camera from an ssh login shell. Task 9 step 3 is the first run under
`systemd-run --uid=trey` (no login session). I expect it to work: systemd sets the user's supplementary groups
for `User=`, so `video` is there. But it is unproven, and a miss shows as an attract title that sees nobody.
Fix: run Task 8 step 7 once through the runbook's start line with the no-card config.

### 12. Runbook section 4 and Task 9 step 5: "`late 0`" is not what the sender prints

Evidence: `show/display/colorlight.py:265`: "colorlight sender: %d frames, %d late (over 1 ms), worst ...".
A clean run reads "0 late (over 1 ms)" and "real-time yes". Fix the two texts.

### 13. Task 9 step 4: no way back from a bad first calibration

`calibrate` has never run anywhere, and the roadmap's notes list open faults in it ("The clear step saves with
an empty static mask when the camera dies in its first seconds", Q155, Q156). `run` loads the file at every
start (`arcade/main.py:167`). Step 5 follows at once. Fix: after step 4, `cat data/calibration.json` into the
record and repeat step 3's 60 s mirror; if the figure is gone or out of place, remove the file (under the lock)
and go on without it.

### 14. Task 2: a missing camera gives the doctor an opaque reason

With picamera2 installed and no camera, `Picamera2(index)` raises inside the constructor (as far as I know
`RuntimeError: Camera __init__ sequence did not complete`, or an `IndexError`; not verified), which the doctor
prints as is; the "is the ribbon seated" hint is only on the no-frames path. Fix: in `probe_picamera2`, catch
the constructor's exception and append the hint.

## Checked and found correct

- Tasks 1 to 5 and 8b paste and pass: `test_config.py` 52 passed; `test_capture_picamera2.py` 6 passed; Task 3
  step 5's six files 82 passed (one scratch-only failure: `git_sha()` is None outside a git tree); `test_main.py`
  and `test_doctor.py` 22 passed; `test_capture_rpicam.py` 1 passed. Every line reference in Tasks 1 to 5 is
  right.
- No existing assert changes. `probe_camera`'s two messages are the same strings after `_first_frame`. The
  two-argument `probe_camera` lambdas of `test_main.py:191, 197` still fit. `make_probes` has two callers, both
  updated. `all_games` is called once (`test_main_builds_runner_with_the_small_lobby_and_games_once` passes).
  `test_default_file_in_repo_lists_every_field_with_its_default` and `test_importing_main_loads_no_hardware_module`
  pass. No import cycle.
- `--game`: `Lobby.featured` and the runner work with one game (`lobby.py:142-147`); in the scratch copy
  `run --script walkup --game dodge` logged a `dodge` session, and `--game tetris` printed the list and gave 2.
- Task 6's count: 2326 collected now (2323 passed, 3 skipped), plus 16, is 2339 passed.
- picamera2: `create_video_configuration(main=..., controls={"FrameRate": n})`, `configure`, `start`, `stop`,
  `close` are as the plan uses them (docs). `"RGB888"` is `[B, G, R]` in memory, and `camera_configuration()`
  exists (from what I know, not from the docs fetched). 640x480 is not realigned unless `align()` is called,
  and the plan's own check refuses another size. numpy 2.x against apt's modules built for numpy 2.2 should
  import; Task 8b covers the case that it does not.
- Task 9's command: `tools/wall_pattern.py gamma --backend colorlight --iface eth0 --width 128 --height 64
  --seconds 20` has every flag (`wall_pattern.py:299-317`) and the blocks are where the plan says (138-146).
  `--seconds` ends a run through the same close as SIGINT. No step edits `arcade/flash.py`,
  `arcade/brightness.py`, `show/wall.py` or the driver; finding 1 is the only step that changes their input.
- `live-smoke.md` has the `Strongman` row; `roadmap.md` has "Spec revision 4 notes"; Q181's block has the form
  of Q180's.
