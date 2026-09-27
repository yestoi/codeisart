# Iteration 2: Carried Fixes, the Sensed Record and Actors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land iteration 1's carried fixes C1-C3 and C5-C9 (the Colorlight ones before GATE B), then the first half of roadmap milestone M2: the Sensed record of spec revision 3 (timestamps, velocity, `player`, `present`, zone, reach box, mirroring) and the actors that feed it (exact event ticks, wrist ramps, poses, motion and level scripts, `degrade`, `REAL_NOISE`, festival scenes).

**Architecture:** The carried fixes harden what iteration 1 built (`show/display/`, `arcade/config.py`, `arcade/calibration.py`, `arcade/main.py`, `.gitignore`) without changing any existing assert. `arcade/sensed.py` is the only input games will see: frozen dataclasses with helper properties and `place()`, which maps a body into the calibrated zone. `arcade/sources/actors.py` produces deterministic `Sensed` streams from scripted people, lights, motion and sound, and `degrade()` turns them into what a 10 fps camera with latency, dropout and jitter gives. `arcade/poses.py` holds named poses as offsets. Nothing here imports hardware modules.

**Tech Stack:** Python 3.12 from uv, numpy, pygame (tests of the SDL display only), pytest; the venv from iteration 1.

**Spec:** `docs/superpowers/specs/2026-09-26-wall-arcade-design.md`, revision 3 (sections 5, 6.4, 6.6, 7.3; 4.3 for C5; 3 for C1-C3).

**Sources merged here (this plan overrides them where they differ):** the roadmap's "Carried fixes" C1-C9 (`docs/superpowers/workflow/roadmap.md`) with iteration 1's verdict (`docs/superpowers/workflow/evidence/it01/reviewer-verdict.md`); core plan `docs/superpowers/plans/2026-09-26-wall-arcade-core.md` Task 3 and Task 4 with their per-task amendments and "Global Constraints, revised"; `docs/superpowers/reviews/2026-09-26-arcade-review-lenses/05-plan.md` (S10 and the forward-compatibility table). Every file below is final, amendment-applied code; an implementer needs nothing else.

## Global Constraints

Carried from the core plan ("Global Constraints" as replaced by "Global Constraints, revised"):

- Frames are numpy arrays of shape `(height, width, 3)`, dtype uint8, RGB, row-major.
- Every game declares `layouts`; its tests are parametrized over the declared layouts (spec 9.1). 128x32 is the default and design layout. (No games in this iteration.)
- Brightness: the runner calls `display.set_brightness(cfg.brightness)` once. The Colorlight backend enforces it at the panel with the card's brightness packet; the fake and SDL displays store the level (the SDL window shows full brightness on purpose until core Task 6's `PreviewDisplay` models it); DDP logs once that it is Falcon Player's setting. Pixels pushed to hardware are never scaled for `brightness`. (The core plan's wording, "SDL and fake model it in the preview", overstated iteration 1's `SDLDisplay`; corrected here, no behaviour change.)
- Tick rate 30 Hz; `dt` handed to games is clamped to 100 ms; clocks and random sources are injected.
- Never seed from `hash()` of a str; use `zlib.crc32` and print the seed in the assertion message.
- Modules that import `mediapipe`, `picamera2`, `cv2.VideoCapture` devices, or `sounddevice` do so inside the class constructor, probe function or thread, never at module import. Tests never need hardware extras.
- Tests run headless: `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` are set in `tests/conftest.py` before pygame is imported.
- No `print` in library code; use `logging.getLogger("arcade")` in `arcade/` and `logging.getLogger(__name__)` in `show/`. CLI entry points and `tools/` may print.
- Python 3.12 through uv on the Mac; one OpenCV distribution, `opencv-contrib-python`.
- Commit after every task with the exact message and `git add` list given in the task.

Operator rules for this loop:

