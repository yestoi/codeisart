# LEDVision VM kit

The Colorlight 5A-75E card is configured once with LEDVision 8.8, which is Windows-only and talks raw Ethernet to
the card. This kit runs it in a Windows 11 VM (`ledvision`) on the Omarchy host, gives the VM the host's second
wired port, and lets an agent on the host or on the Mac drive it: screenshots, clicks, typing, PowerShell, files,
and a webcam photo of the wall to see what the panels do.

```
 Mac (agent, webcam)  --ssh-->  Omarchy host 192.168.12.127
                                 |- enp4s0: LAN, SSH (the host's own)
                                 |- virbr0 (libvirt NAT) -- guest "NAT"      e1000e 52:54:00:4c:ed:01
                                 '- enp5s0 (82574L, macvtap passthrough)
                                          '-- guest "LED-Card" e1000e 52:54:00:4c:ed:02 --cable--> 5A-75E J1/J2 -> panels
```

| File | What |
|---|---|
| `vm.py` | the VM from the command line: `status`, `start`, `stop`, `shot`, `click`, `drag`, `type`, `keys`, `guest`, `put`, `get`, `desktop-run`, `ledvision`, `authorize-key` |
| `wall_cam.py` | a webcam photo of the wall (`shots/wall.png`) |
| `provision/provision.sh` | builds the VM unattended on the host |
| `provision/autounattend.xml`, `provision/setup.ps1.in` | the Windows answer file and first-logon script |
| `../../.claude/skills/ledvision-card-setup/SKILL.md` | the agent's procedure for setting up a card |
| `docs/superpowers/workflow/evidence/hardware.md` | what is known about the card and panels so far |

## 1. Provision (on the Omarchy host, once)

Already done on the Omarchy box (2026-09-28). To rebuild or build elsewhere:

1. BIOS: Intel Virtualization Technology (VT-x) on. VT-d too, if PCI passthrough of the NIC may be needed.
2. `pacman -S qemu-full libvirt virt-install edk2-ovmf swtpm dnsmasq libisoburn uv`,
   `systemctl enable --now libvirtd`, `usermod -aG libvirt $USER`, log in again.
3. The card port must be free of NetworkManager and the host firewall must let libvirt's NAT work. The script
   checks and prints these, which need root:
   ```sh
   printf '[keyfile]\nunmanaged-devices=interface-name:enp5s0\n' | sudo tee /etc/NetworkManager/conf.d/90-ledvision-unmanaged.conf
   sudo nmcli general reload conf
   sudo ufw allow in on virbr0 to any port 67 proto udp; sudo ufw allow in on virbr0 to any port 53
   sudo ufw route allow in on virbr0
   ```
4. Download the Windows 11 x64 ISO from microsoft.com/software-download/windows11 and run
   ```sh
   tools/ledvision/provision/provision.sh --iso ~/Downloads/Win11_25H2_English_x64_v2.iso \
       --key ~/.ssh/id_ed25519.pub --key mac.pub
   ```
   Each `--key` is trusted by the guest's sshd (the host's key is needed for `authorize-key`; add the Mac's too).

Windows installs unattended (about 30 minutes): Windows 11 Pro, unactivated, local admin `led` with auto-logon
(its password is random, in `~/.local/share/ledvision-vm/guest-password` on the host, unless `--password` was
given; only RDP asks for it), firewall off, RDP on, OpenSSH server on. The VM is a throwaway behind NAT; that is
why. The VM built on 2026-09-28 predates this; its password is in the owner's local notes.

## 2. Drive it

On the host, run `python3 -m tools.ledvision.vm ...` from the repo root. On the Mac, from the repo's venv:

```sh
export LEDVISION_HOST=trey@192.168.12.127      # virsh runs there over ssh; guest traffic jumps through it
python -m tools.ledvision.vm authorize-key ~/.ssh/id_ed25519.pub   # once: lets the Mac ssh into the guest
python -m tools.ledvision.vm start             # waits until the guest's sshd answers
python -m tools.ledvision.vm shot --out shots/vm.png --scale 0.75
python -m tools.ledvision.wall_cam --out shots/wall.png
```

- Coordinates for `click`/`drag` are guest pixels on the 1280x800 screen, i.e. a full-size `shot`. After a
  `--scale 0.75` shot, divide what you read by 0.75. Crop to read small text: `--crop X,Y,W,H`.
- `type` is US layout, ASCII. `keys` holds its keys together: `keys KEY_LEFTALT KEY_Y` answers a UAC prompt.
- A program with windows must run on the desktop, not in the ssh session: `desktop-run 'C:\path\app.exe'`
  (elevated, through a scheduled task). `ledvision` does that for LEDVision.
