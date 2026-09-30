"""The rest of what a capture holds: where it starts and ends, the row headers, the picture, the sync's byte 37.

Usage: python tools/sender_spike/pcap_detail.py CAPTURE.pcapng [CAPTURE.pcapng ...]
Offsets count from the start of the Ethernet frame (the packet type is byte 12).
"""
import collections
import datetime
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcapng

COLORLIGHT_DST = "112233445566"


def runs(values):
    """[(first index, length, value)] of each run of equal values."""
    out, start = [], 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[start]:
            out.append((start, i - start, values[start]))
            start = i
    return out


for path in sys.argv[1:]:
    pk = list(pcapng.read(path))
    cl = [p for p in pk if p[1][0:6].hex() == COLORLIGHT_DST]
    print(os.path.basename(path))
    print(" packets", len(pk), "to the card", len(cl), "cut short by the capture",
          sum(1 for ts, b, orig in pk if len(b) != orig))
    print(" starts", datetime.datetime.fromtimestamp(pk[0][0], datetime.timezone.utc).isoformat(),
          "lasts %.3f s" % (pk[-1][0] - pk[0][0]))
    frames = []
    before = 0
    for ts, b, orig in cl:
        if b[12] == 0x01:
            if not frames or frames[-1]["rest"]:
                frames.append({"t": ts, "sync": b, "rest": []})
        elif frames:
            frames[-1]["rest"].append(b)
        else:
            before += 1
    first, last = frames[0], frames[-1]
    print(" packets before the first sync:", before)
    print(" first packet: type 0x%02x, byte 14 = %d;" % (cl[0][1][12], cl[0][1][14]),
          "last packet: type 0x%02x;" % cl[-1][1][12],
          "packets after the last sync:", len(last["rest"]))
    print(" sources (byte 6 to 11):", dict(collections.Counter(b[6:12].hex() for ts, b, orig in cl)))
    rows = [b for ts, b, orig in cl if b[12] == 0x55]
    print(" row headers (bytes 13 to 20, with the row number in byte 14 set to 0):",
          dict(collections.Counter((b[13:14] + b"\0" + b[15:21]).hex() for b in rows)))
    whole = [f for f in frames if len([b for b in f["rest"] if b[12] == 0x55]) >= 1]
    order = collections.Counter(
        tuple(b[14] for b in f["rest"] if b[12] == 0x55) == tuple(range(len([b for b in f["rest"] if b[12] == 0x55])))
        for f in whole)
    print(" frames with rows", len(whole), "rows in rising order:", dict(order))
    pictures = [hashlib.sha1(b"".join(b[21:] for b in f["rest"] if b[12] == 0x55)).hexdigest()[:8] for f in whole]
    print(" distinct pictures", len(set(pictures)), "runs of one picture (first frame, frames):",
          [(a, n) for a, n, v in runs(pictures)][:12])
    px = b"".join(b[21:] for b in whole[0]["rest"] if b[12] == 0x55)
    print(" first picture: bytes", len(px), "min", min(px), "max", max(px),
          "mean of wire byte 0, 1, 2: %.1f %.1f %.1f" % tuple(sum(px[i::3]) / len(px[i::3]) for i in range(3)))
    b37 = [f["sync"][37] for f in frames]
    print(" byte 37 values:", dict(collections.Counter(b37)))
    t0 = frames[0]["t"]
    marks = [i for i, v in enumerate(b37) if v != b37[0]]
    print(" syncs where byte 37 is not %d (frame, byte 14, seconds in, value):" % b37[0],
          [(i, frames[i]["sync"][14], round(frames[i]["t"] - t0, 3), b37[i]) for i in marks][:20])
    if len(marks) > 1:
        print(" between them: frames", [b - a for a, b in zip(marks, marks[1:])],
              "seconds", [round(frames[b]["t"] - frames[a]["t"], 3) for a, b in zip(marks, marks[1:])])
    for i in marks[:20]:
        if 0 < i < len(frames) - 1 and i < len(pictures):
            print("   frame %d: picture as before: %s; period before %.3f ms, after %.3f ms" % (
                i, pictures[i] == pictures[i - 1],
                (frames[i]["t"] - frames[i - 1]["t"]) * 1e3, (frames[i + 1]["t"] - frames[i]["t"]) * 1e3))
    print(" the sync beyond byte 40 is all zero:", all(not any(f["sync"][41:]) for f in frames))