- Test modules are copied from this plan verbatim. Any difference, however small, is a Deviation and must be reported as one.
- Never remove or weaken an existing assert; only add or tighten. If an existing assert must change, the task and its commit message say why. (No task in this plan changes one.)
- Never push. Never run `git push` or `gh pr create`.
- Use `.venv/bin/python` (Python 3.12 from uv). Never use the system `python3` (3.14), never `pip`, never activate the venv in a way later commands depend on.
- Install with `uv pip install --python .venv/bin/python ...`. (This iteration installs nothing.)
- Run tests from the repo root with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` (append a path to run one module).

## Loop decisions taken by this plan (journal each one)

1. **C1, Colorlight brightness: start at the configured level (`SAFE_BRIGHTNESS = 0.4` without one), resend the brightness packet every `BRIGHTNESS_EVERY = 3` pushes, and fail dark on NaN.** Falcon Player (`src/channeloutput/ColorLight-5a-75.cpp`, master, read 2026-09-27) builds its message list once with the 0x0A brightness packet first (a second copy for card firmware 13 and later) and the row packets after it, sends that whole list from `PrepData()` on every frame, and sends the 0x07 display-frame packet from `SendData()` (twice on firmware 13 and later). So Falcon Player resends brightness every frame. This plan resends it on every 3rd push (0.1 s at 30 Hz; a push count, so tests stay deterministic), after the display-frame packet and before the rows, and resets the count on `set_brightness` (`test_set_brightness_restarts_the_resend_count`). 3 is the smallest interval that no plan-literal test reaches: `test_push_matches_reference_encoder` pushes twice and compares the whole packet stream, so an interval of 1 or 2 changes what three plan-literal tests pin (`test_push_sends_frame_packet_then_rows`, `test_push_matches_reference_encoder`, `test_colorlight_set_brightness_sends_packet`), and changing a plan-literal test is the owner's call (operator design section 5). Every-frame resend (Falcon Player parity) and the doubled packets for firmware 13 and later stay with GATE B's firmware record (C4). The start level is a constructor keyword; `make_display` passes the configured level (the arcade's `brightness`, the daemon's `effective_brightness`), and 0.4 (the approved `arcade.toml` `brightness` and the daemon's `brightness_cap`) is the default when a config has none. Refusing to push until `set_brightness` was rejected because `test_push_matches_reference_encoder` pushes without setting it. `_level` maps NaN and anything not above 0 to 0, so a NaN from any config or computed level fails dark, never at 255. No brightness ceiling, night level or gamma placement changes.
2. **Raise line and body centre** (spec 5): the raise line is 0.3 torso above the shoulder midpoint; the nose is used only when both shoulders are under `MIN_CONF`, and with neither nothing is raised. With exactly one confident shoulder, `shoulder_mid` takes that shoulder's y (so the raise line does not move) and its x from both hips when both are confident, else a confident nose, else the one hip seen, else the shoulder itself. Taking the shoulder's own x moved the anchor, `zone_x` and the reach box half a shoulder width whenever one shoulder dropped out (a still player's cursor jumped 0.15 and `zone_x` 0.12); taking a lone hip's x first still moved them up to 0.1 (a door is 0.33) whenever one shoulder and one hip dropped out together, while a confident nose is on the centre line. At the spec 6.4 noise (`fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01`, as literals so a `REAL_NOISE` refit never touches it) a still player now has no cursor reading more than 0.1 from the median and no `zone_x` reading more than 0.05 away; `test_still_player_keeps_cursor_and_zone_steady_under_spec_noise` pins both at 2 percent or less, and `test_nose_fallback_only_without_shoulders` pins the order.
3. **Torso and scale without every joint.** Torso is shoulder midpoint to hip midpoint; with no hip it is 1.25 shoulder widths. `Body.scale = 0.0` means "measure": nose to hip midpoint, or 1.5 torso lengths when the nose is hidden (the standing figure's ratio, 0.45 / 0.30). Both are 0.0 when nothing is seen.
4. **Reach box without shoulders** (spec 7.3 is silent): the body box is the frame, so `reach` never raises and still moves.
5. **Cursor:** the confident wrist further from its own hip (then the hip midpoint, then the shoulder midpoint), through `reach`; `None` without a confident wrist. It is stateless: when the pointing wrist drops out for one capture (15 percent of captures at the spec 6.4 dropout) the cursor jumps to the other wrist, even though loop decision 2 keeps the body centre still. The docstring says so. Every cursor consumer (core Task 8's `input.py`, Task 9's director, a paddle) needs a grace period or hysteresis, which the amendments for those tasks must carry (`Hold(grace=0.25)` covers dwell, not a paddle); see Forwarded to later amendments.
6. **`motion` defaults to an empty `(0, 0)` grid** (spec 5: "empty when the grid is judged global"); `with_motion(size)` turns empty into all False and resamples another shape with `np.logical_or.reduceat`, so shrinking never loses a lit cell.
7. **`camera_seq` counts from 1** in `scene` and `degrade`; 0 with `camera_fresh = False` means no camera frame yet, which is `Sensed`'s default.
8. **`degrade` timing:** capture k is taken at `k / fps` from the scene frame at or before that time and is visible from `k / fps + latency` until the next capture. With the defaults, the first capture shows at tick 5 (0.167 s) and 29 of 90 ticks are fresh. Dropout sets a keypoint's confidence to 0 and keeps its position; jitter is uniform within plus or minus `jitter`. Blobs and motion are held with the capture; audio and `t` are never delayed. A stream whose frame i does not have `t = i * TICK` (sliced, offset or gapped) raises `ValueError`, because keying by index would silently give it zero latency.
9. **`shake`** yields an empty `(0, 0)` motion grid and 0.03 keypoint jitter inside its window, the same empty grid the camera source reports for a global grid, and re-places the jittered bodies against the calibration it is given (the default one when `None`), which must be the scene's.
10. **`probe_pose` timeout (C9):** the landmarker runs in a daemon thread joined with the timeout (`within`). `import mediapipe` runs untimed on the calling thread first: a cold first import took about 4.5 s in the scratch run and would have failed a 5 s doctor. `probe_camera` stays on the calling thread and says why (macOS asks for camera access only from the main thread).
11. **`REAL_NOISE` is refit data, not a spec constant.** Its test pins the key set and that it runs through `degrade`; the spec 6.4 defaults of `degrade` are pinned against literals in a separate assert. The still-player test (loop decision 2) runs on the spec 6.4 literals, not `REAL_NOISE`. Refitting `REAL_NOISE` from the GATE A fixtures therefore changes no test.

## Forwarded to later amendments

- Core Task 8 (`input.py`) and Task 9 (director) amendments: the cursor grace period or hysteresis of loop decision 5 (round-1 note N5). `Body.cursor` stays stateless, so a pointing wrist that drops out for one capture moves the cursor to the other wrist unless the consumer holds it.
- Core Task 7 amendment: the scenario `decode` builds `Sensed` with the empty `(0, 0)` grid, not `motion=None` (loop decision 6; `Sensed` accepts `None` as the empty grid, but a record should not rely on it).

## Resolved conflicts (the arcade amendments win)

- **Core Task 3 tests.** The amendment replaces `test_raised_wrist_and_both_hands` (nose-based) with `test_raise_line_is_above_shoulders`, `test_nose_fallback_only_without_shoulders` and `test_hooded_body_still_raises`; replaces `test_sensed_defaults_and_primary` with `test_sensed_defaults`; and drops `test_with_motion_rasterizes_boxes_and_keeps_existing` with `rasterize_boxes` (motion never comes from body boxes), replaced by `test_with_motion_resamples_never_rasterizes`. None of the revision 2 tests was ever in the repo, so no committed assert changes.
- **Core Task 3 interface.** `Audio(level, peak, onset, beat, bpm)` and `Sensed(t, bodies, blobs, motion=None, audio)` become spec 5's fields with defaults; `Sensed.primary` is gone (the runner sets `player`).
- **Core Task 4 file list.** `arcade/sources/__init__.py` already exists (iteration 1, empty); this plan does not recreate it.
- **`_on_tick` becomes `_fires`** (05-plan S10): an event fires on exactly one tick, the first at or after it. `test_scene_assigns_ids_and_ticks` now expects `frames[0].motion` all False on the 128x64 grid, not `None` (amendment).
- **Pose table type.** 05-plan's table says `POSES: dict[str, tuple[Keypoint, ...]]`; the Task 4 amendment says 17 `(dx, dy)` offsets in body-height units from the hip centre. The amendment wins. `make_keypoints` is now built from `POSES["stand"]` and `POSES["arms_up"]`; its numbers are revision 2's exactly. Its docstring said "centred at (cx, cy)", but the hips were always at `dy = 0`, so `(cx, cy)` is the hip centre and `Person.y` is hip height.
- **`pose(named)`** was deferred to the second plan in revision 2; the amendment adds it now with `t_pose` and `arms_up` (plus `stand`).

## Additions beyond the source plans (reviewer: check these on purpose)

- Colorlight: `ColorlightDisplay(..., brightness=SAFE_BRIGHTNESS)` keyword, filled by `make_display` from the config (plan review N9); constants `SAFE_BRIGHTNESS` and `BRIGHTNESS_EVERY`; `_level` fails dark on NaN; the raw-socket `PermissionError` names `CAP_NET_RAW`, the systemd `AmbientCapabilities` line and `setcap`; a failed `bind` closes the socket and raises an `OSError` naming the interface. The test helper `Recorder` in `tests/test_colorlight.py` accepts and records keyword arguments (`**kwargs`), so `make_display` can pass `brightness=`; its existing asserts on `.args` are unchanged. `test_display.py`'s SDL test gains asserts (C7 tightening, the loop's call).
- Config (C5 plus): `camera_fps > 0` and `night_lux >= 0` are checked with the listed fields; NaN fails every range check and `gamma` must be finite. The `*_seconds` list is read from the dataclass fields, so a new `*_seconds` field is covered automatically.
- Calibration (C6 plus): `zone` entries must lie in 0..1 with `x0 < x1` and `y0 < y1` (kept from iteration 1); `audio_floor_db` must be in [-200, 0]; a static-mask radius must be over 0; booleans are rejected as numbers; one bad value still rejects the whole file (safer than half a calibration), a missing key takes its default, and unknown keys are ignored, all with a warning naming the keys. The `zone` and `static_mask` comments now say they are in the mirrored display space the keypoints use.
- Doctor: `within(timeout, what, fn)` in `arcade/main.py`; `tests/test_gitignore.py` (a new module) pins the anchored ignores with `git check-ignore --no-index`.
- Sensed: constants `RAISE_TORSOS`, `REACH_WIDTHS`, `REACH_TOP_TORSOS`, `TORSO_PER_SHOULDER_WIDTH`, `NOSE_TO_HIP_PER_TORSO`, `MOTION_GRID = (128, 64)`; `Body.shoulder_width`, `Body.anchor` (shoulders, then nose, then hips: the tracker's anchor order from spec 5, and what `place` maps); `place_blob(blob, calibration)`, whose docstring says blobs must be in the mirrored display space (a blob source mirrors x as `mirror_keypoints` does); `Sensed` is `eq=False` because it holds an array, and `Sensed.__post_init__` stores a read-only view of `motion` (None becomes the empty grid), because one grid is shared by every tick that holds it; the producer's own array stays writeable, and the docstring says a producer must not change a grid after handing it over.
- Actors: `scene(..., calibration=None)`, `degrade(..., calibration=None)` and `shake(..., calibration=None)` (default calibration when `None`); `scene` sorts bodies largest scale first (stable) and caps blobs at 8 in script order (spec 5 says brightest first, but a `Blob` has no brightness); `claps` also sets `Audio.clap`; `Person.body_at` fills `vx` and `vy` from a causal one-tick difference of the hip centre; `Person.wrist` computes the reach box from the pose offsets, so it works for a body partly out of frame; `motion_rect`'s docstring says its rectangle is in fractions of the motion grid (the zone at the wall's aspect), not camera x; `POSES["stand"]`; `crowd(n, start=0.0)`, `headlamps(period=20.0, cross_seconds=6.0)`, `wind(gust_every=2.7)`, `shake(start, seconds, jitter=0.03, calibration=None)` return values and defaults are this plan's; `degrade` validates its parameters and its input's timing and keeps only the scene frames it may still capture.

## Review Focus

1. A pose model returns a keypoint outside 0..1 or NaN (core Review Focus 1). `Body` clamps it with confidence 0 and never raises. Test: Task 4, `test_body_cleans_bad_keypoints`.
2. A hooded, masked person in the dark: nothing confident but the box. Every helper must return `None`, `False` or a clamped value and `place` must still work, never raise into the runner. Test: Task 4, `test_body_with_nothing_confident_never_raises_or_fails`.
3. A float or int64 frame handed to a hardware backend (a game draws with floats and forgets `astype`), or a NaN brightness from a config or a computed night level. Colorlight and DDP must raise on the frame before a byte leaves, and a NaN level must go out as 0, never 255. Test: Task 1, `test_push_rejects_a_frame_that_is_not_uint8_rgb` in both modules, `test_nan_or_negative_brightness_fails_dark`.
4. `calibration.json` hand-edited with one bad value, or written by an older version without a newer key. A bad value falls back to the defaults with a warning naming the key; a missing key takes its default and keeps the rest. Test: Task 2, `test_bad_value_falls_back_to_defaults_naming_the_key`, `test_missing_key_takes_its_default_and_keeps_the_rest`.
5. A 128 bpm track, or an event on a half-tick boundary: two adjacent ticks must never both fire (05-plan S10). Test: Task 5, `test_tempo_128_exactly_one_beat_per_period`, `test_claps_fire_exactly_once`.

## Environment facts verified 2026-09-27

- HEAD is `7697d01`; the suite is 66 collected, 66 passed, 0 skipped. `.venv` is Python 3.12.13 with numpy 2.5.3, pygame 2.6.1, pytest 9.1.1, mediapipe 1.0.0. `arcade/sources/__init__.py` exists and is empty; `arcade/sensed.py`, `arcade/poses.py` and `arcade/sources/actors.py` do not exist.
- Falcon Player's `ColorLight-5a-75.cpp` (master): the brightness packet is `m_msgs[0]` (and `m_msgs[1]` for firmware 13 and later), all of `m_msgs` goes out from `PrepData()` each frame, and the display-frame packet goes out from `SendData()`, twice for firmware 13 and later.
- `git check-ignore -q --no-index PATH` exits 0 for an ignored path and 1 otherwise, whether or not the path exists or is tracked.
- `np.logical_or.reduceat` with start indices `(arange(n) * N) // n` resamples in both directions: 2x2 to 4x8 repeats cells, and 128x64 to 64x32 moves cell (33, 101) to (16, 50) and keeps it lit.
- `.venv/bin/python -m arcade doctor --require pose` with this plan's `probe_pose`: `ok` in 0.74 to 1.27 s wall time; `--timeout 0.01` prints `pose    UNAVAILABLE  pose landmarker did not finish within 0.01 s` and exits 1.
- `BRIGHTNESS_EVERY` against the three plan-literal Colorlight tests: 1 and 2 break them (the reference encoder pushes twice and compares the whole stream), 3 passes them (plan review, confirmed by this plan's replay).
- A still player with the right hand up for 30 s through `degrade` at the spec 6.4 values (299 captures): with the one-shoulder centre of loop decision 2, 0 percent of cursor readings are more than 0.1 from the median and 0 percent of `zone_x` readings more than 0.05; with the hip midpoint first (a lone hip allowed) they were 7 and 10 percent under `REAL_NOISE`, and with the shoulder's own x both were 31 percent.
- The whole plan's code was replayed from this file's text in a scratch clone of `7697d01`, task by task, after the plan review's revisions: every failure and count below was observed.

## File map

```
show/display/colorlight.py      Task 1  safe start brightness, periodic brightness packet, dtype check, equal row split, CAP_NET_RAW hint
show/display/__init__.py        Task 1  colorlight branch: clear error without an interface
show/display/ddp.py             Task 1  dtype and shape check
tests/test_colorlight.py        Task 1
tests/test_ddp.py               Task 1
tests/test_display.py           Task 1  C7 asserts
arcade/config.py                Task 2  range checks
arcade/calibration.py           Task 2  per-key validation, missing keys default, directory fsync
tests/arcade/test_config.py     Task 2
tests/arcade/test_calibration.py Task 2
.gitignore                      Task 3  anchored /models/, /data/, /shots/
arcade/main.py                  Task 3  within(), probe_pose timeout, --require "" exits 2
tests/arcade/test_doctor.py     Task 3
tests/test_gitignore.py         Task 3  new
arcade/sensed.py                Task 4  new: Keypoint, Body, Blob, Audio, Sensed, place, place_blob
arcade/sources/mirror.py        Task 4  new: mirror_keypoints, mirror_box
tests/arcade/test_sensed.py     Task 4  new
tests/arcade/test_mirror.py     Task 4  new
arcade/poses.py                 Task 5  new: POSES
arcade/sources/actors.py        Task 5  new; Task 6 adds degrade, REAL_NOISE, festival scenes
tests/arcade/test_actors.py     Task 5  new
tests/arcade/test_festival.py   Task 6  new
```

---

### Task 1: Display hardening (carried C1, C2, C3, C7, C8)

**Files:**
- Modify: `show/display/colorlight.py` (whole file below), `show/display/__init__.py` (whole file below), `show/display/ddp.py` (whole file below)
- Test: `tests/test_colorlight.py`, `tests/test_ddp.py`, `tests/test_display.py` (whole files below)

**Interfaces:**
- Consumes: iteration 1's `show.display` (`make_display`, `DisplayConfig`, `FakeDisplay`, `SDLDisplay`, `DDPDisplay`, `ColorlightDisplay`), `show.config.Config`.
- Produces: `ColorlightDisplay(width: int, height: int, iface: str, sock=None, brightness: float = SAFE_BRIGHTNESS)`; `SAFE_BRIGHTNESS = 0.4`; `BRIGHTNESS_EVERY = 3` (the 0x0A packet goes out on every 3rd push, between the frame packet and the rows); `brightness_packet` and `frame_packet` send 0 for a NaN or non-positive level; `row_packets(row, pixels)` splits a row into the fewest equal packets of at most `CHUNK_PIXELS`, as `push` does; `ColorlightDisplay.push` and `DDPDisplay.push` raise `ValueError` for a frame that is not `(height, width, 3)` uint8, before sending anything; `make_display` raises `ValueError` for the colorlight backend with an empty interface and passes `brightness=` the config's `effective_brightness`, else its `brightness`, else `SAFE_BRIGHTNESS`; the raw-socket `PermissionError` names `CAP_NET_RAW`; a failed `bind` closes the socket and raises `OSError` naming the interface.

Changes to existing test lines, none of them an assert: in `tests/test_colorlight.py` the import block gains `math`, `BRIGHTNESS_EVERY` and `SAFE_BRIGHTNESS`; `test_push_matches_reference_encoder`'s parametrize gains `(384, 4)` (C8); the helper `Recorder.__init__` accepts `**kwargs` and stores them as `self.kwargs` (so `make_display` can pass `brightness=`). No assert is removed or changed. `tests/test_display.py`'s `test_sdl_display_pushes_headless` keeps every line and gains asserts (C7).

- [ ] **Step 1: Write the failing tests**

`tests/test_colorlight.py`:

```python
import math
import socket
from types import SimpleNamespace

import numpy as np
import pytest

import show.display.colorlight as colorlight
from show.config import Config
from show.display import make_display
from show.display.colorlight import (BRIGHTNESS_EVERY, DST_MAC, SAFE_BRIGHTNESS, SRC_MAC, ColorlightDisplay,
                                     brightness_packet, frame_packet, row_packets)


class FakeSocket:
    """Stands in for the AF_PACKET socket, which exists only on Linux."""

    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, data):
        self.sent.append(bytes(data))  # copy: push() reuses its packet buffer
        return len(self.sent[-1])

    def close(self):
        self.closed = True


def test_row_packets_chunk_512_pixels_into_two():
    pixels = np.zeros((512, 3), np.uint8)
    pixels[0] = (255, 0, 0)          # red pixel at column 0
    pixels[256] = (0, 0, 255)        # blue pixel at column 256
    pk = row_packets(5, pixels)
    assert len(pk) == 2
    header = pk[0][:14]
    assert header[:6] == DST_MAC and header[6:12] == SRC_MAC and header[12:14] == b"\x55\x00"
    payload = pk[0][14:]
    assert payload[:7] == bytes([5, 0, 0, 1, 0, 0x08, 0x88])          # row 5, offset 0, count 256
    assert payload[7:10] == bytes([255, 0, 0])                        # RGB order, as Falcon Player
    payload2 = pk[1][14:]
    assert payload2[:7] == bytes([5, 1, 0, 1, 0, 0x08, 0x88])         # offset 256
    assert payload2[7:10] == bytes([0, 0, 255])
    assert all(len(p) == 14 + 7 + 256 * 3 for p in pk)


def test_row_packets_split_384_pixels_equally():
    pixels = np.zeros((384, 3), np.uint8)
    pixels[192] = (0, 255, 0)
    pk = row_packets(2, pixels)
    assert [len(p) for p in pk] == [14 + 7 + 192 * 3] * 2              # 192 + 192, as push() sends
    assert pk[1][14:21] == bytes([2, 0, 192, 0, 192, 0x08, 0x88])      # offset 192, count 192
    assert pk[1][21:24] == bytes([0, 255, 0])


def test_row_above_255_sets_ethertype_low_byte():
    pk = row_packets(300, np.zeros((8, 3), np.uint8))
    assert pk[0][12:14] == b"\x55\x01" and pk[0][14] == 300 & 0xFF


def test_frame_packet_matches_falcon_player():
    fp = frame_packet(0.5)
    assert fp[:12] == DST_MAC + SRC_MAC and fp[12:14] == b"\x01\x07" and len(fp) == 112
    assert fp[35] == 127 and fp[36] == 0x05 and fp[38:41] == bytes([127, 127, 127])
    assert sum(fp[14:]) == 127 * 4 + 5


def test_brightness_packet_matches_falcon_player():
    bp = brightness_packet(0.4)
    assert bp[:12] == DST_MAC + SRC_MAC and len(bp) == 77
    assert bp[12] == 0x0A and bp[13:17] == bytes([102, 102, 102, 0xFF])
    assert not any(bp[17:])
    assert brightness_packet(1.7)[13] == 255 and brightness_packet(-1.0)[13] == 0


def test_push_sends_frame_packet_then_rows():
    sock = FakeSocket()
    d = ColorlightDisplay(512, 4, "eth0", sock=sock)
    d.set_brightness(0.2)
    assert sock.sent[-1][12] == 0x0A
    d.push(np.zeros((4, 512, 3), np.uint8))
    pushed = sock.sent[1:]
    assert len(pushed) == 1 + 4 * 2
    assert pushed[0][12:14] == b"\x01\x07" and pushed[0][35] == 51
    assert all(p[12] == 0x55 for p in pushed[1:])


@pytest.mark.parametrize("width,height", [(128, 32), (64, 64), (512, 4), (384, 4)])
def test_push_matches_reference_encoder(width, height):
    rng = np.random.default_rng(width * height)
    sock = FakeSocket()
    d = ColorlightDisplay(width, height, "eth0", sock=sock)
    for _ in range(2):  # the second push must overwrite the first push's pixels
        frame = rng.integers(0, 256, (height, width, 3), dtype=np.uint8)
        sock.sent.clear()
        d.push(frame)
        expected = [p for y in range(height) for p in row_packets(y, frame[y])]
        assert sock.sent[1:] == expected


def test_push_rejects_a_frame_of_the_wrong_shape():
    d = ColorlightDisplay(64, 64, "eth0", sock=FakeSocket())
    with pytest.raises(ValueError, match="frame shape"):
        d.push(np.zeros((32, 128, 3), np.uint8))   # same byte count, wrong layout


@pytest.mark.parametrize("frame", [np.zeros((32, 128, 3)), np.full((32, 128, 3), 300, np.int64),
                                   np.zeros((32, 128, 4), np.uint8), np.zeros((32, 128), np.uint8)],
                         ids=["float64", "int64", "rgba", "grey"])
def test_push_rejects_a_frame_that_is_not_uint8_rgb(frame):
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    with pytest.raises(ValueError, match="frame"):
        d.push(frame)
    assert sock.sent == []   # nothing reaches the wall, not even the frame packet


def test_width_that_cannot_split_evenly_rejected():
    with pytest.raises(ValueError, match="width 257"):
        ColorlightDisplay(257, 4, "eth0", sock=FakeSocket())


def test_colorlight_set_brightness_sends_packet():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    d.set_brightness(0.4)
    assert sock.sent[-1] == brightness_packet(0.4)
    assert d.brightness == 0.4
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[1] == frame_packet(0.4)
    d.close()
    assert sock.closed


def test_starts_at_the_safe_brightness_until_told():
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock)
    assert d.brightness == SAFE_BRIGHTNESS == 0.4
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[0] == frame_packet(0.4) and sock.sent[0][35] == 102   # never 255 before set_brightness
    assert ColorlightDisplay(128, 32, "eth0", sock=FakeSocket(), brightness=0.1).brightness == 0.1


def test_brightness_packet_resent_every_3_pushes():
    sock = FakeSocket()
    d = ColorlightDisplay(64, 64, "eth0", sock=sock)   # never told a level: resends the safe one
    frame = np.zeros((64, 64, 3), np.uint8)
    per_push = 1 + 64
    assert BRIGHTNESS_EVERY == 3
    d.push(frame)
    d.push(frame)
    assert len(sock.sent) == 2 * per_push and all(p[12] != 0x0A for p in sock.sent)
    d.push(frame)
    third = sock.sent[2 * per_push:]
    assert third[0] == frame_packet(SAFE_BRIGHTNESS)
    assert third[1] == brightness_packet(SAFE_BRIGHTNESS)   # after the frame packet, before the rows
    assert len(third) == per_push + 1 and all(p[12] == 0x55 for p in third[2:])
    d.set_brightness(0.2)   # sending a level restarts the count
    sock.sent.clear()
    for _ in range(6):
        d.push(frame)
    resent = [i for i, p in enumerate(sock.sent) if p[12] == 0x0A]
    assert resent == [2 * per_push + 1, 5 * per_push + 2]
    assert all(sock.sent[i] == brightness_packet(0.2) for i in resent)


def test_set_brightness_restarts_the_resend_count():
    sock = FakeSocket()
    d = ColorlightDisplay(64, 64, "eth0", sock=sock)
    frame = np.zeros((64, 64, 3), np.uint8)
    d.push(frame)
    d.push(frame)
    d.set_brightness(0.2)   # two pushes in: without the restart the next push would resend
    sock.sent.clear()
    d.push(frame)
    d.push(frame)
    assert all(p[12] != 0x0A for p in sock.sent)
    d.push(frame)
    assert [p for p in sock.sent if p[12] == 0x0A] == [brightness_packet(0.2)]


def test_nan_or_negative_brightness_fails_dark():
    assert brightness_packet(math.nan)[13] == 0 and brightness_packet(math.nan)[14:16] == b"\x00\x00"
    assert frame_packet(math.nan)[35] == 0 and frame_packet(math.nan)[38:41] == b"\x00\x00\x00"
    assert frame_packet(0.0)[35] == 0 and frame_packet(-0.5)[35] == 0
    sock = FakeSocket()
    d = ColorlightDisplay(128, 32, "eth0", sock=sock, brightness=math.nan)
    d.push(np.zeros((32, 128, 3), np.uint8))
    assert sock.sent[0][35] == 0
    d.set_brightness(math.nan)
    assert sock.sent[-1] == brightness_packet(0.0)


def test_without_raw_sockets_a_clear_error(monkeypatch):
    monkeypatch.delattr(socket, "AF_PACKET", raising=False)
    with pytest.raises(OSError, match="Linux raw sockets"):
        ColorlightDisplay(128, 32, "eth0")


def test_raw_socket_permission_error_names_cap_net_raw(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)   # present on Linux, added here for the Mac
    monkeypatch.setattr(socket, "socket", denied)
    with pytest.raises(PermissionError, match="CAP_NET_RAW"):
        ColorlightDisplay(128, 32, "eth0")


def test_failed_bind_closes_the_socket_and_names_the_interface(monkeypatch):
    class Unbindable(FakeSocket):
        def __init__(self, *args):
            super().__init__()
            opened.append(self)

        def bind(self, address):
            raise OSError(19, "No such device")

    opened = []
    monkeypatch.setattr(socket, "AF_PACKET", 17, raising=False)
    monkeypatch.setattr(socket, "socket", Unbindable)
    with pytest.raises(OSError, match="eth7: No such device"):
        ColorlightDisplay(128, 32, "eth7")
    assert len(opened) == 1 and opened[0].closed


class Recorder:
    """Replaces ColorlightDisplay in make_display tests: raw sockets are Linux-only."""

    def __init__(self, width, height, iface, sock=None, **kwargs):
        self.args = (width, height, iface)
        self.kwargs = kwargs


def test_make_display_reads_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    cfg = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048, iface="eth9")
    assert make_display(cfg).args == (128, 32, "eth9")


def test_make_display_falls_back_to_colorlight_iface(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    assert make_display(Config(backend="colorlight", colorlight_iface="eth3")).args == (512, 192, "eth3")


@pytest.mark.parametrize("cfg", [SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8,
                                                 ddp_host="127.0.0.1", ddp_port=4048, iface=""),
                                 Config(backend="colorlight", colorlight_iface="")],
                         ids=["arcade-shape-empty-iface", "daemon-empty-colorlight-iface"])
def test_make_display_without_an_interface_is_a_clear_error(monkeypatch, cfg):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    with pytest.raises(ValueError, match="iface"):
        make_display(cfg)


def test_make_display_starts_at_the_configured_brightness(monkeypatch):
    monkeypatch.setattr(colorlight, "ColorlightDisplay", Recorder)
    arcade = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                             ddp_port=4048, iface="eth9", brightness=0.25)
    assert make_display(arcade).kwargs == {"brightness": 0.25}
    daemon = Config(backend="colorlight", colorlight_iface="eth3", brightness=0.9, brightness_cap=0.4)
    assert make_display(daemon).kwargs == {"brightness": 0.4}             # the daemon's capped level
    bare = SimpleNamespace(width=128, height=32, backend="colorlight", sdl_scale=8, ddp_host="127.0.0.1",
                           ddp_port=4048, iface="eth9")
    assert make_display(bare).kwargs == {"brightness": SAFE_BRIGHTNESS}
```

`tests/test_ddp.py`:

```python
import logging
import struct

import numpy as np
import pytest

from show.config import Config
from show.display import make_display
from show.display.ddp import DDPDisplay, packets


class FakeSocket:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append((data, addr))

    def close(self):
        pass


def test_packets_split_and_flag_last():
    data = bytes(512 * 192 * 3)
    pk = packets(data, seq=3)
    assert len(pk) == 205
    flags, seq, dtype, dest, off, length = struct.unpack("!BBBBIH", pk[0][:10])
    assert (flags, seq, dtype, dest, off, length) == (0x40, 3, 0x0B, 1, 0, 1440)
    flags, _, _, _, off, length = struct.unpack("!BBBBIH", pk[-1][:10])
    assert flags == 0x41 and off == 204 * 1440 and length == 294912 - 204 * 1440
    assert sum(len(p) - 10 for p in pk) == len(data)


def test_push_does_not_scale_and_cycles_sequence():
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    d.set_brightness(0.5)
    frame = np.full((1, 4, 3), 200, np.uint8)
    d.push(frame)
    data, addr = sock.sent[0]
    assert addr == ("10.0.0.2", 4048)
    assert data[10:13] == bytes([200, 200, 200])
    seqs = []
    for _ in range(16):
        d.push(frame)
        seqs.append(sock.sent[-1][0][1])
    assert seqs[0] == 2 and 15 in seqs and 0 not in seqs and seqs[-1] == 2


@pytest.mark.parametrize("frame", [np.zeros((1, 4, 3)), np.full((1, 4, 3), 300, np.int64),
                                   np.zeros((2, 8, 3), np.uint8), np.zeros((1, 4), np.uint8)],
                         ids=["float64", "int64", "wrong-size", "grey"])
def test_push_rejects_a_frame_that_is_not_uint8_rgb(frame):
    sock = FakeSocket()
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=sock)
    with pytest.raises(ValueError, match="frame"):
        d.push(frame)
    assert sock.sent == []


def test_make_display_ddp():
    d = make_display(Config(backend="ddp"))
    assert isinstance(d, DDPDisplay)
    d.close()


def test_ddp_brightness_logged_once(caplog):
    caplog.set_level(logging.INFO, logger="show.display.ddp")
    d = DDPDisplay(4, 1, "10.0.0.2", 4048, sock=FakeSocket())
    d.set_brightness(0.4)
    d.set_brightness(0.2)
    records = [r for r in caplog.records if "Falcon Player" in r.getMessage()]
    assert len(records) == 1 and d.brightness == 0.2
```

`tests/test_display.py`:

```python
import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from show.config import Config
from show.display import make_display
from show.display.fake import FakeDisplay
from show.display.sdl import SDLDisplay


def test_fake_display_keeps_last_and_count():
    d = FakeDisplay()
    frame = np.zeros((192, 512, 3), np.uint8)
    d.push(frame)
    frame[0, 0] = 255
    d.push(frame)
    assert d.count == 2
    assert d.last.sum() == 765
    d.set_brightness(0.2)
    assert d.brightness == 0.2
    d.close()
    assert d.closed


def test_sdl_display_pushes_headless():
    pressed = []
    d = SDLDisplay(512, 192, scale=1, on_key=pressed.append)
    d.push(np.zeros((192, 512, 3), np.uint8))
    assert d.window.get_size() == (512, 192)
    assert tuple(d.window.get_at((0, 0)))[:3] == (0, 0, 0)
    d.push(np.full((192, 512, 3), 40, np.uint8))
    assert tuple(d.window.get_at((511, 191)))[:3] == (40, 40, 40)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))   # not 1..9: ignored
    frame = np.zeros((192, 512, 3), np.uint8)
    frame[5, 7] = (200, 10, 30)
    d.push(frame)
    assert pressed == [2]                                                    # key 3 is index 2
    assert tuple(d.window.get_at((7, 5)))[:3] == (200, 10, 30)               # row 5, column 7: not transposed
    assert tuple(d.window.get_at((5, 7)))[:3] == (0, 0, 0)
    d.set_brightness(0.15)
    assert d.brightness == 0.15
    d.close()
    assert not pygame.display.get_init()


def test_make_display_fake_and_unknown():
    assert isinstance(make_display(Config(backend="fake")), FakeDisplay)
    for backend in ("hologram", "matrix"):  # the matrix backend was removed (daemon Task 17)
        with pytest.raises(ValueError):
            make_display(Config(backend=backend))


def test_make_display_accepts_any_config_object():
    cfg = SimpleNamespace(width=64, height=64, backend="fake", sdl_scale=8,
                          ddp_host="127.0.0.1", ddp_port=4048)
    assert isinstance(make_display(cfg), FakeDisplay)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_colorlight.py`
Expected: collection error, `ImportError: cannot import name 'BRIGHTNESS_EVERY' from 'show.display.colorlight'`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_ddp.py tests/test_display.py`
Expected: `4 failed, 8 passed` (the four `test_push_rejects_a_frame_that_is_not_uint8_rgb` cases in `test_ddp.py`; the tightened SDL test already passes).

- [ ] **Step 3: Implement**

`show/display/colorlight.py`:

```python
"""Raw Ethernet driver for Colorlight 5A-75B/E receiving cards (Linux only, needs CAP_NET_RAW).

Constants diffed on 2026-09-27 against Falcon Player's src/channeloutput/ColorLight-5a-75.cpp
(master) and H. Kubota's protocol notes (hkubota.wordpress.com, 2022-01-31, updated 2022-09-29).
chubby75 documents the card's hardware, not this protocol. Every packet: destination MAC
11:22:33:44:55:66, source MAC 22:22:33:44:55:66, then a packet-type byte at offset 12 whose
first data byte shares the EtherType field at offset 13.

- 0x01 display frame, 112 bytes, EtherType 0x0107: data[21] brightness, data[22] 0x05,
  data[24..26] brightness for R, G, B (data counted from offset 14).
- 0x0A brightness, 77 bytes, EtherType 0x0A<b>: then b, b, 0xFF, zeros.
- 0x55 row data, EtherType 0x5500 | row >> 8: row & 0xFF, pixel offset (2 bytes), pixel count
  (2 bytes), 0x08, 0x88, then pixels in RGB order (Falcon Player; Kubota's panel needed BGR).
  A row wider than CHUNK_PIXELS is split into equal packets.

Falcon Player's loop sends each display frame packet and then the next frame's rows; push()
does the same, so the card shows a pushed frame when the next push starts. Verify the pixel
order with the rgb test pattern on the panel before trusting colours.

Brightness. The display starts at SAFE_BRIGHTNESS (0.4, the power-supply cap of both the arcade
and the show daemon configs) unless make_display passes the configured level, so a push before
set_brightness never runs the wall at 255. Falcon Player sends the 0x0A packet with every frame
(twice on firmware 13 and later); this driver sends it on set_brightness and again every
BRIGHTNESS_EVERY pushes, between the display frame packet and the rows, so a card that browns out
and restarts is back at the cap within 0.1 s at 30 Hz. The display frame packet carries the level
on every push as well. A level that is NaN or not above 0 is sent as 0: it fails dark, never bright.
"""
from __future__ import annotations

import math
import socket

import numpy as np

DST_MAC = bytes.fromhex("112233445566")
SRC_MAC = bytes.fromhex("222233445566")
ETH_ROW = 0x5500
ETH_FRAME = 0x0107
ETH_BRIGHTNESS = 0x0A00
CHUNK_PIXELS = 256          # most pixels per row packet; Falcon Player allows up to 497
ROW_HEADER_LEN = 14 + 7     # Ethernet header plus the 7-byte row header
FRAME_PAYLOAD_LEN = 98
BRIGHTNESS_PAYLOAD_LEN = 63
SAFE_BRIGHTNESS = 0.4       # the level before set_brightness: arcade.toml's brightness, show.toml's cap
BRIGHTNESS_EVERY = 3        # pushes between brightness packets: 0.1 s at 30 Hz


def _eth(ethertype: int) -> bytes:
    return DST_MAC + SRC_MAC + ethertype.to_bytes(2, "big")


def _level(level: float) -> int:
    if not level > 0.0:   # NaN, zero or negative: dark
        return 0
    return int(min(1.0, level) * 255)


def _row_header(row: int, offset: int, count: int) -> bytes:
    return _eth(ETH_ROW | (row >> 8)) + bytes([row & 0xFF, offset >> 8, offset & 0xFF,
                                               count >> 8, count & 0xFF, 0x08, 0x88])


def _chunk_pixels(width: int) -> int:
    """Pixels per row packet: the row split into the fewest equal packets of at most CHUNK_PIXELS."""
    chunks = math.ceil(width / CHUNK_PIXELS) if width > 0 else 0
    if chunks == 0 or width % chunks:
        raise ValueError(f"width {width} does not split into {chunks} equal row packets")
    return width // chunks


def row_packets(row: int, pixels: np.ndarray) -> list[bytes]:
    """Reference encoder for one row of (width, 3) RGB pixels; push() must match it byte for byte."""
    chunk = _chunk_pixels(pixels.shape[0])
    out = []
    for off in range(0, pixels.shape[0], chunk):
        data = np.ascontiguousarray(pixels[off : off + chunk], dtype=np.uint8)
        out.append(_row_header(row, off, chunk) + data.tobytes())
    return out


def frame_packet(brightness: float) -> bytes:
    b = _level(brightness)
    payload = bytearray(FRAME_PAYLOAD_LEN)
    payload[21] = b
    payload[22] = 0x05
    payload[24] = payload[25] = payload[26] = b
    return _eth(ETH_FRAME) + bytes(payload)


def brightness_packet(level: float) -> bytes:
    b = _level(level)
    payload = bytearray(BRIGHTNESS_PAYLOAD_LEN)
    payload[0] = payload[1] = b
    payload[2] = 0xFF
    return _eth(ETH_BRIGHTNESS | b) + bytes(payload)


class ColorlightDisplay:
    def __init__(self, width: int, height: int, iface: str, sock=None, brightness: float = SAFE_BRIGHTNESS):
        self._chunk = _chunk_pixels(width)
        chunks = width // self._chunk
        self.width, self.height = width, height
        # One prebuilt packet per (row, chunk); headers are fixed, push() fills the pixels.
        self._packets = np.zeros((height, chunks, ROW_HEADER_LEN + self._chunk * 3), np.uint8)
        for y in range(height):
            for c in range(chunks):
                header = _row_header(y, c * self._chunk, self._chunk)
                self._packets[y, c, :ROW_HEADER_LEN] = np.frombuffer(header, np.uint8)
        self._pixels = self._packets[:, :, ROW_HEADER_LEN:]
        if sock is None:
            sock = _open_raw_socket(iface)
        self.sock = sock
        self.brightness = brightness
        self._since_brightness = 0   # pushes since the last brightness packet

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        self.sock.send(brightness_packet(level))
        self._since_brightness = 0

    def push(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame shape {frame.shape} is not ({self.height}, {self.width}, 3)")
        if frame.dtype != np.uint8:
            raise ValueError(f"frame dtype {frame.dtype} is not uint8; convert before push")
        self.sock.send(frame_packet(self.brightness))   # shows the rows sent by the previous push
        self._since_brightness += 1
        if self._since_brightness >= BRIGHTNESS_EVERY:
            self.sock.send(brightness_packet(self.brightness))
            self._since_brightness = 0
        self._pixels[...] = frame.reshape(self.height, -1, self._chunk * 3)
        for packet in self._packets.reshape(-1, self._packets.shape[-1]):
            self.sock.send(packet.data)

    def close(self) -> None:
        self.sock.close()


def _open_raw_socket(iface: str) -> socket.socket:
    if not hasattr(socket, "AF_PACKET"):
        raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET); "
                      "use --backend sdl on this machine")
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    except PermissionError as e:
        raise PermissionError(f"a raw socket on {iface} needs CAP_NET_RAW: run under the arcade's systemd unit "
                              "(AmbientCapabilities=CAP_NET_RAW) or grant it once with "
                              "sudo setcap cap_net_raw+ep on the venv's real python binary") from e
    try:
        sock.bind((iface, 0))
    except OSError as e:
        sock.close()
        raise OSError(e.errno, f"cannot bind a raw socket to {iface}: {e.strerror or e}") from e
    return sock