- A real mouse instead: `ssh -L 3389:192.168.122.119:3389 trey@192.168.12.127`, then an RDP client
  (macOS: Windows App) to `localhost:3389` as `led`. Stop RDP before the agent drives the console again.
- `stop` shuts Windows down cleanly; libvirt then gives `enp5s0` back to the host for `tools/wall_pattern.py`.

## 3. Install LEDVision (once per VM)

Done on the current VM (LEDVision 8.8.41956, WinPcap 4.1.3). On a fresh one:

1. Download `https://support.colorlightinside.com/uploads/LEDVISIONV8.8_1712797235.zip` (linked from
   `https://en.colorlightinside.com/service/download/?cat=3559`; the server answers 403 without a browser
   User-Agent and that page as Referer). It holds `LEDVISION_Setup_8.8.41956.exe`
   (sha256 `6974519f2e6adfc268b6a3737d30234f5437f06b6d8870c4b6b4da4f3910d2a6`).
2. `vm put LEDVISION_Setup_8.8.41956.exe C:/Users/led/Downloads/`, then
   `vm desktop-run 'C:\Users\led\Downloads\LEDVISION_Setup_8.8.41956.exe'`. Do not run it with `/S`: it
   bundles the free WinPcap installer, which has no silent mode and hangs invisibly.
3. Click through, with a `shot` before each click: tick "I accept Software agreements", Quick Installation;
   the WinPcap wizard: Next, I Agree, Install (keep "start the driver at boot"), Finish; then **Finish** (not
   Start) on LEDVision's last page.
4. Check: `vm guest "Get-Service npf; Get-ItemProperty HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | ? DisplayName -match 'LED|WinPcap' | ft DisplayName,DisplayVersion"`
   shows npf Running and LEDVISION 8.8, WinPcap 4.1.3.

## 4. Configure a card

The procedure, the safety rules and the answers found so far are in the skill,
`.claude/skills/ledvision-card-setup/SKILL.md`. The short version: keep the wall black and at 40% or less,
detect on adapter **#2**, preset "14 full-color eight scan", 128x64 in two chains, run the Intelligent Setting
wizard watching the wall through the webcam, **Send** and check before **Save to Receivers**, then save the
`.rcvbp`, copy it out with `vm get`, and record everything in `hardware.md`.

### Where things were on screen (hints; always `shot` first)

Main window (LEDVision at its default place): menus at y=168: File 271, Control 330, Play 389, Test 565.
Control > LED Screen Settings (397,195), Brightness Adjustment (400,319), Screen Size and Count (429,255).
Test > Gray Test (608,195).

LED Screen Settings (opens at the top left, password 168): tabs Sending Device (171,45), Receiver Parameters
(269,45), Receiver Mapping (416,45). Sending Device: Net Card (189,105), adapter list (363,243), its second
entry "#2" (280,275), Use Net Card (158,201), Detect Receivers (692,198). Receiver Parameters bottom row
at y=727: Read 199, Load 304, Save 412, Send 518, Save to Receivers 625, Restore Backup 731; Intelligent
Setting (253,685); Data Group list (800,211); Intelligent Module Setting (948,383).

Wizard Guide 8 grid (maximised): column c at x = 60 + 35(c-1), row r at y = 153 + 35(r-1). Columns past 34
need the horizontal scrollbar (y=688) dragged right; then column c is at x = 60 + 35(c-30).

## 5. Things that bit us

- `/dev/kvm` missing: VT-x was off in the BIOS.
- The guest had no network: ufw dropped DHCP on virbr0 (see 1.3). The first-logon script now waits for the
  Internet before installing sshd.
- LED Screen Settings forgets the adapter: every time it opens it falls back to the NAT adapter
  ("…Connection" without "#2"). Re-select #2 and Detect Receivers first, or Read/Send say "No Receiver Detected".
- LEDVision streams its virtual screen (the box at the top left of the desktop, LED1 logos) to the card at the
  card's brightness as soon as a Net Card is in use. Test > Gray Test at value 0 with "Hide Gray Value"
  holds it black; leave that window open (drag it aside).
- The brightness box ignores typing: click the slider, Home, then Right 40 times for 40%.
- The Intelligent Setting wizard ignores that brightness, and each page starts with "Automatic changes"
  ticked, which flashes the wall. Untick it first on every page.
- A stale DHCP lease outlives the guest; `vm start`/`status` wait for sshd, not the lease.

## 6. Tear down

```sh
python3 -m tools.ledvision.vm stop
virsh -c qemu:///system undefine ledvision --nvram --tpm
virsh -c qemu:///system vol-delete --pool default ledvision.qcow2   # and the two ISOs if not wanted
sudo rm /etc/NetworkManager/conf.d/90-ledvision-unmanaged.conf && sudo nmcli general reload conf
sudo ufw status numbered   # then delete the three virbr0 rules
```
