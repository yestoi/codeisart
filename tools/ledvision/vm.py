"""Drive the `ledvision` Windows VM (LEDVision 8.8 for the Colorlight card), from the Omarchy host or the Mac.

    python -m tools.ledvision.vm status                 # VM state, guest IP, the card port's link
    python -m tools.ledvision.vm start                  # starts the NAT network if needed, waits for an IP
    python -m tools.ledvision.vm shot --out shots/vm.png [--crop X,Y,W,H] [--scale 0.75]
    python -m tools.ledvision.vm click 640 400          # guest screen pixels, as in a full-size shot
    python -m tools.ledvision.vm drag 400 144 1000 500
    python -m tools.ledvision.vm type 'C:\\Users\\led\\Documents\\card1.rcvbp'
    python -m tools.ledvision.vm keys KEY_LEFTCTRL KEY_A
    python -m tools.ledvision.vm ledvision              # LEDVision, elevated, on the guest desktop
    python -m tools.ledvision.vm desktop-run 'C:\\Users\\led\\Downloads\\setup.exe'
    python -m tools.ledvision.vm guest 'Get-NetAdapter' # PowerShell in the guest
    python -m tools.ledvision.vm put setup.exe 'C:/Users/led/Downloads/'
    python -m tools.ledvision.vm get 'C:/Users/led/Documents/card1.rcvbp' .
    python -m tools.ledvision.vm stop                   # clean shutdown; the card port goes back to the host

On the Mac set LEDVISION_HOST=trey@192.168.12.127 (or pass --host). Every virsh call then runs on the host
over SSH, so the Mac needs only ssh and Pillow. Guest commands, put and get jump through the host (ssh -J),
so the Mac's key must be in the guest once: `python -m tools.ledvision.vm authorize-key ~/.ssh/id_ed25519.pub`.

Anything started over SSH runs in a hidden session; a program with windows goes through `desktop-run`.
Setup and the LEDVision procedure: tools/ledvision/README.md.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

DOMAIN = "ledvision"
URI = "qemu:///system"
NAT_MAC = "52:54:00:4c:ed:01"         # the guest's libvirt NAT adapter ("NAT" in Windows)
CARD_IFACE = "enp5s0"                 # the host port the card is plugged into (macvtap passthrough)
GUEST_USER = "led"
LEDVISION_EXE = r"C:\Program Files (x86)\ColorLight\LEDVISION\LEDVISION.exe"
SCREEN = (1280, 800)                  # the guest's resolution under OVMF and the VGA model
ABS_MAX = 32767                       # QEMU's absolute pointer range
HOLD_MS = 30
GUEST_SSH_OPTS = ("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "LogLevel=ERROR")

PLAIN = {" ": "KEY_SPACE", "-": "KEY_MINUS", "=": "KEY_EQUAL", "[": "KEY_LEFTBRACE", "]": "KEY_RIGHTBRACE",
         ";": "KEY_SEMICOLON", "'": "KEY_APOSTROPHE", "`": "KEY_GRAVE", "\\": "KEY_BACKSLASH", ",": "KEY_COMMA",
         ".": "KEY_DOT", "/": "KEY_SLASH", "\n": "KEY_ENTER", "\t": "KEY_TAB"}
SHIFTED = {"!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
           "_": "-", "+": "=", "{": "[", "}": "]", ":": ";", '"': "'", "~": "`", "|": "\\", "<": ",", ">": ".",
           "?": "/"}


def keyname(ch: str) -> str:
    """The Linux key code name for one unshifted character (US layout)."""
    if ch.isascii() and ch.isalpha():
        return f"KEY_{ch.upper()}"
    if ch.isascii() and ch.isdigit():
        return f"KEY_{ch}"
    if ch in PLAIN:
        return PLAIN[ch]
    raise ValueError(f"no key for {ch!r} (US layout, ASCII only)")


def keystrokes(text: str) -> list[list[str]]:
    """One chord per character: shift plus the key for capitals and shifted symbols."""
    chords = []
    for ch in text:
        if ch.isascii() and ch.isalpha() and ch.isupper():
            chords.append(["KEY_LEFTSHIFT", keyname(ch)])
        elif ch in SHIFTED:
            chords.append(["KEY_LEFTSHIFT", keyname(SHIFTED[ch])])
        else:
            chords.append([keyname(ch)])
    return chords


def abs_value(pixel: int, size: int) -> int:
    """A screen pixel as QEMU's absolute pointer value, clamped to the screen."""
    pixel = min(max(pixel, 0), size - 1)
    return pixel * ABS_MAX // (size - 1)