```

`show/display/__init__.py`:

```python
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np


class DisplayConfig(Protocol):
    """Any object with these attributes can be handed to make_display.

    `iface` is the wired interface for the colorlight backend; the daemon's Config calls it
    `colorlight_iface`, and make_display reads either.
    """

    width: int
    height: int
    backend: str
    sdl_scale: int
    ddp_host: str
    ddp_port: int
    iface: str


class Display(Protocol):
    def push(self, frame: np.ndarray) -> None: ...
    def set_brightness(self, level: float) -> None: ...
    def close(self) -> None: ...


def make_display(cfg: DisplayConfig, on_key: Callable[[int], None] | None = None) -> Display:
    if cfg.backend == "fake":
        from show.display.fake import FakeDisplay
        return FakeDisplay()
    if cfg.backend == "sdl":
        from show.display.sdl import SDLDisplay
        return SDLDisplay(cfg.width, cfg.height, cfg.sdl_scale, on_key)
    if cfg.backend == "colorlight":
        from show.display.colorlight import SAFE_BRIGHTNESS, ColorlightDisplay
        iface = getattr(cfg, "iface", None) or getattr(cfg, "colorlight_iface", None)
        if not iface:
            raise ValueError("the colorlight backend needs a wired interface: set iface in arcade.toml "
                             "(colorlight_iface in show.toml)")
        # Start at the configured level (the daemon's capped one), so the wall is never brighter than
        # asked for before the first set_brightness.
        start = getattr(cfg, "effective_brightness", getattr(cfg, "brightness", SAFE_BRIGHTNESS))
        return ColorlightDisplay(cfg.width, cfg.height, iface, brightness=start)
    if cfg.backend == "ddp":
        from show.display.ddp import DDPDisplay
        return DDPDisplay(cfg.width, cfg.height, cfg.ddp_host, cfg.ddp_port)
    raise ValueError(f"unknown display backend {cfg.backend!r}")
```

`show/display/ddp.py`:

```python
from __future__ import annotations

import logging
import socket
import struct

import numpy as np

log = logging.getLogger(__name__)

DDP_PORT = 4048
MAX_DATA = 1440
FLAG_VERSION1 = 0x40
FLAG_PUSH = 0x01
DATA_TYPE_RGB8 = 0x0B   # RGB, 8 bits per channel
DEST_DEFAULT = 0x01


def packets(data: bytes, seq: int) -> list[bytes]:
    out = []
    total = len(data)
    for off in range(0, total, MAX_DATA):
        chunk = data[off : off + MAX_DATA]
        last = off + len(chunk) >= total
        flags = FLAG_VERSION1 | (FLAG_PUSH if last else 0)
        header = struct.pack("!BBBBIH", flags, seq & 0x0F, DATA_TYPE_RGB8, DEST_DEFAULT, off, len(chunk))
        out.append(header + chunk)
    return out


class DDPDisplay:
    """Sends frames unscaled; the panel brightness is Falcon Player's output setting."""

    def __init__(self, width: int, height: int, host: str, port: int = DDP_PORT, sock=None):
        self.width, self.height = width, height
        self.addr = (host, port)
        self.sock = sock or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.brightness = 1.0
        self._seq = 1
        self._brightness_logged = False

    def set_brightness(self, level: float) -> None:
        self.brightness = level
        if not self._brightness_logged:
            self._brightness_logged = True
            log.info("DDP sends pixels unscaled; brightness %.2f is Falcon Player's setting", level)

    def push(self, frame: np.ndarray) -> None:
        if frame.dtype != np.uint8 or frame.shape != (self.height, self.width, 3):
            raise ValueError(f"frame {frame.shape} {frame.dtype} is not ({self.height}, {self.width}, 3) uint8")
        for packet in packets(np.ascontiguousarray(frame).tobytes(), self._seq):
            self.sock.sendto(packet, self.addr)
        self._seq = self._seq % 15 + 1

    def close(self) -> None:
        self.sock.close()
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_colorlight.py tests/test_ddp.py tests/test_display.py`
Expected: `41 passed` (29, 8, 4).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `85 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add show/display/colorlight.py show/display/__init__.py show/display/ddp.py tests/test_colorlight.py tests/test_ddp.py tests/test_display.py
git commit -m "fix(show): Colorlight safe start brightness and periodic resend, uint8 frame checks, clear iface and CAP_NET_RAW errors (it01 C1-C3, C7, C8)" -m "No existing assert changed. In test_colorlight only the import block, the reference-encoder parametrize (adds 384x4) and the Recorder helper (accepts **kwargs) are edited; test_sdl_display_pushes_headless gains asserts. Brightness is resent every 3 pushes, the smallest interval no plan-literal test reaches."
```

---

### Task 2: Config range checks and calibration validation (carried C5, C6)

**Files:**
- Modify: `arcade/config.py` (whole file below), `arcade/calibration.py` (whole file below)
- Test: `tests/arcade/test_config.py`, `tests/arcade/test_calibration.py` (whole files below)

**Interfaces:**
- Consumes: iteration 1's `ArcadeConfig`, `load_config`, `Calibration`, `load_calibration`, `save_calibration`.
- Produces: `load_config` raises `ValueError` naming the field for `brightness`, `apl_cap_day`, `apl_cap_night` outside (0, 1]; `fps`, `camera_fps`, `gamma` not over 0; `sdl_scale` under 1; any `*_seconds` or `night_lux` under 0; NaN anywhere in those. `arcade.calibration.FIELDS` (the field names); `load_calibration` validates each key present, returns the defaults with a warning on any bad value, fills a missing key with its default and ignores unknown keys (one warning naming them); `save_calibration` fsyncs the file, renames, then fsyncs the directory.

Both test modules only add tests; every existing test and assert is unchanged.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_config.py`:

```python
import dataclasses
import tomllib
from pathlib import Path

import pytest

from arcade.config import ArcadeConfig, load_config

REPO_TOML = Path(__file__).resolve().parents[2] / "arcade.toml"


def write(tmp_path, text):
    p = tmp_path / "arcade.toml"
    p.write_text(text + "\n")
    return p


def test_defaults_when_file_missing(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg.size == (128, 32)
    assert cfg.backend == "sdl" and cfg.sdl_scale == 8 and cfg.iface == "eth0"
    assert (cfg.ddp_host, cfg.ddp_port) == ("127.0.0.1", 4048)
    assert cfg.camera == "mediapipe" and cfg.camera_index == 0 and cfg.camera_fps == 10
    assert cfg.audio == "sounddevice" and cfg.audio_device == "" and cfg.scenario == ""
    assert cfg.mirror is True and cfg.brightness == 0.4 and cfg.gamma == 2.2 and cfg.look == "led"
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.night_lux) == (0.12, 0.06, 5.0)
    assert (cfg.night_start, cfg.night_end) == ("01:00", "06:00")
    assert cfg.dwell_seconds == 1.2
    assert (cfg.present_on_seconds, cfg.present_off_seconds, cfg.player_lost_seconds) == (1.0, 3.0, 0.5)
    assert (cfg.leave_seconds, cfg.inactive_seconds, cfg.max_session_seconds) == (8.0, 30.0, 180.0)
    assert cfg.exit_seconds == 3.0 and cfg.allow_record is False
    assert cfg.data_dir == Path("data") and cfg.font_path == Path("fonts/5x7.bin") and cfg.fps == 30
    assert not hasattr(cfg, "idle_seconds")


def test_values_from_file(tmp_path):
    cfg = load_config(write(tmp_path, 'width = 64\nheight = 64\nbackend = "colorlight"\niface = "eth1"\n'
                                      'camera = "replay"\nscenario = "s.jsonl"\ndata_dir = "d"\nleave_seconds = 10'))
    assert cfg.size == (64, 64) and cfg.layout == "64x64"
    assert cfg.backend == "colorlight" and cfg.iface == "eth1"
    assert cfg.camera == "replay" and cfg.scenario == "s.jsonl"
    assert cfg.data_dir == Path("d")
    assert cfg.leave_seconds == 10.0 and isinstance(cfg.leave_seconds, float)


@pytest.mark.parametrize("line,field", [('backend = "hologram"', "backend"), ('audio = "tape"', "audio"),
                                        ("brightness = 1.5", "brightness"), ("brightness = 0", "brightness"),
                                        ("brightnes = 0.2", "brightnes"), ("width = 4", "width")])
def test_bad_values_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('backend = "matrix"', "backend"), ('camera = "kinect"', "camera"),
                                        ('look = "crt"', "look")])
def test_rejects_bad_enum_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line", ['night_start = "25:00"', 'night_end = "6pm"', 'night_start = "12:60"'])
def test_rejects_bad_night_time(tmp_path, line):
    with pytest.raises(ValueError, match="HH:MM"):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [('brightness = "0.4"', "brightness"), ("width = 12.5", "width"),
                                        ('mirror = "yes"', "mirror"), ("width = true", "width")])
def test_wrong_type_rejected(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("line,field", [("apl_cap_day = 0", "apl_cap_day"), ("apl_cap_day = 5", "apl_cap_day"),
                                        ("apl_cap_night = -0.1", "apl_cap_night"),
                                        ("apl_cap_night = nan", "apl_cap_night"), ("fps = 0", "fps"),
                                        ("fps = -3", "fps"), ("camera_fps = 0", "camera_fps"), ("gamma = 0", "gamma"),
                                        ("gamma = nan", "gamma"), ("gamma = inf", "gamma"),
                                        ("sdl_scale = 0", "sdl_scale"),
                                        ("night_lux = -1", "night_lux"), ("dwell_seconds = nan", "dwell_seconds")])
def test_rejects_out_of_range_values(tmp_path, line, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, line))


@pytest.mark.parametrize("field", [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")])
def test_every_seconds_field_rejects_negative(tmp_path, field):
    with pytest.raises(ValueError, match=field):
        load_config(write(tmp_path, f"{field} = -1.0"))


def test_range_edges_accepted(tmp_path):
    cfg = load_config(write(tmp_path, "apl_cap_day = 1.0\napl_cap_night = 1\ndwell_seconds = 0\nsdl_scale = 1\n"
                                      "night_lux = 0"))
    assert (cfg.apl_cap_day, cfg.apl_cap_night, cfg.dwell_seconds, cfg.sdl_scale, cfg.night_lux) == (1.0, 1.0, 0.0, 1, 0.0)


def test_layout_name():
    assert ArcadeConfig().layout == "128x32"
    assert ArcadeConfig(width=64, height=64).layout == "64x64"


def test_default_file_in_repo_lists_every_field_with_its_default():
    keys = set(tomllib.loads(REPO_TOML.read_text()))
    assert keys == {f.name for f in dataclasses.fields(ArcadeConfig)}
    assert load_config(REPO_TOML) == ArcadeConfig()
```

`tests/arcade/test_calibration.py`:

```python
import dataclasses
import json
import logging
import math
import os
import stat

import pytest

from arcade.calibration import Calibration, load_calibration, save_calibration


def test_default_calibration(tmp_path):
    cal = load_calibration(tmp_path)
    assert cal == Calibration()
    assert cal.zone == (0.2, 0.2, 0.8, 0.8)   # the central 60 percent of the frame
    assert cal.min_height == 0.45 and cal.calibrated is False
    assert cal.static_mask == () and cal.baseline_scale == 0.0 and cal.audio_floor_db == -90.0


def test_calibration_round_trip(tmp_path):
    cal = Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, baseline_scale=0.31,
                      static_mask=((0.12, 0.4, 0.02), (0.9, 0.1, 0.05)), audio_floor_db=-62.5, calibrated=True)
    save_calibration(tmp_path / "data", cal)
    assert load_calibration(tmp_path / "data") == cal
    assert [p.name for p in (tmp_path / "data").iterdir()] == ["calibration.json"]   # no temp file left


@pytest.mark.parametrize("text", ["", "{not json", "[]", '{"zone": [0.1, 0.2, 0.3]}',
                                  '{"zone": [0.8, 0.2, 0.2, 0.8], "min_height": 0.4, "baseline_scale": 0,'
                                  ' "static_mask": [], "audio_floor_db": -60, "calibrated": true}'])
def test_corrupt_calibration_falls_back_to_defaults(tmp_path, caplog, text):
    (tmp_path / "calibration.json").write_text(text)
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == Calibration()
    assert "calibration.json" in caplog.text


@pytest.mark.parametrize("key,value", [("min_height", -3), ("min_height", 1.5), ("min_height", True),
                                       ("baseline_scale", -1),
                                       ("static_mask", [[5, 5, 0.02]]), ("static_mask", [[0.5, 0.5, -2]]),
                                       ("static_mask", [[0.5, 0.5, 0]]), ("static_mask", [[0.5, 0.5]]),
                                       ("audio_floor_db", math.nan), ("audio_floor_db", 12.0),
                                       ("calibrated", "no"), ("calibrated", 1), ("zone", [0.1, 0.2, 0.9, "0.8"])],
                         ids=["height-negative", "height-over-1", "height-bool", "scale-negative", "light-outside",
                              "radius-negative", "radius-zero", "light-two-values", "floor-nan", "floor-positive",
                              "calibrated-string", "calibrated-int", "zone-string"])
def test_bad_value_falls_back_to_defaults_naming_the_key(tmp_path, caplog, key, value):
    good = Calibration(zone=(0.1, 0.2, 0.9, 0.8), min_height=0.5, calibrated=True)
    (tmp_path / "calibration.json").write_text(json.dumps(dataclasses.asdict(good) | {key: value}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == Calibration()
    assert key in caplog.text


def test_missing_key_takes_its_default_and_keeps_the_rest(tmp_path, caplog):
    data = dataclasses.asdict(Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, audio_floor_db=-62.5,
                                          calibrated=True))
    del data["audio_floor_db"]
    (tmp_path / "calibration.json").write_text(json.dumps(data))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        cal = load_calibration(tmp_path)
    assert cal == Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, calibrated=True)
    assert cal.audio_floor_db == -90.0 and "audio_floor_db" in caplog.text


def test_unknown_key_is_ignored_with_a_warning(tmp_path, caplog):
    cal = Calibration(zone=(0.1, 0.3, 0.7, 0.95), min_height=0.5, calibrated=True)
    (tmp_path / "calibration.json").write_text(json.dumps(dataclasses.asdict(cal) | {"exposure": 7}))
    with caplog.at_level(logging.WARNING, logger="arcade"):
        assert load_calibration(tmp_path) == cal
    assert "exposure" in caplog.text


def test_save_fsyncs_the_file_then_its_directory(tmp_path, monkeypatch):
    synced = []
    real_fsync = os.fsync

    def spy(fd):
        synced.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    save_calibration(tmp_path, Calibration())
    assert synced == [False, True]   # the bytes, then the rename
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_config.py tests/arcade/test_calibration.py`
Expected: `36 failed, 29 passed`.

- [ ] **Step 3: Implement**

`arcade/config.py`:

```python
"""ArcadeConfig: the flat arcade.toml (spec 4.3). Calibration lives in arcade/calibration.py."""
from __future__ import annotations

import dataclasses
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

BACKENDS = ("sdl", "fake", "colorlight", "ddp")
CAMERAS = ("mediapipe", "imx500", "replay", "none")
AUDIOS = ("sounddevice", "replay", "none")
LOOKS = ("plain", "led", "distance")
HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@dataclass
class ArcadeConfig:
    width: int = 128
    height: int = 32
    backend: str = "sdl"
    sdl_scale: int = 8
    iface: str = "eth0"
    ddp_host: str = "127.0.0.1"
    ddp_port: int = 4048
    camera: str = "mediapipe"
    camera_index: int = 0
    camera_fps: int = 10
    audio: str = "sounddevice"
    audio_device: str = ""
    scenario: str = ""
    mirror: bool = True
    brightness: float = 0.4
    apl_cap_day: float = 0.12
    apl_cap_night: float = 0.06
    night_start: str = "01:00"
    night_end: str = "06:00"
    night_lux: float = 5.0
    gamma: float = 2.2
    look: str = "led"
    dwell_seconds: float = 1.2
    present_on_seconds: float = 1.0
    present_off_seconds: float = 3.0
    player_lost_seconds: float = 0.5
    leave_seconds: float = 8.0
    inactive_seconds: float = 30.0
    max_session_seconds: float = 180.0
    exit_seconds: float = 3.0
    allow_record: bool = False
    data_dir: Path = Path("data")
    font_path: Path = Path("fonts/5x7.bin")
    fps: int = 30

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def layout(self) -> str:
        return f"{self.width}x{self.height}"


def _coerce(name: str, value, default):
    """A TOML value as the field's type. Ints are accepted for float fields; true/false only for bools."""
    if isinstance(default, Path):
        if isinstance(value, str):
            return Path(value)
    elif isinstance(default, bool):
        if isinstance(value, bool):
            return value
    elif isinstance(value, bool):
        pass
    elif isinstance(default, float) and isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, type(default)):
        return value
    kind = "a path string" if isinstance(default, Path) else type(default).__name__
    raise ValueError(f"{name} must be {kind}, got {value!r}")


def load_config(path: Path | str) -> ArcadeConfig:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    defaults = ArcadeConfig()
    names = {f.name for f in dataclasses.fields(ArcadeConfig)}
    unknown = sorted(set(raw) - names)
    if unknown:
        raise ValueError(f"unknown config keys: {unknown}")
    cfg = ArcadeConfig(**{k: _coerce(k, v, getattr(defaults, k)) for k, v in raw.items()})
    for name, allowed in (("backend", BACKENDS), ("camera", CAMERAS), ("audio", AUDIOS), ("look", LOOKS)):
        if getattr(cfg, name) not in allowed:
            raise ValueError(f"{name} must be one of {allowed}, got {getattr(cfg, name)!r}")
    for name in ("night_start", "night_end"):
        if not HHMM.fullmatch(getattr(cfg, name)):
            raise ValueError(f"{name} must be HH:MM (00:00 to 23:59), got {getattr(cfg, name)!r}")
    for name in ("brightness", "apl_cap_day", "apl_cap_night"):
        if not 0 < getattr(cfg, name) <= 1:   # NaN fails too
            raise ValueError(f"{name} must be in (0, 1], got {getattr(cfg, name)}")
    for name in ("fps", "camera_fps", "gamma"):
        if not getattr(cfg, name) > 0:
            raise ValueError(f"{name} must be greater than 0, got {getattr(cfg, name)}")
    if not math.isfinite(cfg.gamma):
        raise ValueError(f"gamma must be finite, got {cfg.gamma}")
    if cfg.sdl_scale < 1:
        raise ValueError(f"sdl_scale must be at least 1, got {cfg.sdl_scale}")
    for name in [f.name for f in dataclasses.fields(ArcadeConfig) if f.name.endswith("_seconds")] + ["night_lux"]:
        if not getattr(cfg, name) >= 0:
            raise ValueError(f"{name} must be 0 or more, got {getattr(cfg, name)}")
    if cfg.width < 8 or cfg.height < 8:
        raise ValueError(f"width and height must be at least 8, got {cfg.layout}")
    return cfg
```

