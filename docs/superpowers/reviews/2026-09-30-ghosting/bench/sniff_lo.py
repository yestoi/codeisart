"""Bench: count what a sender puts on the loopback interface for a few seconds (nothing reaches the card)."""
import socket, sys, time
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003)); s.bind(("lo", 0)); s.settimeout(0.3)
end = time.time() + float(sys.argv[1]); kinds = {}; lit = rows = 0; sync = None; seen = set()
while time.time() < end:
    try: p, addr = s.recvfrom(4096)
    except socket.timeout: continue
    if addr[2] == socket.PACKET_OUTGOING: continue            # loopback shows each frame twice
    t = p[12]; kinds[t] = kinds.get(t, 0) + 1
    if t == 0x55:
        rows += 1; lit += any(p[21:])
    if t == 0x01 and sync is None: sync = p
print("by type", {hex(k): v for k, v in sorted(kinds.items())}, "| row packets with lit pixels", lit, "of", rows,
      "| sync len", len(sync or b""), "level", sync[35] if sync else None)
