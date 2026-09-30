# Lane 05: our software. The sender audited, the pictures that map the fault, the workaround costed

2026-09-30. Read-only: nothing was sent to the wall, the card, the Pi or the Omarchy box. Two files written in
the repo: this report and `ghost_map.py` beside it. Scratch work (the proofs quoted below) is in
`/private/tmp/claude-502/-Users-trey-dev-codeisart/489bd663-dd66-40f0-8952-22058687bf7d/scratchpad/lane05/`.

Labels: CONFIRMED (code at file and line, or a measurement described), LIKELY, SPECULATIVE.

## Verdict in short

- **The sender does not make the copy and does not alter the pixels.** CONFIRMED. On both paths (the pattern
  tool and the arcade) the bytes drawn are the bytes on the wire, swapped to B, G, R and nothing else. No gamma,
  no brightness scaling, no dither. In the morning's level-line test the card received byte 255 for "pixel
  value 255" (measured by running the repo's own sender on a list, section 1.2).
- **`--brightness 0.1` is a level byte of 25, sent in both the sync packet and the 0x0A packet, twice each,
  every frame.** CONFIRMED. Which of the two firmware 13.17 obeys, and on what scale, is NOT settled; LIKELY the
  sync byte, read linearly (9.8 %).
- **`gamma = 2.2` in `arcade.toml` changes no byte.** CONFIRMED. It is only the light model of the flash
  governor and the brightness limiter ("light is linear in the byte"). The card's 2.8 then acts on unmodified
  bytes: 64 is 2.1 % of full light, 128 is 14.5 %, 255 is 100 %. The model is wrong for this card, which
  matters to the governor (section 1.3) apart from the ghost.
- **The sender holds two levers at most:** the pixel values, and the level byte (with its three per-colour
  bytes). Everything that sets how the card scans (refresh, multiple, grey mode, blanking, line switch time,
  decoder, gamma, Brightness Level) lives in the card and is reached only through LEDVision.
- **The diagnostic script is written and proven without the wall:** `ghost_map.py`, eleven pictures, every
  frame through `wall_pattern.py`'s own governed run. In a dry run of two cycles of every picture the governor
  held 0 ticks and altered 0 frames. The run sheet is in section 2.3: about 15 minutes at the wall.
- **No software workaround can be sized yet.** Which one is worth building turns on one measurement the
  script makes (picture 7): whether the copy follows the pixel's value or the light that comes out. If the
  value, trading pixel value for card level costs no light while the level has headroom (peak 155 at level
  0.4 gives the light of 255 at 0.1). If the light, software can only hide the copy, not shrink it.

## 1. Part A: the sender, audited

### 1.1 A frame's path to the wire

From `tools/wall_pattern.py` (and so from `ghost_test.py` and `ghost_map.py`, which run through its main):

| Step | Where | What it does to pixel values |
|---|---|---|
| The pattern draws | `tools/wall_pattern.py:260` (`PATTERNS[pattern](width, height, t)`) | the frame, uint8 RGB |
| The governor | `show/wall.py:106-112` (`_govern`), `arcade/flash.py:159-208` (`apply`) | returns the same array unless a pixel is over its flash budget; a held pixel keeps its previous output (`flash.py:200`). Never scales |
| The display's push | `show/display/colorlight.py:203-211` | shape and dtype checked, copied into the shared slot (`colorlight_sender.py:163-167`). No change |
| The child sender | `show/display/colorlight_sender.py:254-255` | the one transform: `frame[..., ::-1]`, RGB to BGR, into the prebuilt row packets |
| The wire | `colorlight_sender.py:270-276` | sync x2, brightness x2, 64 row packets of 128 pixels, 59 times a second |

From the arcade (`python -m arcade run`):

| Step | Where | What it does to pixel values |
|---|---|---|
| The game or lobby draws | `arcade/canvas.py` onto `Runner.canvas.frame` | colours clamped to 0..255 (`canvas.py:30-43`) |
| The brightness limiter | `arcade/runner.py:552`, `arcade/brightness.py:100-114` | **the only place bytes are scaled**: when the frame's average picture level (in the limiter's model) is over `apl_cap_day` 0.12 (night 0.06), every byte is multiplied by a factor of 0.5 to 1 through a table (`brightness.py:112-114`). Under the cap the frame is returned as it is |
| The governor | `arcade/runner.py:552`, the runner's own `FlashGovernor` (`runner.py:296`) | as above: holds, never scales |
| The display | `arcade/main.py:135-142` to `show/display/__init__.py:41-47`: the same `ColorlightDisplay` | as above |

CONFIRMED (code). The arcade does not use `GovernedDisplay`; it applies its own governor and pushes to the
driver direct. The show daemon uses `GovernedDisplay` (`show/main.py:189-201, 310`) and has no limiter.

The lobby frame in the evidence folder (`lobby.png`, the frame the arcade pushed) has two colours,
(255, 120, 0) on 475 pixels and (0, 199, 0) on 76; its picture level in the limiter's model is 0.031, under the
0.12 cap, so the limiter left it alone and (255, 120, 0) reached the wire as drawn. CONFIRMED (measured from
the file with `arcade.brightness.apl`).

### 1.2 How brightness reaches the card

- `wall_pattern.py:240` calls `wall.set_brightness(level)`; `show/wall.py:119-120` passes it to the display;
  `colorlight.py:213-215` stores `level_byte(level)` in the slot's header. The arcade does the same once, at
  `arcade/runner.py:328` with `cfg.brightness`. `make_display` also opens the driver at the configured level
  (`show/display/__init__.py:45-46`), so the first frames carry it too.
