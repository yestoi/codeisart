from __future__ import annotations

from collections import deque
from collections.abc import Iterator

from show.entries import Entry


class EntryQueue:
    """FIFO of entries waiting to play, deduplicated by value."""

    def __init__(self) -> None:
        self._items: deque[Entry] = deque()

    def push(self, entry: Entry) -> bool:
        if entry in self._items:
            return False
        self._items.append(entry)
        return True

    def pop(self) -> Entry | None:
        return self._items.popleft() if self._items else None

    def peek(self) -> Entry | None:
        return self._items[0] if self._items else None

    def clear(self) -> None:
        self._items.clear()

    def position(self, entry: Entry) -> int | None:
        """1 for the next to play; None when not queued."""
        for i, item in enumerate(self._items, start=1):
            if item == entry:
                return i
        return None

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, entry: object) -> bool:
        return entry in self._items

    def __iter__(self) -> Iterator[Entry]:
        return iter(list(self._items))