def lease_ip(leases: str, mac: str = NAT_MAC) -> str | None:
    """The IPv4 address `virsh net-dhcp-leases` lists for mac, or None."""
    for line in leases.splitlines():
        if mac.lower() in line.lower():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)/\d+", line)
            if m:
                return m.group(1)
    return None


def parse_crop(spec: str) -> tuple[int, int, int, int]:
    """'X,Y,W,H' in guest pixels."""
    parts = [int(p) for p in spec.split(",")]
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("crop is X,Y,W,H with W and H over 0")
    return parts[0], parts[1], parts[2], parts[3]


def link_summary(ethtool: str) -> str:
    """'1000Mb/s Full, link yes' from ethtool's output."""
    field = {k: re.search(rf"{k}:\s*(.+)", ethtool) for k in ("Speed", "Duplex", "Link detected")}
    speed, duplex, link = ((m.group(1).strip() if m else "?") for m in field.values())
    return f"{speed} {duplex}, link {link}"


def pointer_events(x: int, y: int, screen: tuple[int, int] = SCREEN) -> list[dict]:
    return [{"type": "abs", "data": {"axis": "x", "value": abs_value(x, screen[0])}},
            {"type": "abs", "data": {"axis": "y", "value": abs_value(y, screen[1])}}]


def button_event(down: bool) -> list[dict]:
    return [{"type": "btn", "data": {"down": down, "button": "left"}}]