- `level_byte` is `int(min(1.0, level) * 255)` (`colorlight_packets.py:39-43`): 0.1 is 25, 0.23 is 58, 0.4 is
  102.
- The child builds both packets from that byte whenever it changes (`colorlight_sender.py:236-241`):
  - the 0x01 sync, 112 bytes: the byte at Ethernet offsets 35 and 38, 39, 40; offset 36 is 0x05
    (`colorlight_packets.py:80-86`);
  - the 0x0A packet, 77 bytes: the byte at offsets 13, 14, 15; offset 16 is 0xFF
    (`colorlight_packets.py:89-94`).
- Pixel bytes are never scaled for brightness. `show/wall.py:6-7`: "No software brightness: the device holds
  the level"; `arcade/preview.py:14`: "pixels pushed to hardware are never scaled".

All CONFIRMED in code, and by measurement: `lane05/wire.py` builds `ghost_test.py`'s `levels` frame, passes it
through `GovernedDisplay` at brightness 0.1 into a real `Slot`, and runs the repo's `Sender` with a list for a
socket. What came out:

```
governor returned the frame unchanged: True held ticks: 0
sync: len 112 bytes 12..13 01 07 byte 35 = 25 byte 36 = 0x05 bytes 38..40 = [25, 25, 25]
0x0A: len 77 bytes 12..16 = ['0a', '19', '19', '19', 'ff'] rest zero: True
row 16 pixel 94 (orange 255 line): frame RGB (255, 127, 0) -> wire bytes [0, 127, 255] (B, G, R)
row 40 pixel 94 (white 255 line): frame RGB (255, 255, 255) -> wire bytes [255, 255, 255] (B, G, R)
row 16 pixel 52 (orange 128 line): frame RGB (128, 64, 0) -> wire bytes [0, 64, 128] (B, G, R)
row 16 pixel 10 (orange 64 line): frame RGB (64, 32, 0) -> wire bytes [0, 32, 64] (B, G, R)
```

So in the level-line test the card received 255, 128 and 64 as drawn. Note the test's "orange" is
(level, level // 2, 0): at the card's gamma the green of the 255 line is 14 % of its red, which is why the
photograph shows it red (the bench report says the same of (255, 120, 0)).

What is NOT settled: which level field firmware 13.17 obeys.

- The sync byte is linear in the references (Kubota: 0x1a is 10 %): 25 would be 9.8 %. The 0x0A byte is
  gamma-coded in LEDVision's own traffic (`255 * p ** 0.405`): read on that scale 25 would be 0.32 %
  (`2026-09-29-flicker/01-protocol-refs.md`, section 5.2). We send the same linear byte in both.
- LIKELY the card obeys the sync byte: in the sender-card spike, runs P2_2 and P2_4 (sync level 25, no 0x0A
  packet, pixel 25) were "dark" and S8 (sync level 0xff, no 0x0A, pixel 25) showed a picture
  (`2026-09-29-sender-card-spike.md`, section 3). That is one comparison, in the S2's sync format, and the spike
  itself lists "which level field the card obeys" as not settled.
- The wall's `steps` check (`wall_pattern.py steps`) has not been run on this card. Picture 7 of the new script
  answers the same question as a by-product (section 2.3).
- How the card applies the level (a shorter output-enable time, or a multiplication of the grey data) cannot
  be read from our side at all. It matters: see picture 7.
- The arcade's level in the morning's runs is from the record ("brightness 0.1", `00-bench.md` section 3 and
  `hardware.md`). The repo's `arcade.toml:17` says 0.4; the bench script that ran the arcade on the Pi
  (`~/bench/arcade_load.py`) is not in the repo and I did not read it.

For the other lanes' arithmetic: the light of a pixel at the card is, LIKELY,
`Brightness Level 3 (23 %) x sender level (25/255) x (byte / 255) ** 2.8`, with the byte exactly as drawn.
The first two factors are the same for the line and its copy; only the last varies between the test's lines.

### 1.3 Gamma: what each side does

- Our side applies none. `gamma_lut` and `apply_gamma` (`arcade/look.py:31-40`) are used only by
  `look.render` for the SDL preview (`look.py:177`); nothing on the hardware path calls them. CONFIRMED
  (`graft grep` of every use).
- `gamma = 2.2` (`arcade.toml:23`, `show.toml`, `wall_pattern.py --gamma`) feeds `light_lut`
  (`look.py:65-78`): light = `(byte / 255) ** (2.2 / gamma)`. At 2.2 that is linear in the byte: the governor
  and the limiter are told "the card sends bytes as they are". At 1.0 it is `(byte / 255) ** 2.2`: "the card
  applies gamma". The allowed range is 1.0 to 2.2 (`show/wall.py:31`, `arcade/config.py:106`), so the card's
  2.8 cannot be given exactly; 1.0 is the nearest.
- The card applies 2.8 to whatever arrives (saved setting; `hardware.md` line 227).

Consequences, apart from the ghost (a side finding, LIKELY, by arithmetic):

- The flash governor counts a swing of 0.1 of full light as a transition. In the linear model that is 26
  bytes anywhere on the scale. On this card a swing from 231 to 255 is 24 % of full light and is not counted;
  a swing from 0 to 64 is 2 % and is. The model is too strict in the dark and too lax at the top. With
  `gamma = 1.0` the same top swing is 0.195 in the model and is counted. The `gamma` wall check that decides
  this is still the owner's; this review adds the number, not a new decision.
- The limiter's picture level is likewise overstated for dim frames: a field at byte 48 is 19 % in the linear
  model and under 1 % of light at the card. This matters to one workaround below.

### 1.4 What the sender could change on the wire, and what it cannot reach

LEDVision's own paused grid shows the copy at the saved settings, so the sender is not the cause (brief,
observation 1). The question here is only whether it holds a lever.

