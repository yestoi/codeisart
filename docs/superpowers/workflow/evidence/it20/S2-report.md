# it20 S2: scenario files and replay sources (implementer's report)

Branch `worktree-agent-a8f45f86fcf2790d9`, base b4f1e9b (checked first). Work test-first (superpowers TDD skill).

## Files (all new; nothing else touched, `arcade/sources/__init__.py` not edited, `blobs.py` not imported)
- `arcade/sources/scenario.py`: `make_header`, `check_header`, `encode`, `decode(line, calibration=None)`,
  `RawRecord`, `encode_raw`, `decode_raw`, `wav_bytes`, `wav_samples`, `ScenarioWriter(path, header)`,
  `ScenarioReader(path, calibration=None)` (`header`, `cues`, `skipped`).
- `arcade/sources/replay.py`: `ReplayStream(records, clock)`, `ReplayCamera`, `ReplayAudio`,
  `open_replay(path, calibration=None, clock=time.monotonic)`.
- `tests/arcade/test_scenario.py`: 16 tests.

## Tests and how each failed first
Three red rounds, each run before the code it drove:
1. Sensed records (9 tests): first `ModuleNotFoundError: arcade.sources.scenario`. Then a stub with the API's names
   raising `NotImplementedError`: all 9 failed on it. Then the sensed implementation: 9 passed.
   `test_round_trip`, `test_reader_skips_bad_lines`, `test_a_cut_off_recording_replays_what_it_holds`,
   `test_a_file_without_a_header_is_refused`, `test_gz_round_trip_with_header`, `test_header_cues_readable`,
   `test_sensed_line_has_only_schema_fields`, `test_blob_ids_and_velocities_round_trip`,
   `test_decode_places_bodies_with_the_recordings_calibration`.
2. Raw records (1 test): first `ImportError: cannot import name 'RawRecord'`. Then with the names stubbed to None:
   `TypeError: 'NoneType' object is not callable`. Then the raw implementation: passed. `test_raw_record_round_trip`.
3. Replay (6 tests): first `ModuleNotFoundError: arcade.sources.replay`. Then a stub: all 6 failed with
   `NotImplementedError`. Then a minimal replay that stamps every record as it is read (the plan's words, as
   `ScriptedCamera` does): 5 passed and `test_replay_holds_a_capture_as_the_recording_did` failed
   (`[True, True, ...] != [False, False, ...]`: a 10 fps recording replayed as 30 fresh captures a second). Then
   the capture logic (deviation D1 below): 6 passed. `test_raw_file_is_not_replayed_yet`,
   `test_writer_and_open_replay`, `test_replay_of_empty_stream_yields_empty_sensed`,
   `test_motion_packed_on_128x64_resampled_to_wall`, `test_open_replay_takes_the_recordings_calibration`,
   `test_replay_holds_a_capture_as_the_recording_did`.

All eleven acceptance tests the plan names are present under their names. Five are added:
`test_a_cut_off_recording_replays_what_it_holds` and `test_a_file_without_a_header_is_refused` (Review Focus 4 for
gzip), `test_raw_file_is_not_replayed_yet`, `test_open_replay_takes_the_recordings_calibration` (C21 through
`open_replay`), `test_replay_holds_a_capture_as_the_recording_did` (D1).

