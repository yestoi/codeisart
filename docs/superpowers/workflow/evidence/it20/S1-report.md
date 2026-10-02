# it20 S1 report: blobs and motion from camera frames (M5's first lane)

Implementer: opus, worktree branch `worktree-agent-ad3f0b6a0ff391d2e`, BASE b4f1e9b (checked: HEAD was b4f1e9b).

## Files
- `arcade/sources/blobs.py` (new): `find_blobs`, `motion_grid`, `BlobTracker`, `StaticMask`, `FrameFeatures`, and
  the constants below.
- `tests/arcade/test_blobs.py` (new): 16 tests.
- This report.
- Not touched: `arcade/sources/__init__.py` (no export), `camera.py`, `pose_mediapipe.py`, and every other file.

## Final constants (`arcade/sources/blobs.py`)
| name | value | meaning |
|---|---|---|
| `LIGHT_V` | 220 | a core pixel's value (its largest channel) is at least this |
| `HALO_PX` | 3 | the halo is the ring this many px around the core (7x7 ellipse dilation) |
| `HALO_S` | 0.5 | the halo's mean colour needs at least this saturation |
| `MAX_AREA` | 0.005 | a core over this share of the frame is rejected (96 px at 160x120) |
| `MIN_AREA` | 4 | px, the draft's floor (see Q1 below) |
| `MAX_BLOBS` | 8 | spec 5, at most 8, largest first |
| `SCAN_BLOBS` | 32 | new: FrameFeatures tracks and masks this many lights before it keeps 8 (see deviation 9) |
| `MATCH_DIST` | 0.1 | frame widths, between consecutive captures |
| `STATIC_SECONDS` | 5.0 | a blob still this long is masked |
| `STATIC_MOVE` | 0.01 | frame widths from where it stopped |
| `FRAME_ASPECT` | 4/3 | default only; FrameFeatures sets the real aspect from each frame |
| `MOTION_T` | 0.25 | threshold on the median-normalised difference |
| `CELL_FILL` | 0.2 | a cell is lit when more than this share of its pixels moved |
| `SHAKE_SHARE` | 0.35 | more than this share of cells lit gives an empty grid and a counted shake |
| `WALL_ASPECT` | `MOTION_GRID[0] / MOTION_GRID[1]` = 2.0 | the 128x64 wall (Q82) |

## Interfaces
- `find_blobs(frame_bgr, max_blobs=8, min_area=4) -> tuple[Blob, ...]`: camera coordinates (not mirrored),
  largest first, `id` -1.
- `motion_grid(prev_gray, gray, zone, size) -> np.ndarray`: bool `(h, w)` for `size = (w, h)`, or `(0, 0)` on a
  shake.
- `BlobTracker(aspect=4/3).update(blobs, t) -> tuple[Blob, ...]`.
- `StaticMask(aspect=4/3).update(blobs, t) -> tuple[Blob, ...]`: returns the shown blobs.
- `FrameFeatures(size=(160, 120), calibration=None)` (None means `Calibration()`, as `BodyTracker` does), with
  `update(frame_bgr, t) -> (blobs, motion)` and `shakes: int`. It also exposes `tracker`, `mask`, `size` and
  `calibration`.

## Tests, and how each failed first
At first, collection failed with `ModuleNotFoundError: No module named 'arcade.sources.blobs'`. Against a skeleton,
all 16 tests then failed with `NotImplementedError`. Two tests also failed later, after part of the code was in:
- `test_a_non_finite_centroid_is_dropped`, after `find_blobs` was written without the finite check: `assert
  (Blob(x=0.0, y=0.0, ...),) == ()`. This is C17's bug exactly: a NaN component became a light at (0, 0). It was
  green once the check was in.
- `test_static_lamps_do_not_crowd_out_a_moving_light`, after `FrameFeatures` was written with the draft's cap of 8
  before the mask: `assert 0 == 1`. Nine still lamps took all 8 places, were masked, and hid the moving light. It was
  green once the cap moved after the mask (`SCAN_BLOBS`).

Mutation checks, run in a scratch script and not committed:
- `test_uniform_brightness_step_gives_no_motion` fails when the median division is removed (`_median` patched to
  return 1).
- `test_motion_zone_crop_maps_to_wall_cell` fails when the left-to-right flip is removed.

