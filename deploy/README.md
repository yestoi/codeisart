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
pings systemd's watchdog every few seconds (`WatchdogSec=15`); a hung daemon is
killed and restarted. `ProtectSystem=strict` makes the system read-only; only
`entries/` and a private `/tmp` are writable.

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