`arcade/calibration.py`:

```python
"""Per-setup calibration (spec 6.6), stored in data_dir/calibration.json and read at startup."""
from __future__ import annotations

import dataclasses
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("arcade")

FILENAME = "calibration.json"


@dataclass(frozen=True)
class Calibration:
    # x0, y0, x1, y1, 0..1, in the mirrored display space the keypoints use (after mirror_keypoints):
    # a change of the mirror setting after calibrating flips the zone.
    zone: tuple[float, float, float, float] = (0.2, 0.2, 0.8, 0.8)
    min_height: float = 0.45                 # shortest body, as a fraction of frame height, that counts in-zone
    baseline_scale: float = 0.0              # the operator's standing scale; 0.0 means not measured
    static_mask: tuple[tuple[float, float, float], ...] = ()   # static lights as (x, y, radius), 0..1, same space
    audio_floor_db: float = -90.0
    calibrated: bool = False


FIELDS = tuple(f.name for f in dataclasses.fields(Calibration))


def _number(name: str, value, lo: float, hi: float) -> float:
    """A JSON number within [lo, hi]. Booleans, strings and NaN are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ValueError(f"{name} must be a number in [{lo}, {hi}], got {value!r}")
    return float(value)


def _from_json(d) -> Calibration:
    """Every key present is validated, and one bad value rejects the file; a missing key takes its default."""
    if not isinstance(d, dict):
        raise ValueError(f"expected a JSON object, got {type(d).__name__}")
    values: dict = {}
    if "zone" in d:
        if not isinstance(d["zone"], list) or len(d["zone"]) != 4:
            raise ValueError(f"zone must be [x0, y0, x1, y1], got {d['zone']!r}")
        zone = tuple(_number("zone", v, 0.0, 1.0) for v in d["zone"])
        if not (zone[0] < zone[2] and zone[1] < zone[3]):
            raise ValueError(f"zone must have x0 < x1 and y0 < y1, got {zone}")
        values["zone"] = zone
    for name in ("min_height", "baseline_scale"):
        if name in d:
            values[name] = _number(name, d[name], 0.0, 1.0)
    if "static_mask" in d:
        if not isinstance(d["static_mask"], list):
            raise ValueError(f"static_mask must be a list of [x, y, radius], got {d['static_mask']!r}")
        mask = []
        for light in d["static_mask"]:
            if not isinstance(light, list) or len(light) != 3:
                raise ValueError(f"static_mask entries must be [x, y, radius], got {light!r}")
            x, y, r = (_number("static_mask", v, 0.0, 1.0) for v in light)
            if r == 0.0:
                raise ValueError(f"static_mask radius must be over 0, got {light!r}")
            mask.append((x, y, r))
        values["static_mask"] = tuple(mask)
    if "audio_floor_db" in d:
        values["audio_floor_db"] = _number("audio_floor_db", d["audio_floor_db"], -200.0, 0.0)
    if "calibrated" in d:
        if not isinstance(d["calibrated"], bool):
            raise ValueError(f"calibrated must be true or false, got {d['calibrated']!r}")
        values["calibrated"] = d["calibrated"]
    return dataclasses.replace(Calibration(), **values)


def load_calibration(data_dir: Path | str) -> Calibration:
    """The saved calibration, or the uncalibrated defaults when the file is absent or unreadable."""
    path = Path(data_dir) / FILENAME
    if not path.exists():
        return Calibration()
    try:
        data = json.loads(path.read_text())
        cal = _from_json(data)
    except (OSError, ValueError) as e:
        log.warning("ignoring %s (%s: %s); using the uncalibrated defaults", path, type(e).__name__, e)
        return Calibration()
    missing = [name for name in FIELDS if name not in data]
    unknown = sorted(set(data) - set(FIELDS))
    if missing or unknown:
        log.warning("%s: missing %s take their defaults; unknown %s ignored", path, missing, unknown)
    return cal


def save_calibration(data_dir: Path | str, cal: Calibration) -> None:
    path = Path(data_dir) / FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(FILENAME + ".tmp")
    with open(tmp, "w") as f:
        json.dump(dataclasses.asdict(cal), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)   # the rename lives in the directory: sync it too
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_config.py tests/arcade/test_calibration.py`
Expected: `65 passed` (42, 23).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `123 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/config.py arcade/calibration.py tests/arcade/test_config.py tests/arcade/test_calibration.py
git commit -m "fix(arcade): config range checks, per-key calibration validation, fsync the directory (it01 C5, C6)"
```

---

### Task 3: Tooling (carried C9)

**Files:**
- Modify: `.gitignore` (whole file below), `arcade/main.py` (whole file below)
- Create: `tests/test_gitignore.py`
- Test: `tests/arcade/test_doctor.py` (whole file below)

