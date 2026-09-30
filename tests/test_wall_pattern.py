import numpy as np
import pytest

from show.display.colorlight import ColorlightDisplay
from show.display.fake import FakeDisplay
from tests.colorlight_fakes import SYNC, Cranked, FakeClock, FakeSocket
from tools import wall_pattern as wp

LAYOUTS = [(128, 64), (128, 32), (64, 64)]
RED, GREEN, BLUE, WHITE = (wp.LEVEL, 0, 0), (0, wp.LEVEL, 0), (0, 0, wp.LEVEL), (wp.LEVEL,) * 3


class Recording(FakeDisplay):
    """A FakeDisplay that keeps every frame and every brightness level."""

    def __init__(self):
        super().__init__()
        self.frames, self.levels = [], []

    def push(self, frame):
        super().push(frame)
        self.frames.append(frame.copy())

    def set_brightness(self, level):
        super().set_brightness(level)
        self.levels.append(level)


def run(pattern, display, **kw):
    kw.setdefault("sleep", lambda s: None)
    kw.setdefault("out", [].append)
    return wp.run(pattern, display, 128, 32, **kw)


@pytest.mark.parametrize("pattern", sorted(wp.PATTERNS))
@pytest.mark.parametrize("width,height", LAYOUTS)
def test_every_pattern_is_a_uint8_frame_that_lights_under_half_the_wall(pattern, width, height):
    frame = wp.PATTERNS[pattern](width, height, 0.0)
    assert frame.shape == (height, width, 3) and frame.dtype == np.uint8
    assert frame.mean() / 255.0 < 0.5   # the power supply is sized for 0.4, and this runs at the desk


