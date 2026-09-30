"""What the sync (0x01) packets of a capture hold: lengths, non-zero bytes, bytes that change, other packet types.

Usage: python tools/sender_spike/pcap_sync.py CAPTURE.pcapng [CAPTURE.pcapng ...]
Offsets count from the start of the Ethernet frame (the packet type is byte 12).
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcapng

COLORLIGHT_DST = "112233445566"

for path in sys.argv[1:]:
    pk = [p for p in pcapng.read(path) if p[1][0:6].hex() == COLORLIGHT_DST]
    syncs = [b for ts, b, orig in pk if b[12] == 0x01]
    print(os.path.basename(path))
    print(" sync packets", len(syncs), "lengths", dict(collections.Counter(len(s) for s in syncs)))
    first = syncs[0]
    print(" non-zero bytes of the first (offset: value):",
          [(i, hex(first[i])) for i in range(12, len(first)) if first[i]])
    seen = collections.defaultdict(set)
    for s in syncs:
        for i in range(12, len(s)):
            seen[i].add(s[i])
    print(" offsets that change (offset: distinct values):", {i: len(v) for i, v in seen.items() if len(v) > 1})
    counter = [s[14] for s in syncs]
    print(" byte 14 step between syncs:",
          dict(collections.Counter((b - a) % 256 for a, b in zip(counter, counter[1:]))))
    rows = [b for ts, b, orig in pk if b[12] == 0x55]
    print(" row packets", len(rows), "lengths", dict(collections.Counter(len(b) for b in rows)),
          "header tail (bytes 19-20)", dict(collections.Counter(b[19:21].hex() for b in rows)))
    print(" other packet types (type, length): count",
          dict(collections.Counter((hex(b[12]), len(b)) for ts, b, orig in pk if b[12] not in (0x01, 0x55))))