**Interfaces:**
- Consumes: iteration 1's `arcade.main` (`doctor`, `main`, `probe_pose`, `MODEL_PATH`).
- Produces: `arcade.main.within(timeout: float, what: str, fn: Callable[[], tuple[bool, str]]) -> tuple[bool, str]` (fn's result, or `(False, f"{what} did not finish within {timeout:g} s")`; fn's exception is re-raised); `probe_pose(timeout, model)` returns within the timeout (after an untimed `import mediapipe`); `doctor([])` and `arcade doctor --require ""` print "names no source" and return 2; `.gitignore` ignores only the top-level `models/`, `data/` and `shots/` (`tests/test_gitignore.py` checks with `git -c core.excludesFile=/dev/null check-ignore --no-index`, so a user's global excludes cannot change the result).

`tests/arcade/test_doctor.py` only adds tests; it imports `threading`, its `arcade.main` import line gains `probe_pose` and `within`, and every existing assert is unchanged. The `within` tests release their worker with a `threading.Event`, so no thread is left sleeping.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_doctor.py`:

```python
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from arcade.main import doctor, main, probe_pose, within

ROOT = Path(__file__).resolve().parents[2]


def fixed(ok, detail="fine"):
    return lambda timeout: (ok, detail)


def boom(timeout):
    raise OSError("device busy")


def test_exit_code_and_report(capsys):
    assert doctor(["camera", "mic"], {"camera": fixed(True), "mic": fixed(True)}) == 0
    assert "UNAVAILABLE" not in capsys.readouterr().out
    assert doctor(["camera", "mic"], {"camera": fixed(True), "mic": fixed(False, "no frames")}) == 1
    out = capsys.readouterr().out
    assert "mic" in out and "UNAVAILABLE" in out and "no frames" in out


def test_raising_probe_counts_as_unavailable(capsys):
    assert doctor(["pose"], {"pose": boom}) == 1
    assert "OSError: device busy" in capsys.readouterr().out


def test_unknown_source_exits_two():
    assert doctor(["radar"], {"camera": fixed(True)}) == 2
    assert main(["doctor", "--require", "radar"]) == 2


def test_every_probe_gets_five_seconds():
    seen = []
    spy = lambda timeout: (seen.append(timeout), (True, ""))[1]
    assert doctor(["camera", "mic"], {"camera": spy, "mic": spy}) == 0 and seen == [5.0, 5.0]


def test_importing_main_loads_no_hardware_module():
    code = "import sys, arcade.main; print(sorted({'cv2', 'mediapipe', 'sounddevice'} & set(sys.modules)))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


@pytest.mark.parametrize("require", ["", " , "])
def test_require_naming_nothing_exits_two(capsys, require):
    assert main(["doctor", "--require", require]) == 2
    assert "names no source" in capsys.readouterr().out
    assert doctor([], {"camera": fixed(True)}) == 2


def test_within_gives_up_at_the_timeout():
    release = threading.Event()
    t0 = time.monotonic()
    ok, detail = within(0.2, "slow thing", lambda: (release.wait(5), (True, "late"))[1])
    assert not ok and detail == "slow thing did not finish within 0.2 s"
    assert time.monotonic() - t0 < 1.0
    release.set()   # let the worker finish instead of leaving it sleeping
    assert within(1.0, "quick thing", lambda: (True, "done")) == (True, "done")


def test_within_raises_what_the_function_raised(capsys):
    with pytest.raises(OSError, match="device busy"):
        within(1.0, "boom", lambda: boom(0))
    release = threading.Event()
    slow = lambda timeout: within(timeout, "pose landmarker", lambda: (release.wait(5), (True, ""))[1])
    assert doctor(["pose"], {"pose": slow}, timeout=0.2) == 1
    assert "did not finish within 0.2 s" in capsys.readouterr().out
    release.set()


def test_probe_pose_without_model_is_unavailable(tmp_path):
    ok, detail = probe_pose(1.0, tmp_path / "missing.task")
    assert not ok and "model missing" in detail
```

`tests/test_gitignore.py`:

```python
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def ignored(path: str) -> bool:
    """git check-ignore on a path name; the path need not exist. The user's global excludes are left out."""
    run = subprocess.run(["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "-q", "--no-index", path],
                         cwd=ROOT)
    assert run.returncode in (0, 1), f"git check-ignore failed for {path}"
    return run.returncode == 0


@pytest.mark.parametrize("path", ["models/pose_landmarker_lite.task", "data/calibration.json", "shots/paint.png"])
def test_top_level_runtime_dirs_are_ignored(path):
    assert ignored(path)


@pytest.mark.parametrize("path", ["tests/arcade/fixtures/data/walk.jsonl.gz", "tools/models/notes.md",
                                  "docs/superpowers/workflow/evidence/it02/shots/sheet.png"])
def test_nested_dirs_with_the_same_names_are_tracked(path):
    assert not ignored(path)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_doctor.py`
Expected: collection error, `ImportError: cannot import name 'within' from 'arcade.main'`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/test_gitignore.py`
Expected: `3 failed, 3 passed` (the nested paths are ignored by the unanchored rules).

- [ ] **Step 3: Implement**

`.gitignore`:

```text
.venv/
__pycache__/
*.pyc
*.egg-info/
*.swp
*.swo
.DS_Store

# arcade operator: per-run Stop-hook block counter (reset by the loop)
docs/superpowers/workflow/.blocks

# arcade: pose model, runtime data, contact sheets (anchored: tests/arcade/fixtures/ may hold data/ dirs)
/models/
/data/
/shots/

# show daemon: entry build products stay local; sources, entry.toml and fallback casts are tracked
entries/*/*
!entries/*/*.c
!entries/*/entry.toml
!entries/*/fallback.cast
```

`arcade/main.py`:

```python
"""Arcade command line. Task 0 provides `doctor`; Task 18 adds run (the default), calibrate, record, stats."""
from __future__ import annotations

import argparse
import importlib.metadata
import sys
import threading
import time
from pathlib import Path
from typing import Callable, TextIO

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
TIMEOUT = 5.0
Probe = Callable[[float], tuple[bool, str]]


def probe_camera(timeout: float, index: int = 0) -> tuple[bool, str]:
    """Runs on the calling thread, unlike probe_pose: macOS asks for camera access only from the
    main thread. The deadline is checked between reads, so one blocking read can overrun it."""
    import cv2  # inside the probe, so importing arcade.main never loads OpenCV

    cap, frames, deadline = cv2.VideoCapture(index), 0, time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frames += 1
            if frame.any():
                return True, f"device {index}: {frame.shape[1]}x{frame.shape[0]}"
        why = f"{frames} frames, all black" if frames else f"no frames in {timeout:.0f} s"
        return False, f"device {index}: {why} (macOS: grant this terminal camera access)"
    finally:
        cap.release()


def probe_mic(timeout: float, device: str = "") -> tuple[bool, str]:
    import numpy as np
    import sounddevice as sd

    blocks: list = []
    with sd.InputStream(samplerate=16000, channels=1, dtype="float32", device=device or None,
                        callback=lambda data, n, t, status: blocks.append(data.copy())):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(np.any(b != 0.0) for b in list(blocks)):
                return True, f"{device or 'default input'}: {sum(len(b) for b in blocks)} samples"
            time.sleep(0.05)
    why = "exact zeros (macOS: grant this terminal microphone access)" if blocks else "no audio callbacks"
    return False, f"{device or 'default input'}: {why}"


def within(timeout: float, what: str, fn: Callable[[], tuple[bool, str]]) -> tuple[bool, str]:
    """fn's result if it finishes within timeout, else unavailable. fn runs in a daemon thread,
    which cannot be killed: a hung fn keeps running until the process exits, which for the
    doctor is right away. An exception in fn is raised here, so the doctor reports it."""
    box: dict = {}

    def target():
        try:
            box["result"] = fn()
        except BaseException as e:
            box["error"] = e

    worker = threading.Thread(target=target, name=f"doctor-{what}", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return False, f"{what} did not finish within {timeout:g} s"
    if "error" in box:
        raise box["error"]
    return box["result"]


def probe_pose(timeout: float, model: Path = MODEL_PATH) -> tuple[bool, str]:
    if not Path(model).exists():
        return False, f"model missing at {model}; run: python tools/env_check.py"
    import mediapipe as mp   # untimed: a cold first import can take seconds, but it does not hang

    return within(timeout, "pose landmarker", lambda: _run_pose(mp, Path(model)))


def _run_pose(mp, model: Path) -> tuple[bool, str]:
    import numpy as np

    vision = mp.tasks.vision
    options = vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                                           running_mode=vision.RunningMode.VIDEO, num_poses=2)
    frame = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.full((480, 640, 3), 96, np.uint8))
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        t0 = time.monotonic()
        landmarker.detect_for_video(frame, 0)
        ms = (time.monotonic() - t0) * 1000
    return True, f"mediapipe {importlib.metadata.version('mediapipe')}: landmarker ran in {ms:.0f} ms"


def doctor(require: list[str], probes: dict[str, Probe], timeout: float = TIMEOUT,
           out: TextIO | None = None) -> int:
    out = out or sys.stdout  # CLI output, not library logging
    if not require:
        print(f"doctor: --require names no source; choose from {', '.join(sorted(probes))}", file=out)
        return 2
    unknown = [n for n in require if n not in probes]
    if unknown:
        print(f"doctor: unknown source {', '.join(unknown)}; choose from {', '.join(sorted(probes))}", file=out)
        return 2
    failed = 0
    for name in require:
        try:
            ok, detail = probes[name](timeout)
        except Exception as e:  # a probe that raises is a source that is unavailable
            ok, detail = False, f"{type(e).__name__}: {e}"
        print(f"{name:7s} {'ok' if ok else 'UNAVAILABLE'}  {detail}", file=out)
        failed += not ok
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arcade", description="Wall arcade")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="exit 1 if a required source is unavailable after the timeout")
    d.add_argument("--require", default="camera,mic,pose", help="comma list of camera, mic, pose")
    d.add_argument("--timeout", type=float, default=TIMEOUT)
    d.add_argument("--camera-index", type=int, default=0)
    d.add_argument("--audio-device", default="")
    d.add_argument("--model", default=str(MODEL_PATH))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    probes = {"camera": lambda t: probe_camera(t, args.camera_index),
              "mic": lambda t: probe_mic(t, args.audio_device),
              "pose": lambda t: probe_pose(t, Path(args.model))}
    return doctor([n.strip() for n in args.require.split(",") if n.strip()], probes, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_doctor.py tests/test_gitignore.py`
Expected: `16 passed` (10, 6).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `134 passed`, no skips.

Run: `.venv/bin/python -m arcade doctor --require pose; echo "exit $?"`
Expected: `pose    ok  mediapipe 1.0.0: landmarker ran in ... ms` and `exit 0` (mediapipe's `W0000 ... inference_feedback_manager` lines on stderr are normal).

Run: `.venv/bin/python -m arcade doctor --require pose --timeout 0.01; echo "exit $?"`
Expected: `pose    UNAVAILABLE  pose landmarker did not finish within 0.01 s` and `exit 1`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore arcade/main.py tests/arcade/test_doctor.py tests/test_gitignore.py
git commit -m "fix(arcade): anchor the runtime ignores, doctor --require '' exits 2, probe_pose honours its timeout (it01 C9)"
```

---

### Task 4: The Sensed record (core plan Task 3 with its amendment)

**Files:**
- Create: `arcade/sensed.py`, `arcade/sources/mirror.py`
- Test: `tests/arcade/test_sensed.py`, `tests/arcade/test_mirror.py`

**Interfaces:**
- Consumes: `arcade.calibration.Calibration` (`zone`, `min_height`).
- Produces, in `arcade/sensed.py` (`shoulder_mid` with one confident shoulder: its y, x from both hips, else a confident nose, else the one hip seen, else the shoulder; `Sensed.motion` is a read-only view, the caller's array stays writeable, and `motion=None` becomes the empty grid): the COCO constants `NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE` (0..16), `KEYPOINT_NAMES`, `SKELETON`, `MIN_CONF = 0.3`, `MOTION_GRID = (128, 64)` (width, height); `Keypoint(x, y, conf=1.0)`; `Body(id, box, keypoints, vx=0.0, vy=0.0, scale=0.0, in_zone=True, zone_x=0.5, zone_y=0.5, seen_ago=0.0)` with properties `nose`, `left_wrist`, `right_wrist`, `shoulder_mid`, `hip_mid` (`Keypoint | None`), `shoulder_width`, `torso`, `anchor`, `raise_line` (`float | None`), `raised_wrist`, `both_hands_up`, `cursor` (`(u, v) | None`), `center`, `height`, `confidence`, and `reach(kp) -> (u, v)`; `Blob(x, y, size, color, in_zone=True)`; `Audio(level=0.0, level_smooth=0.0, peak=0.0, voice_db=-90.0, floor_db=-90.0, voice=0.0, clap=False, onset=False, beat=False, bpm=None)`; `Sensed(t, camera_t=0.0, camera_fresh=False, camera_seq=0, bodies=(), player=None, player2=None, present=False, blobs=(), motion=<(0, 0) bool>, audio=Audio())` with `with_motion(size: tuple[int, int]) -> Sensed`; `place(body, calibration) -> Body`; `place_blob(blob, calibration) -> Blob`. In `arcade/sources/mirror.py`: `mirror_keypoints(keypoints) -> tuple[Keypoint, ...]`, `mirror_box(box) -> tuple`.

`test_body_requires_17_keypoints`, `test_body_cleans_bad_keypoints` and `test_skeleton_indices_valid` are revision 2's, verbatim. The others are the amendment's replacements and additions (see Resolved conflicts) plus `test_clean_clamps_confidence_and_rejects_non_finite`, `test_body_defaults_and_measured_scale`, `test_one_shoulder_does_not_move_the_centre` (loop decision 2), `test_body_with_nothing_confident_never_raises_or_fails` (Review Focus 2), `test_anchor_order` and `test_place_blob`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_sensed.py`:

```python
import math

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import (LEFT_ANKLE, LEFT_EAR, LEFT_ELBOW, LEFT_EYE, LEFT_HIP, LEFT_KNEE,
                           LEFT_SHOULDER, LEFT_WRIST, NOSE, RIGHT_ANKLE, RIGHT_EAR, RIGHT_ELBOW,
                           RIGHT_EYE, RIGHT_HIP, RIGHT_KNEE, RIGHT_SHOULDER, RIGHT_WRIST, SKELETON,
                           Audio, Blob, Body, Keypoint, Sensed, place, place_blob)


def kps(**over):
    pts = [Keypoint(0.5, 0.2 + i * 0.04) for i in range(17)]
    for idx, kp in over.items():
        pts[int(idx)] = kp
    return tuple(pts)


# A standing figure: shoulders at y 0.4, 0.2 apart; hips at y 0.7, so the torso is 0.3 and the raise
# line is at 0.4 - 0.3 * 0.3 = 0.31. The nose (0.22) is above it, the wrists hang at hip height.
FIGURE = {
    NOSE: Keypoint(0.5, 0.22), LEFT_EYE: Keypoint(0.48, 0.2), RIGHT_EYE: Keypoint(0.52, 0.2),
    LEFT_EAR: Keypoint(0.46, 0.21), RIGHT_EAR: Keypoint(0.54, 0.21),
    LEFT_SHOULDER: Keypoint(0.4, 0.4), RIGHT_SHOULDER: Keypoint(0.6, 0.4),
    LEFT_ELBOW: Keypoint(0.37, 0.55), RIGHT_ELBOW: Keypoint(0.63, 0.55),
    LEFT_WRIST: Keypoint(0.35, 0.7), RIGHT_WRIST: Keypoint(0.65, 0.7),
    LEFT_HIP: Keypoint(0.45, 0.7), RIGHT_HIP: Keypoint(0.55, 0.7),
    LEFT_KNEE: Keypoint(0.45, 0.85), RIGHT_KNEE: Keypoint(0.55, 0.85),
    LEFT_ANKLE: Keypoint(0.45, 0.95), RIGHT_ANKLE: Keypoint(0.55, 0.95),
}
BOX = (0.3, 0.2, 0.7, 1.0)


def figure(over=None, box=BOX, **fields):
    pts = dict(FIGURE)
    pts.update(over or {})
    return Body(1, box, tuple(pts[i] for i in range(17)), **fields)


def test_body_requires_17_keypoints():
    with pytest.raises(ValueError):
        Body(1, (0, 0, 1, 1), tuple(Keypoint(0, 0) for _ in range(5)))


def test_body_cleans_bad_keypoints():
    pts = kps(**{str(LEFT_WRIST): Keypoint(1.7, -0.2, 0.9), str(RIGHT_WRIST): Keypoint(math.nan, 0.5, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.left_wrist == Keypoint(1.0, 0.0, 0.0)
    assert b.right_wrist.conf == 0.0 and b.right_wrist.x == 0.0


def test_clean_clamps_confidence_and_rejects_non_finite():
    pts = kps(**{str(NOSE): Keypoint(0.5, 0.2, 5.0), str(LEFT_EYE): Keypoint(0.5, 0.2, -1.0),
                 str(RIGHT_EYE): Keypoint(0.5, 0.2, math.nan), str(LEFT_EAR): Keypoint(math.inf, 0.2, 0.9),
                 str(RIGHT_EAR): Keypoint(0.5, -math.inf, 0.9)})
    b = Body(1, (0, 0, 1, 1), pts)
    assert b.keypoints[NOSE] == Keypoint(0.5, 0.2, 1.0)
    assert b.keypoints[LEFT_EYE] == Keypoint(0.5, 0.2, 0.0)
    assert b.keypoints[RIGHT_EYE] == Keypoint(0.0, 0.0, 0.0)
    assert b.keypoints[LEFT_EAR] == Keypoint(1.0, 0.2, 0.0)
    assert b.keypoints[RIGHT_EAR] == Keypoint(0.5, 0.0, 0.0)


def test_body_defaults_and_measured_scale():
    b = figure()
    assert (b.vx, b.vy, b.in_zone, b.zone_x, b.zone_y, b.seen_ago) == (0.0, 0.0, True, 0.5, 0.5, 0.0)
    assert b.scale == pytest.approx(0.48)            # nose to mid-hip
    assert figure(scale=0.7).scale == 0.7            # a given scale is kept
    assert b.shoulder_mid == Keypoint(0.5, 0.4) and b.hip_mid == Keypoint(0.5, 0.7)
    assert b.shoulder_width == pytest.approx(0.2) and b.torso == pytest.approx(0.3)
    assert b.center == (0.5, 0.6) and b.height == pytest.approx(0.8)
    assert b.nose == b.keypoints[NOSE] and b.confidence == 1.0
    assert Body(1, (0, 0, 1, 1), kps()).scale == pytest.approx(0.46)


def test_raise_line_is_above_shoulders():
    b = figure()
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist is None and not b.both_hands_up
    low = 0.4 - 0.1 * 0.3                             # 0.1 torso above the shoulders: not raised
    assert figure({RIGHT_WRIST: Keypoint(0.65, low)}).raised_wrist is None
    high = 0.4 - 0.4 * 0.3                            # 0.4 torso above: raised
    up = figure({RIGHT_WRIST: Keypoint(0.65, high)})
    assert up.raised_wrist == Keypoint(0.65, high) and not up.both_hands_up
    assert figure({RIGHT_WRIST: Keypoint(0.65, 0.3)}).raised_wrist is not None   # below the nose, still raised
    both = figure({LEFT_WRIST: Keypoint(0.35, 0.1), RIGHT_WRIST: Keypoint(0.65, high)})
    assert both.both_hands_up and both.raised_wrist == Keypoint(0.35, 0.1)      # the higher one
    faint = figure({RIGHT_WRIST: Keypoint(0.65, 0.1, 0.1)})
    assert faint.raised_wrist is None


def test_nose_fallback_only_without_shoulders():
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    b = figure(hidden)
    assert b.shoulder_mid is None and b.raise_line == pytest.approx(0.22)
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.25)}).raised_wrist is None
    assert figure({**hidden, RIGHT_WRIST: Keypoint(0.65, 0.18)}).raised_wrist is not None
    one = figure({RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})    # one shoulder still sets the line
    assert one.shoulder_mid == Keypoint(0.5, 0.4)                 # its y; x from the hips
    assert one.raise_line == pytest.approx(0.31)
    no_hips = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), LEFT_HIP: Keypoint(0.45, 0.7, 0.0),
               RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(no_hips).shoulder_mid == Keypoint(0.5, 0.4)    # x from the nose
    alone = {**no_hips, NOSE: Keypoint(0.5, 0.22, 0.0)}
    assert figure(alone).shoulder_mid == Keypoint(0.4, 0.4)      # nothing else: the shoulder itself
    one_hip = {RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0), RIGHT_HIP: Keypoint(0.55, 0.7, 0.0)}
    assert figure(one_hip).shoulder_mid == Keypoint(0.5, 0.4)    # one hip is off centre too: the nose


def test_one_shoulder_does_not_move_the_centre():
    # Shoulders 0.24 apart for the 0.3 torso: the 1.25 ratio TORSO_PER_SHOULDER_WIDTH assumes, as actors use.
    up = {LEFT_SHOULDER: Keypoint(0.38, 0.4), RIGHT_WRIST: Keypoint(0.7, 0.1)}
    seen = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.31)})
    lost = figure({**up, RIGHT_SHOULDER: Keypoint(0.62, 0.4, 0.29)})    # crosses MIN_CONF
    assert abs(seen.anchor.x - lost.anchor.x) < 0.03
    assert abs(seen.cursor[0] - lost.cursor[0]) < 0.03
    assert abs(seen.cursor[1] - lost.cursor[1]) < 0.03
    cal = Calibration()
    assert abs(place(seen, cal).zone_x - place(lost, cal).zone_x) < 0.03


def test_hooded_body_still_raises():
    hood = {NOSE: Keypoint(0.5, 0.22, 0.0), LEFT_EYE: Keypoint(0.48, 0.2, 0.0),
            RIGHT_EYE: Keypoint(0.52, 0.2, 0.0)}
    b = figure({**hood, RIGHT_WRIST: Keypoint(0.65, 0.2)})
    assert b.raise_line == pytest.approx(0.31)
    assert b.raised_wrist == Keypoint(0.65, 0.2)
    assert b.scale == pytest.approx(0.3 * 1.5)        # no nose: 1.5 torso lengths


def test_body_with_nothing_confident_never_raises_or_fails():
    blank = Body(1, BOX, tuple(Keypoint(0.5, 0.5, 0.0) for _ in range(17)))
    assert blank.raise_line is None and blank.raised_wrist is None and not blank.both_hands_up
    assert blank.cursor is None and blank.anchor is None and blank.scale == 0.0
    assert blank.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))
    placed = place(blank, Calibration())
    assert placed.in_zone and (placed.zone_x, placed.zone_y) == pytest.approx((0.5, 2 / 3))


def test_sensed_defaults():
    s = Sensed(t=1.0)
    assert s.bodies == () and s.blobs == () and s.audio == Audio()
    assert s.motion.shape == (0, 0) and s.motion.dtype == bool
    grid = np.zeros((4, 8), bool)
    held = Sensed(0.0, motion=grid)
    with pytest.raises(ValueError, match="read-only"):
        held.motion[0, 0] = True                     # one grid is shared by the ticks that hold it
    assert not held.with_motion((4, 2)).motion.flags.writeable
    assert grid.flags.writeable                      # the record holds a read-only view, not the caller's array
    assert Sensed(0.0, motion=None).motion.shape == (0, 0)
    assert (s.camera_t, s.camera_fresh, s.camera_seq) == (0.0, False, 0)
    assert s.player is None and s.player2 is None and not s.present
    assert not hasattr(s, "primary")
    a = Audio()
    assert (a.level, a.level_smooth, a.peak, a.voice, a.voice_db, a.floor_db) == (0, 0, 0, 0, -90.0, -90.0)
    assert not (a.clap or a.onset or a.beat) and a.bpm is None


def test_with_motion_resamples_never_rasterizes():
    b = figure()
    s = Sensed(0.0, bodies=(b,)).with_motion((8, 4))
    assert s.motion.shape == (4, 8) and s.motion.dtype == bool and not s.motion.any()
    given = np.ones((4, 8), bool)
    held = Sensed(0.0, motion=given)
    assert held.with_motion((8, 4)) is held and np.shares_memory(held.motion, given)
    small = np.array([[True, False], [False, True]])
    up = Sensed(0.0, motion=small).with_motion((8, 4)).motion
    assert up.shape == (4, 8)
    assert up[:2, :4].all() and up[2:, 4:].all() and not up[:2, 4:].any() and not up[2:, :4].any()
    grid = np.zeros((64, 128), bool)
    grid[33, 101] = True
    down = Sensed(0.0, motion=grid).with_motion((64, 32)).motion
    assert down.shape == (32, 64) and down.sum() == 1 and down[16, 50]    # one lit cell survives shrinking


def test_reach_box_corners():
    b = figure()     # shoulder mid (0.5, 0.4), shoulders 0.2 apart, torso 0.3, hips at 0.7
    top = 0.4 - 1.05 * 0.3
    assert b.reach(Keypoint(0.2, top)) == pytest.approx((0.0, 0.0))
    assert b.reach(Keypoint(0.8, 0.7)) == pytest.approx((1.0, 1.0))
    assert b.reach(Keypoint(0.5, (top + 0.7) / 2)) == pytest.approx((0.5, 0.5))
    assert b.reach(Keypoint(0.0, 1.0)) == (0.0, 1.0)                        # clamped
    half = {i: Keypoint(0.5 + (k.x - 0.5) / 2, 0.5 + (k.y - 0.5) / 2) for i, k in FIGURE.items()}
    small = figure(half, box=(0.4, 0.35, 0.6, 0.75))
    wrist = Keypoint(0.7, 0.3)
    assert small.reach(Keypoint(0.5 + (wrist.x - 0.5) / 2, 0.5 + (wrist.y - 0.5) / 2)) == pytest.approx(b.reach(wrist))
    no_shoulders = figure({LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)})
    assert no_shoulders.reach(Keypoint(0.5, 0.6)) == pytest.approx((0.5, 0.5))   # the body box


def test_cursor_is_wrist_further_from_hip():
    right = figure({RIGHT_WRIST: Keypoint(0.8, 0.3), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert right.cursor == right.reach(right.right_wrist)
    assert right.cursor == pytest.approx((1.0, (0.3 - 0.085) / 0.615))
    left = figure({LEFT_WRIST: Keypoint(0.25, 0.2), RIGHT_WRIST: Keypoint(0.6, 0.72)})
    assert left.cursor == left.reach(left.left_wrist)
    only = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65)})
    assert only.cursor == only.reach(only.left_wrist)
    none = figure({RIGHT_WRIST: Keypoint(0.8, 0.3, 0.0), LEFT_WRIST: Keypoint(0.4, 0.65, 0.1)})
    assert none.cursor is None


def test_anchor_order():
    assert figure().anchor == Keypoint(0.5, 0.4)
    hidden = {LEFT_SHOULDER: Keypoint(0.4, 0.4, 0.0), RIGHT_SHOULDER: Keypoint(0.6, 0.4, 0.0)}
    assert figure(hidden).anchor == Keypoint(0.5, 0.22)
    assert figure({**hidden, NOSE: Keypoint(0.5, 0.22, 0.0)}).anchor == Keypoint(0.5, 0.7)


def test_place_uses_calibration_zone():
    b = figure()
    placed = place(b, Calibration())                  # zone (0.2, 0.2, 0.8, 0.8), min_height 0.45
    assert placed.in_zone
    assert (placed.zone_x, placed.zone_y) == pytest.approx((0.5, (0.4 - 0.2) / 0.6))
    assert placed.keypoints == b.keypoints and placed.scale == b.scale and b.zone_y == 0.5
    right = place(b, Calibration(zone=(0.6, 0.0, 1.0, 1.0)))
    assert not right.in_zone and right.zone_x == 0.0                       # clamped to the zone edge
    short = place(figure(box=(0.3, 0.2, 0.7, 0.6)), Calibration())         # 0.4 tall, under min_height
    assert not short.in_zone
    tall_enough = place(figure(box=(0.3, 0.2, 0.7, 0.65)), Calibration())
    assert tall_enough.in_zone


def test_place_blob():
    assert place_blob(Blob(0.5, 0.5, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert not place_blob(Blob(0.05, 0.1, 0.03, (255, 255, 255)), Calibration()).in_zone
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).in_zone


def test_skeleton_indices_valid():
    assert all(0 <= a < 17 and 0 <= b < 17 for a, b in SKELETON)
    assert Blob(0.1, 0.2, 0.05, (255, 0, 0)).color == (255, 0, 0)
```

`tests/arcade/test_mirror.py`:

```python
import pytest

from arcade.sensed import LEFT_WRIST, RIGHT_WRIST, Keypoint
from arcade.sources.mirror import mirror_box, mirror_keypoints


def pts():
    out = [Keypoint(0.5, 0.5, 0.9) for _ in range(17)]
    out[RIGHT_WRIST] = Keypoint(0.2, 0.3, 0.8)    # the camera sees the person's right hand on the image left
    out[LEFT_WRIST] = Keypoint(0.7, 0.6, 0.4)
    return tuple(out)


def test_mirror_flips_x_keeps_labels():
    m = mirror_keypoints(pts())
    assert isinstance(m, tuple) and len(m) == 17
    assert m[RIGHT_WRIST].x == pytest.approx(0.8) and (m[RIGHT_WRIST].y, m[RIGHT_WRIST].conf) == (0.3, 0.8)
    assert m[LEFT_WRIST].x == pytest.approx(0.3) and (m[LEFT_WRIST].y, m[LEFT_WRIST].conf) == (0.6, 0.4)
    assert mirror_box((0.1, 0.2, 0.3, 0.9)) == pytest.approx((0.7, 0.2, 0.9, 0.9))


def test_mirror_twice_is_identity():
    original = pts()
    back = mirror_keypoints(mirror_keypoints(original))
    for a, b in zip(original, back):
        assert (b.x, b.y, b.conf) == pytest.approx((a.x, a.y, a.conf))
    assert mirror_box(mirror_box((0.1, 0.2, 0.3, 0.9))) == pytest.approx((0.1, 0.2, 0.3, 0.9))
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py tests/arcade/test_mirror.py`
Expected: `2 errors during collection`, each `ModuleNotFoundError: No module named 'arcade.sensed'`.

- [ ] **Step 3: Implement**

`arcade/sensed.py`:

```python
"""The Sensed record (spec 5): the only input games see, built once per tick by the runner."""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from arcade.calibration import Calibration

(NOSE, LEFT_EYE, RIGHT_EYE, LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW,
 RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE,
 RIGHT_ANKLE) = range(17)

KEYPOINT_NAMES = ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "left_shoulder",
                  "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
                  "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle")

SKELETON = ((LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW),
            (RIGHT_ELBOW, RIGHT_WRIST), (LEFT_SHOULDER, RIGHT_SHOULDER), (LEFT_SHOULDER, LEFT_HIP),
            (RIGHT_SHOULDER, RIGHT_HIP), (LEFT_HIP, RIGHT_HIP), (LEFT_HIP, LEFT_KNEE),
            (LEFT_KNEE, LEFT_ANKLE), (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
            (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER))

MIN_CONF = 0.3
RAISE_TORSOS = 0.3               # the raise line sits this many torso lengths above the shoulder midpoint
REACH_WIDTHS = 1.5               # the reach box spans this many shoulder widths each side of the shoulder midpoint,
REACH_TOP_TORSOS = 1.05          # and from this many torso lengths above it (head plus a forearm) down to the hips
TORSO_PER_SHOULDER_WIDTH = 1.25  # torso length estimated from shoulder width when no hip is seen
NOSE_TO_HIP_PER_TORSO = 1.5      # scale estimated from the torso when the nose is not seen
MOTION_GRID = (128, 64)          # (width, height) of the fixed grid scenario files and actors store motion on


@dataclass(frozen=True)
class Keypoint:
    x: float
    y: float
    conf: float = 1.0


def _clean(kp: Keypoint) -> Keypoint:
    x, y, conf = kp.x, kp.y, kp.conf
    bad = any(v is None or math.isnan(v) for v in (x, y, conf))
    if bad:
        return Keypoint(0.0, 0.0, 0.0)
    return Keypoint(min(1.0, max(0.0, x)), min(1.0, max(0.0, y)),
                    0.0 if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0 else min(1.0, max(0.0, conf)))


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, v))


def _mid(a: Keypoint, b: Keypoint) -> Keypoint | None:
    """The midpoint of the confident ones of a and b; one alone stands in for the pair."""
    seen = [k for k in (a, b) if k.conf >= MIN_CONF]
    if not seen:
        return None
    return Keypoint(sum(k.x for k in seen) / len(seen), sum(k.y for k in seen) / len(seen),
                    min(k.conf for k in seen))


@dataclass(frozen=True)
class Body:
    """One tracked person. Keypoints are normalized camera coordinates, already mirrored and smoothed.

    scale 0.0 means "measure it": the nose-to-mid-hip length, or 1.5 torso lengths without a nose.
    """

    id: int
    box: tuple[float, float, float, float]
    keypoints: tuple[Keypoint, ...]
    vx: float = 0.0
    vy: float = 0.0
    scale: float = 0.0
    in_zone: bool = True
    zone_x: float = 0.5
    zone_y: float = 0.5
    seen_ago: float = 0.0

    def __post_init__(self):
        if len(self.keypoints) != 17:
            raise ValueError(f"a body has 17 keypoints, got {len(self.keypoints)}")
        object.__setattr__(self, "keypoints", tuple(_clean(k) for k in self.keypoints))
        if self.scale == 0.0:
            object.__setattr__(self, "scale", self._measured_scale())

    def _measured_scale(self) -> float:
        hip = self.hip_mid
        if self.nose.conf >= MIN_CONF and hip is not None:
            return math.hypot(self.nose.x - hip.x, self.nose.y - hip.y)
        return NOSE_TO_HIP_PER_TORSO * self.torso

    @property
    def nose(self) -> Keypoint:
        return self.keypoints[NOSE]

    @property
    def left_wrist(self) -> Keypoint:
        return self.keypoints[LEFT_WRIST]

    @property
    def right_wrist(self) -> Keypoint:
        return self.keypoints[RIGHT_WRIST]

    @property
    def shoulder_mid(self) -> Keypoint | None:
        """The midpoint of the confident shoulders, None without one.

        With one shoulder, its y stands in for the pair, but x comes from both hips, else a confident
        nose, else the one hip seen, else that shoulder: the centre (and so anchor, zone_x and the reach
        box) does not jump half a shoulder or hip width when one shoulder and one hip drop out.
        """
        left, right = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        seen = [k for k in (left, right) if k.conf >= MIN_CONF]
        if len(seen) != 1:
            return _mid(left, right)
        one = seen[0]
        hips = (self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])
        if all(h.conf >= MIN_CONF for h in hips):
            x = (hips[0].x + hips[1].x) / 2
        elif self.nose.conf >= MIN_CONF:
            x = self.nose.x
        else:
            hip = self.hip_mid
            x = hip.x if hip is not None else one.x
        return Keypoint(x, one.y, one.conf)

    @property
    def hip_mid(self) -> Keypoint | None:
        return _mid(self.keypoints[LEFT_HIP], self.keypoints[RIGHT_HIP])

    @property
    def shoulder_width(self) -> float:
        """Distance between the shoulders, 0.0 unless both are confident."""
        a, b = self.keypoints[LEFT_SHOULDER], self.keypoints[RIGHT_SHOULDER]
        if a.conf < MIN_CONF or b.conf < MIN_CONF:
            return 0.0
        return math.hypot(a.x - b.x, a.y - b.y)

    @property
    def torso(self) -> float:
        """Shoulder midpoint to hip midpoint; from the shoulder width without hips; 0.0 when unknown."""
        s, h = self.shoulder_mid, self.hip_mid
        if s is not None and h is not None:
            return math.hypot(s.x - h.x, s.y - h.y)
        return TORSO_PER_SHOULDER_WIDTH * self.shoulder_width

    @property
    def anchor(self) -> Keypoint | None:
        """What the tracker and place() follow: the shoulder midpoint, then the nose, then the hips."""
        s = self.shoulder_mid
        if s is not None:
            return s
        if self.nose.conf >= MIN_CONF:
            return self.nose
        return self.hip_mid

    @property
    def raise_line(self) -> float | None:
        """A wrist above this y is raised: 0.3 torso above the shoulders; the nose only without shoulders."""
        s = self.shoulder_mid
        if s is not None:
            return s.y - RAISE_TORSOS * self.torso
        if self.nose.conf >= MIN_CONF:
            return self.nose.y
        return None

    @property
    def raised_wrist(self) -> Keypoint | None:
        """The higher confident wrist above the raise line, else None."""
        line = self.raise_line
        if line is None:
            return None
        best = None
        for w in (self.left_wrist, self.right_wrist):
            if w.conf >= MIN_CONF and w.y < line and (best is None or w.y < best.y):
                best = w
        return best

    @property
    def both_hands_up(self) -> bool:
        line = self.raise_line
        return line is not None and all(w.conf >= MIN_CONF and w.y < line
                                        for w in (self.left_wrist, self.right_wrist))

    def reach(self, kp: Keypoint) -> tuple[float, float]:
        """kp in the body-relative reach box (spec 7.3), (u, v) each clamped to 0..1.

        u runs across 1.5 shoulder widths each side of the shoulder midpoint; v runs from 1.05 torso
        above the shoulder midpoint (head plus a forearm) down to hip height. Without shoulders the
        body box is the frame of reference.
        """
        s, torso = self.shoulder_mid, self.torso
        width = self.shoulder_width or torso / TORSO_PER_SHOULDER_WIDTH
        if s is None or torso <= 0.0 or width <= 0.0:
            x0, y0, x1, y1 = self.box
            u = (kp.x - x0) / (x1 - x0) if x1 > x0 else 0.5
            v = (kp.y - y0) / (y1 - y0) if y1 > y0 else 0.5
        else:
            hip = self.hip_mid
            top = s.y - REACH_TOP_TORSOS * torso
            bottom = hip.y if hip is not None else s.y + torso
            u = (kp.x - (s.x - REACH_WIDTHS * width)) / (2 * REACH_WIDTHS * width)
            v = (kp.y - top) / (bottom - top)
        return (_clamp01(u), _clamp01(v))

    @property
    def cursor(self) -> tuple[float, float] | None:
        """The confident wrist further from its hip, through reach(); None without a confident wrist.

        Stateless: when the pointing wrist drops out for a frame the cursor jumps to the other wrist
        (15 percent of captures at the spec 6.4 dropout), so every consumer needs a grace period or hysteresis.
        """
        best, far = None, -1.0
        for wrist, hip_index in ((self.left_wrist, LEFT_HIP), (self.right_wrist, RIGHT_HIP)):
            if wrist.conf < MIN_CONF:
                continue
            own = self.keypoints[hip_index]
            ref = next((k for k in (own if own.conf >= MIN_CONF else None, self.hip_mid, self.shoulder_mid)
                        if k is not None), wrist)
            d = math.hypot(wrist.x - ref.x, wrist.y - ref.y)
            if d > far:
                best, far = wrist, d
        return None if best is None else self.reach(best)

    @property
    def center(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    @property
    def confidence(self) -> float:
        return sum(k.conf for k in self.keypoints) / 17


@dataclass(frozen=True)
class Blob:
    x: float
    y: float
    size: float
    color: tuple[int, int, int]
    in_zone: bool = True


@dataclass(frozen=True)
class Audio:
    level: float = 0.0            # broadband RMS with slow gain, 0..1, for ambient visuals only
    level_smooth: float = 0.0     # level with 50 ms attack and 300 ms release
    peak: float = 0.0
    voice_db: float = -90.0       # absolute dBFS in the 300 Hz to 3.4 kHz band
    floor_db: float = -90.0       # rolling 30 s 90th percentile of voice_db
    voice: float = 0.0            # (voice_db - floor_db) / 30, clamped 0..1
    clap: bool = False
    onset: bool = False
    beat: bool = False
    bpm: float | None = None


def _in(zone: tuple[float, float, float, float], x: float, y: float) -> bool:
    x0, y0, x1, y1 = zone
    return x0 <= x <= x1 and y0 <= y <= y1


def place(body: Body, calibration: Calibration) -> Body:
    """body with in_zone, zone_x and zone_y from the calibration (spec 6.6). Actors and the tracker call it.

    The anchor (shoulders, then nose, then hips; the box centre without any) maps into the zone, 0..1
    across the mat and clamped. In the zone means the anchor inside it and the body at least min_height tall.
    """
    x0, y0, x1, y1 = calibration.zone
    a = body.anchor
    ax, ay = (a.x, a.y) if a is not None else body.center
    inside = _in(calibration.zone, ax, ay) and body.height >= calibration.min_height
    return dataclasses.replace(body, in_zone=inside, zone_x=_clamp01((ax - x0) / (x1 - x0)),
                               zone_y=_clamp01((ay - y0) / (y1 - y0)))


def place_blob(blob: Blob, calibration: Calibration) -> Blob:
    """blob with in_zone from the calibration zone. The blob must be in the zone's space, the mirrored
    display space of the keypoints: a blob source mirrors x as mirror_keypoints does."""
    return dataclasses.replace(blob, in_zone=_in(calibration.zone, blob.x, blob.y))


def _resample(motion: np.ndarray, width: int, height: int) -> np.ndarray:
    """Nearest-cell resample that keeps every lit cell: a shrinking axis ORs the source cells it covers."""
    rows = (np.arange(height) * motion.shape[0]) // height
    cols = (np.arange(width) * motion.shape[1]) // width
    grid = np.logical_or.reduceat(motion.astype(bool), rows, axis=0)
    return np.logical_or.reduceat(grid, cols, axis=1)


@dataclass(frozen=True, eq=False)
class Sensed:
    t: float                                     # seconds since runner start
    camera_t: float = 0.0                        # capture time of the newest camera frame, on the runner clock
    camera_fresh: bool = False                   # true on the tick a new camera frame arrived
    camera_seq: int = 0
    bodies: tuple[Body, ...] = ()                # tracked, stable ids, largest scale first
    player: Body | None = None                   # the locked player (spec 7.2), set by the runner
    player2: Body | None = None
    present: bool = False                        # someone is in the zone, with hysteresis, set by the runner
    blobs: tuple[Blob, ...] = ()                 # light sources, brightest first, at most 8
    motion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))   # bool (height, width)
    audio: Audio = field(default_factory=Audio)

    def __post_init__(self):
        # One grid is shared by every tick that holds it (degrade, with_motion), so the record keeps a
        # read-only view; the producer's own array stays writeable, but must not change after hand-over.
        # None (an old scenario record) means the empty grid.
        motion = np.zeros((0, 0), bool) if self.motion is None else np.asarray(self.motion, bool)
        motion = motion.view()
        motion.flags.writeable = False
        object.__setattr__(self, "motion", motion)

    def with_motion(self, size: tuple[int, int]) -> "Sensed":
        """This record with motion as a (height, width) grid for size (width, height).

        An empty grid becomes all False; a grid of another shape is resampled. Bodies are never
        rasterized into it.
        """
        w, h = size
        if self.motion.shape == (h, w):
            return self
        if self.motion.size == 0:
            return dataclasses.replace(self, motion=np.zeros((h, w), bool))
        return dataclasses.replace(self, motion=_resample(self.motion, w, h))
```

`arcade/sources/mirror.py`:

```python
"""The one place x is flipped (spec 5): after inference on both platforms, never swapping labels."""
from __future__ import annotations

from typing import Iterable

from arcade.sensed import Keypoint


def mirror_keypoints(keypoints: Iterable[Keypoint]) -> tuple[Keypoint, ...]:
    """x becomes 1 - x. Index order and confidence are kept, so RIGHT_WRIST is still the person's
    right wrist, and with the flip it lands on the right of the wall."""
    return tuple(Keypoint(1.0 - k.x, k.y, k.conf) for k in keypoints)


def mirror_box(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (1.0 - x1, y0, 1.0 - x0, y1)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_sensed.py tests/arcade/test_mirror.py`
Expected: `19 passed` (17, 2).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `153 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/sensed.py arcade/sources/mirror.py tests/arcade/test_sensed.py tests/arcade/test_mirror.py
git commit -m "feat(arcade): Sensed record per spec 5 with raise line, reach box, place() and mirroring (core Task 3)"
```

---

### Task 5: Actors, poses and exact event ticks (core plan Task 4 with its amendment, part 1)

**Files:**
- Create: `arcade/poses.py`, `arcade/sources/actors.py`
- Test: `tests/arcade/test_actors.py`

**Interfaces:**
- Consumes: from Task 4 `Keypoint`, `Body`, `Blob`, `Audio`, `Sensed`, `place`, `place_blob`, `MOTION_GRID`, the COCO constants; `Calibration`.
- Produces: `arcade.poses.POSES: dict[str, tuple[tuple[float, float], ...]]` with `stand`, `arms_up`, `t_pose` (17 `(dx, dy)` offsets in body heights from the hip centre). In `arcade/sources/actors.py`: `TICK = 1 / 30`; `MAX_BLOBS = 8`; `make_keypoints(cx, cy, h, left_up=False, right_up=False, conf=1.0) -> tuple[Keypoint, ...]` (hip centre at `(cx, cy)`); `body_box(keypoints) -> tuple`; `Person(x=0.5, y=0.55, height=0.6, id=None)` with chainable `walk(x_to, seconds, at=None)`, `raise_hand(at, seconds=0.5, hand="right")`, `both_hands_up(at, seconds)`, `wrist(hand, y_from, y_to, seconds, at=None)` (reach-box v units; `ValueError` for a hand other than `"left"` or `"right"`), `pose(name, at, seconds)` (`ValueError` for an unknown name, at call time), `jump(at, height=0.15, seconds=0.6)`, `leave(at)`, `arrive(at)`, and `present(t) -> bool`, `body_at(t, id) -> Body` (with `vx`, `vy`); type aliases `BlobScript`, `MotionScript`, `AudioScript`; `moving_blob(x0, y0, x1, y1, seconds, color=(255, 255, 255), size=0.03, start=0.0)`; `motion_rect(x0, y0, x1, y1, start, seconds) -> MotionScript` (a `(64, 128)` bool grid or `None`); `silence()`, `loud(level)`, `level_ramp(points)`, `claps(times)`, `tempo(bpm, start=0.0)`; `_fires(t, when)`; `scene(persons=(), blobs=(), motion=(), audio=None, ticks=90, calibration=None) -> Iterator[Sensed]`.

The six revision 2 tests are kept; `test_scene_assigns_ids_and_ticks`'s last line follows the amendment (motion all False, not `None`). The amendment's tests follow, then `test_scene_stamps_camera_and_places_bodies` and `test_person_velocity`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_actors.py`:

```python
import math

import numpy as np
import pytest

from arcade.poses import POSES
from arcade.sensed import LEFT_WRIST, NOSE, RIGHT_WRIST, Keypoint
from arcade.sources.actors import (TICK, Person, claps, level_ramp, loud, make_keypoints, motion_rect,
                                   moving_blob, scene, silence, tempo)


def test_make_keypoints_is_a_standing_figure():
    kps = make_keypoints(0.5, 0.5, 0.6)
    assert len(kps) == 17
    assert kps[NOSE].y < kps[LEFT_WRIST].y
    up = make_keypoints(0.5, 0.5, 0.6, right_up=True)
    assert up[RIGHT_WRIST].y < up[NOSE].y and up[LEFT_WRIST].y > up[NOSE].y


def test_person_walks_and_holds_position():
    p = Person(0.1).walk(0.9, seconds=2.0)
    assert p.body_at(0.0, 0).center[0] == pytest.approx(0.1, abs=0.02)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.5, abs=0.02)
    assert p.body_at(5.0, 0).center[0] == pytest.approx(0.9, abs=0.02)


def test_person_chained_walks_start_where_the_last_ended():
    p = Person(0.2).walk(0.6, 1.0).walk(0.2, 1.0)
    assert p.body_at(1.0, 0).center[0] == pytest.approx(0.6, abs=0.02)
    assert p.body_at(2.0, 0).center[0] == pytest.approx(0.2, abs=0.02)


def test_hands_and_jump_and_presence():
    p = Person().raise_hand(at=1.0, seconds=0.5).both_hands_up(at=3.0, seconds=1.0).jump(at=5.0, height=0.2)
    assert p.body_at(0.5, 0).raised_wrist is None
    assert p.body_at(1.2, 0).raised_wrist is not None and not p.body_at(1.2, 0).both_hands_up
    assert p.body_at(3.5, 0).both_hands_up
    standing = p.body_at(4.0, 0).nose.y
    assert p.body_at(5.3, 0).nose.y < standing - 0.1
    q = Person().leave(at=2.0)
    assert q.present(1.9) and not q.present(2.1)
    r = Person().arrive(at=2.0)
    assert not r.present(1.9) and r.present(2.1)


def test_scene_assigns_ids_and_ticks():
    frames = list(scene(persons=[Person(0.2), Person(0.8)], ticks=3))
    assert len(frames) == 3
    assert [b.id for b in frames[0].bodies] == [0, 1]
    assert frames[1].t == pytest.approx(TICK)
    assert frames[0].motion.shape == (64, 128) and not frames[0].motion.any()


def test_blob_and_audio_scripts():
    b = moving_blob(0.0, 0.5, 1.0, 0.5, seconds=2.0, color=(255, 0, 0))
    assert b(-0.1) is None and b(2.1) is None
    assert b(1.0).x == pytest.approx(0.5) and b(1.0).color == (255, 0, 0)
    assert silence()(3.0).level == 0.0
    c = claps([1.0, 2.0])
    hits = [i for i in range(90) if c(i * TICK).onset]
    assert len(hits) == 2
    t = tempo(120)
    beats = [i for i in range(90) if t(i * TICK).beat]
    assert beats == [0, 15, 30, 45, 60, 75]
    assert t(0.1).bpm == 120
    assert loud(0.9)(0.0).level == 0.9
    frames = list(scene(blobs=[b], audio=c, ticks=60))
    assert frames[30].blobs[0].x == pytest.approx(0.5, abs=0.01)
    assert frames[30].audio.onset


def test_tempo_128_exactly_one_beat_per_period():
    for bpm in (60, 90, 100, 120, 128, 140, 174, 200):
        script = tempo(bpm)
        beats = [i for i in range(1800) if script(i * TICK).beat]
        assert len(beats) == bpm, f"{bpm} bpm gave {len(beats)} beats in 60 s"
        gaps = np.diff(beats)
        assert gaps.min() >= math.floor(1800 / bpm), f"{bpm} bpm has a gap of {gaps.min()} ticks"
    late = tempo(128, start=2.0)
    first = next(i for i in range(1800) if late(i * TICK).beat)
    assert first == 60


def test_claps_fire_exactly_once():
    for k in range(300):
        when = k * 0.0123
        script = claps([when])
        hits = [i for i in range(120) if script(i * TICK).clap]
        assert hits == [math.ceil(when / TICK - 1e-6)], f"clap at {when} fired on ticks {hits}"
        assert all(script(i * TICK).onset == (i in hits) for i in range(120))


def test_wrist_ramp_in_reach_units():
    p = Person().wrist("right", 0.9, 0.1, seconds=2.0, at=1.0).wrist("right", 0.1, 0.5, seconds=1.0)
    assert p.body_at(0.5, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging before
    for t, v in ((1.0, 0.9), (2.0, 0.5), (2.9, 0.14), (3.5, 0.3)):
        body = p.body_at(t, 0)
        assert body.reach(body.right_wrist)[1] == pytest.approx(v, abs=1e-9), f"t={t}"
        assert body.left_wrist == make_keypoints(0.5, 0.55, 0.6)[LEFT_WRIST]
    assert p.body_at(2.9, 0).raised_wrist is not None and p.body_at(1.0, 0).raised_wrist is None
    assert p.body_at(4.0, 0).right_wrist == make_keypoints(0.5, 0.55, 0.6)[RIGHT_WRIST]   # hanging after
    with pytest.raises(ValueError, match="hand"):
        Person().wrist("middle", 0.0, 1.0, 1.0)


def test_wrist_works_for_a_body_partly_out_of_frame():
    low = Person(y=1.05).wrist("right", 0.5, 0.5, seconds=1.0).body_at(0.5, 0)       # hips below the frame
    assert low.hip_mid is None and low.right_wrist.conf == 1.0
    high = Person(y=0.3, height=0.6).jump(at=0.0, height=0.2).wrist("left", 0.0, 0.0, seconds=1.0)
    assert high.body_at(0.3, 0).left_wrist.conf == 0.0                               # above the frame: clamped
    inside = Person().wrist("right", 0.3, 0.3, seconds=1.0).body_at(0.5, 0)
    assert inside.reach(inside.right_wrist)[1] == pytest.approx(0.3, abs=1e-9)


def test_pose_from_table():
    assert set(POSES) >= {"stand", "t_pose", "arms_up"}
    assert all(len(offsets) == 17 for offsets in POSES.values())
    stand = tuple(Keypoint(0.5 + dx * 0.6, 0.55 + dy * 0.6) for dx, dy in POSES["stand"])
    assert make_keypoints(0.5, 0.55, 0.6) == stand
    p = Person(x=0.5, y=0.55, height=0.6).pose("t_pose", at=1.0, seconds=2.0)
    held = p.body_at(1.5, 0)
    for i, (dx, dy) in enumerate(POSES["t_pose"]):
        assert (held.keypoints[i].x, held.keypoints[i].y) == pytest.approx((0.5 + dx * 0.6, 0.55 + dy * 0.6))
    assert p.body_at(0.5, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert p.body_at(3.0, 0).keypoints == make_keypoints(0.5, 0.55, 0.6)
    assert Person().pose("arms_up", at=0.0, seconds=1.0).body_at(0.5, 0).both_hands_up


def test_unknown_pose_raises():
    with pytest.raises(ValueError, match="unknown pose 'dab'"):
        Person().pose("dab", at=0.0, seconds=1.0)


def test_motion_rect_grid():
    m = motion_rect(0.25, 0.5, 0.5, 1.0, start=1.0, seconds=1.0)
    assert m(0.9) is None and m(2.0) is None
    grid = m(1.5)
    assert grid.shape == (64, 128) and grid.dtype == bool
    assert grid[32:, 32:64].all() and grid.sum() == 32 * 32
    tiny = motion_rect(0.5, 0.5, 0.5, 0.5, start=0.0, seconds=1.0)(0.0)
    assert tiny.sum() == 1 and tiny[32, 64]
    frames = list(scene(motion=[m, motion_rect(0.0, 0.0, 0.1, 0.1, start=0.0, seconds=0.5)], ticks=60))
    assert frames[0].motion[:7, :13].all() and not frames[0].motion[32:, 32:64].any()
    assert frames[45].motion[32:, 32:64].all() and not frames[45].motion[:7, :13].any()
    assert not frames[20].motion.any()
    with pytest.raises(ValueError, match="shape"):
        list(scene(motion=[lambda t: np.zeros((4, 4), bool)], ticks=1))


def test_level_ramp_interpolates():
    ramp = level_ramp([(1.0, 0.0), (3.0, 1.0), (4.0, 0.5)])
    assert ramp(0.0).level == 0.0 and ramp(2.0).level == pytest.approx(0.5)
    assert ramp(3.5).level == pytest.approx(0.75) and ramp(9.0).level == 0.5
    assert ramp(2.0).level_smooth == ramp(2.0).peak == ramp(2.0).level
    with pytest.raises(ValueError):
        level_ramp([(2.0, 0.0), (1.0, 1.0)])
    with pytest.raises(ValueError):
        level_ramp([])


def test_scene_stamps_camera_and_places_bodies():
    big, small = Person(0.5, height=0.6), Person(0.1, height=0.3)
    frames = list(scene(persons=[small, big], blobs=[moving_blob(0.5, 0.5, 0.5, 0.5, 9.0)] * 10, ticks=3))
    f = frames[2]
    assert (f.camera_t, f.camera_fresh, f.camera_seq) == (f.t, True, 3)
    assert [b.id for b in f.bodies] == [1, 0]                   # largest scale first
    assert f.bodies[0].in_zone and not f.bodies[1].in_zone     # the small one is short and off to the side
    assert len(f.blobs) == 8 and all(b.in_zone for b in f.blobs)


def test_person_velocity():
    p = Person(0.1).walk(0.9, seconds=2.0).jump(at=3.0, height=0.2)
    assert p.body_at(1.0, 0).vx == pytest.approx(0.4)
    assert p.body_at(0.0, 0).vx == 0.0                          # causal: not yet moving at the start
    assert p.body_at(2.0, 0).vx == pytest.approx(0.4)           # the last tick of the walk still moved
    assert p.body_at(2.5, 0).vx == 0.0 and p.body_at(2.5, 0).vy == 0.0
    assert p.body_at(3.1, 0).vy < 0                             # rising
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_actors.py`
Expected: collection error, `ModuleNotFoundError: No module named 'arcade.poses'`.

- [ ] **Step 3: Implement**

`arcade/poses.py`:

```python
"""Named body poses for actors and the Copy Me game (spec 6.4, 8).

Each pose is 17 (dx, dy) offsets in COCO order, in units of body height, from the hip centre; y grows
downward. Only the offsets are stored so a pose fits any body size and position.
"""
from __future__ import annotations

_HEAD = ((0.0, -0.45), (-0.03, -0.47), (0.03, -0.47), (-0.06, -0.46), (0.06, -0.46))
_SHOULDERS = ((-0.12, -0.30), (0.12, -0.30))
_LEGS = ((-0.08, 0.0), (0.08, 0.0), (-0.08, 0.22), (0.08, 0.22), (-0.08, 0.45), (0.08, 0.45))


def _pose(left_elbow, right_elbow, left_wrist, right_wrist) -> tuple[tuple[float, float], ...]:
    return _HEAD + _SHOULDERS + (left_elbow, right_elbow, left_wrist, right_wrist) + _LEGS


POSES: dict[str, tuple[tuple[float, float], ...]] = {
    "stand": _pose((-0.16, -0.15), (0.16, -0.15), (-0.18, 0.0), (0.18, 0.0)),
    "arms_up": _pose((-0.16, -0.45), (0.16, -0.45), (-0.15, -0.60), (0.15, -0.60)),
    "t_pose": _pose((-0.24, -0.30), (0.24, -0.30), (-0.36, -0.30), (0.36, -0.30)),
}
```

`arcade/sources/actors.py`:

```python
"""Scripted synthetic input for tests and tools (spec 6.4). Deterministic: no randomness, no wall clock."""
from __future__ import annotations

import math
from typing import Callable, Iterable, Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.poses import POSES
from arcade.sensed import (LEFT_ELBOW, LEFT_HIP, LEFT_SHOULDER, LEFT_WRIST, MOTION_GRID, REACH_TOP_TORSOS,
                           RIGHT_ELBOW, RIGHT_HIP, RIGHT_SHOULDER, RIGHT_WRIST, Audio, Blob, Body, Keypoint,
                           Sensed, place, place_blob)

TICK = 1 / 30
MAX_BLOBS = 8
_ARMS = {"left": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), "right": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)}

Offsets = tuple[tuple[float, float], ...]


def _points(cx: float, cy: float, h: float, offsets: Offsets, conf: float = 1.0) -> list[Keypoint]:
    return [Keypoint(cx + dx * h, cy + dy * h, conf) for dx, dy in offsets]


def make_keypoints(cx: float, cy: float, h: float, left_up: bool = False, right_up: bool = False,
                   conf: float = 1.0) -> tuple[Keypoint, ...]:
    """A standing figure with its hip centre at (cx, cy) and total height h, coordinates normalized."""
    offsets = list(POSES["stand"])
    for hand, up in (("left", left_up), ("right", right_up)):
        if up:
            for i in _ARMS[hand][1:]:
                offsets[i] = POSES["arms_up"][i]
    return tuple(_points(cx, cy, h, tuple(offsets), conf))


def body_box(keypoints: Iterable[Keypoint]) -> tuple[float, float, float, float]:
    xs = [k.x for k in keypoints]
    ys = [k.y for k in keypoints]
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(xs) - 0.02), clamp(min(ys) - 0.02), clamp(max(xs) + 0.02), clamp(max(ys) + 0.02))