class Host:
    """Runs commands on the VM host: here, or over ssh when target is set."""

    def __init__(self, target: str | None, screen: tuple[int, int] = SCREEN):
        self.target, self.screen = target or None, screen

    def argv(self, argv: list[str]) -> list[str]:
        return ["ssh", "-o", "BatchMode=yes", self.target, shlex.join(argv)] if self.target else argv

    def run(self, argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(self.argv(argv), capture_output=True, check=check)

    def script(self, lines: list[list[str]], pause: float = 0.0) -> None:
        """Several commands in one round trip (one ssh connection), each after the one before succeeds."""
        sep = f" && sleep {pause} && " if pause else " && "
        self.run(["sh", "-c", sep.join(shlex.join(line) for line in lines)])

    def virsh(self, *args: str, check: bool = True) -> str:
        return self.run(["virsh", "-c", URI, *args], check=check).stdout.decode()

    # --- VM state -------------------------------------------------------------------------------------------
    def state(self) -> str:
        return self.virsh("domstate", DOMAIN).strip()

    def guest_ip(self) -> str | None:
        return lease_ip(self.virsh("net-dhcp-leases", "default", check=False))

    def ssh_up(self, ip: str | None) -> bool:
        """The guest's sshd answers. A lease alone proves nothing: libvirt keeps it after a shutdown."""
        return bool(ip) and self.run(["timeout", "3", "bash", "-c", f"exec 3<>/dev/tcp/{ip}/22"],
                                     check=False).returncode == 0

    def ready_ip(self) -> str | None:
        ip = self.guest_ip()
        return ip if self.ssh_up(ip) else None

    def link(self) -> str:
        return link_summary(self.run(["ethtool", CARD_IFACE], check=False).stdout.decode())

    # --- screen and input -----------------------------------------------------------------------------------
    def screenshot(self) -> bytes:
        """The guest screen as the bytes virsh writes (PPM or PNG, whichever QEMU chose)."""
        sh = (f'f=$(mktemp) && virsh -c {URI} screenshot {DOMAIN} --file "$f" >/dev/null && cat "$f"; '
              f'r=$?; rm -f "$f"; exit $r')
        return self.run(["sh", "-c", sh]).stdout

    def qmp_line(self, events: list[dict]) -> list[str]:
        cmd = {"execute": "input-send-event", "arguments": {"events": events}}
        return ["virsh", "-c", URI, "qemu-monitor-command", DOMAIN, json.dumps(cmd)]

    def key_line(self, chord: list[str]) -> list[str]:
        return ["virsh", "-c", URI, "send-key", DOMAIN, "--codeset", "linux", "--holdtime", str(HOLD_MS), *chord]

    def keys(self, *chord: str) -> None:
        self.script([self.key_line(list(chord))])

    def type(self, text: str) -> None:
        self.script([self.key_line(c) for c in keystrokes(text)], pause=0.02)

    def click(self, x: int, y: int) -> None:
        self.script([self.qmp_line(pointer_events(x, y, self.screen)), self.qmp_line(button_event(True)),
                     self.qmp_line(button_event(False))], pause=0.08)

    def drag(self, x0: int, y0: int, x1: int, y1: int, steps: int = 10) -> None:
        lines = [self.qmp_line(pointer_events(x0, y0, self.screen)), self.qmp_line(button_event(True))]
        for i in range(1, steps + 1):
            lines.append(self.qmp_line(pointer_events(x0 + (x1 - x0) * i // steps, y0 + (y1 - y0) * i // steps,
                                                      self.screen)))
        lines.append(self.qmp_line(button_event(False)))
        self.script(lines, pause=0.08)

    # --- the guest over ssh ---------------------------------------------------------------------------------
    def require_ip(self) -> str:
        ip = self.guest_ip()
        if not ip:
            sys.exit("no DHCP lease for the guest yet: is the VM running? (`status`, `start`)")
        return ip

    def jump(self) -> list[str]:
        return ["-J", self.target] if self.target else []

    def guest(self, command: str) -> int:
        argv = ["ssh", *GUEST_SSH_OPTS, *self.jump(), f"{GUEST_USER}@{self.require_ip()}", command]
        return subprocess.run(argv, check=False).returncode

    def scp(self, src: str, dst: str) -> int:
        """Copy with scp; a path starting 'guest:' is on the guest."""
        where = f"{GUEST_USER}@{self.require_ip()}:"
        argv = ["scp", *GUEST_SSH_OPTS, *self.jump(), *(where + p[6:] if p.startswith("guest:") else p for p in (src, dst))]
        return subprocess.run(argv, check=False).returncode


def desktop_run_ps(exe: str) -> str:
    """PowerShell that starts exe elevated on the logged-on desktop through a one-off scheduled task."""
    if "'" in exe:
        raise ValueError("the path may not contain a single quote")
    return ("$exe = '" + exe + "'; "
            "$a = New-ScheduledTaskAction -Execute $exe -WorkingDirectory (Split-Path $exe); "
            "$p = New-ScheduledTaskPrincipal -UserId " + GUEST_USER + " -LogonType Interactive -RunLevel Highest; "
            "Register-ScheduledTask -TaskName vm-desktop-run -Action $a -Principal $p -Force | Out-Null; "
            "Start-ScheduledTask -TaskName vm-desktop-run")


def authorize_key_ps(key: str) -> str:
    key = key.strip()
    if not re.fullmatch(r"(ssh|ecdsa)-[\w@.-]+ [A-Za-z0-9+/=]+( [^'\n]*)?", key):
        raise ValueError("that does not look like one OpenSSH public key line")
    return ("Add-Content -Path C:\\ProgramData\\ssh\\administrators_authorized_keys -Encoding ascii -Value '"
            + key + "'")


def save_image(data: bytes, out: Path, crop: tuple[int, int, int, int] | None, scale: float) -> tuple[int, int]:
    """Crop, scale and save the screenshot with Pillow (the repo's venv) or ImageMagick (a bare host Python)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        if not shutil.which("magick"):
            sys.exit("shot needs Pillow (the repo's venv) or ImageMagick's `magick`")
        ops = (["-crop", f"{crop[2]}x{crop[3]}+{crop[0]}+{crop[1]}", "+repage"] if crop else []) + \
              (["-resize", f"{scale * 100:g}%"] if scale != 1.0 else [])
        subprocess.run(["magick", "-", *ops, str(out)], input=data, check=True)
        w, h = subprocess.run(["magick", "identify", "-format", "%w %h", str(out)], capture_output=True,
                              check=True).stdout.split()
        return int(w), int(h)

    img = Image.open(io.BytesIO(data))
    img.load()
    if crop:
        x, y, w, h = crop
        img = img.crop((x, y, x + w, y + h))
    if scale != 1.0:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    img.save(out)
    return img.size


def wait_for(what: str, check, timeout: float, every: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        got = check()
        if got:
            return got
        time.sleep(every)
    sys.exit(f"timed out after {timeout:.0f}s waiting for {what}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vm", description="Drive the ledvision Windows VM")
    p.add_argument("--host", default=os.environ.get("LEDVISION_HOST", ""),
                   help="ssh target of the VM host (default $LEDVISION_HOST; empty runs here)")
    p.add_argument("--screen", default=os.environ.get("LEDVISION_SCREEN", "x".join(map(str, SCREEN))),
                   help="guest screen WxH for clicks (default 1280x800)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    s = sub.add_parser("start")
    s.add_argument("--timeout", type=float, default=240)
    s = sub.add_parser("stop")
    s.add_argument("--timeout", type=float, default=180)
    s = sub.add_parser("shot")
    s.add_argument("--out", default="shots/vm.png")
    s.add_argument("--crop", type=parse_crop, default=None, help="X,Y,W,H in guest pixels")
    s.add_argument("--scale", type=float, default=1.0)
    s = sub.add_parser("click")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s = sub.add_parser("drag")
    for name in ("x0", "y0", "x1", "y1"):
        s.add_argument(name, type=int)
    s = sub.add_parser("type")
    s.add_argument("text")
    s = sub.add_parser("keys")
    s.add_argument("chord", nargs="+", help="Linux key names held together, e.g. KEY_LEFTALT KEY_Y")
    sub.add_parser("ledvision")
    s = sub.add_parser("desktop-run")
    s.add_argument("exe", help="Windows path of the program")
    s = sub.add_parser("guest")
    s.add_argument("command", help="PowerShell, run in the guest")
    s = sub.add_parser("put")
    s.add_argument("local")
    s.add_argument("remote", help="Windows path, e.g. C:/Users/led/Downloads/")
    s = sub.add_parser("get")
    s.add_argument("remote")
    s.add_argument("local")
    s = sub.add_parser("authorize-key")
    s.add_argument("pubkey", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    w, h = (int(v) for v in args.screen.lower().split("x"))
    host = Host(args.host, (w, h))

    if args.cmd == "status":
        state = host.state()
        print(f"vm {DOMAIN}: {state}")
        if state == "running":
            ip = host.guest_ip()
            print(f"guest ip: {ip or 'no lease yet'}; ssh: {'up' if host.ssh_up(ip) else 'not answering'}")
        print(f"card port {CARD_IFACE}: {host.link()}")
    elif args.cmd == "start":
        if not re.search(r"Active:\s+yes", host.virsh("net-info", "default")):
            host.virsh("net-start", "default")
        if host.state() != "running":
            host.virsh("start", DOMAIN)
        ip = wait_for("the guest's sshd", host.ready_ip, args.timeout)
        print(f"running, guest ip {ip}, ssh up; card port {CARD_IFACE}: {host.link()}")
    elif args.cmd == "stop":
        if host.state() == "running":
            host.virsh("shutdown", DOMAIN)
            wait_for("the guest to shut down", lambda: host.state() == "shut off", args.timeout)
        print(f"shut off; card port {CARD_IFACE}: {host.link()}")
    elif args.cmd == "shot":
        size = save_image(host.screenshot(), Path(args.out), args.crop, args.scale)
        print(f"{args.out} {size[0]}x{size[1]}")
    elif args.cmd == "click":
        host.click(args.x, args.y)
    elif args.cmd == "drag":
        host.drag(args.x0, args.y0, args.x1, args.y1)
    elif args.cmd == "type":
        host.type(args.text)
    elif args.cmd == "keys":
        host.keys(*args.chord)
    elif args.cmd == "ledvision":
        return host.guest(desktop_run_ps(LEDVISION_EXE))
    elif args.cmd == "desktop-run":
        return host.guest(desktop_run_ps(args.exe))
    elif args.cmd == "guest":
        return host.guest(args.command)
    elif args.cmd == "put":
        return host.scp(args.local, "guest:" + args.remote)
    elif args.cmd == "get":
        return host.scp("guest:" + args.remote, args.local)
    elif args.cmd == "authorize-key":
        # The host's own key is already trusted by the guest, so this hop runs on the host.
        ip = host.require_ip()
        run = host.run(["ssh", "-o", "BatchMode=yes", f"{GUEST_USER}@{ip}",
                        authorize_key_ps(args.pubkey.read_text())], check=False)
        sys.stderr.write(run.stderr.decode())
        return run.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
