## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)

None.

## Noted, not carried (one line each)

1. **Fixed.** hello.c at 14728d4 was built in the scratchpad and run with `LINES=23 COLUMNS=80`. Every frame was fed to pyte 80x23 (`it11-review/p4b_hello_all_frames.py`). Over all 60 frames, the most `#` on any row is **6**; before the fix it was 70 on the last frame.
2. **The new test fails before the fix and passes after it.** `test_sample_entry_band_leaves_no_trail` was run against each hello.c through `it11-review/p6_new_test_on_old.py`, which points `HELLO_DIR` at a copy of the entry.
   - At 1bc8eff it FAILS: "a row holds 72 '#' in frame 59; 627 rows are not one contiguous band of 6".
   - At 14728d4 it PASSES.
   - `tests/test_entries.py` run alone: 41 passed.
   - `git diff 1bc8eff..14728d4 -- tests/test_entries.py` removes no line: no existing assert is removed or changed. The existing motion test still sees band columns 0..74 and passes its byte-class check (ESC is allowed).
3. **Still one warning, and the screen still does not scroll.**
   - `LC_ALL=C cc -Wall` gives exactly one warning: `hello.c:21:9: warning: unused variable 'leftover' [-Wunused-variable]`.
   - All 60 frames hold exactly 22 newlines and none ends with one. The pyte cursor ends every frame on row 23, so nothing scrolls. `ESC[K` comes before the row's `\n` test, so the last row still gets no newline.
4. **Nothing else broken.** Probe: `it11-review/p7_hello_capture_replay.py`.
   - Pipeline, capture then replay: capture on gives SOURCE, BUILD, RUN, DWELL, DONE, keeps `fallback.cast`, and leaves no `.part`. A `-Werror` build then gives `build failed (exit 1)`, ERROR_HOLD, then FALLBACK replaying the band, with at most 6 `#` on a row.
   - Attract: the source is now 45 lines. The banner still comes after 40 source lines, and the new source line holds the text `\033[K`, not a raw ESC.
   - No child was left; one `./hello` seen once by `pgrep` was gone a moment later, most likely the operator's suite.
- **Plan wording:** T-hello's plan lists "ESC[H, ESC[2J, ESC[?25l/h only" as hello's escapes; `ESC[K` is now a fifth. pyte handles it, and the plan's own "a band" requirement needs it.
