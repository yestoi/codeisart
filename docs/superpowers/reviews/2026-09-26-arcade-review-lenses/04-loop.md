# Lens 4: autonomous agent verification and the loop

Reviewed: spec `docs/superpowers/specs/2026-09-26-wall-arcade-design.md` (sections 4.2, 7.1, 9, 11, 12), plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` (header, Global Constraints, Review Focus, Tasks 7, 8, 13, 14, 20 in full; 4, 9 to 12, 16, 18 skimmed), and the `workflow-loop` skill the operator will run (`~/.claude/skills/workflow-loop/`). Things marked "verified" were run or fetched on 2026-09-26. Nothing in the repo was edited.

The core design is sound. The weakness is one kind: every generic check in Tasks 13 and 20 passes for a game that ignores its input, and the per-game checks come from the agent that wrote the game. That is where an unattended loop will mislead the owner.

## Blockers

### B1. The plan's first command fails on this Mac, and a broken camera still exits green (plan header, Task 1, Task 16, Task 18)

Verified:
- `python3.12` is not installed. `python3` is 3.14.5 and `uv` is at `/opt/homebrew/bin/uv`. Task 1's `python3.12 -m venv .venv` fails at step one.
- mediapipe on PyPI is 1.0.1 (2026-08-14) with `py3-none` wheels for macOS arm64 and manylinux aarch64. The "3.12 on the Mac, mediapipe needs it" premise is stale.
- The pin `mediapipe>=0.10.14` is unbounded and resolves to 1.0.1. Its `requires_dist` includes `opencv-contrib-python`, and the plan depends on `opencv-python`. Two cv2 distributions in one environment is a known breakage.
- The v1.0.0 release notes include "Use standardized enum constants for Running Mode", which may affect `vision.RunningMode.VIDEO` as Task 16 uses it.
- `MediaPipeCamera` catches every exception and logs "unavailable". `python -m arcade --ticks 90` then exits 0 with no pose at all. An operator agent reads that as success.

Changes:
- Add a Task 0 environment spike: `uv venv --python 3.12 .venv`, install `.[dev,mac]`, build a `PoseLandmarker` in VIDEO mode on one JPEG, record working versions in `arcade/sources/README.md`, and pin with an upper bound. Pick one OpenCV distribution (for example `opencv-contrib-python` in the mac extra) and verify mediapipe imports.
- Add `python -m arcade doctor [--require camera,mic,pose]`, which exits non-zero if a required source is unavailable after three seconds. The loop's verify step runs it.
- Add a headless pose test that feeds a five-second 320x240 clip through `MediaPipeCamera` (OpenCV accepts a file path) and asserts a body with nose confidence above 0.5 in at least 80 percent of frames. It catches version breakage with no webcam. The clip is the owner's recording (section D); gitignore it if the repo is public.

### B2. The generic soak test is non-deterministic (Task 20)

`random.Random(hash((game_cls.info.name, size)) & 0xFFFF)` depends on `PYTHONHASHSEED`, randomized per process. Verified: three runs printed 20189, 15000 and 27924. A soak failure appears once and vanishes on rerun, which trains the loop to rerun until green.

Change: seed from `zlib.crc32(f"{name}:{w}x{h}".encode())` and run a fixed list of five seeds per game. Print the seed in the assertion message. Add a pytest option `--soak-seeds N` so the nightly run can widen it.

### B3. The contact sheet test cannot detect a black sheet, and sheets carry no provenance (Task 13)

`test_main_writes_png_from_actors` asserts `np.asarray(img).max() > 0`. Every cell has a `t{idx}` label drawn at (200, 200, 200), so the assertion passes if `render` returns zeros. That is exactly the "every sheet is black but tests pass" failure. The sheet also records nothing about which commit, seed or scenario produced it. A stale PNG from an older iteration is indistinguishable from a fresh one. The workflow-loop skill's "version freshness" check has nothing to check.

Changes:
- `contact_sheet` also returns frame-region rectangles. The test asserts each region equals `render(frames[i], ...)`, black input gives a black region, and paint gives lit pixels inside the region.
- The tool refuses an all-black sheet without `--allow-black` and prints lit fraction per cell.
- Add a header with git sha, dirty flag, game, size, look, seed and scenario, and a per-cell caption of the game's `CAPTION_KEYS` (Frogger: `lane 3 lives 2`).

### B4. No generic check that input matters, and the implementer writes its own acceptance tests (spec 9, Task 20, second plan)

A screensaver that ignores the camera passes soak, budget, both layouts, the contact sheet, and any assertion its own implementer chose. The workflow-loop gives each Sonnet implementer one task with TDD, so test and code share assumptions, and the cheapest fix for a red test is the expected number.

Changes:
- **Counterfactual input test, generic, in `test_all_games.py`.** For each input event in a game's canonical scenario (section A), run twice with the same seed, with and without that event. Assert the frames diverge by at least `RESPONSE_PX` pixels within `LATENCY_TICKS` ticks. Runs are deterministic, so this is exact, and a game that ignores input cannot pass. It is the strongest single test in this review.
- **Plan-literal game tests.** The second plan must contain each game's test module in full, as this plan does. The orchestrator checks that the committed test file matches the plan's code block. Any difference must appear under "Deviations" with a reason.
- **Assertion-diff rule for the reviewer.** Add to the workflow-loop reviewer prompt: "List every removed or changed `assert` line in `git diff BASE..HEAD -- tests/`. Each needs a one-line justification in the commit message, or it is BLOCKING."
- **Monotonic test count.** The journal records `pytest --collect-only -q | tail -1` each iteration. A drop without a journaled reason is a gate.
- **Budgets are append-only for the loop.** Feel budgets live in `arcade/feel_budgets.toml`. The loop may tighten a number and journal it. Loosening one is a human decision.

## Serious

### S1. The 8 ms budget is measured on the wrong machine and the wrong statistic (spec 9, Task 20)

The test times `update` plus `draw` only, as a mean, on an M-series Mac. A Pi 4 runs small numpy and Python loops roughly 5 to 10 times slower and also pays for `blobs.py`, the runner and DDP packing. 8 ms on the Mac can be 40 to 80 ms on the Pi, past the 33 ms tick. A periodic spike passes on the mean and stutters.

Changes: express the budget as a multiple of a committed reference micro-benchmark, calibrated once on the Pi; until then use 2 ms mean and 5 ms p95 on the Mac. Assert p95 and max, timing the whole `Runner.tick`. Run `pytest -m perf` on the Pi the first day it exists and record it in `docs/superpowers/workflow/evidence/pi-perf.md`.

### S2. Open-loop actors cannot play a game that has randomness (spec 6.4, Task 4)

Actors are time scripts; cars, balls and pipes come from the rng. A scripted walk cannot dodge a car it cannot see, so "five crossings wins" tests will hunt for lucky seeds or poke internals.

Change: add `arcade/bots.py`. A `Bot` is a closed-loop policy `(debug_state, t) -> actor spec` with `reaction_ticks` and position noise. Each game ships a `good` bot and a `lazy` bot. Difficulty then becomes measurable: win rate over 20 seeds must fall inside a band (section A).

### S3. Synthetic input is perfect; real input is not (Task 4, Task 20 `random_mix`)

`make_keypoints` gives confidence 1.0 with no jitter, dropout or lag. The soak mix never leaves the frame, reaches the edges, uses `both_hands_up`, or exceeds two bodies. Games tuned on this will jitter and false-trigger on the real camera.

Changes: add deterministic `scene(..., noise=Noise(sigma, dropout, lag_ticks, seed))` with `REAL_NOISE` constants fitted from the fixtures (section D), used by game tests by default. Add a `hostile_mix` soak: five bodies, eight blobs, keypoints at 0 and 1, confidence-0 limbs, flickering presence, short both-hands-up.

### S4. `debug_state` is the game's own claim (spec 7.1, "state first")

"State first, pixels second" means nothing checks that the frog drawn on screen is where `debug_state` says. A game can report `lane: 3` and draw the frog in lane 2.

Change: a convention plus one generic test. A `debug_state` key ending in `_xy` holds wall pixel coordinates of a visible entity. On every tick of every canonical scenario, the generic test asserts that the pixel at each `_xy` is lit in the drawn frame. It costs one line per game and closes the gap between state and pixels.

### S5. The registry is a merge-conflict hotspot and menu order is accidental (Task 7, Tasks 10 and 11)

Each game appends an import to `arcade/games/__init__.py`, so parallel implementers conflict and menu order becomes merge order. `test_menu_dwell_via_steps` hardcodes tile 0 as paint; when order shifts, an agent will "fix" the test.

Change: `arcade/games/__init__.py` holds a fixed `MENU_ORDER` of all eleven names from spec section 8, written once in the first plan. Discovery uses `importlib.import_module(f"arcade.games.{name}")` and skips modules that do not exist yet. Adding a game never touches the registry. A test asserts that `MENU_ORDER` equals the spec order.

### S6. "Both layouts" is a convention, not a check (spec 9)

Nothing enforces that a game's tests use the `size` fixture. Task 10 already has one test hardcoded to (64, 64).

Change: add a `pytest_collection_modifyitems` hook in `tests/arcade/conftest.py`. For every registered game it requires at least three collected items in `test_<name>.py` carrying the `128x32` parameter id. Otherwise collection fails.

### S7. The live smoke is unstructured, and "Done when" includes items the loop cannot verify (spec 9, plan "Done when")

"One minute per game" live on the Mac, and "a raised hand moves the cursor", are human checks. An unattended operator will either skip them silently or claim them from an exit code. The SDL preview will never be looked at by anyone but the owner.

Changes: split "Done when" into loop-verifiable and owner-verified items; the loop may say "done pending owner smoke" and nothing stronger. Commit `docs/superpowers/workflow/live-smoke.md`, which the owner fills in on a phone: per game, did it respond (y/n), could I tell what to do (y/n), did I want another go (1 to 5), anything broken. The loop turns each "n" or score of 2 or less into a Carried fix.

### S8. External skills: install granularity and one dead link (spec 4.2)

Installing `media-os` whole adds 96 skills, and `awesome-gamedev-agent-skills` adds 73, including the `pygame-core` the spec rejects, which its router will likely load because pygame is a dependency. `absolutelyskilled/absolutelyskilled` now redirects to `maddhruv/absolute`, which no longer has `pixel-art-sprites`. Change: vendor only the chosen SKILL.md files into `.claude/skills/vendor/`, pinned by commit sha (section E).

### S9. The model reads a downscaled contact sheet (Task 13)

Defaults `--scale 6 --cols 6` make a 128x32 sheet about 4,600 px wide. The viewer downsamples it about 3x, erasing LED dots and one-pixel features, so the agent approves detail it never saw. Change: auto columns capped at 1,536 px wide, and two sheets per scenario, `plain` for content and `led` for look.

### S10. Skipped tests count as passing

Model and hardware tests `skipif` when absent, so the loop reports green with pose untested. Change: verify with `pytest -rs`, fail if the skip count rose since the last journal entry, and list skips in the evidence.

## Minor

- **The REPL leaves no trace (Task 14).** Add `--log` and a `tools/repl_to_test.py` that turns a log into a pytest case, so probes survive compaction as regression tests.
- **Soak's final check is vacuous after `done()`.** Once a game finishes, `run()` returns the `NullMenu` and `game.debug_state()` checks the menu. Keep a reference to the launched instance, and assert that the scenario reached the game's declared phases.
- **Photosensitivity.** Count full-field luminance swings (over 25 percent of the wall changing by over 20 percent) and fail above three per second. A night festival crowd is where this matters.
- **Puppet draws one-pixel lines (Task 11)** against wall-look's two-pixel rule. Let the `distance` metric decide, then make skill and game agree.
- **Evidence bloat.** Regenerate evidence only for changed games and cap GIFs at 300 KB, or git grows by hundreds of megabytes.
- **Scenario motion is stored at the recording's wall size,** so a 64x64 recording cannot replay at 128x32. Record motion on a fixed 128x64 grid and resample.

## A. Feel metrics: what an agent can measure

Add `arcade/feel.py` and `arcade/feel_budgets.toml`. Every game declares `SCENARIOS`, a dict of named actor or bot scripts. It must include `canonical` (competent play), `idle_body` (a person standing still), `nobody`, `fail` and `win`. Tests, sheets, GIFs and metrics all read this one source of truth.

| Metric | How it is computed headlessly | Default budget |
|---|---|---|
| Response latency | Counterfactual diff (B4): ticks from an input event to the first frame that differs by at least 12 px | at most 2 ticks for control games; at most 1 for toys |
| Response magnitude | Pixels changed by one event, measured in the `distance` render | at least 12 px, or 0.5 percent of the wall |
| Control fidelity | Pearson r between actor x and the controlled `_xy` over a sweep | r of at least 0.9, monotonic |
| Reachable range | Controlled range covered when the actor sweeps 0.25 to 0.75 (real people stand mid-frame) | at least 90 percent of the playfield |
| Liveliness | Median fraction of pixels changed per tick, with and without a player | 0.5 to 40 percent; above 0 with nobody for ambient, life and beat |
| Lit fraction | Median fraction of lit pixels after gamma and brightness | 3 to 60 percent |
| Dim pixels | Fraction of lit pixels with max channel below 48, outside declared fades | at most 10 percent |
| Flashes | Full-field swings per second (see Minor) | at most 3 |
| Distinct states | Distinct 8x8 mean-hash frames per session, and the `phase` values reached | every declared phase reached; at least 6 hashes |
| Score visible | `read_text(frame, box, font)` template-matches the project's own 5x7 font against `debug_state()["score"]` | matches on every tick the score is shown |
| Score legible far away | Pairwise distance between digit glyphs after the `distance` blur, at the game's scale and color | no pair below the font-level threshold (the 8/0/6 pair is the likely failure) |
| Fail vs win | Hue histogram and duration of the transient after each event | the two differ; each lasts 6 to 60 ticks |
| Hint | In `idle_body`, a prompt or animated hint appears | within 90 ticks |
| Round length | `good` bot run until `done()` | 20 to 120 s |
| Difficulty | Win rate over 20 seeds: `good` bot, `lazy` bot, no input | 40 to 90 percent, below 30 percent, 0 percent |

Budgets are per game kind: control (menu, frogger, pong), toy (paint, puppet, life, ambient, beat) and score (jump, scream, flappy, holewall). A game may override a budget in the toml only with a comment. `pytest -m feel` asserts them, and `tools/arcade_feel.py --game X` prints the table for the evidence package.

**What stays human.** No metric says a game is fun. The owner judges whether a stranger gets it in ten seconds, whether the motion feels good or embarrassing, total latency with the real camera, colour taste, night glare, and onlookers wandering into frame. The metrics find dull and broken games cheaply; they cannot find the good ones.

## B. Evidence package for the two-minute phone decision

A single command, `python tools/arcade_evidence.py --iteration N --games changed`, writes the package, so it never depends on the operator's memory. Everything goes under `docs/superpowers/workflow/evidence/itNN/`:

| File | Content |
|---|---|
| `README.md` | Line 1 is the decision: "Decide: A (keep frogger speed 1.4) or B (slow to 1.0). Default A if no answer by iteration N+1." Below it: the feel table for changed games (pass or fail per budget), the reviewer verdict in one line, test count and skip count against last iteration, and every image inline |
| `<game>-64x64-led.png`, `<game>-128x32-led.png` | Canonical scenario sheets with provenance header and state captions (B3) |
| `<game>-64x64-distance.png` | The same run at 15-foot legibility |
| `<game>-canonical.gif` | Canonical scenario at 64x64, led look, 10 fps, at most 6 s and 300 KB |
| `<game>-trace.jsonl` | `debug_state` per tick; `<game>-trace.txt` gives the phase timeline in ten lines |
| `feel.json` | The raw metrics behind the table |
| `review.md` | The reviewer's machine-read verdict, verbatim |

Every question carries a default and a deadline, so the loop never blocks on an absent owner. Record the owner's answers in `docs/superpowers/workflow/decisions.md`, one line each, and have the loop read that file every iteration. For phone viewing, `README.md` renders on GitHub mobile if the owner gives standing consent to push an `evidence` branch. Otherwise the loop publishes the page as a private artifact. Either way, pushing or publishing needs the owner's consent once.

## C. Gate table

| Decision | Who | Note |
|---|---|---|
| Keep or cut a game | Human | Scope; the loop flags cut candidates with evidence |
| Difficulty numbers | Loop | Within bot win-rate bands; journaled; human veto after live play |
| Dwell time | Loop proposes, human confirms | The loop measures false launches and dwell success on recorded fixtures; the owner confirms once live |
| Colour palettes | Loop | Within wall-look metrics; human taste veto from sheets |
| Brightness ceiling | Human | Power, glare, site; the loop never raises it |
| Where gamma is applied | Human | Prototype-week measurement |
| Feels good on the live Mac webcam | Human | `live-smoke.md` |
| Move to the Pi | Human | Hardware in hand; the loop prepares the Pi checklist and perf run |
| Write the second plan | Loop | After plan 1 is loop-done and the owner has done one smoke; owner skims order and budgets, default proceed |
| Loosen a feel budget or change a plan-literal test | Human | Tighten: loop |
| Dependency pins, Python version | Loop | Journal; Task 0 spike evidence |
| Delete or re-record fixtures | Human | Only the owner can re-record |
| Publish evidence outside the machine | Human, once | Standing consent |
| Menu order, icons, skill edits | Loop | |

## D. Real-input fixtures the owner records once

Extend `arcade record` with `--script NAME`. The SDL window shows cues on a timetable ("RAISE RIGHT HAND", "HOLD", "SWEEP LEFT") and writes the cue times into the scenario header. The script is the ground truth, so no hand annotation is needed. Add `--raw` to also save 320x240 video, so source changes (`blobs.py`, landmark mapping) can be regression-tested later. Store files as `.jsonl.gz` in `tests/arcade/fixtures/real/`, with support for `.gz` in `ScenarioReader`.

| Script | Length | What it tests | Consumers |
|---|---|---|---|
| `empty-room` (room lamp toggled at 15 s) | 30 s | Motion noise floor, phantom blobs, idle and attract | runner, life, ambient |
| `walk-in-stand-leave` | 20 s | Presence, tracker ids, return from attract | runner, puppet |
| `menu-point` (4 tiles held 2 s, then sweeps through without stopping) | 30 s | Cursor jitter, dwell, false launches | menu |
| `wrist-sweep` (slow, fast, leaning) | 20 s | Control range and jitter | frogger, pong |
| `exit-gesture` (3 s hold, three 0.5 s false starts) | 15 s | Exit true and false positives | runner |
| `jumps-squats` | 20 s | Baseline and peak | jump |
| `poses-8` | 40 s | Holewall scoring spread | holewall |
| `torch-paint` (phone torch, dark room) | 30 s | Blobs, colour | paint, menu blob cursor |
| `idle-still` | 20 s | No accidental hops; hint appears | all pose games |
| `claps-tempo-voice` (silence, irregular claps, claps at 120 bpm, shouting) | 30 s | Onset, beat lock, level range | flappy, beat, scream |
| `music-speaker` (dance track at about 125 bpm) | 30 s | Beat under real music | beat |
| `two-people-cross` (optional, needs a friend) | 30 s | Id swaps | tracker, pong |

That is about five minutes, once on the Mac. Re-record `menu-point`, `wrist-sweep`, `exit-gesture`, `torch-paint` and `claps-tempo-voice` on the Pi camera and USB microphone when they arrive.

Each fixture yields cue assertions (four launches in `menu-point`, none in its sweep; one exit, on the 3 s hold), a replay through each consuming game with looser feel bands, and the fitted `REAL_NOISE` constants (S3).

## E. External skills (spec 4.2)

| Skill | Real and current? | Verdict |
|---|---|---|
| `cv-mediapipe` (damionrashford/media-os) | Real; last push 2026-05-31; teaches the Tasks API and warns off legacy `solutions`, matching Task 16 | Useful for Task 16 only. Vendor the one file. Do not install the 96-skill plugin |
| `game-feel` (gamedev-skills/awesome-gamedev-agent-skills) | Real; 1,174 stars; pushed 2026-09-25 | Partly useful. Hit-stop, eased tweens, importance tiers and "juice returns to rest" transfer well. It is Godot and Unity code and assumes a sound layer this project does not have. Vendor it and reference it from the project skill |
| `procedural-gen` | Real | Skip for now. Only Life seeds and boids touch it |
| `performance-optimization` | Real; engine-generic profiling advice | Skip. S1's calibrated budget matters more |
| `pixel-art-sprites` (absolutelyskilled) | Gone upstream; the repo is now `maddhruv/absolute` with 11 skills; copies survive only in mirrors | Skip. It targets 16x16 sprites with three-to-five-step shadow ramps, and dark ramp steps vanish at 40 percent brightness with gamma 2.2. That is actively wrong for this wall |
| `skill-creator` | Real (anthropics/claude-plugins-official) | Useful |
| `pyright-lsp` | Real (same repo) | Useful. It catches `Game` protocol drift cheaply |

**Feel guidance for `arcade-game-authoring`:**
- No sound, so every event needs a visible response within two ticks and at least 12 lit pixels; a whole-wall flash or one-pixel shift is the only screen shake.
- Camera latency is already 60 to 150 ms. Use hysteresis, never smoothing that costs more than a tick.
- Map the middle half of the camera to the full playfield; hint within three seconds of a still body; rounds of 20 to 120 s; failure and success differ in hue and motion.
- Declare `SCENARIOS`, `_xy` keys, `phase`, `CAPTION_KEYS` and the budget kind.

**Timing.** Spec section 11 says skills come after two games. Keep that for `arcade-verify` and `arcade-game-authoring`, but write them right after Task 20 and before the second plan's first game. The feel rules and wall-look rules must exist as tests (section A) before any second-plan game, because skill prose is advisory and tests are not.

## F. Loop failure modes

| Failure | Detection | Prevention |
|---|---|---|
| Implementer edits the expected value, not the game | Assertion-diff rule; test differs from plan text | Plan-literal tests, append-only budgets (B4) |
| Two subagents edit the registry | Conflict; order differs from spec | `MENU_ORDER` plus discovery (S5) |
| Perf passes on the Mac, fails on the Pi | Pi perf run in evidence | Calibrated budget, p95 (S1) |
| SDL preview never looked at | `live-smoke.md` empty | Owner gate, "done pending owner smoke" (S7) |
| Contact sheets are black | Frame-region equality test | Black refusal (B3) |
| Stale evidence shown as new | Header sha differs from HEAD | Provenance header (B3) |
| mediapipe or Python assumption fails | `arcade doctor`, video-file pose test | Task 0 spike, pins (B1) |
| Flaky test rerun until green | Seed in failure message | Stable seeds (B2) |
| Tests quietly skipped | Skip count rises | S10 |
| Decisions lost at compaction | Not in `decisions.md` | Loop reads it every iteration (B) |

## Checked and found OK

- Injected clock and rng with the `FakeClock` loop test make runs reproducible; the counterfactual test relies on this.
- The crash guard is tested end to end, including hiding after three crashes.
- Headless SDL in conftest; hardware imports deferred to constructors.
- `Runner.state()` merges `debug_state`, and the REPL is deterministic, typo-proof, one JSON line per verb.
- One `look.render` for preview and sheets, so a correct sheet predicts the preview.
- State first, pixels second is right once S4 is added. Paint's fade test is a proper semantic pixel assertion.