Two of my own new tests had geometry errors. I fixed the tests, not the code:
- `test_frame_features_first_frame_has_no_motion`: the 5x5 blur legitimately spreads a strong change by 2 px, which
  lit grid column 8. I narrowed the stepped-in region to camera columns 90 to 120.
- The perf test's frame cycle (`n % 10`) jumped the block 54 px between frames 9 and 0. That is a real shake, so the
  grid came back `(0, 0)`. The cycle now runs back and forth (6 px per capture), and the test asserts
  `ff.shakes == 0`.

The 16 tests:
1. The amendment's: `test_small_saturated_red_is_a_red_blob`, `test_large_lamp_rejected`,
   `test_white_core_without_saturated_halo_rejected`, `test_static_blob_masked_after_5s_unmasked_on_move`,
   `test_out_of_zone_blob_flagged`, `test_uniform_brightness_step_gives_no_motion`,
   `test_shake_returns_empty_and_counts`, `test_motion_zone_crop_maps_to_wall_cell`, and
   `test_features_under_3ms_at_160x120` (`@pytest.mark.perf`, timed with `time.thread_time`).
2. The draft's, adapted (see deviation 12): `test_frame_features_first_frame_has_no_motion`,
   `test_blobs_sorted_by_size_and_capped`, `test_no_blobs_in_a_dim_frame` (unchanged).
3. New: `test_blob_ids_persist_and_velocities_follow`, `test_a_non_finite_centroid_is_dropped`,
   `test_a_blob_lost_and_found_far_away_gets_a_new_id`.
4. Extra, mine: `test_static_lamps_do_not_crowd_out_a_moving_light` (deviation 9).

## Runs (from the worktree root)
- `pytest -q -rs --durations=15 tests/arcade/test_blobs.py`: 16 passed in 0.33 s. The slowest tests take 0.03 s each
  (the crowd-out test, the uniform step, the perf test, the static mask), so the file adds about 0.3 s to the suite.
  The plan's share was +4 s.
- `pytest -q -rs tests/arcade/test_blobs.py tests/arcade/test_sensed.py tests/arcade/test_game.py`: 85 passed in
  0.33 s, no skips.
- Perf: `FrameFeatures.update` at 160x120 (a textured scene, a moving body, six lights) takes a mean of 0.405 ms and
  at most 0.513 ms (`thread_time`, over 60 updates), against the 3 ms budget. With 32 lights (the `SCAN_BLOBS` worst
  case, measured in a scratch script) it takes a mean of 1.19 ms and at most 1.39 ms.
- The whole suite was not run, as the brief requires.

## Deviations and interpretations, with the reasons
1. **Colour.** The colour is the halo's hue at full saturation, at the value (largest channel) of the core's
   `cv2.mean` over the component's bounding box with its mask. Read alone, the amendment's two clauses ("hue from
   the halo", "colour from `cv2.mean` over the component's bounding box with its mask") conflict for a white core.
   The sensing lens (`reviews/2026-09-26-arcade-review-lenses/03-sensing.md` S3) says: "Take the hue from the halo
   and emit it at full saturation". So the low channel is always 0, and a pastel or white core with a red glow
   gives `(255, 0, 0)`.
2. **Halo saturation.** It is the saturation of the halo's mean colour (one `cv2.mean` with the ring mask), not the
   mean of each pixel's saturation. The per-pixel saturation of near-black noise is random, while the mean colour
   is weighted by the glow. The ring leaves out every lit-core pixel, this component's and any other's.
3. **The draft's `find_blobs`.** `floor` and the 99.5th percentile are gone (`LIGHT_V` replaces them; S3 explains
   why). `min_area=4` is kept. Coordinates are pixel centres, `(cx + 0.5) / w`, so that mirroring with `1 - x` is
   exact.
4. **`FrameFeatures`'s `size` is the motion grid's (width, height)**, as in the draft (`FrameFeatures((16, 12))`
   gives a `(12, 16)` grid) and in `motion_grid`. The default `(160, 120)` is the plan's text. Any frame size is
   accepted and nothing is resized: the Pi's lores stream is already 160x120, and resizing the Mac's 640x480 is
   it21's wiring (see Q2).