## Counts and times
`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs --durations=15
tests/arcade/test_scenario.py tests/arcade/test_sensed.py tests/arcade/test_game.py`: 85 passed (16 + 27 + 42), 0
skipped, 0.16 to 0.23 s. My file's slowest: `test_a_cut_off_recording_replays_what_it_holds` 0.04 s,
`test_gz_round_trip_with_header` 0.01 s, `test_replay_holds_a_capture_as_the_recording_did` 0.01 s; the rest under
0.005 s. S2 adds about 0.1 s to the suite (the plan's share is 2 s). The whole suite was not run (the brief).

## The record schema as built
- File: gzip (`gzip.open` text mode, UTF-8, level 6 on write; read with `errors="replace"` so a bad byte spoils
  one line only). Line 1 is the header; one record per line after it.
- Header: `{"kind": "header", "version": 1, "type": "sensed" | "raw", "fps": <number>, "grid": [128, 64],
  "script": <str|null>, "cues": [[t, "TEXT"], ...], "created": <ISO 8601 UTC|null>, "git": <str|null>}`.
  `check_header` refuses another version, type or grid, a non-finite or non-positive fps, or bad cues.
  `make_header(type="sensed", *, fps=30, script=None, cues=(), created=None, git=None)` builds one; `created`
  defaults to now (UTC); `git` is the caller's (this module never reads the checkout, no subprocess).
- Sensed record, every key a field name of the dataclass it encodes:
  `{"t", "camera_t", "camera_fresh", "bodies": [{"id", "box", "keypoints": [[x, y, conf], x17], "vx", "vy",
  "scale", "seen_ago", "measured", "torso_per_width"}], "blobs": [{"x", "y", "size", "color", "id", "vx", "vy"}],
  "motion": <base64 of np.packbits over the 128x64 grid, 1024 bytes>|null, "audio": {all ten Audio fields}}`.
  Coordinates, times and velocities are rounded to 4 places, confidences to 3. Not stored: `player`, `player2`,
  `present`, `camera_seq` (the runner sets them) and `in_zone`, `zone_x`, `zone_y` (decode places again).
  Motion of another shape is resampled (`sensed._resample`, every lit cell kept) to 128x64 on encode; null is
  the empty grid. Decode gives the 128x64 grid or the empty `(0, 0)` grid, never None; the runner's
  `with_motion(cfg.size)` takes it to the wall.
- Raw record: `{"t": <capture time, 6 places>, "detections": [{"box", "keypoints"}], "frame": <base64 of a 120x160
  uint8 grey frame>, "wav": <base64 of a WAV: a 44-byte RIFF header packed with struct, mono, 16-bit PCM, 16 kHz,
  then the samples>}`. One WAV per record (the capture's sound), so a record stands alone. `RawRecord(t, *,
  detections, frame, samples)` (keywords after t, as C21 asks of Sensed); `wav_samples` reads the length from the
  data chunk's header. No `wave` module, no `.save`, no `imwrite`.

## Deviations from the plan or the draft, and why
- D1 (replay stamping). The plan says "stamped as `ScriptedCamera` stamps": every record a fresh capture at the
  clock. That is what a scene of actors gives (every record fresh, `camera_t == t`), and there replay does exactly
  that. A recording of the runner's Sensed from a 10 fps camera holds each capture over three ticks; stamping
  every record would hand the runner 30 captures a second, and the games that work per capture
  (`input.Glide` by `camera_t`, Freeze's per-capture observation, Flap's wrist captures) would see three
  captures where the camera gave one. So a record stores `camera_t` and `camera_fresh` (Sensed fields, within
  spec 6.5's schema), and `ReplayStream` stamps a new capture only on a fresh record, at the read time less its
  age (`t - camera_t`); a held record keeps the last capture's stamp. Before the recording's first capture
  `ReplayCamera.latest()` gives None (the `| None` of its signature), as a live camera does. The test that
  drives it replays `degrade(scene(...))` through `Runner.sense` and gets the recording's fresh ticks, bodies and
  ages; it failed against the every-record stamping.
- D2 (after the end). The draft holds the last record (kept, its test kept). The held capture keeps its old stamp,
  so the runner sees it go stale after `CAMERA_STALE` (audio after `AUDIO_STALE`), and `available` is a property,
  `not stream.finished`, as `ScriptedCamera.available` reports frames that ran out (the draft had `available =
  True` always). `test_writer_and_open_replay` asserts both.
- D3 (blobs re-placed). C21 and the plan say `place()` on every body; decode also runs `place_blob` on every blob
  with the same calibration, so `Blob.in_zone` is not stored either and follows the caller's calibration.
- D4 (the draft's tests adapted, as the plan asks): the 3-tuple `cam.latest()` is the 4-tuple `CameraResult`;
  `aud.latest() == Audio()` is `(clock.now, Audio())`; `decode(...).motion is None` is the `(0, 0)` grid; the
  draft's `Audio(level=0.8, peak=1.0, onset=True)` is today's `claps()` record (`d.audio == s.audio`, clap and
  onset set); the round trip's grid is 128x64 in the file and resampled back to the draft's 16x8 for the compare;
  files are `.jsonl.gz` with a header; `ScenarioWriter` takes a header. The sample gained a lit motion rectangle
  (the draft's all-False grid could not catch a packing bug). No assert's meaning was weakened. 16x8 is the
  draft's sample grid, not a wall size (Q82); every runner in the tests is 128x64.
- D5 (additions to the signatures): `open_replay` and `ReplayStream` take `clock` (the runner's injected clock,
  as `ScriptedCamera(frames, clock)`); `ScenarioReader` takes `calibration` (for `open_replay`'s); `close()` on the
  sources closes the reader's generator and so its file.
- D6 (bad files). A missing or unreadable header, or a file that is not gzip, raises ValueError when the reader is
  opened (at startup, before the runner ticks). A file cut off mid-write (no gzip end) yields its readable lines,
  then one warning, `skipped += 1`, and ends: never an exception into the runner.
- Not built (the plan: iteration 21): raw replay through `FrameFeatures` and `BodyTracker` (`open_replay` refuses
  a raw file with ValueError), the `record` and `calibrate` CLI, the source factory, an `__init__` export.

## Owner questions (each defaulted)
- Q-S2a: D1, replay keeps the recording's captures (fresh ticks and ages) rather than a fresh capture every tick.
  Default: keep it; a scene of actors replays exactly as `ScriptedCamera` would either way.
- Q-S2b: raw records carry one WAV per capture (base64, inside the line) rather than one WAV beside the file.
  Default: per record, so a cut-off file loses only its tail and a record stands alone.
- Q-S2c: decode re-places blobs with the caller's calibration (D3). Default: yes, as bodies.
