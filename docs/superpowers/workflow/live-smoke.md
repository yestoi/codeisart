# Live smoke — wall arcade

The owner's verdicts from playing each game on the live webcam, filled in on a phone. The loop reads
this every iteration and turns each "n" or a want-another-go score of 2 or less into a Carried fix.
The wall is four 64x32 panels, 2 x 2, 128x64 (Q32, Q33): the only layout, so one row per game. Leave a
row blank if that game is not built yet.

Date and build (git sha) of this smoke: 2026-09-28, 2e016e5 (the Mac's webcam, the preview window; not on the panels). Told to the operator in the session; blank cells were not said

## Games

| game | layout | responded (y/n) | understood (y/n) | want another go (1-5) | broken? | notes |
|---|---|---|---|---|---|---|
| Copy Me | 128x64 |  |  |  |  |  |
| Pong | 128x64 | y, badly |  |  |  | The owner: "using the hand for controls was wonky". The owner's idea while playing: the whole body as the control, moving towards and away from the camera (Q42) |
| Quick Draw | 128x64 |  |  |  |  |  |
| Dodge | 128x64 |  |  |  |  |  |
| Tug | 128x64 |  |  |  |  |  |
| Flap | 128x64 |  |  |  |  |  |
| Swat | 128x64 |  |  |  |  |  |
| Paint | 128x64 |  |  |  |  |  |
| Jump | 128x64 |  |  |  |  |  |
| Freeze | 128x64 |  |  |  |  |  |

## Pong by the body: the second smoke (it09, M4c)

Pong's row above stays as the first smoke's verdict. Play this build and fill a new row: the whole body is the
control now, not the hand.

1. `.venv/bin/python -m arcade run -v` (the camera at 10 a second).
2. Stand about 2 to 2.5 m from the camera with the hips in view. Raise a hand to start. Step in for up, step back for
   down (the hint says "STEP IN = UP", "STEP BACK = DOWN" at the serve).
3. Then the same with the Mac's trial config, the camera at 30 a second:
   `.venv/bin/python -m arcade run -v --config arcade.mac.toml`.

The setup, from the owner's hand-read spike (docs/superpowers/reviews/2026-09-28-hand-read-spike.md on branch
`spike/hand-read`): put the camera at chest height and let it look level, not up from a low table, so that the hips
stay in the picture when you step in; keep lamps and bright fixtures out of the camera's view; light on the player
helps. If the window shows black or the wrong room, the Mac has opened a nearby iPhone as camera 0: move the phone
away or set `camera_index = 1` in the config. When the hips do leave the picture the paddle should hold its place
and still follow a step (task S3, Q48): say if it jumps.

Report for each command: the lag (how long after a step the paddle moves), the jitter when standing still, whether
both ends of the wall are reachable, whether the hint read, and the ball's pace (too slow, right, too fast). Say
which of the two feels better and by how much.

| command | lag | jitter when still | both ends reachable (y/n) | hint read (y/n) | ball's pace | notes |
|---|---|---|---|---|---|---|
| `run -v` |  |  |  |  |  |  |
| `run -v --config arcade.mac.toml` |  |  |  |  |  |  |

## Walk-up flow

| step | layout | responded (y/n) | understood (y/n) | want another go (1-5) | broken? | notes |
|---|---|---|---|---|---|---|
| Attract director and mirror | 128x64 | y |  |  |  | The owner: "the pose detection appears to work". The small lobby, not M8's director |
| Hand-up prompt to first game | 128x64 |  |  |  |  |  |
| Three-door menu | 128x64 |  |  |  |  |  |
