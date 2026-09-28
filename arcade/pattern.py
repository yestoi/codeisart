"""The pattern check (C24; ITU-R BT.1702-3 Guideline 2; owner Q15): no reversing, oscillating or moving stripes of
more than five light-dark pairs over a quarter of the wall.

A check on content for tests and tools, like flash.flash_area: it reads flash.signals and changes nothing. The
governor holds flashes; a regular pattern that moves is the game's to avoid. Reading (owner question, defaulted):
bands of equal width within 1 px, each light band at least flash.THRESHOLD above its dark neighbours in any one of
flash.signals' three measures of light.
"""
from __future__ import annotations

import numpy as np

from arcade.flash import THRESHOLD, signals

PATTERN_PAIRS = 5                         # more than this many light-dark pairs in a row or column is a pattern
PATTERN_AREA = 0.25                       # a changing pattern may cover at most this share of the wall
MIN_BANDS = 2 * (PATTERN_PAIRS + 1)       # bands in a pattern: light and dark, the two outer ones included


def _mark_line(pos: np.ndarray, up: np.ndarray, n: int, out: np.ndarray) -> None:
    """Marks out (n,) over every stripe run of one line, from its boundaries: pos, the index of the first pixel
    after each step of THRESHOLD or more (ascending), and up, whether that step rises.

    A band lies between two boundaries. A run is consecutive bands whose boundaries alternate rise and fall and
    whose widths are within 1 px of each other; the band on either side of the run (to the next boundary or the
    line's end) counts too when at least the run's narrowest width less 1 px, and is marked no wider than the
    run's widest. A run of MIN_BANDS bands or more is marked."""
    pos, up = pos.tolist(), up.tolist()
    k = len(pos)
    widths = [pos[q + 1] - pos[q] for q in range(k - 1)]

    def emit(s: int, e: int) -> None:            # bands s..e, between boundaries s and e + 1
        lo, hi = min(widths[s:e + 1]), max(widths[s:e + 1])
        before = pos[s] - (pos[s - 1] if s > 0 else 0)
        after = (pos[e + 2] if e + 2 < k else n) - pos[e + 1]
        has_before, has_after = before >= max(1, lo - 1), after >= max(1, lo - 1)
        if (e - s + 1) + has_before + has_after < MIN_BANDS:
            return
        start = pos[s] - (min(before, hi) if has_before else 0)
        end = pos[e + 1] + (min(after, hi) if has_after else 0)
        out[start:end] = True

    s = 0
    for e in range(len(widths)):
        if up[e + 1] == up[e]:                    # two rises (or falls) in a row: no band pair spans them
            if e > s:
                emit(s, e - 1)
            s = e + 1
            continue
        window = widths[s:e + 1]
        if max(window) - min(window) > 1:         # e's width does not fit: the run ends before it
            emit(s, e - 1)
            lo = hi = widths[e]
            first = e
            while first - 1 >= s and max(hi, widths[first - 1]) - min(lo, widths[first - 1]) <= 1:
                first -= 1
                lo, hi = min(lo, widths[first]), max(hi, widths[first])
            s = first
    if s < len(widths):
        emit(s, len(widths) - 1)


def _lines(values: np.ndarray, threshold: float) -> np.ndarray:
    """(m, n) values, one line a row: the (m, n) mask of their stripe runs."""
    m, n = values.shape
    out = np.zeros((m, n), bool)
    if n < MIN_BANDS:
        return out
    d = np.diff(values, axis=1)
    steps = np.abs(d) >= threshold
    for line in np.nonzero(steps.sum(axis=1) >= MIN_BANDS - 1)[0]:   # fewer steps cannot make a run
        at = np.nonzero(steps[line])[0]
        _mark_line(at + 1, d[line, at] > 0, n, out[line])
    return out


def _striped(s: np.ndarray, threshold: float = THRESHOLD) -> tuple[np.ndarray, np.ndarray]:
    """(3, h, w) signals: the (h, w) masks of the stripe runs along the rows and along the columns, in any signal."""
    c, h, w = s.shape                             # every signal's lines at once, then any signal
    rows = _lines(s.reshape(c * h, w), threshold).reshape(c, h, w).any(axis=0)
    cols = _lines(s.transpose(0, 2, 1).reshape(c * w, h), threshold).reshape(c, w, h).any(axis=0).T
    return rows, cols


def stripes(frame: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    """(h, w) bool: the pixels in a row or column run of more than PATTERN_PAIRS light-dark band pairs of equal
    width (within 1 px), each light band at least flash.THRESHOLD above its dark neighbours in flash.signals.
    A frame's (h, w, 3) uint8 bytes, as the flash governor takes them."""
    rows, cols = _striped(signals(np.asarray(frame), gamma))
    return rows | cols


def _hit(mask: np.ndarray, changed: np.ndarray) -> np.ndarray:
    """(m, n): the pixels of mask whose run along their row holds a changed pixel."""
    if not mask.any():
        return np.zeros(mask.shape, bool)
    starts = mask.copy()
    starts[:, 1:] &= ~mask[:, :-1]
    ids = np.cumsum(starts.ravel()).reshape(mask.shape) * mask
    hits = np.bincount(ids.ravel(), weights=(changed & mask).ravel()) > 0
    hits[0] = False
    return hits[ids]


def pattern_area(frames, gamma: float = 2.2) -> float:
    """The largest share of the wall, over consecutive frames, striped in both and changed between them: a run
    of stripes, along a row or a column, counts whole when any of its pixels swings by flash.THRESHOLD or more
    (reversing, oscillating or moving stripes). Static stripes count 0."""
    worst = 0.0
    prev = None                                   # (frame, signals, rows, cols) of the frame before
    for frame in frames:
        frame = np.asarray(frame)
        if prev is not None and np.array_equal(frame, prev[0]):
            continue                              # nothing changed: nothing counts, and the stripes are the same
        s = signals(frame, gamma)
        rows, cols = _striped(s)
        if prev is not None:
            _, ps, prows, pcols = prev
            both_rows, both_cols = rows & prows, cols & pcols
            if both_rows.any() or both_cols.any():
                changed = (np.abs(s - ps) >= THRESHOLD).any(axis=0)
                hit = _hit(both_rows, changed) | _hit(both_cols.T, changed.T).T
                worst = max(worst, float(hit.mean()))
        prev = (frame, s, rows, cols)
    return worst