def _check_hand(hand: str) -> None:
    if hand not in _ARMS:
        raise ValueError(f"hand must be 'left' or 'right', got {hand!r}")


class Person:
    """A scripted body. Every method returns self so scripts chain. y is the hip height."""

    def __init__(self, x: float = 0.5, y: float = 0.55, height: float = 0.6, id: int | None = None):
        self.x0, self.y0, self.h, self.id = x, y, height, id
        self._moves: list[tuple[float, float, float, float]] = []
        self._hands: list[tuple[float, float, str]] = []
        self._wrists: list[tuple[float, float, str, float, float]] = []
        self._poses: list[tuple[float, float, str]] = []
        self._jumps: list[tuple[float, float, float]] = []
        self._arrive = 0.0
        self._leave: float | None = None

    def _x_at(self, t: float) -> float:
        x = self.x0
        for t0, t1, xa, xb in self._moves:
            if t >= t1:
                x = xb
            elif t0 <= t < t1:
                x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        return x

    def _lift_at(self, t: float) -> float:
        lift = 0.0
        for at, seconds, height in self._jumps:
            if at <= t < at + seconds:
                u = (t - at) / seconds
                lift = max(lift, height * 4 * u * (1 - u))
        return lift

    def walk(self, x_to: float, seconds: float, at: float | None = None) -> "Person":
        t0 = (self._moves[-1][1] if self._moves else 0.0) if at is None else at
        self._moves.append((t0, t0 + seconds, self._x_at(t0), x_to))
        return self

    def raise_hand(self, at: float, seconds: float = 0.5, hand: str = "right") -> "Person":
        _check_hand(hand)
        self._hands.append((at, at + seconds, hand))
        return self

    def both_hands_up(self, at: float, seconds: float) -> "Person":
        self._hands.append((at, at + seconds, "both"))
        return self

    def wrist(self, hand: str, y_from: float, y_to: float, seconds: float, at: float | None = None) -> "Person":
        """Move one wrist from y_from to y_to in reach-box v units (0 top, 1 hip height) over seconds.

        The wrist follows the script during [at, at + seconds) and hangs at the side outside it. With at
        None it starts where this hand's last wrist script ended, or at 0.
        """
        _check_hand(hand)
        if at is None:
            ends = [t1 for _, t1, h, _, _ in self._wrists if h == hand]
            at = ends[-1] if ends else 0.0
        self._wrists.append((at, at + seconds, hand, y_from, y_to))
        return self

    def pose(self, name: str, at: float, seconds: float) -> "Person":
        """Hold POSES[name] during [at, at + seconds)."""
        if name not in POSES:
            raise ValueError(f"unknown pose {name!r}; known: {', '.join(sorted(POSES))}")
        self._poses.append((at, at + seconds, name))
        return self

    def jump(self, at: float, height: float = 0.15, seconds: float = 0.6) -> "Person":
        self._jumps.append((at, seconds, height))
        return self

    def leave(self, at: float) -> "Person":
        self._leave = at
        return self

    def arrive(self, at: float) -> "Person":
        self._arrive = at
        return self

    def present(self, t: float) -> bool:
        return t >= self._arrive and (self._leave is None or t < self._leave)

    def _offsets_at(self, t: float) -> list[tuple[float, float]]:
        offsets = list(POSES["stand"])
        for t0, t1, name in self._poses:
            if t0 <= t < t1:
                offsets = list(POSES[name])
        for t0, t1, hand in self._hands:
            if t0 <= t < t1:
                for side in ("left", "right") if hand == "both" else (hand,):
                    for i in _ARMS[side][1:]:
                        offsets[i] = POSES["arms_up"][i]
        return offsets

    def _keypoints_at(self, t: float) -> list[Keypoint]:
        cx, cy = self._x_at(t), self.y0 - self._lift_at(t)
        offsets = self._offsets_at(t)
        pts = _points(cx, cy, self.h, tuple(offsets))
        for t0, t1, hand, y_from, y_to in self._wrists:
            if t0 <= t < t1:
                v = y_from + (y_to - y_from) * (t - t0) / (t1 - t0)
                shoulder, elbow, wrist = _ARMS[hand]
                # The reach box of sensed.Body.reach, from the pose offsets rather than the keypoints, so a
                # body partly out of frame (keypoints clamped with confidence 0) still has one.
                sx, sy = [(a + b) / 2 for a, b in zip(offsets[LEFT_SHOULDER], offsets[RIGHT_SHOULDER])]
                hx, hy = [(a + b) / 2 for a, b in zip(offsets[LEFT_HIP], offsets[RIGHT_HIP])]
                top = cy + (sy - REACH_TOP_TORSOS * math.hypot(sx - hx, sy - hy)) * self.h
                y = top + v * (cy + hy * self.h - top)
                pts[wrist] = Keypoint(pts[wrist].x, y)
                pts[elbow] = Keypoint((pts[shoulder].x + pts[wrist].x) / 2, (pts[shoulder].y + y) / 2)
        return pts

    def _anchor_at(self, t: float) -> tuple[float, float]:
        return self._x_at(t), self.y0 - self._lift_at(t)

    def body_at(self, t: float, id: int) -> Body:
        kps = tuple(self._keypoints_at(t))
        (x1, y1), (x0, y0) = self._anchor_at(t), self._anchor_at(t - TICK)
        return Body(self.id if self.id is not None else id, body_box(kps), kps,
                    vx=(x1 - x0) / TICK, vy=(y1 - y0) / TICK)