Reachable from our packets:

| Lever | Where | Could it move a card-side ghost? |
|---|---|---|
| The pixel bytes | the picture itself | CONFIRMED: it does. The copy showed at 255, a trace at 128, none at 64 |
| The sync's level byte (offset 35) | `colorlight_packets.py:83` | SPECULATIVE. If the copy follows the pixel's grey value and not the light out, a higher level with lower pixel values gives the same picture with less copy. Picture 7 tests exactly this |
| The sync's three per-colour bytes (offsets 38 to 40) | `colorlight_packets.py:85` | SPECULATIVE. They are colour-temperature levels in the references (Kubota: `ff 76 06`); their order (R, G, B or B, G, R) is not settled. The same trade per channel: if red alone ghosts, red's level could rise and red's bytes fall |
| The 0x0A packet: its value, or sending none | `colorlight_packets.py:89-94`, `colorlight_sender.py:48, 273` | SPECULATIVE, weak. The S2 sender and PanelPlayer never send it; the spike's N7 against N8 looked the same with and without. If 13.17 does apply both, ours disagree in scale (section 1.2). LEDVision's grid shows the copy with LEDVision's own, consistent values, so a wrong 0x0A value is not the cause |
| Offset 36 (0x05, "enables brightness settings?") | `colorlight_packets.py:84` | SPECULATIVE, no reason to expect it |
| The stream itself: present or stopped | `ColorlightDisplay.pause`, `--stop-for` | Not tested. If the copy is gone while the card holds a frame with no packets arriving, the stream is involved after all. Run sheet step 9 |
| The frame rate and sync timing | `colorlight_sender.py:40` | No: measured clean, and LEDVision (25 frames a second) shows the copy too |

Not reachable from our packets: refresh rate and multiple, grey mode and grey depth, DCLK, blanking value
and the Blanking Phase page (line switch time, the 4051 times), the decoder and driver-chip choice, the
card's gamma table, Brightness Level, current gain. They are receiver parameters, written by LEDVision's own
configuration packets, which none of our references document (`01-protocol-refs.md` covers detection 0x07 and
0x08, the sync, 0x0A and the rows only) and which the repo's driver does not implement. CONFIRMED for the
repo (the driver sends three packet types, `colorlight_sender.py:270-276`); that the references hold nothing
more is what I found in yesterday's protocol file, not a search of the wider web.

The spike's bench sender (`tools/sender_spike/send.py`) already has `--sync-level`, `--bright-level` and
`--bright-reps` to set the two level carriers apart. It draws its own bars and does not pass the governor, so
it is not proposed for this session; it is the tool if the owner later wants the level-field question settled
on its own.

## 2. Part B: the diagnostic pictures

### 2.1 The script

`docs/superpowers/reviews/2026-09-30-ghosting/ghost_map.py`. Like `ghost_test.py` it registers its pictures in
`wall_pattern.PATTERNS` and hands the command line to `wall_pattern.main`, so the governor, the brightness
cap, the driver and its close are used as they are. It sends nothing itself. Its own flags are taken off the
line first (`--hold`, `--step`, `--value`, `--row`, `--channel`, `--offset`, `--no-ruler`); the rest are
`wall_pattern.py`'s.

Design, within the governor:

- Every picture is a list of still steps. A step is held `--hold` seconds (6 by default; under 3 is refused).
  So a pixel changes at most once in 3 seconds, against the governor's budget of 6 transitions in a second.
  Nothing blinks, sweeps or alternates.
- The most any picture lights is 12 % of the wall (picture 6: a block 58 by 16); the rest light under 4 %.
  `wall_pattern.py`'s rule that no pattern lights half the wall (Q64) is kept.
- The brightness refusal is the tool's own (over 0, at most 0.4).
- `--step N` freezes a picture on one step, for a long look, for `--stop-for`, and for `--png`.

What is on the wall besides the test pixels, and why it should not spoil the reading:

- A label (picture name and step, for example `1a r05`) at byte 96 (6.5 % of full light), always in the panel
  row the test is not in: the other chain, other panels, other row drivers.
- A ruler: ticks at byte 64 on the even rows of the test panel, at the first and last three columns of the
  wall (3 pixels at panel rows 0, 8, 16, 24; 2 at rows 4, 12, 20, 28; 1 at the other even rows). It is there
  to count rows in a photograph. It sits at the level where the morning's test showed no copy, and the test
  rows stop 6 columns short of each end. `--no-ruler` removes it and makes the rows truly full width; the run
  sheet has one such run as a check that the ruler changes nothing.

The pictures (rows and scan lines: a row r of the wall is on scan line `r % 8`; rows 0 to 15, 16 to 31, 32 to
47, 48 to 63 are the four 16-row halves; `--row` defaults to 2):

