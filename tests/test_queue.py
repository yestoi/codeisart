from tests.show_helpers import HELLO_C, write_entry
from show.entries import load_entry
from show.queue import EntryQueue


def _entries(tmp_path, n):
    return [load_entry(write_entry(tmp_path, f"e{i}", i + 1, HELLO_C)) for i in range(n)]


def test_fifo_and_dedupe(tmp_path):
    a, b = _entries(tmp_path, 2)
    q = EntryQueue()
    assert q.push(a) is True
    assert q.push(b) is True
    assert q.push(a) is False
    assert len(q) == 2 and a in q
    assert q.peek() == a
    assert q.pop() == a
    assert q.pop() == b
    assert q.pop() is None and q.peek() is None


def test_clear(tmp_path):
    (a,) = _entries(tmp_path, 1)
    q = EntryQueue()
    q.push(a)
    q.clear()
    assert len(q) == 0 and a not in q and q.position(a) is None


def test_position_is_one_based_and_moves_up_on_pop(tmp_path):
    a, b, c = _entries(tmp_path, 3)
    q = EntryQueue()
    for e in (a, b, c):
        q.push(e)
    assert [q.position(e) for e in (a, b, c)] == [1, 2, 3]
    q.pop()
    assert q.position(a) is None
    assert [q.position(e) for e in (b, c)] == [1, 2]


def test_iteration_is_in_play_order(tmp_path):
    a, b, c = _entries(tmp_path, 3)
    q = EntryQueue()
    for e in (c, a, b):
        q.push(e)
    assert list(q) == [c, a, b]
    assert len(q) == 3  # iterating does not consume


def test_equal_entries_loaded_twice_are_deduped(tmp_path):
    d = write_entry(tmp_path, "a", 1, HELLO_C)
    first, second = load_entry(d), load_entry(d)
    assert first is not second
    q = EntryQueue()
    assert q.push(first) is True
    assert q.push(second) is False
    assert second in q and q.position(second) == 1
    assert len(q) == 1
