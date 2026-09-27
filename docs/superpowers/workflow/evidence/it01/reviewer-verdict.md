## Verdict: APPROVED

## Blocking findings (file:line — what — why it blocks)

None.

- **Plan match:** all 25 code blocks in the plan (every test module, every source file, `pyproject.toml`, `show.toml`, `arcade.toml`) are byte-identical to HEAD. The intermediate `show/display/__init__.py` at 58d476d (Task 4) and 7979d01 (Task 5) also match their plan versions. The five `__init__.py` files are empty, as specified.
- **Commits:** the seven commit subjects match the plan exactly and in order. Each commit's file list matches its task's `git add` list. Only `docs/superpowers/workflow/state.md` is dirty, which the plan allows.
- **`.gitignore`:** the diff only appends lines. The operator's `docs/superpowers/workflow/.blocks` line is kept.
- **Font:** the sha256 of `fonts/5x7.bin` is `c6628e1c13dd7445117e2179862bbe27d43e3ac0ce0b6153b7eee906cccf96ae`, as the plan expects. `arcade/sources/README.md` records mediapipe 1.0.0, opencv-contrib-python 5.0.0.93, numpy 2.5.3, pygame 2.6.1, sounddevice 0.5.6, Pillow 12.3.0 and pytest 9.1.1, matching the plan. `uv pip list` shows one OpenCV only.
- **Asserts:** `git diff 1da4910..HEAD -- tests/` has no removed or changed lines. Every test file is new, so there is nothing to justify.
- **Collect-only:** `66 tests collected`. Per module: doctor 5, show config 5, font 7, display 4, colorlight 14, ddp 4, arcade config 20, calibration 7. These all match the plan.
- **Full run:** `66 passed`. `grep -c SKIPPED` gives `0`.
- **Conventions:** there is no `print` in library code; only `arcade/main.py` prints, as the CLI. Logger names follow the plan (`arcade` in `arcade/calibration.py`, `__name__` in `show/display/ddp.py`). Hardware imports (`cv2`, `sounddevice`, `mediapipe`) sit inside the probes, and the subprocess test confirms this.

## Notes (non-blocking)

Plan defects from the orchestrator's list. I checked each against the running code.

1. **Plan defect, confirmed: brightness packet only from `set_brightness`.** `ColorlightDisplay.set_brightness` (`show/display/colorlight.py`) is the only place that sends the 0x0A brightness packet. `push` sends only the 0x01 frame packet, which does carry brightness bytes at data[21] and data[24..26]. So whether the wall stays capped after the card power-cycles depends on which field the firmware honours; see item 3. I did not re-check Falcon Player's per-frame resend against its source.
2. **Plan defect, confirmed: ColorlightDisplay starts at brightness 1.0.** A `push` before `set_brightness` sends a frame packet with brightness byte 255, which I observed. Together with item 1, anything that pushes without calling `set_brightness` first runs the wall at full brightness. That includes an ad-hoc GATE B test-pattern script. Nothing pushes to hardware this iteration, so it is not blocking. Carry it as must-fix before GATE B: start at the config ceiling, or refuse to push until brightness is set.
3. **Plan defect, confirmed: card firmware version is not in GATE B.** "firmware" appears nowhere in the plan or the spec.
4. **Plan defect, confirmed, and it reaches further: frame dtype/shape unchecked.** DDP sent 96 data bytes for a float64 (1, 4, 3) frame instead of 12, and 48 for a (2, 8, 3) frame on a 4x1 display, with no error (`show/display/ddp.py`, `DDPDisplay.push`). The same dtype gap exists on the wall path: `ColorlightDisplay.push` checks shape but not dtype. A float frame in 0..1 went out as all zeros, and an int64 value of 300 wrapped to 44, both silently (`show/display/colorlight.py`, the `self._pixels[...] = frame.reshape(...)` line in `push`).
5. **Plan defect, confirmed: empty iface.** `make_display(ArcadeConfig(backend="colorlight", iface=""))` raises `AttributeError: 'ArcadeConfig' object has no attribute 'colorlight_iface'` (`show/display/__init__.py`, colorlight branch: `getattr(cfg, "iface", None) or cfg.colorlight_iface`).
6. **Plan defect, confirmed and wider: ArcadeConfig has no range checks.** `apl_cap_day = 5`, `fps = -3`, `gamma = 0`, `sdl_scale = 0` and `dwell_seconds = -1` all load without error (`arcade/config.py`, `load_config`).
7. **Plan defect, confirmed: calibration** (`arcade/calibration.py`, `_from_json`).
   - It accepts `min_height = -3`, `baseline_scale = -1`, a static-mask light at (5, 5) with radius -2, and `audio_floor_db = NaN`.
   - `"calibrated": "no"` loads as `True`, because `bool()` is applied to a string.
   - A single missing key (`audio_floor_db`) discards the whole file with a KeyError warning.
8. **Plan defect, confirmed: SDL test has no asserts.** `test_sdl_display_pushes_headless` (`tests/test_display.py`) asserts nothing, and its `pressed` list is never checked. It only proves that no exception is raised.
9. **Plan defect, confirmed: `row_packets` vs `push` at width 384.** At width 384, `push` sends two 192-pixel packets per row (597 bytes each), while `row_packets` sends 256 + 128 (789 and 405 bytes). They are not equal, and the reference test only covers widths 128, 64 and 512. Both encodings are valid on the wire, so only the "push matches the reference" guarantee breaks.

Additional observations, all verbatim from the plan and minor:

10. **Doctor edge cases** (`arcade/main.py`).
    - `arcade doctor --require ""` exits 0 without running any check.
    - `probe_pose` ignores its `timeout` argument.
    - `probe_camera` only checks its deadline between `cap.read()` calls, so a blocking read can overrun it.
11. **Unanchored `.gitignore` patterns.** `models/`, `data/` and `shots/` match at any depth; a future `tests/data/` fixture directory would be ignored silently. `/data/` etc. would be safer.
12. **`save_calibration` durability** (`arcade/calibration.py`). It fsyncs the file but not the directory after `os.replace`. After a power cut the rename may not have persisted and the old calibration can come back. The result is stale, not corrupt, so it is low risk.