| Picture | Steps | What it shows |
|---|---|---|
| `1a` `1b` `1c` `1d` | 16 each | one single row at full value, stepping down the 16 rows of one half (1a rows 0 to 15, 1b 16 to 31, 1c 32 to 47, 1d 48 to 63). The label gives the wall row |
| `2` | 5 | the same row lit over 1, 4, 16, 64 and 128 pixels in turn. Columns 24 to 27 are lit in every step (64 is the left panel's whole row, 128 the wall's). No ruler |
| `3` | 4 | a level ladder on one row: 32, 64, 96, 128, 160, 192, 224, 255 left to right; red, then green, blue, white |
| `4` | 6 | left panel against right panel: row k alone against rows k and k + 8 (same scan line); k alone against k and the row on line k + 4; the k + 4 row alone against both. Each pair both ways round, so a difference between the two panels cancels |
| `5` | 4 | one pixel; a column 4 rows long (lines 0 to 3 of the band); a column over the 16 rows of the half; a column the wall's full height |
| `6` | 16 | the inverse: a lit block 16 rows high on the left panel with one dark row stepping through it |
| `7` | 1 | picture 8's first step at the byte that gives, at the `--brightness` asked, the light that 255 gives at 0.1 (if the level is linear and the gamma 2.8): 255 at 0.1, 199 at 0.2, 189 at 0.23, 155 at 0.4 |
| `8` | 5 | the match: a source segment, and on the row `--offset` below it (4) eight reference patches at 1, 2, 4, 7, 10, 15, 25 and 40 % of the source's light. The source steps 255, 224, 192, 160, 128 |

Picture 8 is the one addition to the list I was given, and the one I would not drop. The record's numbers for
the copy's strength are camera ratios taken where the line saturates the sensor. Picture 8 turns the
measurement into a match between two dim things side by side: the copy, and a patch whose light is a known
share of the source's. The eye does that well and the camera's clipping of the source no longer matters. The
patch bytes are `round(source * share ** (1 / 2.8))`; for a source of 255 they are 49, 63, 81, 99, 112, 130,
155, 184. The reading is only as good as the card's gamma being 2.8 and its low greys being true, so the
bytes are given here for a re-reading if either turns out otherwise.

One caution on picture 8: the patches sit on the scan line where the copy lands. If picture 2 shows that the
copy depends on how much of a line is lit, read picture 8 with that in mind, or move the patches with
`--offset`.

### 2.2 Proof without the wall

Run on the Mac, nothing sent anywhere (`lane05/prove.py`):