BlobScript = Callable[[float], Blob | None]
MotionScript = Callable[[float], np.ndarray | None]
AudioScript = Callable[[float], Audio]


def moving_blob(x0: float, y0: float, x1: float, y1: float, seconds: float,
                color: tuple[int, int, int] = (255, 255, 255), size: float = 0.03,
                start: float = 0.0) -> BlobScript:
    def script(t: float) -> Blob | None:
        if t < start or t > start + seconds:
            return None
        u = (t - start) / seconds if seconds > 0 else 1.0
        return Blob(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, size, color)
    return script


def motion_rect(x0: float, y0: float, x1: float, y1: float, start: float, seconds: float) -> MotionScript:
    """Motion cells lit over a rectangle during [start, start + seconds), on the 128x64 grid.

    The rectangle is in fractions of the motion grid, which covers the calibrated zone at the wall's
    aspect (spec 5), not in the camera coordinates Person(x) uses: x 0.5 is the middle of the zone.
    """
    w, h = MOTION_GRID
    c0, r0 = int(x0 * w), int(y0 * h)
    c1, r1 = max(c0 + 1, math.ceil(x1 * w)), max(r0 + 1, math.ceil(y1 * h))
    grid = np.zeros((h, w), bool)
    grid[max(r0, 0):min(r1, h), max(c0, 0):min(c1, w)] = True

    def script(t: float) -> np.ndarray | None:
        return grid.copy() if start <= t < start + seconds else None
    return script


def silence() -> AudioScript:
    return lambda t: Audio()


def loud(level: float) -> AudioScript:
    return lambda t: Audio(level=level, level_smooth=level, peak=level)


def level_ramp(points: list[tuple[float, float]]) -> AudioScript:
    """level (and level_smooth and peak) interpolated linearly between (t, level) points, ends held."""
    if not points or any(b[0] < a[0] for a, b in zip(points, points[1:])):
        raise ValueError(f"level_ramp needs (t, level) points in time order, got {points!r}")

    def script(t: float) -> Audio:
        level = points[0][1] if t <= points[0][0] else points[-1][1]
        for (ta, la), (tb, lb) in zip(points, points[1:]):
            if ta <= t < tb:
                level = la + (lb - la) * (t - ta) / (tb - ta)
                break
        return Audio(level=level, level_smooth=level, peak=level)
    return script


def _fires(t: float, when: float) -> bool:
    """Exactly one tick per event: the first tick at or after it."""
    return when - 1e-9 <= t < when + TICK - 1e-9


def claps(times: list[float]) -> AudioScript:
    def script(t: float) -> Audio:
        hit = any(_fires(t, c) for c in times)
        return Audio(level=0.8 if hit else 0.05, level_smooth=0.8 if hit else 0.05,
                     peak=1.0 if hit else 0.05, clap=hit, onset=hit)
    return script


def tempo(bpm: float, start: float = 0.0) -> AudioScript:
    period = 60.0 / bpm

    def script(t: float) -> Audio:
        n = math.floor((t - start) / period + 1e-9)
        hit = t >= start - 1e-9 and _fires(t, start + n * period)
        return Audio(level=0.6 if hit else 0.3, level_smooth=0.6 if hit else 0.3, peak=0.9 if hit else 0.3,
                     onset=hit, beat=hit, bpm=bpm)
    return script


