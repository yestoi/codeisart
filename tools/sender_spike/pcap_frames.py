import os
import sys, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcapng

path = sys.argv[1]
pk = [p for p in pcapng.read(path) if p[1][0:6].hex() == "112233445566"]
# group into frames: a frame starts at the first 0x01 after a non-0x01 packet
frames = []
cur = None
prevtype = None
for ts, b, orig in pk:
    t = b[12]
    if t == 0x01 and prevtype != 0x01:
        cur = {"t": ts, "types": collections.Counter(), "first_row": None, "last": ts, "rows": [], "sync": b}
        frames.append(cur)
    if cur is not None:
        cur["types"][t] += 1
        cur["last"] = ts
        if t == 0x55:
            if cur["first_row"] is None:
                cur["first_row"] = ts
            cur["rows"].append((b[13] << 8) | b[14])
    prevtype = t
per = [(b["t"] - a["t"]) * 1000 for a, b in zip(frames, frames[1:])]
print(path)
print(" frames", len(frames), " fps %.2f" % (1000 / statistics.mean(per)))
print(" period ms: mean %.3f median %.3f min %.3f max %.3f stdev %.3f" % (
    statistics.mean(per), statistics.median(per), min(per), max(per), statistics.pstdev(per)))
hist = collections.Counter(round(p) for p in per)
print(" period histogram (ms: count):", sorted(hist.items()))
burst = [(f["last"] - f["t"]) * 1000 for f in frames[:-1]]
print(" burst length ms (first 0x01 to last packet of frame): mean %.3f max %.3f" % (statistics.mean(burst), max(burst)))
gap = [(b["t"] - a["last"]) * 1000 for a, b in zip(frames, frames[1:])]
print(" idle gap ms (last row to next 0x01): mean %.3f min %.3f max %.3f" % (statistics.mean(gap), min(gap), max(gap)))
shapes = collections.Counter(tuple(sorted(f["types"].items())) for f in frames[:-1])
print(" frame shapes:", shapes.most_common(5))
rowsets = collections.Counter((len(f["rows"]), len(set(f["rows"])), min(f["rows"]) if f["rows"] else -1, max(f["rows"]) if f["rows"] else -1) for f in frames[:-1])
print(" rows per frame (packets, distinct rows, min, max):", rowsets.most_common(5))
syncs = collections.Counter(f["sync"][13:60].hex() for f in frames)
print(" distinct 0x01 payload prefixes:", len(syncs))
for k, v in syncs.most_common(3):
    print("   ", v, k)
