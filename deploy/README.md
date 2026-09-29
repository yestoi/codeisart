# Pi 4 deployment

Nothing here is installed by the repo. The owner installs it by hand on the Pi.

1. Flash Raspberry Pi OS Lite (64-bit), or the Falcon Player image for the DDP path.
2. `sudo apt install -y git python3-venv python3-dev build-essential libsdl2-dev alsa-utils`
3. `git clone <repo> /home/pi/codeisart && cd /home/pi/codeisart`
4. `python3 -m venv .venv && .venv/bin/pip install -e '.[pi]'`
5. Edit `show.toml`: set `backend` to `ddp` or `colorlight`, and `brightness`.
6. Edit `deploy/show.service`: change `User=` and every `/home/pi/codeisart` path to
   match your machine. Raspberry Pi OS Bookworm has no `pi` user unless you create one
   in the imager, so check with `id`.
7. `sudo cp deploy/show.service /etc/systemd/system/ && sudo systemctl daemon-reload`
8. `sudo systemctl enable --now show`
9. Check: `journalctl -u show -f`.

The unit never gives up (`StartLimitIntervalSec=0`, `Restart=always`) and the daemon
pings systemd's watchdog (`WATCHDOG=1`) every second (`WatchdogSec=15`); a hung daemon is
killed and restarted. `ProtectSystem=strict` makes the system read-only; only
`entries/` and a private `/tmp` are writable.

## Stop, and a broken config

`systemctl stop show` sends SIGTERM. The daemon sends two governed black frames and turns
the lights off, then exits. The entries die with the unit's cgroup (the default
`KillMode`, which the unit does not change).

A broken `show.toml` puts the error frame on the file's own display, at the lower of the
file's brightness and the default. If the file is not valid TOML the display is `sdl`;
read `journalctl -u show` for the reason.

With no carrier the start waits for `network-online.target` (the wait-online timeout),
then runs anyway. The unit stays ordered after `network-online.target` (Q63).

## Soak and test pattern

Stop the unit first (`sudo systemctl stop show`); the soak and the pattern tool need the
wall to themselves. The overnight soak and the GATE C soak:

    .venv/bin/python -m tools.show_soak --minutes 600 --press-every 180 --real-devices

While it runs, watch the CPU temperature (`while sleep 10; do vcgencmd measure_temp; done`).
Afterwards, with the unit running again, `systemctl show show -p NRestarts` must say
`NRestarts=0`.

The test pattern goes through the governor, capped:

    .venv/bin/python tools/wall_pattern.py --config show.toml

## Hardware watchdog

In `/etc/systemd/system.conf` set `RuntimeWatchdogSec=20`, then reboot. Add
`dtparam=watchdog=on` to `/boot/firmware/config.txt` if `/dev/watchdog` is missing.

## Read-only overlay filesystem

Enable the overlay filesystem (`sudo raspi-config`, Performance Options, Overlay File
System) so a generator refuel cannot corrupt the SD card. `entries/` must stay writable
or be on a separate partition: turn the overlay on only after the entries are in place.
A second Pi 4 with a cloned card travels with the piece.

## Brightness

Brightness is set on the card or in Falcon Player's output brightness, never by scaling
pixels in software. Falcon Player's output brightness must equal `show.toml`'s
`brightness`, and neither may ever exceed `brightness_cap`.

## Colorlight raw backend

The unit grants `CAP_NET_RAW` (`AmbientCapabilities`), needed only for the `colorlight`
backend. The card sits on a dedicated USB gigabit Ethernet adapter.

## LEDVision settings record

The card is configured with LEDVision 8.8 on a Windows PC wired directly to the card
(gigabit Ethernet, no sender card), following the Wired Watts guide: "14 full color
eight scan", saved to the receiver cards. Record the final settings here once they are
set, and configure the spare card identically:

- Receiving card:
- Scan / driver settings:
- Chain order and ports:
- Brightness on the card:
