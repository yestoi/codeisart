# The arcade on the wall: the essentials

Date: 2026-10-02. Owner: Trey. Status: draft, for the owner's review.

## 1. Goal

Show the arcade's whole experience on the real wall, from the Pi 5, through the Raspberry Pi AI Camera, today
or tomorrow, with the owner standing by it: attract, walk up, play, result, back to attract. One game feeling
right is enough; the loop around it must be whole.

What the owner said (2026-10-02): hold iteration 22's plan; "do it proper but only the essentials to show a
complete vision. Even if it's just one game working but the full experience attract/play/etc."; the camera is
the AI Camera (IMX500); the attract is the spec's full director; it is started by hand and the owner is there.

Assumed, not said: the wall is the 2 x 2 128x64 one and no other (Q82); Paint, Tug and the project skills wait.

## 2. Where it stands

- Eight games are on main (Copy Me, Pong, Quick Draw, Dodge, Flap, Swat, Jump, Freeze). None has been played
  on the wall. Only Pong has been played at all (the Mac's webcam, 2026-09-28).
- The small lobby gives the loop in its least form: a dim title, the mirror figure, the hand-up invite, the
  game, the card. A raised hand always starts the first game of `MENU_ORDER` (Copy Me); no flag picks another.
- The camera source is MediaPipe on frames from `cv2.VideoCapture`. It cannot open a ribbon camera. The
  `imx500` source of the arcade spec (6.1, core plan Task 19) is not written.
- On the Pi, MediaPipe's lite model was timed at 56 ms an inference: 10 captures a second hold, with the
  wall's sender steady (2026-09-30, no camera attached). The Pi drives the wall through the proven driver.
- The operator is gated (gate.md, Q180) with iteration 22's plan (Paint, Tug) written and not built.

## 3. Stage 1: playable on the wall (this session, with the owner at the wall)

The AI Camera is used as a plain camera first. Every game and the tracker were tuned on MediaPipe's
keypoints, and MediaPipe is already timed on the Pi; the on-sensor parser is unwritten and untested.

Built:

1. **A picamera2 capture.** `arcade/sources/capture_picamera2.py`: `Picamera2Capture`, with the two calls the
   MediaPipe source already takes from an injected capture (`read() -> (ok, bgr)` at `CAPTURE_SIZE`,
   `release()`). picamera2 is imported in the constructor, never at module import.
2. **A config key `capture`**: `"opencv"` (the default, today's behaviour) or `"picamera2"`. `make_sources`
   and the doctor's camera probe follow it, so `run`, `calibrate`, `record` and `doctor` all do. `camera`
   keeps its values; `imx500` stays the on-sensor source's name (stage 3).
3. **`arcade run --game NAME`**: the lobby and the runner get that one game, so a raised hand starts it. An
   unknown name is refused with the list, before any source opens.
4. **`arcade.pi.toml`**: the Colorlight backend on `eth0`, `capture = "picamera2"`, the camera at 10 a second;
   every other key at its default, as the lobby ran on the card on 2026-09-30. `gamma` (the governor's light
   model, not a change to the bytes) follows the wall session's gamma check (below).
5. **The Pi's setup, written down** (`docs/runbooks/arcade-on-the-pi.md`): the apt packages, the venv seeing
   them, MediaPipe and the lite model (`mediapipe` joins the `pi` extra; today it is a hand install), the
   start command as user trey with the two capabilities (the show's form), one signal to stop, never
   `timeout`, every command under the Pi's lock.

Not changed: the flash governor, the limiter, the driver and its wall-proven settings.

Tests: the capture against a fake picamera2 object (frame shape, channel order, a failed read, release); the
config key; `--game` (a known name, an unknown one); the doctor's probe by `capture`. The full suite runs once
on the Mac before the code goes to main, under 540 s (Q102).

The wall session, in this order, by the wall session protocol:

1. The gamma check with `tools/wall_pattern.py` (the owner's open item since 2026-09-30, when the lobby's
   orange figure read red: the card applies its own gamma to bytes the arcade sends as if none were; the
   route A bench report, section 3). Its result sets `gamma` in `arcade.pi.toml`. Colours that still read
   wrong after it are a carried fix, not this session's, unless a game cannot be read.
2. `doctor`, then the mirror figure alone: does the camera see a body, and is left left.
3. `calibrate` (its first run anywhere).
4. Copy Me through the lobby: walk up, hand up, play, card, walk away.
5. Each other game by `--game`, as far as time allows.

The owner's verdicts go into `live-smoke.md`. A fault that stops play is fixed in the session; anything else
becomes a carried fix for the loop.

Done when: from the Pi, with the AI Camera, a person walks up, sees their figure, raises a hand, plays one
game to its card and walks away to the title; the sender's line reads no late frame; one game's row in
`live-smoke.md` is filled.

## 4. Stage 2: the full director (the operator, headless on the Mac, beside stage 1)

The operator's next iteration is M8, not M7b. It builds the arcade spec's 7.3 and 7.7 as written: the
director as the lobby, the presence tiers, Watcher, Echo, Warp and Contours, the scheduling, the crossfades,
the mirror and invite over the running mode, the three doors, the ten-second guarantee, the featured game's
rotation, the status pixels. The demo replays of 7.3 step 1 are cut. With `--game`, the director offers only
that game.

If one iteration cannot hold it, the first holds the director, the tiers, the four modes and the crossfades;
the second the doors, the guarantee and the rotation.

The loop's rules stand: its own plan with one adversarial review, no Pi, nothing to the card, at most two
agents. Recorded as a new decision; `roadmap.md` puts M8 before M7b; iteration 22's written plan is kept for
M7b's return. The owner deletes gate.md and starts the loop.

Done when: the owner sees the director on the wall with stage 1's setup, and every game is reachable by the
doors.

## 5. Stage 3: pose on the sensor (after; not needed for the vision)

Core plan Task 19 as `camera = "imx500"`, compared with MediaPipe at the wall. Taken when stage 1's session
says 10 captures a second is not enough, or after stage 2.

Brought forward 2026-10-02 night (owner decision Q182): stage 1's plays at 15 captures a second read as lag and
stutter. The spike (`docs/superpowers/reviews/2026-10-02-imx500-pose-spike.md`) chose PoseNet on the sensor over
HigherHRNet; the design is `docs/superpowers/specs/2026-10-02-pose-on-the-sensor-design.md`. Stage 3 now comes
before stage 2.

## 6. Two sessions, one main

Stage 1's code goes to main before the operator starts, so the loop builds on it. While the loop runs, this
session commits on a branch `wall-bringup` in its own worktree, the Pi checks that branch out, and it merges
to main between the loop's iterations. The Pi is this session's alone while the loop runs (the loop's rule
already keeps it off).

## 7. Risks

- **Lag.** 10 captures a second is what the Pi holds. The one live play so far ran at that rate and the hand
  control felt wonky (Pong has since moved to the body). Stage 1 shows it; stage 3 is the answer if it is not
  enough.
- **picamera2 and the venv.** apt's picamera2 has to import beside the venv's numpy and OpenCV. If it does
  not, the capture reads `rpicam-vid`'s raw frames from a pipe instead; the capture's two calls stay the same.
- **The Pi is not reachable from the Mac** as this is written (`codeisart.local` does not resolve). Nothing in
  stage 1's session starts before it is.
- **The card is shared.** `promptviz-party.service` is stopped at the owner's word while the arcade has it.
- **The Mac's memory.** Stage 1 is built inline, with no agents, so the loop keeps its two.

## 8. Left out

Paint and Tug (M7b), the project skills (M6), the start at boot, the status file and the thermal policy (GATE
B's Task 24), GATE A's recordings, anything for a bigger wall, the microphone.
