"""Asciinema v2 cast writer and a gap-compressing player."""
from __future__ import annotations

import codecs
import json
import time
from pathlib import Path
from typing import Callable


class CastError(ValueError):
    """A cast file that cannot be read."""


class CastWriter:
    def __init__(self, path: Path, columns: int, rows: int,
                 clock: Callable[[], float] = time.monotonic):
        self.path = Path(path)
        self._clock = clock
        self._t0 = clock()
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._fh = self.path.open("w", encoding="utf-8")
        header = {"version": 2, "width": columns, "height": rows,
                  "timestamp": int(time.time())}
        self._fh.write(json.dumps(header) + "\n")
        self._fh.flush()

    def _emit(self, text: str) -> None:
        if text:
            t = round(self._clock() - self._t0, 4)
            self._fh.write(json.dumps([t, "o", text]) + "\n")
            self._fh.flush()

    def write(self, data: bytes) -> None:
        if self._fh.closed:
            return
        # A character split across two reads is held until its tail arrives.
        self._emit(self._decoder.decode(data))

    def close(self) -> None:
        if self._fh.closed:
            return
        self._emit(self._decoder.decode(b"", final=True))
        self._fh.close()

    def __enter__(self) -> "CastWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class CastPlayer:
    def __init__(self, path: Path, max_gap: float = 2.0):
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as e:
            raise CastError(f"cannot read {path}: {e}") from e
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            raise CastError(f"{path}: no header")
        try:
            self.header = json.loads(lines[0])
        except ValueError as e:
            raise CastError(f"{path}: bad header: {e}") from e
        if not isinstance(self.header, dict):
            raise CastError(f"{path}: header is not an object")
        try:
            self.columns = int(self.header["width"])
            self.rows = int(self.header["height"])
        except (KeyError, TypeError, ValueError) as e:
            raise CastError(f"{path}: header lacks width/height") from e
        self.events: list[tuple[float, bytes]] = []
        t = last = 0.0
        for n, line in enumerate(lines[1:], start=2):
            try:
                ts, kind, text = json.loads(line)
                if kind != "o":
                    continue
                ts = float(ts)
                data = text.encode("utf-8")
            except (ValueError, TypeError, AttributeError) as e:
                raise CastError(f"{path}: bad event {n}: {e}") from e
            t += max(0.0, min(ts - last, max_gap))
            last = ts
            self.events.append((t, data))
        self._i = 0
        self._t0 = 0.0

    def start(self, now: float) -> None:
        self._t0 = now
        self._i = 0

    def tick(self, now: float) -> bytes:
        out = b""
        elapsed = now - self._t0
        while self._i < len(self.events) and self.events[self._i][0] <= elapsed:
            out += self.events[self._i][1]
            self._i += 1
        return out

    @property
    def done(self) -> bool:
        return self._i >= len(self.events)

    @property
    def duration(self) -> float:
        return self.events[-1][0] if self.events else 0.0