def scene(persons: Iterable[Person] = (), blobs: Iterable[BlobScript] = (), motion: Iterable[MotionScript] = (),
          audio: AudioScript | None = None, ticks: int = 90,
          calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Sensed records at 30 Hz with a fresh camera frame every tick, as a perfect 30 fps camera gives.

    Bodies are placed against the calibration (the default one when None) and sorted largest scale
    first; blobs are placed, kept in script order (a Blob has no brightness to sort by) and capped at 8;
    motion scripts are ORed on the 128x64 grid.
    """
    persons, blobs, motion = list(persons), list(blobs), list(motion)
    audio = audio or silence()
    cal = calibration or Calibration()
    w, h = MOTION_GRID
    for i in range(ticks):
        t = i * TICK
        bodies = [place(p.body_at(t, idx), cal) for idx, p in enumerate(persons) if p.present(t)]
        bodies.sort(key=lambda b: -b.scale)
        lights = tuple(place_blob(b, cal) for b in (s(t) for s in blobs) if b is not None)[:MAX_BLOBS]
        grid = np.zeros((h, w), bool)
        for script in motion:
            cells = script(t)
            if cells is not None:
                if cells.shape != (h, w):
                    raise ValueError(f"a motion script returned shape {cells.shape}, not {(h, w)}")
                grid |= cells
        yield Sensed(t=t, camera_t=t, camera_fresh=True, camera_seq=i + 1, bodies=tuple(bodies),
                     blobs=lights, motion=grid, audio=audio(t))
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_actors.py`
Expected: `16 passed`.

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `169 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/poses.py arcade/sources/actors.py tests/arcade/test_actors.py
git commit -m "feat(arcade): actors with exact event ticks, wrist ramps, poses, motion and level scripts (core Task 4, part 1)"
```

---

### Task 6: degrade, REAL_NOISE and festival scenes (core plan Task 4 with its amendment, part 2)

**Files:**
- Modify: `arcade/sources/actors.py` (whole file below: Task 5's file with `import dataclasses` and `import zlib` added and the festival section appended)
- Test: `tests/arcade/test_festival.py`

**Interfaces:**
- Consumes: Task 5's actors; `place` and `Calibration`.
- Produces: `crowd(n, start=0.0) -> list[Person]` (0.3 tall, ids 100 + i, out of zone); `headlamps(period=20.0, cross_seconds=6.0) -> tuple[BlobScript, BlobScript]` (above the default zone); `camp_kick(bpm=125.0, start=0.0) -> AudioScript`; `wind(gust_every=2.7) -> AudioScript`; `shake(start, seconds, jitter=0.03, calibration=None) -> Callable[[Iterable[Sensed]], Iterator[Sensed]]`; `degrade(frames, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01, calibration=None) -> Iterator[Sensed]` (`ValueError` "degrade needs ..." for bad parameters, and for a stream whose frame i does not have `t = i * TICK`); `REAL_NOISE = {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}`, used as `degrade(scene(...), **REAL_NOISE)`.

- [ ] **Step 1: Write the failing tests**

`tests/arcade/test_festival.py`:

```python
import inspect
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from arcade.calibration import Calibration
from arcade.sensed import MIN_CONF
from arcade.sources.actors import (REAL_NOISE, TICK, Person, camp_kick, claps, crowd, degrade, headlamps,
                                   motion_rect, scene, shake, wind)

ROOT = Path(__file__).resolve().parents[2]

DIGEST = """
import hashlib
from arcade.sources.actors import Person, crowd, degrade, scene
frames = degrade(scene(persons=[Person(0.3).walk(0.7, 2.0).raise_hand(at=1.0), *crowd(3)], ticks=90))
h = hashlib.sha256()
for f in frames:
    h.update(repr((f.camera_seq, f.camera_fresh, [(b.id, b.keypoints, b.in_zone) for b in f.bodies])).encode())
digest = h.hexdigest()
"""


def walker():
    return Person(0.2).walk(0.8, 3.0)


def test_degrade_samples_holds_and_delays():
    source = list(scene(persons=[walker()], audio=claps([0.2]), ticks=90))
    frames = list(degrade(iter(source)))
    assert len(frames) == 90
    fresh = [i for i, f in enumerate(frames) if f.camera_fresh]
    assert fresh == list(range(5, 90, 3)) and len(fresh) == 29        # 10 fps, first visible at 0.15 s
    for f in frames[:5]:
        assert f.bodies == () and f.camera_seq == 0 and f.motion.size == 0
    for i, f in enumerate(frames[5:], start=5):
        assert f.t == source[i].t
        assert 0.15 - 1e-9 <= f.t - f.camera_t < 0.25, f"tick {i}: camera_t {f.camera_t}"
        assert f.camera_seq == (i - 5) // 3 + 1
    assert frames[6].bodies == frames[5].bodies and frames[7].bodies == frames[5].bodies
    assert frames[8].bodies != frames[5].bodies
    assert frames[6].audio.clap and not frames[6].camera_fresh     # audio is not delayed
    clean = list(degrade(iter(source), keypoint_dropout=0.0, jitter=0.0))
    assert clean[8].bodies == source[3].bodies                       # capture 1 is the scene at 0.1 s


def test_degrade_without_noise_is_the_scene():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 0.5, 0.5, 0.0, 1.0)], ticks=40))
    frames = list(degrade(iter(source), fps=30, latency=0.0, keypoint_dropout=0.0, jitter=0.0))
    for i, (f, s) in enumerate(zip(frames, source)):
        assert f.bodies == s.bodies and f.camera_fresh and f.camera_seq == i + 1
        assert f.camera_t == s.t and np.array_equal(f.motion, s.motion)


def test_degrade_drops_and_jitters_at_the_given_rates():
    source = list(scene(persons=[walker(), Person(0.7, id=7)], ticks=300))
    frames = [f for f in degrade(iter(source), latency=0.0) if f.camera_fresh]
    dropped = total = 0
    for f in frames:
        truth = source[round(f.camera_t / TICK)]
        for b, t in zip(f.bodies, truth.bodies):
            for k, kt in zip(b.keypoints, t.keypoints):
                total += 1
                dropped += k.conf == 0.0
                assert abs(k.x - kt.x) <= 0.01 + 1e-9 and abs(k.y - kt.y) <= 0.01 + 1e-9
    assert total == 100 * 2 * 17
    assert 0.10 <= dropped / total <= 0.20, f"dropped {dropped} of {total}"


def test_degrade_rejects_bad_parameters():
    for bad in ({"fps": 0}, {"latency": -0.1}, {"keypoint_dropout": 1.5}, {"jitter": -0.01},
                {"fps": float("nan")}):
        with pytest.raises(ValueError, match="degrade needs"):
            list(degrade(scene(ticks=1), **bad))


def test_degrade_refuses_a_stream_that_does_not_start_at_zero():
    source = list(scene(persons=[walker()], ticks=60))
    with pytest.raises(ValueError, match="starts at t=0; frame 0 has t=1.0"):
        list(degrade(iter(source[30:])))
    with pytest.raises(ValueError, match="frame 2"):
        list(degrade(iter(source[:2] + source[3:])))


def test_still_player_keeps_cursor_and_zone_steady_under_spec_noise():
    source = scene(persons=[Person().raise_hand(at=0.0, seconds=99.0)], ticks=900)
    noise = degrade(source, fps=10, latency=0.15, keypoint_dropout=0.15, jitter=0.01)   # spec 6.4 literals
    captures = [f.bodies[0] for f in noise if f.camera_fresh]
    assert len(captures) == 299
    u = np.array([b.cursor[0] for b in captures if b.right_wrist.conf >= MIN_CONF])
    zone_x = np.array([b.zone_x for b in captures])
    assert np.median(u) == pytest.approx(0.71, abs=0.02) and np.median(zone_x) == pytest.approx(0.5, abs=0.01)
    # A dropped shoulder, or a dropped shoulder and hip, once moved the centre half a width (u by 0.15).
    assert np.mean(np.abs(u - np.median(u)) > 0.1) <= 0.02
    assert np.mean(np.abs(zone_x - np.median(zone_x)) > 0.05) <= 0.02


def test_degrade_is_deterministic():
    runs = []
    for _ in range(2):
        ns: dict = {}
        exec(DIGEST, ns)
        runs.append(ns["digest"])
    for seed in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run([sys.executable, "-c", DIGEST + "print(digest)"], cwd=ROOT, env=env,
                             capture_output=True, text=True, check=True)
        runs.append(out.stdout.strip())
    assert len(set(runs)) == 1, runs


def test_real_noise_is_a_degrade_setting():
    assert set(REAL_NOISE) == {"fps", "latency", "keypoint_dropout", "jitter"}     # values are refit (spec 9.5)
    assert len(list(degrade(scene(persons=[walker()], ticks=30), **REAL_NOISE))) == 30
    names = ("fps", "latency", "keypoint_dropout", "jitter")
    defaults = {n: inspect.signature(degrade).parameters[n].default for n in names}
    assert defaults == {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}   # spec 6.4


def test_crowd_is_out_of_zone():
    people = crowd(6)
    assert len(people) == 6 and len({p.id for p in people}) == 6
    raised = 0
    for f in scene(persons=[Person(0.5), *people], ticks=300):
        assert len(f.bodies) == 7
        assert [b.in_zone for b in f.bodies] == [True] + [False] * 6
        assert f.bodies[0].id == 0                                    # the player is the largest
        raised += sum(b.raised_wrist is not None for b in f.bodies[1:])
    assert raised > 0                                                 # the crowd waves


def test_camp_kick_has_onsets_but_no_claps():
    kick = camp_kick(125)
    frames = [kick(i * TICK) for i in range(1800)]
    assert sum(a.onset for a in frames) == 125 and sum(a.beat for a in frames) == 125
    assert not any(a.clap for a in frames)
    assert all(a.voice == 0.0 and a.voice_db == a.floor_db and a.bpm == 125 for a in frames)


def test_wind_never_claps():
    frames = [wind()(i * TICK) for i in range(1800)]
    assert not any(a.clap or a.beat for a in frames)
    assert 20 <= sum(a.onset for a in frames) <= 25
    assert all(a.voice < 0.1 for a in frames) and max(a.level for a in frames) > 0.45


def test_headlamps_are_out_of_zone():
    frames = list(scene(blobs=headlamps(), ticks=1800))
    assert all(f.blobs and not any(b.in_zone for b in f.blobs) for f in frames)
    crossing = [i for i, f in enumerate(frames) if len(f.blobs) == 2]
    assert crossing and crossing[0] == 0 and 600 in crossing and 300 not in crossing


def test_shake_empties_motion_and_jitters():
    source = list(scene(persons=[walker()], motion=[motion_rect(0.0, 0.0, 1.0, 1.0, 0.0, 9.0)], ticks=90))
    shaken = list(shake(1.0, 1.0)(iter(source)))
    assert len(shaken) == 90
    for i, (f, s) in enumerate(zip(shaken, source)):
        if 30 <= i < 60:
            assert f.motion.size == 0
            for k, ks in zip(f.bodies[0].keypoints, s.bodies[0].keypoints):
                assert abs(k.x - ks.x) <= 0.03 + 1e-9 and abs(k.y - ks.y) <= 0.03 + 1e-9 and k.conf == ks.conf
            assert f.bodies[0].keypoints != s.bodies[0].keypoints
        else:
            assert f is s
    first = list(shake(1.0, 1.0)(iter(source)))
    assert all(a.bodies == b.bodies for a, b in zip(first, shaken))


def test_shake_places_against_the_scene_calibration():
    right = Calibration(zone=(0.5, 0.2, 1.0, 0.8))
    source = list(scene(persons=[Person(0.85)], ticks=60, calibration=right))
    assert all(f.bodies[0].in_zone for f in source)
    shaken = list(shake(0.5, 1.0, calibration=right)(iter(source)))
    assert all(f.bodies[0].in_zone for f in shaken)
    assert not list(shake(0.5, 1.0)(iter(source)))[30].bodies[0].in_zone     # the default zone ends at 0.8
```

- [ ] **Step 2: Run them to verify they fail**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_festival.py`
Expected: collection error, `ImportError: cannot import name 'REAL_NOISE' from 'arcade.sources.actors'`.

- [ ] **Step 3: Implement**

`arcade/sources/actors.py`:

```python
"""Scripted synthetic input for tests and tools (spec 6.4). Deterministic: no randomness, no wall clock."""
from __future__ import annotations

import dataclasses
import math
import zlib
from typing import Callable, Iterable, Iterator

import numpy as np

from arcade.calibration import Calibration
from arcade.poses import POSES
from arcade.sensed import (LEFT_ELBOW, LEFT_HIP, LEFT_SHOULDER, LEFT_WRIST, MOTION_GRID, REACH_TOP_TORSOS,
                           RIGHT_ELBOW, RIGHT_HIP, RIGHT_SHOULDER, RIGHT_WRIST, Audio, Blob, Body, Keypoint,
                           Sensed, place, place_blob)

TICK = 1 / 30
MAX_BLOBS = 8
_ARMS = {"left": (LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), "right": (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)}

Offsets = tuple[tuple[float, float], ...]


def _points(cx: float, cy: float, h: float, offsets: Offsets, conf: float = 1.0) -> list[Keypoint]:
    return [Keypoint(cx + dx * h, cy + dy * h, conf) for dx, dy in offsets]


def make_keypoints(cx: float, cy: float, h: float, left_up: bool = False, right_up: bool = False,
                   conf: float = 1.0) -> tuple[Keypoint, ...]:
    """A standing figure with its hip centre at (cx, cy) and total height h, coordinates normalized."""
    offsets = list(POSES["stand"])
    for hand, up in (("left", left_up), ("right", right_up)):
        if up:
            for i in _ARMS[hand][1:]:
                offsets[i] = POSES["arms_up"][i]
    return tuple(_points(cx, cy, h, tuple(offsets), conf))


def body_box(keypoints: Iterable[Keypoint]) -> tuple[float, float, float, float]:
    xs = [k.x for k in keypoints]
    ys = [k.y for k in keypoints]
    clamp = lambda v: min(1.0, max(0.0, v))
    return (clamp(min(xs) - 0.02), clamp(min(ys) - 0.02), clamp(max(xs) + 0.02), clamp(max(ys) + 0.02))


def _check_hand(hand: str) -> None:
    if hand not in _ARMS:
        raise ValueError(f"hand must be 'left' or 'right', got {hand!r}")


class Person:
    """A scripted body. Every method returns self so scripts chain. y is the hip height."""

    def __init__(self, x: float = 0.5, y: float = 0.55, height: float = 0.6, id: int | None = None):
        self.x0, self.y0, self.h, self.id = x, y, height, id
        self._moves: list[tuple[float, float, float, float]] = []
        self._hands: list[tuple[float, float, str]] = []
        self._wrists: list[tuple[float, float, str, float, float]] = []
        self._poses: list[tuple[float, float, str]] = []
        self._jumps: list[tuple[float, float, float]] = []
        self._arrive = 0.0
        self._leave: float | None = None

    def _x_at(self, t: float) -> float:
        x = self.x0
        for t0, t1, xa, xb in self._moves:
            if t >= t1:
                x = xb
            elif t0 <= t < t1:
                x = xa + (xb - xa) * (t - t0) / (t1 - t0)
        return x

    def _lift_at(self, t: float) -> float:
        lift = 0.0
        for at, seconds, height in self._jumps:
            if at <= t < at + seconds:
                u = (t - at) / seconds
                lift = max(lift, height * 4 * u * (1 - u))
        return lift

    def walk(self, x_to: float, seconds: float, at: float | None = None) -> "Person":
        t0 = (self._moves[-1][1] if self._moves else 0.0) if at is None else at
        self._moves.append((t0, t0 + seconds, self._x_at(t0), x_to))
        return self

    def raise_hand(self, at: float, seconds: float = 0.5, hand: str = "right") -> "Person":
        _check_hand(hand)
        self._hands.append((at, at + seconds, hand))
        return self

    def both_hands_up(self, at: float, seconds: float) -> "Person":
        self._hands.append((at, at + seconds, "both"))
        return self

    def wrist(self, hand: str, y_from: float, y_to: float, seconds: float, at: float | None = None) -> "Person":
        """Move one wrist from y_from to y_to in reach-box v units (0 top, 1 hip height) over seconds.

        The wrist follows the script during [at, at + seconds) and hangs at the side outside it. With at
        None it starts where this hand's last wrist script ended, or at 0.
        """
        _check_hand(hand)
        if at is None:
            ends = [t1 for _, t1, h, _, _ in self._wrists if h == hand]
            at = ends[-1] if ends else 0.0
        self._wrists.append((at, at + seconds, hand, y_from, y_to))
        return self

    def pose(self, name: str, at: float, seconds: float) -> "Person":
        """Hold POSES[name] during [at, at + seconds)."""
        if name not in POSES:
            raise ValueError(f"unknown pose {name!r}; known: {', '.join(sorted(POSES))}")
        self._poses.append((at, at + seconds, name))
        return self

    def jump(self, at: float, height: float = 0.15, seconds: float = 0.6) -> "Person":
        self._jumps.append((at, seconds, height))
        return self

    def leave(self, at: float) -> "Person":
        self._leave = at
        return self

    def arrive(self, at: float) -> "Person":
        self._arrive = at
        return self

    def present(self, t: float) -> bool:
        return t >= self._arrive and (self._leave is None or t < self._leave)

    def _offsets_at(self, t: float) -> list[tuple[float, float]]:
        offsets = list(POSES["stand"])
        for t0, t1, name in self._poses:
            if t0 <= t < t1:
                offsets = list(POSES[name])
        for t0, t1, hand in self._hands:
            if t0 <= t < t1:
                for side in ("left", "right") if hand == "both" else (hand,):
                    for i in _ARMS[side][1:]:
                        offsets[i] = POSES["arms_up"][i]
        return offsets

    def _keypoints_at(self, t: float) -> list[Keypoint]:
        cx, cy = self._x_at(t), self.y0 - self._lift_at(t)
        offsets = self._offsets_at(t)
        pts = _points(cx, cy, self.h, tuple(offsets))
        for t0, t1, hand, y_from, y_to in self._wrists:
            if t0 <= t < t1:
                v = y_from + (y_to - y_from) * (t - t0) / (t1 - t0)
                shoulder, elbow, wrist = _ARMS[hand]
                # The reach box of sensed.Body.reach, from the pose offsets rather than the keypoints, so a
                # body partly out of frame (keypoints clamped with confidence 0) still has one.
                sx, sy = [(a + b) / 2 for a, b in zip(offsets[LEFT_SHOULDER], offsets[RIGHT_SHOULDER])]
                hx, hy = [(a + b) / 2 for a, b in zip(offsets[LEFT_HIP], offsets[RIGHT_HIP])]
                top = cy + (sy - REACH_TOP_TORSOS * math.hypot(sx - hx, sy - hy)) * self.h
                y = top + v * (cy + hy * self.h - top)
                pts[wrist] = Keypoint(pts[wrist].x, y)
                pts[elbow] = Keypoint((pts[shoulder].x + pts[wrist].x) / 2, (pts[shoulder].y + y) / 2)
        return pts

    def _anchor_at(self, t: float) -> tuple[float, float]:
        return self._x_at(t), self.y0 - self._lift_at(t)

    def body_at(self, t: float, id: int) -> Body:
        kps = tuple(self._keypoints_at(t))
        (x1, y1), (x0, y0) = self._anchor_at(t), self._anchor_at(t - TICK)
        return Body(self.id if self.id is not None else id, body_box(kps), kps,
                    vx=(x1 - x0) / TICK, vy=(y1 - y0) / TICK)


BlobScript = Callable[[float], Blob | None]
MotionScript = Callable[[float], np.ndarray | None]
AudioScript = Callable[[float], Audio]


def moving_blob(x0: float, y0: float, x1: float, y1: float, seconds: float,
                color: tuple[int, int, int] = (255, 255, 255), size: float = 0.03,
                start: float = 0.0) -> BlobScript:
    def script(t: float) -> Blob | None:
        if t < start or t > start + seconds:
            return None
        u = (t - start) / seconds if seconds > 0 else 1.0
        return Blob(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, size, color)
    return script


def motion_rect(x0: float, y0: float, x1: float, y1: float, start: float, seconds: float) -> MotionScript:
    """Motion cells lit over a rectangle during [start, start + seconds), on the 128x64 grid.

    The rectangle is in fractions of the motion grid, which covers the calibrated zone at the wall's
    aspect (spec 5), not in the camera coordinates Person(x) uses: x 0.5 is the middle of the zone.
    """
    w, h = MOTION_GRID
    c0, r0 = int(x0 * w), int(y0 * h)
    c1, r1 = max(c0 + 1, math.ceil(x1 * w)), max(r0 + 1, math.ceil(y1 * h))
    grid = np.zeros((h, w), bool)
    grid[max(r0, 0):min(r1, h), max(c0, 0):min(c1, w)] = True

    def script(t: float) -> np.ndarray | None:
        return grid.copy() if start <= t < start + seconds else None
    return script


def silence() -> AudioScript:
    return lambda t: Audio()


def loud(level: float) -> AudioScript:
    return lambda t: Audio(level=level, level_smooth=level, peak=level)


def level_ramp(points: list[tuple[float, float]]) -> AudioScript:
    """level (and level_smooth and peak) interpolated linearly between (t, level) points, ends held."""
    if not points or any(b[0] < a[0] for a, b in zip(points, points[1:])):
        raise ValueError(f"level_ramp needs (t, level) points in time order, got {points!r}")

    def script(t: float) -> Audio:
        level = points[0][1] if t <= points[0][0] else points[-1][1]
        for (ta, la), (tb, lb) in zip(points, points[1:]):
            if ta <= t < tb:
                level = la + (lb - la) * (t - ta) / (tb - ta)
                break
        return Audio(level=level, level_smooth=level, peak=level)
    return script


def _fires(t: float, when: float) -> bool:
    """Exactly one tick per event: the first tick at or after it."""
    return when - 1e-9 <= t < when + TICK - 1e-9


def claps(times: list[float]) -> AudioScript:
    def script(t: float) -> Audio:
        hit = any(_fires(t, c) for c in times)
        return Audio(level=0.8 if hit else 0.05, level_smooth=0.8 if hit else 0.05,
                     peak=1.0 if hit else 0.05, clap=hit, onset=hit)
    return script


def tempo(bpm: float, start: float = 0.0) -> AudioScript:
    period = 60.0 / bpm

    def script(t: float) -> Audio:
        n = math.floor((t - start) / period + 1e-9)
        hit = t >= start - 1e-9 and _fires(t, start + n * period)
        return Audio(level=0.6 if hit else 0.3, level_smooth=0.6 if hit else 0.3, peak=0.9 if hit else 0.3,
                     onset=hit, beat=hit, bpm=bpm)
    return script


def scene(persons: Iterable[Person] = (), blobs: Iterable[BlobScript] = (), motion: Iterable[MotionScript] = (),
          audio: AudioScript | None = None, ticks: int = 90,
          calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Sensed records at 30 Hz with a fresh camera frame every tick, as a perfect 30 fps camera gives.

    Bodies are placed against the calibration (the default one when None) and sorted largest scale
    first; blobs are placed, kept in script order (a Blob has no brightness to sort by) and capped at 8;
    motion scripts are ORed on the 128x64 grid.
    """
    persons, blobs, motion = list(persons), list(blobs), list(motion)
    audio = audio or silence()
    cal = calibration or Calibration()
    w, h = MOTION_GRID
    for i in range(ticks):
        t = i * TICK
        bodies = [place(p.body_at(t, idx), cal) for idx, p in enumerate(persons) if p.present(t)]
        bodies.sort(key=lambda b: -b.scale)
        lights = tuple(place_blob(b, cal) for b in (s(t) for s in blobs) if b is not None)[:MAX_BLOBS]
        grid = np.zeros((h, w), bool)
        for script in motion:
            cells = script(t)
            if cells is not None:
                if cells.shape != (h, w):
                    raise ValueError(f"a motion script returned shape {cells.shape}, not {(h, w)}")
                grid |= cells
        yield Sensed(t=t, camera_t=t, camera_fresh=True, camera_seq=i + 1, bodies=tuple(bodies),
                     blobs=lights, motion=grid, audio=audio(t))


# Festival scenes (spec 6.4, 9.3): what a burn puts in front of the camera and microphone.

def crowd(n: int, start: float = 0.0) -> list[Person]:
    """n small people behind the player: 0.3 tall, so under the zone's min_height, drifting and waving."""
    people = []
    for i in range(n):
        x = (i + 0.5) / n
        p = Person(x, y=0.35, height=0.3, id=100 + i)
        p.walk(min(1.0, x + 0.04), 3.0, at=start + 0.4 * i).walk(x, 3.0)
        p.raise_hand(at=start + 1.0 + 0.7 * i, seconds=0.8, hand="left" if i % 2 else "right")
        people.append(p)
    return people


def headlamps(period: float = 20.0, cross_seconds: float = 6.0) -> tuple[BlobScript, BlobScript]:
    """A headlamp parked at the top left, and one crossing the top of the frame every period seconds.

    Both stay above the default zone (y under 0.2), so games never see them."""
    parked = lambda t: Blob(0.05, 0.15, 0.02, (255, 244, 214))

    def crossing(t: float) -> Blob | None:
        u = (t % period) / cross_seconds
        return Blob(-0.05 + 1.1 * u, 0.1, 0.02, (255, 250, 235)) if u < 1.0 else None
    return parked, crossing


def camp_kick(bpm: float = 125.0, start: float = 0.0) -> AudioScript:
    """A neighbouring camp's kick drum: broadband onsets on the beat, no claps, voice at the floor."""
    beat = tempo(bpm, start)

    def script(t: float) -> Audio:
        hit = beat(t).beat
        level = 0.7 if hit else 0.45
        return Audio(level=level, level_smooth=0.55, peak=0.95 if hit else 0.5, voice_db=-42.0,
                     floor_db=-42.0, voice=0.0, clap=False, onset=hit, beat=hit, bpm=bpm)
    return script


def wind(gust_every: float = 2.7) -> AudioScript:
    """Wind on the microphone: a slow swell with an onset at each gust peak, never a clap or a voice."""
    def script(t: float) -> Audio:
        level = 0.3 + 0.2 * math.sin(2 * math.pi * t / 7.0) ** 2
        gust = _fires(t, gust_every * math.floor(t / gust_every + 1e-9))
        return Audio(level=level, level_smooth=level, peak=min(1.0, level + (0.3 if gust else 0.05)),
                     voice_db=-58.0, floor_db=-60.0, voice=2.0 / 30, onset=gust)
    return script


def _unit(tag: str, tick: int, body_id: int, joint: int) -> float:
    """A fixed pseudo-random number in [0, 1) for this tag, tick, body and joint (never hash() or random)."""
    return zlib.crc32(f"{tag}:{tick}:{body_id}:{joint}".encode()) / 2**32


def _noisy(body: Body, tick: int, tag: str, dropout: float, jitter: float) -> Body:
    pts = []
    for j, k in enumerate(body.keypoints):
        x = k.x + (2 * _unit(tag + "x", tick, body.id, j) - 1) * jitter
        y = k.y + (2 * _unit(tag + "y", tick, body.id, j) - 1) * jitter
        conf = 0.0 if _unit(tag + "drop", tick, body.id, j) < dropout else k.conf
        pts.append(Keypoint(x, y, conf))
    return dataclasses.replace(body, keypoints=tuple(pts))


def shake(start: float, seconds: float, jitter: float = 0.03,
          calibration: Calibration | None = None) -> Callable[[Iterable[Sensed]], Iterator[Sensed]]:
    """What the gated camera source yields while the wall or pole shakes: an empty motion grid and
    keypoints jittered by up to 0.03, during [start, start + seconds). Wraps a scene; pass the
    scene's calibration so jittered bodies are placed against the same zone."""
    def wrap(frames: Iterable[Sensed]) -> Iterator[Sensed]:
        cal = calibration or Calibration()
        for i, s in enumerate(frames):
            if start - 1e-9 <= s.t < start + seconds - 1e-9:
                bodies = tuple(place(_noisy(b, i, "shake", 0.0, jitter), cal) for b in s.bodies)
                s = dataclasses.replace(s, bodies=bodies, motion=np.zeros((0, 0), bool))
            yield s
    return wrap


def degrade(frames: Iterable[Sensed], fps: float = 10, latency: float = 0.15, keypoint_dropout: float = 0.15,
            jitter: float = 0.01, calibration: Calibration | None = None) -> Iterator[Sensed]:
    """Perfect 30 Hz input turned into what the Pi camera gives (spec 6.4).

    The camera captures at fps; capture k is taken at k / fps from the scene's frame at or before that
    time and becomes visible latency seconds later, then holds until the next one. Each keypoint of a
    capture is dropped (confidence 0) with probability keypoint_dropout and moved by up to jitter,
    keyed by zlib.crc32 of (tick, body id, joint). Audio and t stay on the current tick.
    """
    if not fps > 0 or not latency >= 0 or not 0 <= keypoint_dropout <= 1 or not jitter >= 0:
        raise ValueError(f"degrade needs fps > 0, latency >= 0, dropout in [0, 1], jitter >= 0; got "
                         f"{fps}, {latency}, {keypoint_dropout}, {jitter}")
    cal = calibration or Calibration()
    seen: dict[int, Sensed] = {}             # scene frames not yet captured, by tick
    held: tuple[int, Sensed] | None = None
    for i, s in enumerate(frames):
        if abs(s.t - i * TICK) > 1e-6:   # a sliced or offset stream would silently lose its latency
            raise ValueError(f"degrade needs a 30 Hz scene that starts at t=0; frame {i} has t={s.t}")
        seen[i] = s
        k = math.floor((s.t - latency) * fps + 1e-9)
        if k < 0:
            yield dataclasses.replace(s, camera_t=0.0, camera_fresh=False, camera_seq=0, bodies=(), blobs=(),
                                      motion=np.zeros((0, 0), bool))
            continue
        fresh = held is None or held[0] != k
        if fresh:
            src = min(math.floor(k / fps / TICK + 1e-9), i)
            shot = seen[src]
            for old in [j for j in seen if j < src]:
                del seen[old]
            bodies = tuple(place(_noisy(b, src, "degrade", keypoint_dropout, jitter), cal) for b in shot.bodies)
            held = (k, dataclasses.replace(shot, bodies=bodies))
        shot = held[1]
        yield dataclasses.replace(s, camera_t=shot.t, camera_fresh=fresh, camera_seq=k + 1, bodies=shot.bodies,
                                  blobs=shot.blobs, motion=shot.motion)


REAL_NOISE = {"fps": 10, "latency": 0.15, "keypoint_dropout": 0.15, "jitter": 0.01}   # refit from the real fixtures (spec 9.5)
```

- [ ] **Step 4: Run the tests**

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs tests/arcade/test_festival.py tests/arcade/test_actors.py`
Expected: `30 passed` (14, 16).

Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs`
Expected: `183 passed`, no skips.

- [ ] **Step 5: Commit**

```bash
git add arcade/sources/actors.py tests/arcade/test_festival.py
git commit -m "feat(arcade): degrade, REAL_NOISE and festival scenes (core Task 4, part 2)"
```

---

## Iteration verify

Run inline by the operator after Task 6, from the repo root.

1. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest --collect-only -q | tail -1` prints `183 tests collected` (66 before this iteration; the count rises at every task: 85, 123, 134, 153, 169, 183).
2. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs` prints `183 passed` with **0 skipped**. Per module: `tests/arcade/test_actors.py` 16, `tests/arcade/test_calibration.py` 23, `tests/arcade/test_config.py` 42, `tests/arcade/test_doctor.py` 10, `tests/arcade/test_festival.py` 14, `tests/arcade/test_mirror.py` 2, `tests/arcade/test_sensed.py` 17, `tests/test_colorlight.py` 29, `tests/test_config.py` 5, `tests/test_ddp.py` 8, `tests/test_display.py` 4, `tests/test_font.py` 7, `tests/test_gitignore.py` 6.
3. No existing assert weakened: `git diff 7697d01 -- tests/ | grep '^-[^-]'` prints exactly five lines: `from arcade.main import doctor, main` (`tests/arcade/test_doctor.py`); and in `tests/test_colorlight.py` the two lines of the old `from show.display.colorlight import (DST_MAC, ...` import, the old `@pytest.mark.parametrize("width,height", [(128, 32), (64, 64), (512, 4)])`, and the old `    def __init__(self, width, height, iface, sock=None):` of the `Recorder` helper. None is an assert. Anything else is a Deviation.
4. `.venv/bin/python -m arcade doctor --require pose; echo "exit $?"` prints `pose    ok ...` and `exit 0`; with `--timeout 0.01` it prints `did not finish within 0.01 s` and `exit 1`; `.venv/bin/python -m arcade doctor --require ""; echo "exit $?"` prints `names no source` and `exit 2`.
5. `git check-ignore --no-index -v tests/arcade/fixtures/data/x.jsonl.gz; echo "exit $?"` prints only `exit 1`.
6. `.venv/bin/python -c "import sys, arcade.sources.actors, arcade.sensed; print(sorted({'cv2', 'mediapipe', 'sounddevice', 'pygame'} & set(sys.modules)))"` prints `[]`.
7. `git log --oneline -6` shows the six commit messages above, in order, and `git status --short` is clean apart from `docs/superpowers/workflow/` files.