@pytest.mark.parametrize("width,height", LAYOUTS)
def test_rgb_is_four_bands_red_green_blue_white_from_the_left(width, height):
    frame = wp.rgb(width, height, 0.0)
    band, y = width // 4, height - 1            # the bottom row is below the letters
    for i, colour in enumerate([RED, GREEN, BLUE, WHITE]):
        assert tuple(frame[y, i * band + band // 2]) == colour
        assert tuple(frame[y, i * band]) == colour and tuple(frame[y, (i + 1) * band - 1]) == colour


def test_rgb_letters_are_dark_holes_inside_their_bands():
    frame = wp.rgb(128, 32, 0.0)
    for i in range(4):
        band = frame[:12, i * 32:(i + 1) * 32]
        assert (band.reshape(-1, 3).sum(axis=1) == 0).any()      # the letter
    assert not (frame[12:].reshape(-1, 3).sum(axis=1) == 0).any()  # nothing dark below it


@pytest.mark.parametrize("width,height", [(128, 32), (64, 64)])   # 128x64 has two seams: the test below
def test_index_marks_the_four_corners_and_the_panel_seam(width, height):
    frame = wp.index(width, height, 0.0)
    assert tuple(frame[0, 0]) == RED                      # top left
    assert tuple(frame[0, width - 1]) == GREEN            # top right
    assert tuple(frame[height - 1, 0]) == BLUE            # bottom left
    assert tuple(frame[height - 1, width - 1]) == WHITE   # bottom right
    cyan, yellow = (0, wp.LEVEL, wp.LEVEL), (wp.LEVEL, wp.LEVEL, 0)
    if width > height:    # two 64x32 panels side by side: the seam is between two columns
        assert tuple(frame[height // 2, width // 2 - 1]) == cyan
        assert tuple(frame[height // 2, width // 2]) == yellow
    else:                 # stacked: the seam is between two rows
        assert tuple(frame[height // 2 - 1, width // 2]) == cyan
        assert tuple(frame[height // 2, width // 2]) == yellow


def test_index_marks_every_panel_seam():
    cyan, yellow = (0, wp.LEVEL, wp.LEVEL), (wp.LEVEL, wp.LEVEL, 0)
    f = wp.index(128, 64, 0.0)
    assert tuple(f[5, 63]) == cyan and tuple(f[5, 64]) == yellow          # the column seam
    assert tuple(f[31, 5]) == cyan and tuple(f[32, 5]) == yellow          # the row seam
    wide = wp.index(128, 32, 0.0)
    assert tuple(wide[5, 63]) == cyan and tuple(wide[5, 64]) == yellow
    assert (wide == cyan).all(axis=2)[5].sum() == 1           # one seam, no row seam
    tall = wp.index(64, 64, 0.0)
    assert tuple(tall[31, 5]) == cyan and tuple(tall[32, 5]) == yellow
    assert (tall == yellow).all(axis=2)[:, 5].sum() == 1      # one seam, no column seam


def test_default_size_is_the_four_panel_wall():
    args = wp.build_parser().parse_args(["index"])
    assert (args.width, args.height) == (128, 64)
    assert (wp.PANEL_W, wp.PANEL_H) == (64, 32)


@pytest.mark.parametrize("width,height", LAYOUTS)
def test_gamma_has_a_checker_between_a_128_patch_and_a_186_patch(width, height):
    frame = wp.gamma(width, height, 0.0)
    third = width // 3
    top = frame[: height // 2]
    assert (top[:, :third] == 128).all()
    assert (top[:, 2 * third:3 * third] == 186).all()
    checker = top[:, third:2 * third, 0].astype(int)
    assert set(np.unique(checker)) == {0, 255}
    assert (np.abs(np.diff(checker, axis=1)) == 255).all() and (np.abs(np.diff(checker, axis=0)) == 255).all()
    assert not frame[height // 2: height - height // 4].any()       # a dark gap, then the ramp
    ramp = frame[height - height // 4:, :, 0].astype(int)
    assert ramp[0, 0] == 0 and ramp[0, -1] == 255 and (np.diff(ramp[0]) >= 0).all()
    assert len(np.unique(ramp)) == 16 and (ramp == ramp[0]).all()


def test_steps_walks_the_syncs_level_and_shows_which_step():
    display = Recording()
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("steps", display, brightness=0.4, seconds=8.0, fps=1, clock=lambda: next(clock))
    shown = [lv for lv in display.levels if lv > 0]
    assert shown[0] == 0.05 and set(shown) == {0.05, 0.1, 0.2, 0.4}
    assert shown == sorted(shown)                                  # it climbs, 2 s a step
    bars = [int((f[-1, :, 0] > 0).sum()) for f in display.frames[:-2]]
    assert sorted(set(bars)) == [32, 64, 96, 128]                  # a bar a quarter of the wall per step


def test_steps_never_passes_the_brightness_asked_for():
    display = Recording()
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("steps", display, brightness=0.1, seconds=8.0, fps=1, clock=lambda: next(clock))
    assert max(display.levels) == 0.1


def test_run_sets_the_brightness_first_and_ends_dark_and_closed():
    display = Recording()
    clock = iter(np.arange(0.0, 100.0, 0.5))
    assert run("rgb", display, brightness=0.1, seconds=2.0, fps=2, clock=lambda: next(clock)) == 0
    assert display.levels[0] == 0.1
    assert len(display.frames) >= 3 and display.frames[0].any()
    assert not display.frames[-1].any() and not display.frames[-2].any()   # black, sent twice (see colorlight)
    assert display.closed


def test_run_ends_dark_and_closed_when_interrupted():
    display = Recording()

    def interrupted(seconds):
        raise KeyboardInterrupt

    assert run("index", display, brightness=0.1, seconds=0.0, fps=20, sleep=interrupted) == 0
    assert not display.frames[-1].any() and display.closed


@pytest.mark.parametrize("level", [0.41, 1.0, 0.0, -0.1, float("nan")])
def test_run_refuses_a_brightness_outside_the_supply_cap(level):
    display, said = Recording(), []
    assert run("rgb", display, brightness=level, seconds=1.0, out=said.append) == 2
    assert display.frames == [] and display.levels == []
    assert "0.4" in said[-1]


def test_run_refuses_an_unknown_pattern():
    display, said = Recording(), []
    assert run("plaid", display, brightness=0.1, seconds=1.0, out=said.append) == 2
    assert display.frames == [] and "rgb" in said[-1]


def test_run_says_what_to_look_for_and_where_to_write_it():
    said = []
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("gamma", Recording(), brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), out=said.append)
    text = "\n".join(said)
    assert "gamma = 2.2" in text and "gamma = 1.0" in text
    assert "docs/superpowers/workflow/evidence/hardware.md" in text


def test_the_colorlight_backend_gets_the_level_in_its_first_packets():
    sock, fake = FakeSocket(), FakeClock()
    c = Cranked(sock, fake)
    display = ColorlightDisplay(128, 32, "eth0", sock=sock, brightness=0.1, launch=c.launch, clock=fake.seconds,
                                sleep=c.sleep)
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("rgb", display, brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), sleep=lambda s: c.crank(2))
    levels = {p[35] for p in sock.sent if p[12] == SYNC}
    assert levels == {int(0.1 * 255)}
    assert sock.closed == 1


def test_main_builds_the_display_from_its_arguments(monkeypatch):
    made = {}

    def fake_make_display(cfg, on_key=None):
        made.update(backend=cfg.backend, width=cfg.width, height=cfg.height, iface=cfg.iface,
                    brightness=cfg.brightness)
        return Recording()

    monkeypatch.setattr(wp, "make_display", fake_make_display)
    monkeypatch.setattr(wp.time, "sleep", lambda s: None)
    code = wp.main(["index", "--width", "64", "--height", "64", "--iface", "enp3s0", "--brightness", "0.2",
                    "--seconds", "0.01"])
    assert code == 0
    assert made == {"backend": "colorlight", "width": 64, "height": 64, "iface": "enp3s0", "brightness": 0.2}


def test_main_reports_a_backend_that_cannot_open(monkeypatch, capsys):
    def no_raw_sockets(cfg, on_key=None):
        raise OSError("the colorlight backend needs Linux raw sockets (AF_PACKET)")

    monkeypatch.setattr(wp, "make_display", no_raw_sockets)
    assert wp.main(["rgb"]) == 1
    assert "AF_PACKET" in capsys.readouterr().out


def test_png_saves_the_pattern_without_a_display(tmp_path):
    from PIL import Image

    path = tmp_path / "rgb.png"
    assert wp.main(["rgb", "--png", str(path)]) == 0
    with Image.open(path) as im:
        assert im.size == (128 * 8, 64 * 8)
        assert im.getpixel((8 * 16, 8 * 31)) == RED


# --- the steady sender: deadline pacing, a dry run, the sender's stats

def test_run_is_paced_by_deadlines_not_by_sleep_after_push():
    display, slept, now = Recording(), [], [0.0]

    def clock():
        now[0] += 0.02                      # every read costs 20 ms: a slow render
        return now[0]

    def sleep(s):
        slept.append(s)
        now[0] += s

    run("rgb", display, brightness=0.1, seconds=2.0, fps=10, clock=clock, sleep=sleep)
    assert all(0 < s < 0.1 for s in slept)                       # never the whole period: the render's time is taken off
    assert 17 <= len(display.frames) - 2 <= 21                   # about 10 a second for 2 s, the two black ones aside


def test_run_restarts_the_grid_after_a_late_tick_with_no_catch_up():
    display, slept, now, pushed_at = Recording(), [], [0.0], []
    reads = [0]

    def clock():
        reads[0] += 1
        now[0] += 0.5 if reads[0] == 6 else 0.001              # one stall of half a second
        return now[0]

    def sleep(s):
        slept.append(s)
        now[0] += s

    push = display.push
    display.push = lambda frame: (pushed_at.append(now[0]), push(frame))
    run("rgb", display, brightness=0.1, seconds=1.5, fps=10, clock=clock, sleep=sleep)
    assert min(slept) > 0.05 and len(display.frames) - 2 <= 12  # no burst of pushes after the stall
    gaps = [b - a for a, b in zip(pushed_at, pushed_at[1:])][:-2]
    assert min(gaps) > 0.05 and max(gaps) > 0.4                 # the late push at once, the next a period after it


def test_run_prints_the_senders_stats_at_the_end():
    class WithStats(Recording):
        def stats(self):
            return {"frames": 5, "late": 0, "slips": 0, "worst_us": 30.0, "mean_us": 0.0, "sd_us": 4.0,
                    "errors": 0, "restarts": 0, "rt": True, "wake_worst_us": 0.0, "rows_late": 0, "row_worst_us": 12.0}

    said = []
    clock = iter(np.arange(0.0, 100.0, 1.0))
    run("rgb", WithStats(), brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), out=said.append)
    assert any("colorlight sender: 5 frames" in s and "real-time yes" in s for s in said)


def test_run_reports_a_close_that_fails_and_still_returns():
    class FailsAtClose(Recording):
        def push(self, frame):
            if self.frames and not frame.any():                  # the governed black at the close
                raise OSError("the colorlight sender's send failed: Network is down")
            super().push(frame)

    display, said = FailsAtClose(), []
    clock = iter(np.arange(0.0, 100.0, 1.0))
    assert run("rgb", display, brightness=0.1, seconds=1.0, fps=1, clock=lambda: next(clock), out=said.append) == 1
    assert display.closed and any("closing the wall failed" in s for s in said)


def test_dry_run_builds_the_colorlight_driver_on_a_socket_that_discards(monkeypatch):
    made = {}

    def fake_dry(width, height, brightness):
        made.update(width=width, height=height, brightness=brightness)
        return Recording()

    monkeypatch.setattr(wp, "dry_display", fake_dry)
    monkeypatch.setattr(wp.time, "sleep", lambda s: None)
    assert wp.main(["rgb", "--dry-run", "--brightness", "0.2", "--seconds", "0.01"]) == 0
    assert made == {"width": 128, "height": 64, "brightness": 0.2}


def test_dry_display_is_the_driver_with_a_discarding_socket():
    sock, clock = FakeSocket(), FakeClock()
    c = Cranked(sock, clock)
    d = wp.dry_display(128, 64, 0.1, launch=c.launch, clock=clock.seconds, sleep=c.sleep)
    assert d.width == 128 and d.brightness == 0.1
    assert d.sock.send(b"x" * 405) == 405 and d.sock is not sock       # the discarding sink, not a raw socket
    d.close()


def test_stop_for_pauses_the_display_and_pushes_nothing_meanwhile():
    class Pausable(Recording):
        def __init__(self):
            super().__init__()
            self.paused_at = []

        def pause(self):
            self.paused_at.append(len(self.frames))

    display, said, now = Pausable(), [], [0.0]

    def clock():
        return now[0]

    def sleep(s):
        now[0] += s

    run("grid", display, brightness=0.1, seconds=12.0, fps=10, clock=clock, sleep=sleep, out=said.append,
        stop_for=3.0)
    assert len(display.paused_at) == 1 and 45 <= display.paused_at[0] <= 55    # at 5 s in
    assert 85 <= len(display.frames) - 2 <= 95                                  # 3 s of no pushes out of 12
    assert any("stopped the stream for 3" in s for s in said)
    assert wp.build_parser().parse_args(["grid", "--stop-for", "3"]).stop_for == 3.0
