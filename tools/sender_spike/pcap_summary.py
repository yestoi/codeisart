import os
import sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcapng

path = sys.argv[1]
pk = list(pcapng.read(path))
t0 = pk[0][0]
print(path, "packets", len(pk), "duration %.3f s" % (pk[-1][0] - t0))
c = collections.Counter()
for ts, b, orig in pk:
    c[(b[0:6].hex(), b[6:12].hex(), b[12], orig)] += 1
for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:40]:
    print("  dst %s src %s type 0x%02x len %4d  x%d" % (k[0], k[1], k[2], k[3], v))
