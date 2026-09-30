import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcapng

path, start, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pk = [p for p in pcapng.read(path) if p[1][0:6].hex() == "112233445566"]
prev = pk[start][0]
for ts, b, orig in pk[start : start + n]:
    t = b[12]
    if t == 0x55:
        row = (b[13] << 8) | b[14]
        off = (b[15] << 8) | b[16]
        cnt = (b[17] << 8) | b[18]
        extra = "row %3d off %3d cnt %3d tail %s" % (row, off, cnt, b[19:21].hex())
    else:
        extra = b[13:45].hex()
    print("%10.6f  +%8.1f us  0x%02x len %4d  %s" % (ts, (ts - prev) * 1e6, t, orig, extra))
    prev = ts
