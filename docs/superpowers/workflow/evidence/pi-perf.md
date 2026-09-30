# The Pi 5's timing budgets

The numbers spec 9.2 asks for: the arcade's budget tests on the Pi 5. Run on the Pi as

    ARCADE_TICK_BUDGET_MS=20 ARCADE_GOVERNOR_BUDGET_MS=2 .venv/bin/python -m pytest -m perf -s

The Pi: a Raspberry Pi 5 Model B Rev 1.1, 8 GB, Raspberry Pi OS Lite 64-bit (Trixie), kernel 6.18.50+rpt-rpi-2712,
Python 3.13.5, numpy 2.5.3.

## 2026-09-30, the idle Pi, main at 99930e0 with Q79's change

14 passed (every test marked `perf`), 6 s. MEASURED, on the thread's CPU clock, the medians and means the tests print:

| Test | Wall | Tick mean, ms | Tick p95, ms | Governor median, ms | The governor's share |
|---|---|---|---|---|---|
| strobe (the governor holding) | 128x32 | 0.989 | 1.070 | 0.500 | 51 % |
| strobe | 64x64 | 1.104 | 1.205 | 0.571 | 52 % |
| strobe | 128x64 | 1.642 | 1.802 | 1.048 | 64 % |
| static | 128x32 | 0.935 | 0.946 | 0.455 | 49 % |
| static | 64x64 | 1.025 | 1.038 | 0.521 | 51 % |
| static | 128x64 | 1.515 | 1.531 | 0.948 | 63 % |

The render test's median: 2.77 ms (2.75 to 2.92 over 50).

What the numbers say:

- **The whole tick** is about 1.5 ms at the arcade's 128x64: inside the Pi's 20 ms, and inside the Mac's 2.0 too (the
  full suite with no variable set failed no tick budget on the Pi). At 30 ticks a second a tick has 33 ms.
- **The governor** is 0.95 to 1.05 ms at 128x64, about three times the Mac's 0.3. It fails the Mac's 0.5 ms and passes
  the Pi's 2 (Q79, the owner's, 2026-09-30). In a paced loop, where the core idles between pushes, it measured about
  1.4 ms (docs/superpowers/reviews/2026-09-29-route-a/00-bench.md, section 3).
- **With no variable set** the suite on the Pi fails five or six tests, all the governor's 0.5 ms
  (`tests/arcade/test_flash.py::test_governor_under_half_ms_at_128x32`, at the line: 0.50 to 0.53 ms, and five of
  `tests/arcade/test_headless.py::test_tick_budget_with_the_governors_share`). The full suite takes 766 s there, 321 s
  on the Mac.
