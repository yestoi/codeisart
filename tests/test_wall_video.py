"""tools/wall_video.py: frames from a byte stream, every one through the governor, the wall closed dark."""
import io

import numpy as np

from tests.test_wall_pattern import Recording
from tools import wall_video as wv


def test_frames_are_cut_whole_from_the_stream_and_a_short_tail_is_dropped():
    a = np.full((4, 8, 3), 7, np.uint8)
    b = np.arange(4 * 8 * 3, dtype=np.uint8).reshape(4, 8, 3)
    stream = io.BytesIO(a.tobytes() + b.tobytes() + b"\x01\x02\x03")
    got = list(wv.frames(stream, 8, 4))
    assert len(got) == 2 and (got[0] == a).all() and (got[1] == b).all()


def test_play_pushes_every_frame_through_the_governor_and_ends_dark():
    display, said, now = Recording(), [], [0.0]
    frames = [np.full((64, 128, 3), v, np.uint8) for v in (10, 20, 30)]

    def clock():
        return now[0]

    def sleep(s):
        now[0] += s

    assert wv.play(iter(frames), display, 128, 64, fps=30, brightness=0.1, clock=clock, sleep=sleep, out=said.append) == 0
    assert display.levels == [0.1] and len(display.frames) == 3 + 2       # the three, then the governed black
    assert (display.frames[0] == 10).all() and not display.frames[-1].any() and display.closed
    assert any("3 frames shown" in s for s in said)


def test_play_refuses_a_brightness_over_the_cap_without_touching_the_display():
    display, said = Recording(), []
    assert wv.play(iter([]), display, 128, 64, brightness=0.5, out=said.append) == 2
    assert display.frames == [] and display.levels == [] and "0.4" in said[-1]


def test_ffmpeg_argv_scales_letterboxes_and_paces():
    argv = wv.ffmpeg_argv("clip.mp4", 128, 64, 30.0, loop=False)
    assert argv[0] == "ffmpeg" and "-stream_loop" not in argv
    assert argv[argv.index("-vf") + 1] == ("scale=128:64:force_original_aspect_ratio=decrease,"
                                          "pad=128:64:(ow-iw)/2:(oh-ih)/2:black,fps=30")
    assert argv[-4:] == ["-f", "rawvideo", "-pix_fmt", "rgb24"] or argv[-1] == "-"
    assert "-stream_loop" in wv.ffmpeg_argv("clip.mp4", 128, 64, 30.0, loop=True)