- Every step of every picture rendered to PNG by calling the pattern functions direct; I looked at all of
  them (`lane05/sheet-1a.png` to `sheet-8.png`, and `1b-step5.png`, `7-b0.1.png`, `7-b0.2.png`, `7-b0.4.png`
  through the tool's own `--png`). They are what the table above says.
- Every picture run for two whole cycles through `wall_pattern.run` itself (so through `GovernedDisplay`,
  `from_dark=True`, the governor at 20 frames a second, gamma 2.2) on a recording display with a stepped
  clock. "Altered" counts pushed frames that differ from what the picture function gave for that instant.

| Picture | Steps | Most pixels lit | Share of the wall | Frames pushed | Ticks held | Frames altered | `flash_area` | `square_flashes` |
|---|---|---|---|---|---|---|---|---|
| 1a | 16 | 241 | 0.029 | 3839 | 0 | 0 | 0.000 | 0 |
| 1b | 16 | 242 | 0.030 | 3839 | 0 | 0 | 0.000 | 0 |
| 1c | 16 | 235 | 0.029 | 3839 | 0 | 0 | 0.000 | 0 |
| 1d | 16 | 243 | 0.030 | 3839 | 0 | 0 | 0.000 | 0 |
| 2 | 5 | 199 | 0.024 | 1199 | 0 | 0 | 0.000 | 0 |
| 3 | 4 | 213 | 0.026 | 959 | 0 | 0 | 0.000 | 0 |
| 4 | 6 | 314 | 0.038 | 1439 | 0 | 0 | 0.000 | 0 |
| 5 | 4 | 200 | 0.024 | 959 | 0 | 0 | 0.000 | 0 |
| 6 | 16 | 996 | 0.122 | 3839 | 0 | 0 | 0.000 | 0 |
| 7 | 1 | 210 | 0.026 | 239 | 0 | 0 | 0.000 | 0 |
| 8 | 5 | 220 | 0.027 | 1199 | 0 | 0 | 0.000 | 0 |

  CONFIRMED: the governor holds nothing and changes nothing in any picture, and each run ended with the two
  governed black frames and the display closed.
- The whole command line, end to end, through `wall_pattern.py --dry-run` (the real driver and its child on a
  socket that discards; no interface, no root): `1a --dry-run --seconds 8 --hold 3 --fps 30` and
  `8 --step 0 --dry-run --seconds 9 --stop-for 2 --brightness 0.23` both exited 0, printed the look-for text
  and the sender's stats line, the second with the stop at 5.0 s. No slot file was left behind.
- The refusals: `--hold 1`, `--row 62` with picture 8, picture 7 under brightness 0.1, `--brightness 0.5` (the
  tool's own cap), an unknown picture, `--config`, and `1c` on a 32-row wall all exit 2 before any display is
  opened.

Not proven: anything about the wall. The script has never driven the card.

### 2.3 The run sheet

Before the session:

1. Power-cycle the receiver card, so its RAM holds the saved settings again (960, x16, Level 3). The record
   says it may still hold x4 from the last trial.
2. Put the script on the Pi. It is uncommitted on the Mac (this review commits nothing). Either commit and
   pull, or from the Mac:
   `ssh trey@codeisart.local mkdir -p codeisart/docs/superpowers/reviews/2026-09-30-ghosting` and
   `scp docs/superpowers/reviews/2026-09-30-ghosting/ghost_map.py trey@codeisart.local:codeisart/docs/superpowers/reviews/2026-09-30-ghosting/`.
   A copy in `~/bench/` works too, run from `~/codeisart`.
3. The phone on a stand, square to the wall, far enough to hold all four panels. Room lights on, as in the
   morning's photograph: the unlit LEDs then show as a grid and rows can be counted. Lock focus and exposure
   on the lit row and turn the exposure down until the lit row no longer clips (it should look coloured or
   grey, not blown white). For the stepping pictures film the whole run; the label in every frame says which
   step it is.
4. A caution on the camera: if rows of the same value differ in brightness from one still to the next, the
   shutter is shorter than the panel's scan and the camera is catching part of a scan. Then trust the video
   (average a few frames) and picture 8's match by eye, not a single still.

On the Pi, brightness 0.1 unless the line says otherwise:

```
cd ~/codeisart
G=docs/superpowers/reviews/2026-09-30-ghosting/ghost_map.py

# 1. where each row's copy falls: 16 rows, 6 s each
sudo .venv/bin/python $G 1a --iface eth0 --seconds 100
sudo .venv/bin/python $G 1b --iface eth0 --seconds 100
sudo .venv/bin/python $G 1c --iface eth0 --seconds 100
sudo .venv/bin/python $G 1d --iface eth0 --seconds 100
#    the ruler changes nothing: row 2 alone, truly full width
sudo .venv/bin/python $G 1a --no-ruler --step 2 --iface eth0 --seconds 15

# 2. does the copy depend on how much of the row is lit
sudo .venv/bin/python $G 2 --iface eth0 --seconds 32

# 3. the level ladder, a colour every 10 s (two photographs a colour)
sudo .venv/bin/python $G 3 --iface eth0 --hold 10 --seconds 42

# 4. two rows on one scan line, and rows on lines k and k + 4
sudo .venv/bin/python $G 4 --iface eth0 --seconds 38

# 5. one pixel and one column
sudo .venv/bin/python $G 5 --iface eth0 --seconds 26

# 6. the inverse: a lit block with a dark row
sudo .venv/bin/python $G 6 --iface eth0 --seconds 100

# 8. the match: how strong the copy is, by eye, at three levels, then per colour
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52 --brightness 0.23
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52 --brightness 0.4
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52 --channel r
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52 --channel g
sudo .venv/bin/python $G 8 --iface eth0 --hold 10 --seconds 52 --channel b

# 7. the same light from three levels: pixel 255 at 0.1, 199 at 0.2, 155 at 0.4
sudo .venv/bin/python $G 7 --iface eth0 --seconds 20 --brightness 0.1
sudo .venv/bin/python $G 7 --iface eth0 --seconds 20 --brightness 0.2
sudo .venv/bin/python $G 7 --iface eth0 --seconds 20 --brightness 0.4

# 9. the card holding a frame: the stream stops 5 s in, for 15 s, then restarts
sudo .venv/bin/python $G 8 --step 0 --iface eth0 --seconds 30 --stop-for 15
```

If time is short: 1a, 8 at 0.1, 7 at the three levels and step 9 are the four that decide the most. 1b to 1d
can run at `--hold 3 --seconds 50`. Once picture 1 has shown where a row on lines 4 to 7 sends its copy,
pictures 2, 4 and 8 are worth one more run on such a row: add `--row 5`, and for picture 8 `--offset` set to
the copy's row less 5 (it may be negative: `--offset -3` rendered correctly in the proof).

What to record for each:

| Run | Photograph or film | Write down |
|---|---|---|
| 1a to 1d | the whole run, filmed; or a still a step | for each source row: the row or rows that show a copy; whether any copy is in the other half of the panel or on the other panel row; whether the copy runs the row's full length and is even along it |
| 1a `--no-ruler` | one still | the copy looks as it did with the ruler: yes or no |
| 2 | a still a step, same locked exposure | the copy under columns 24 to 27: the same in all five steps, or growing with the length |
| 3 | two stills a colour: one exposed for the 255 segment, one two stops brighter | per colour, the lowest segment with a visible copy; whether a white segment's copy is white or tinted |
| 4 | a still a step | which side's copy is stronger in steps 0 and 1; in steps 2 and 3, whether the side with both rows shows any copy, and on which row |
| 5 | a close still a step | the pixel's copy: one pixel, same column, which row; the 4-row column: how many rows look lit; the long columns: any light beside them or past their ends |
| 6 | the run, filmed | is the dark row fully dark; is another row of the block dimmer, and how many rows from the dark one |
| 8 | by eye first, then a still a step | for each source value, the number (1 to 8 from the left) of the patch the copy matches; "dimmer than 1" and "brighter than 8" are answers too |
| 7 | one still a level, same locked exposure | is the source equally bright at all three levels; the matching patch at each |
| 9 | filmed across the stop and the restart | is the copy there, and unchanged, while the stream is stopped |

Picture 8's patch numbers read as shares of the source's light: 1 is 1 %, 2 is 2 %, 3 is 4 %, 4 is 7 %, 5 is
10 %, 6 is 15 %, 7 is 25 %, 8 is 40 %.

### 2.4 How each outcome reads

The mechanism is lanes 02 and 03's. What follows is only what each picture can tell apart; the predictions
are mine, from the geometry and the brief, and are LIKELY at best where they are plain arithmetic and
SPECULATIVE where they lean on how a cause behaves electrically.

**Picture 1, the map.** For a source on scan line k, where the copy lands (rows counted within the 8-row
band; "+" is below):

| Reading | Line 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| (a) the line lit next, order 0,4,1,5,2,6,3,7 | +4 | +4 | +4 | +4 | -3 | -3 | -3 | -7 |
| the line lit before, same order | +7 | +3 | +3 | +3 | -4 | -4 | -4 | -4 |
| (b) line (k + 4) mod 8 | +4 | +4 | +4 | +4 | -4 | -4 | -4 | -4 |
| the line lit next, plain order 0 to 7 | +1 | +1 | +1 | +1 | +1 | +1 | +1 | -7 |
| not a scan effect (light inside the panel, a reflection) | the same offset for every row, and across the half's edge |

Rows 4 to 7 of any half decide between (a) and (b): 3 above or 4 above. Row 7 is the sharpest single step:
7 above under (a), 4 above under (b). The morning's arm (three rows thick, a two-row copy 4 below, a one-row
copy "just above") fits (a) if the arm sat on lines 2, 3, 4 (copies on 6, 7 and on line 1, touching the arm)
and fits (b) less well (the upper copy would be one dark row clear of the arm); that is a reading of one
enlarged frame and is why the map is needed. A copy that leaves its 8-row band, or appears twice, fits none
of the rows above and points at how the card lays data onto the chain, not at the panel's analogue side
(SPECULATIVE). 1b to 1d say whether the four halves and both chains behave alike; a difference between panels
points at a panel, not the card.

**Picture 2, length.** The copy under the same four columns unchanged from 4 to 64 pixels: each column makes
its own copy, which fits a cause in the column path or in the card's timing. A copy that grows with the
length: something shared by the row is involved (the row driver, the row's supply or ground). 64 against 128
says whether the other panel on the chain matters; it should not.

**Picture 3 and picture 8, the level.** These settle the caution in the brief. If the copy is a fixed share
of the source's light, picture 8 gives the same patch number at every source value, and the morning's
"nothing at 64, a trace at 128, plain at 255" is only the card's gamma. If the patch number falls as the
source falls (say patch 6 at 255 and under patch 1 at 160), the copy grows faster than the light and
something with a threshold is at work (the longest grey-scale pulses, the top bit planes). A jump between two
neighbouring source values, not a slide, would say the same more strongly. Picture 3 shows the same thing per
colour in one view, and whether red copies at a lower value than green and blue. A white segment with a red
copy says the channels differ; with a white copy, they do not, and the "redder" copy of the orange figure is
only its green being 12 % of its red.

**Picture 4, two rows.** Steps 0 and 1: if the copy of row k is stronger when its scan-line partner k + 8 is
lit too, the load on the scan line matters (as picture 2's growth would). Steps 2 to 5 test the geometry a
second way: with rows on lines k and k + 4 both lit, reading (b) puts each row's copy on the other, so no
copy is seen anywhere; reading (a) puts the k + 4 row's copy 3 above it, on line k + 1, where it shows.

**Picture 5, pixel and column.** A copy in the neighbouring columns means sideways coupling; every row-scan
reading predicts the copy in the same column only. The 4-row column should look 8 rows long if lines 0 to 3
copy 4 below. Light past the ends of the 16-row column says the copy crosses the half's edge.

**Picture 6, the inverse.** Every additive cause predicts a dark row that is not fully dark. The second thing
to look for is a row of the block that is slightly dimmer: the row that would have received the dark row's
copy. Where it sits relative to the dark row gives the map again with the opposite sign, from a picture in
which nothing clips.

**Picture 7, the same light from three levels.** First, the source: if it is not equally bright at 0.1, 0.2
and 0.4, the card's level is not the linear byte of the sync packet and section 1.2's open question is
answered the other way. Then the copy. The same patch at all three levels: the copy follows the light that
comes out, whatever bytes made it. A weaker copy at the higher level (where the pixel byte is lower): the copy
follows the pixel's grey value, and the level is a lever. A stronger one: the copy follows the level itself.

**Picture 8 at three levels.** Here the bytes stay and the light changes. The patches scale with the source,
so an unchanged patch number says the share is the same at every level. Together with picture 7 this
separates value from light without any guess about how the card applies the level.

**Step 9, the held frame.** The copy unchanged while no packet arrives: the card's scan of the panel makes it,
and nothing in the stream is involved. CONFIRMED already in part: LEDVision's paused grid shows it, but
LEDVision keeps sending frames while paused. The copy gone during the stop: the stream is involved, and the
whole question moves to the sender side. I expect the first (LIKELY), but it has not been looked at.

**The colour runs of picture 8.** The patch number per channel is the strength per channel, which the
workaround arithmetic needs (section 3.3).

## 3. Part C: the software workaround, costed, not built

### 3.1 Where thin full-value lines on black come from

Survey of the palettes (CONFIRMED in code; the light column is `(byte / 255) ** 2.8`, arithmetic):

| Source | Colour | Where | Light of each lit channel at the card |
|---|---|---|---|
| The lobby's mirror figure, 2 px strokes | `PLAYER_COLORS` (255, 120, 0) and (0, 160, 255) | `arcade/juice.py:58`, `arcade/figure.py:95-104`, `arcade/attract/lobby.py:204-206` | red 100 %, green 12 %; blue 100 %, green 27 % |
| The lobby's card text | `TEXT_COLOR` (255, 160, 0) | `arcade/attract/lobby.py:46` | 100 %, 27 % |
| The lobby's pictogram | `PICTOGRAM_COLOR` (0, 200, 0), breathing from 0.4 of it | `lobby.py:47, 287-291` | 51 % at the top, 3.9 % at the bottom |
| The attract title, the title card | `TITLE_COLOR` (120, 60, 0) | `lobby.py:45`, `runner.py:178` | 12 %, 1.7 % |
| Pong: ball, score, hint | (255, 255, 255), `HINT_COLOR` (255, 160, 0) | `arcade/games/pong.py:45, 55, 417-447` | 100 % |
| Pong: CPU paddle, net | (0, 200, 0), `NET_COLOR` (0, 0, 96) | `pong.py:54, 56` | 51 %; 6.5 % |
| Quick Draw: line, ticks, texts | `LINE_COLOR` (255, 120, 0), `DRAW_COLOR` white, `SOON_COLOR` (255, 0, 0) | `arcade/games/quickdraw.py:55-57, 352-378` | 100 % |
| The runner's prompt, the banner, score pops | (255, 255, 255) text on a black box | `arcade/runner.py:533`, `arcade/juice.py:233` | 100 % |
| The exit ring, the crash icon | `RING` (160, 160, 160), `CRASH_RED` (96, 0, 0) | `runner.py:46, 57` | 27 %; 6.5 % |
| The show's terminal text | phosphor green (51, 255, 51) or amber (255, 176, 0); bold at 100 %, normal at 0.7 | `show/config.py:8-11`, `show/renderer.py:13, 51` | bold 100 %; normal (byte 178) 37 % |
| The show's strip, `bright-on-field` | letters at full phosphor on a field at 0.25 of it | `show/renderer.py:17-18, 53-55` | letters 100 %; the field (byte 63) 2 % |
| `wall_pattern.py` | `LEVEL` 128, `DIM` 40; `gamma` has 255 and 186 | `tools/wall_pattern.py:52, 66-67, 136-144` | 14.5 %; 0.6 % |

So almost everything a player reads is a 1 or 2 pixel stroke with a channel at 255, on black: the worst case
for this fault. This is by rule, not by accident: the game-authoring skill asks for saturated colours with the
low channels at 0 and no lit pixel with every channel under 140 (`.claude/skills/arcade-game-authoring/SKILL.md`
lines 202 to 205, `arcade/feel.py:42` `DIM_LEVEL = 140`, `feel_budgets.toml` `dim_fraction` at most 0.1). The
calibration patterns sit at 128 and looked clean for that reason. In the lobby frame of the evidence folder,
353 of the 551 lit pixels have a dark pixel where a copy 4 rows away in the band would land (measured): the
copy has black to show against nearly everywhere.

### 3.2 The options

Light figures use the card's gamma 2.8. "Frozen" means `arcade/flash.py` (frozen) and the Game protocol (tag
`game-protocol-v1`). A "safety slice" is a change to `arcade/flash.py`, `arcade/brightness.py`,
`show/display/colorlight.py` or the order limiter, governor, push (`docs/superpowers/workflow/config.md`,
rule 4); it gets an adversarial plan review.

| Option | Where it would live | Cost at the wall | Governor, frozen interfaces | Tests that change |
|---|---|---|---|---|
| **0. Trade value for level**: scale every byte by s, raise the card's level by `s ** -2.8` | one table lookup on the frame, plus the level: in `runner._push` and `GovernedDisplay` before the governor, or in the driver after it | none in light or contrast while the level has room: a pure power law keeps every ratio. Peak 155 at level 0.4 is the light of 255 at 0.1; from the show's 0.15 the cap of 0.40 allows peak 180; from 0.23, peak 209. Lost: grey steps (155 codes for 255) and the power-supply headroom the 0.4 cap was keeping | a fixed, monotone, per-pixel map: it cannot add a transition. Before the governor the governor sees what is sent. After it (in the driver) the swings on the wall are smaller than those counted, which is the safe side. Either place is a safety slice. It also ends "pixels pushed to hardware are never scaled" (`arcade/preview.py:14`, `show/wall.py:6`) | `tests/test_colorlight.py` (the wire shows the frame), `tests/test_wall.py`, `tests/arcade/test_runner.py`, `tests/test_main.py` (the level set once), and the brightness-cap tests if the level moves |
| **1. A cap on the peak value** at the display layer, level unchanged | the same table, clipping or scaling | the light itself: a cap of 224 keeps 70 %, 200 keeps 51 %, 160 keeps 27 %, 128 keeps 14.5 %. A clip (not a scale) also flattens colour: (255, 120, 0) capped at 160 becomes (160, 120, 0), green rising from 12 % to 45 % of red, amber turning yellow | as option 0 | as option 0 |
| **2. A cap for thin features only** | it needs to know what is thin. In the canvas's drawing calls (`Canvas.line`, `text`, `blit`) or as palette constants in each game and the lobby; not as a filter on the finished frame | the strokes lose what option 1 loses, and they are exactly what must read at 2 to 10 m; filled shapes keep their light. The rule "no lit pixel with every channel under 140" limits how far a palette can fall (140 is 19 % of full light) | as palette changes: none on the governor, and the Game protocol is untouched (colours are not in it). As a filter on the frame it is a spatial operation: a pixel would change because its neighbour did, so it must sit before the governor and is a safety slice | every test that names a palette colour: `tests/arcade/test_lobby.py`, `test_quickdraw.py`, `test_pong.py`, `test_juice.py`, `test_figure.py`, `test_feel.py` (`dim_fraction`), `tests/test_renderer.py`, `tests/test_show_shot.py` |
| **3. Thin lines on a dim field**, not on black | a field drawn by `Canvas.clear` in the games and lobby, or added at the display layer | hides the copy, does not remove it: the copy has to be small against the field. A field at byte 64 is 2 % of full light and raises the black of the whole wall, all night, in a dark place; at byte 48, 0.9 %. Power rises with it | at the display layer it is a constant added everywhere: no new transitions. But the limiter reads a field at byte 48 as 19 % picture level while `gamma = 2.2` stands, over the 0.12 cap, and would scale the whole frame down: the gamma setting has to be settled first. Drawn by games it breaks the feel oracle: `lit_fraction` at most 0.5 and `dim_fraction` at most 0.1 (`arcade/feel_budgets.toml`) | `tests/arcade/test_feel.py`, `test_all_games.py`, `test_brightness.py`, the lobby and game draw tests |
| **4. Pre-compensation**: subtract the predicted copy from the row it lands on | a filter on the frame before the governor, with the map from picture 1 and the strength from picture 8 | none where it works, but it works only where the target pixel is lit at least as brightly as the copy. On black there is nothing to subtract from: in the lobby frame that is 353 of 551 lit pixels. It needs the copy to be stable (across panels, levels, warm-up) to better than it is visible | spatial, so before the governor, and a safety slice; it also makes the frame on the wall differ from the frame the game drew, which the oracle and the evidence tools compare | new tests; `tests/arcade/test_runner.py` |
| **5. Colours whose channels stay under the level where the copy shows** | palette constants: `PLAYER_COLORS`, `TEXT_COLOR`, `HINT_COLOR`, `LINE_COLOR`, the whites, the show's phosphors | the same light as a cap at that level, with the hue chosen rather than clipped. If the copy only shows above about 160, the palette keeps 27 % of its light per channel; two channels at 160 (a yellow or a cyan) give back some of it where one at 255 was used | none on the governor or the protocol. It collides with the authoring rule (saturated, low channels at 0) and, under 140, with `DIM_LEVEL` | as option 2 |

Reading the table:

- Options 1, 2 and 5 are the same trade in three places: less light from the strokes. They help only if the
  copy falls faster than the light as the value falls. If the copy is a fixed share of the light, the stroke
  and its copy dim together and nothing is gained but a darker wall.
- Option 0 is the only one that could cost nothing, and only if the copy follows the pixel value and not the
  light out. Picture 7 is the test. If the source is not equally bright at the three levels in that picture,
  option 0's arithmetic is wrong as well and the level's scale has to be measured first (`wall_pattern.py
  steps`).
- Options 3 and 4 do not depend on that question, and both are poor fits for a wall that is mostly black by
  design.
- Whatever is chosen, the display layer is the cheaper place to build it (one table, the show and the arcade
  alike, the palettes and their tests untouched) and the more expensive place to justify: it is a safety
  slice and it retires a stated rule. A palette change is the reverse.

I recommend building none of them before the wall session, and none at all if the card-side lanes find a
setting that removes the copy.

### 3.3 The measurements needed before any of them can be sized

1. Picture 8 at brightness 0.1: the copy's share of the source's light at 255, 224, 192, 160, 128. This is the
   curve every option is sized from. A flat curve rules out options 1, 2 and 5.
2. Picture 8 per channel (`--channel r`, `g`, `b`): whether one channel carries the problem. If red alone
   does, only the red-heavy colours need to move and option 5 becomes cheap.
3. Picture 7: value or light. Decides option 0.
4. Picture 1: the map, which options 3 and 4 need, and which says where in a drawing the copy will show.
5. Picture 2: whether the strength depends on how much of a row is lit. If it does, none of the per-pixel
   arithmetic above holds and a workaround has to reason about whole rows.
6. The level the wall will run at on the night. The headroom of option 0 is the gap between it and the 0.40
   cap.
7. The `gamma` wall check, which has been the owner's since it13: until the model's gamma is settled the
   limiter and the governor misread any dim field or scaled frame (section 1.3).

## 4. What I looked for and could not settle

- Which level field firmware 13.17 obeys, and how it applies the level. Not answerable from our code; picture
  7 and `wall_pattern.py steps` would answer it.
- The arcade's actual level in the morning's runs: from the record only. `~/bench/arcade_load.py` is on the Pi
  and was not read.
- Whether any receiver parameter can be set from a Linux sender. I found no reference for LEDVision's
  configuration packets in the repo's protocol notes; I did not search beyond them.
- Anything about the wall itself. Every statement about the copy here is from the record or is a prediction;
  the script has been proven only as far as its frames and the governor.
- The camera caution in section 2.3 (a short shutter catching part of a scan) is SPECULATIVE as an
  explanation of the x4 trial's odd ratios; I did not examine the videos (lane 01's).