5. **The crop at the wall's aspect** keeps the zone's whole width, so a grid column matches the `zone_x` a body
   there has (figures map `zone_x`). Its rows are `width / 2.0`, centred on the zone's middle row and clamped inside
   the frame. A zone narrower than 2:1 loses rows at its top and bottom; a wider zone takes rows from outside it.
6. **The flip.** The flag array of moved pixels is flipped, not the two frames. The result is the same, because
   every step before it is per pixel or symmetric under a flip (the box blur's reflected border included), and
   one flip is cheaper than two.
7. **The median** comes from a histogram (`np.median` costs 0.12 ms at 160x120) and is floored at 1, so a black
   frame does not divide by zero.
8. **The grid.** "Empty" means shape `(0, 0)`: spec 5's "empty when the grid is judged global", as
   `actors.shake` already yields it. The first frame (and a frame of a new size) gives all-False `(h, w)`.
9. **New `SCAN_BLOBS = 32`.** With the draft's cap of 8 before the mask, eight or more still lamps larger than a
   carried light would hold every place and hide it after 5 s, so the mask could never free a place. FrameFeatures
   now finds up to 32, tracks and masks them, and then keeps 8. `test_static_lamps_do_not_crowd_out_a_moving_light`
   pins this. The cost is shown above.
10. **Units.** `vx` and `vy` are the matched step over dt in the blob's own coordinates (x in frame widths per
    second, y in frame heights per second, as `Body.vx` and `vy`). E0's comment says "fw/s", which is exact for
    `vx` only (Q3). Distances for `MATCH_DIST` and `STATIC_MOVE` are in frame widths (`dy / aspect`), with the
    aspect taken from each frame.
11. **Tracker.** It pairs greedily, nearest pairs first, with the previous capture only: there is no coasting, so a
    blob missing for one capture gets a new id when it returns. Ids start at 1 and are never reused. A repeated
    capture time keeps the last velocity. The non-finite drop happens in `find_blobs`, at the component and before
    a `Blob` is built, because `Blob.__post_init__` already turns NaN into 0.0, so nothing non-finite could reach
    the tracker.
12. **Draft tests.**
    - The draft's `test_bright_disc_becomes_one_blob_with_rgb_colour` and `test_motion_grid_marks_changed_region_only`
      are replaced by the amendment's tests, as the amendment says ("replace the old blob tests"). Under the
      amendment, the draft's half-frame white change would be a lamp and a shake.
    - `test_blobs_sorted_by_size_and_capped` now uses lights with halos at 160x120. The draft's 8 px white disc is a
      rejected lamp now.
    - `test_frame_features_first_frame_has_no_motion` keeps its point: the first update, even of a frame with a
      light, has no motion, and the next one does, on the mirrored side.
13. **`StaticMask`** is keyed by the tracker's id. It measures stillness from the point where the blob stopped, not
    from capture to capture, so a slow drift still unmasks it. An untracked blob (id -1) is always shown.
    `Calibration.static_mask` (the lights captured at calibration) is not applied: S1's text does not ask for it,
    and it belongs to it21 or to calibrate.

## Owner questions (each with a default)
- **Q1, `MIN_AREA` at 160x120.** The draft's 4 px was set when blobs ran on the 640x480 frame, which has 16 times the
  area. Rough estimate: at 160 px across about 4 m (3 m away), a 2 cm glow stick's core is about 1 px wide, and a
  15 cm stick is a few px long before bloom. Default: keep 4 until GATE A's recorded lamps, then refit it with C34.
- **Q2, the default grid size.** `FrameFeatures(size=(160, 120))` is the plan's text, but a grid at the wall's
  `MOTION_GRID` (128, 64) would make the runner's `with_motion` a no-op. The runner resamples any grid, so both work.
  Default: keep the plan's, and let it21's wiring pass the size. it21 also downsizes the Mac's 640x480 before
  `update`; at 640x480 the lens measured `find_blobs` at about 10 ms.
- **Q3, `vy`'s unit.** E0's comment says fw/s, while `vy` here is in frame heights per second (Blob's own y, as
  `Body.vy`). Default: keep it, and correct the comment in `sensed.py` when E0's file is next touched (not my file).
- **Night note (no question).** On a very dark frame the median is small, so dividing by it amplifies noise and
  more grids come back as shakes, which are empty. That is the safe way to fail. Tuning it waits for GATE A's
  recordings.
