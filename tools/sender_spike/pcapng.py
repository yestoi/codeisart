"""Minimal pcapng reader: yields (timestamp_seconds, packet_bytes, orig_len)."""
import struct


def read(path):
    with open(path, "rb") as f:
        data = f.read()
    pos, end = 0, len(data)
    endian = "<"
    tsres = {}
    nif = 0
    while pos + 12 <= end:
        btype = struct.unpack_from("<I", data, pos)[0]
        if btype == 0x0A0D0D0A:
            bom = struct.unpack_from("<I", data, pos + 8)[0]
            endian = "<" if bom == 0x1A2B3C4D else ">"
            nif = 0
            tsres = {}
        blen = struct.unpack_from(endian + "I", data, pos + 4)[0]
        if blen < 12:
            break
        body = data[pos + 8 : pos + blen - 4]
        if btype == 1:  # interface description
            res = 1e-6
            o = 8
            while o + 4 <= len(body):
                code, ln = struct.unpack_from(endian + "HH", body, o)
                o += 4
                if code == 0:
                    break
                if code == 9 and ln >= 1:
                    v = body[o]
                    res = 2.0 ** -(v & 0x7F) if v & 0x80 else 10.0 ** -v
                o += (ln + 3) & ~3
            tsres[nif] = res
            nif += 1
        elif btype == 6:  # enhanced packet
            ifid, th, tl, cap, orig = struct.unpack_from(endian + "IIIII", body, 0)
            ts = ((th << 32) | tl) * tsres.get(ifid, 1e-6)
            yield ts, body[20 : 20 + cap], orig
        pos += blen
