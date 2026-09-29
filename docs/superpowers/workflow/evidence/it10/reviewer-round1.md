## Verdict: APPROVED

## Blocking findings (file:line, the input, what happens, why it blocks)
None.

What I checked and found to work:
- Suite: `pytest --collect-only -q`: 888 collected (762 at the base). The seven show modules: 125 passed, 1 skipped in 4.6 s. The one skip is `test_sandbox.py:153`, the `unshare` loopback test on macOS, which the plan expects.
- Asserts: `git diff 2eb5f3e..HEAD -- tests/` only adds files. No test file is modified or deleted, and no `assert` is removed or changed. The arcade's tests are untouched.
- Every acceptance test the plan names for T3, T4, T6, T7, T8, T9 and T-shot is present, and several have extra coverage.
- Terminal safety probe: 35 runs through one `Terminal` with `limits(2)`. The commands were `true`, `exit 3`, `yes x`, `sleep 30 & exit 0`, `exec >&- 2>&- <&-; sleep 30`, `kill -9 $$`, and invalid UTF-8 plus `ESC[?3h`. Each run was followed by `finished_or_orphaned(0.3)`, `kill()` and `reset()`. The `/dev/fd` count was 4 before and 4 after, and no `sleep`/`yes` process was left.
- `kill()` with the shell exited but not reaped (a zombie) and a SIGHUP-deaf orphan in the group: the orphan dies.
- Pump budget: I measured pyte's cost to feed one `READ_CHUNK` (1024 B) on this Mac. `yes` output takes 1.0 ms, `ESC[H ESC[J` plus text 1.3 ms, invalid UTF-8 0.9 ms, CJK 0.6 ms, SGR soup 0.5 ms and insert-line 0.4 ms. Realistic output stays inside the 8 ms budget.
- Realistic escape output: 97 xterm sequences (every `tput` capability for TERM=xterm plus common extras such as `?1049h`, `?2004h`, `22;0;0t`, `>4;2m`, 256-colour and truecolour SGR, `?3h`, `?5h`) fed without an exception.
- Renderer cache: every pyte method that changes a cell adds to `screen.dirty`, and the renderer redraws the whole frame whenever dirty is non-empty. The cursor state is in the cache key, so the cache is sound.

Deviation (a), accepted. The plan's test is meant to show four things: an exited leader whose background child holds the pty is not `finished`; `finished_or_orphaned(0.3)` is False when the exit is first seen and True 0.3 s later; and the orphan is killed through the group. The committed test proves all four with a Python session leader. Its `sleep` is in the leader's process group and holds the slave, which is the same arrangement dash gives on the Pi.

I ran the plan-exact test from the scratchpad. It fails on this Mac at `assert not term.finished` because EOF arrives at once, which confirms the orchestrator's reason. The `sh` form is still covered on both platforms by `test_finished_or_orphaned_kills_the_orphans_of_a_shell`: on Linux it goes through the grace path, on macOS through the kill on the finished path.

Deviation (b), accepted. The plan types SCRIPTS as `Callable[[], list[Step]]` and Step carries bytes, so a script has to feed data. The warning and the program output are both real `cc -Wall` output. One fidelity loss: `cc` writing to a pipe emits no colour or bold escapes, while on the wall (a pty with TERM=xterm) gcc and clang diagnostics come out bold. The I2 sheet will show them at normal weight.

## Noted, not carried (one line each)
- show/terminal.py:118: the grace starts at the first sighting of the exit, not at the last data, and `kill()` then pumps once (4 KB). On Linux a pty can still hold roughly 64 KB when a fast writer exits (e.g. `seq 1 100000`), so the tail of the output, and with it the final screen, could be dropped. The code matches the plan and spec 4.6 as written. macOS does not show it (`seq 1 200000` ends at `200000` here). Worth one check on the Omarchy box before D2/D3.
- show/terminal.py:59 and 125: `_signal_group()` re-sends SIGKILL to an old pgid on the next `run()` and on every `finished_or_orphaned()` after the finish. Once the group is empty and the pid is reused as a group leader, that signal hits an unrelated process. Unlikely within seconds.
- show/terminal.py: pyte raises TypeError on malformed CSI such as `ESC[?3A`, `ESC[;;@` and `ESC[?1;2c`, and `pump()` propagates it. None of the 97 realistic sequences did this; random binary output hits it at about 1e-8 per byte. D3's loop catches the exception.
- show/terminal.py: `ESC#8` (DECALN) costs about 330 ms per 1024 B chunk in pyte, and an `ESC[2J` flood about 10 ms per chunk on this Mac, so either can overrun `budget_ms` inside one chunk. No realistic program emits these floods.
- show/terminal.py:68: `start_new_session` with a dup'd slave gives the child no controlling terminal on Linux, so an entry that opens `/dev/tty` gets ENXIO. That is a curation concern.
- show/terminal.py: a grandchild that calls `setsid()`/`daemon()` leaves the group and outlives `kill()`. The plan's design is a group kill, and no curated entry is expected to daemonize.
- show/renderer.py:55: DECSCNM (`ESC[?5h`) does not light blank cells that pyte never stored. The plan does not require it.
- show/recording.py:75: a cast cut short mid-line (or mid UTF-8 character) raises CastError, so the whole fallback is dropped rather than its complete events. This matches the plan ("an event not JSON" raises). D2's capture should write to a temp file and rename.
- tools/show_shot.py:97: gcc under a UTF-8 locale on the Pi prints ‘unused’ with U+2018/U+2019 quotes, which render as `?`. D2's build may want `LC_ALL=C`.
