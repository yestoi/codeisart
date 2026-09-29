#!/usr/bin/env bash
# Build the `ledvision` Windows 11 VM on the Omarchy host, unattended, for LEDVision and the Colorlight card.
#
#   tools/ledvision/provision/provision.sh --iso ~/Downloads/Win11_25H2_English_x64_v2.iso \
#       [--nic enp5s0] [--key ~/.ssh/id_ed25519.pub] [--key laptop.pub] [--password PW]
#
# Run it as your user on the host (libvirt group, no sudo). It checks what it needs, and for the two host
# changes that need root it prints the command and stops. Then it builds Secure Boot vars with Microsoft's
# keys, an answer disc (autounattend.xml + setup.ps1 with your keys), the volumes, the VM, and boots the
# installer. Windows installs, logs on as led and sets itself up without a keyboard; about 30 minutes later
# `python -m tools.ledvision.vm status` shows an IP and `vm guest hostname` answers.
# Everything generated goes to ~/.local/share/ledvision-vm, including guest-password (the password of the guest's
# local admin `led`, random unless --password is given; only RDP needs it). Images go to libvirt's default pool.
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
DOMAIN=ledvision
URI=qemu:///system
NIC=enp5s0
ISO=""
KEYS=()
PASSWORD=""
WORK=${XDG_DATA_HOME:-$HOME/.local/share}/ledvision-vm
OVMF_CODE=/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd
OVMF_VARS=/usr/share/edk2/x64/OVMF_VARS.4m.fd
V=(virsh -c "$URI")

die() { echo "provision: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "missing $1 (install: $2)"; }

while [ $# -gt 0 ]; do
    case $1 in
        --iso) ISO=$2; shift 2 ;;
        --nic) NIC=$2; shift 2 ;;
        --key) KEYS+=("$2"); shift 2 ;;
        --password) PASSWORD=$2; shift 2 ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) die "unknown argument $1" ;;
    esac
done
[ ${#KEYS[@]} -gt 0 ] || KEYS=("$HOME/.ssh/id_ed25519.pub")

# 1. What the host needs -------------------------------------------------------------------------------------
need virsh "pacman -S libvirt"
need virt-install "pacman -S virt-install"
need xorriso "pacman -S libisoburn"
need uvx "pacman -S uv"
need python3 "pacman -S python"
[ -e /dev/kvm ] || die "/dev/kvm is missing: turn on Intel Virtualization Technology (VT-x) in the BIOS"
"${V[@]}" list >/dev/null 2>&1 || die "virsh cannot reach $URI: join the libvirt group and log in again"
[ -f "$OVMF_CODE" ] && [ -f "$OVMF_VARS" ] || die "OVMF firmware not found (pacman -S edk2-ovmf)"
command -v swtpm >/dev/null || die "missing swtpm (pacman -S swtpm)"
[ -n "$ISO" ] && [ -f "$ISO" ] || die "--iso: the Windows 11 x64 ISO from microsoft.com/software-download/windows11"
for k in "${KEYS[@]}"; do [ -f "$k" ] || die "--key $k: no such file"; done
ip link show "$NIC" >/dev/null 2>&1 || die "no interface $NIC (ip -br link)"
if ip route show default | grep -q " dev $NIC "; then
    die "$NIC carries the host's default route; the card needs a port of its own"
fi
if command -v nmcli >/dev/null && ! nmcli -g GENERAL.STATE device show "$NIC" 2>/dev/null | grep -q unmanaged; then
    echo "NetworkManager manages $NIC and will run DHCP against the card. Run, then re-run this script:"
    echo "  printf '[keyfile]\\nunmanaged-devices=interface-name:$NIC\\n' | sudo tee /etc/NetworkManager/conf.d/90-ledvision-unmanaged.conf && sudo nmcli general reload conf"
    exit 1
fi
if "${V[@]}" dominfo "$DOMAIN" >/dev/null 2>&1; then
    die "the VM exists already. To rebuild: virsh -c $URI undefine $DOMAIN --nvram --tpm, then delete ledvision.qcow2 from the default pool"
fi
if systemctl is-active -q ufw 2>/dev/null; then
    echo "ufw is active. Its defaults drop DHCP, DNS and forwarding for libvirt's virbr0, so the guest gets no"
    echo "address or Internet. If you have not already, run:"
    echo "  sudo ufw allow in on virbr0 to any port 67 proto udp; sudo ufw allow in on virbr0 to any port 53; sudo ufw route allow in on virbr0"
fi

# 2. Secure Boot vars with Microsoft's keys (Arch's OVMF ships none enrolled) ---------------------------------
mkdir -p "$WORK"
uvx --from virt-firmware virt-fw-vars --input "$OVMF_VARS" --output "$WORK/OVMF_VARS.ms.4m.fd" \
    --enroll-redhat --secure-boot >/dev/null 2>&1
echo "secure boot vars: $WORK/OVMF_VARS.ms.4m.fd"

# 3. The answer disc: autounattend.xml with the password, setup.ps1 with the SSH keys the guest will trust ---
[ -n "$PASSWORD" ] || PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')
(umask 077; printf '%s\n' "$PASSWORD" > "$WORK/guest-password")
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
LEDVISION_PASSWORD=$PASSWORD python3 - "$HERE" "$stage" "${KEYS[@]}" <<'PY'
import os, sys
from xml.sax.saxutils import escape
here, stage, *keys = sys.argv[1:]
xml = open(f"{here}/autounattend.xml").read().replace("@PASSWORD@", escape(os.environ["LEDVISION_PASSWORD"]))
open(f"{stage}/autounattend.xml", "w").write(xml)
lines = ["    '" + line.strip().replace("'", "''") + "'"
         for k in keys for line in open(k).read().splitlines() if line.strip()]
with open(f"{stage}/setup.ps1", "w", newline="\r\n") as f:
    f.write(open(f"{here}/setup.ps1.in").read().replace("@AUTHORIZED_KEYS@", "\n".join(lines)))
PY
xorriso -as mkisofs -J -r -V UNATTEND -o "$WORK/unattend.iso" "$stage" 2>/dev/null
echo "answer disc: $WORK/unattend.iso (${#KEYS[@]} key file(s)); guest password in $WORK/guest-password"

# 4. Storage: libvirt's default pool; the ISOs are uploaded so qemu never needs to read your home ----------
if ! "${V[@]}" pool-info default >/dev/null 2>&1; then
    "${V[@]}" pool-define-as default dir --target /var/lib/libvirt/images >/dev/null
    "${V[@]}" pool-autostart default >/dev/null
fi
"${V[@]}" pool-info default | grep -qE 'State:\s+running' || "${V[@]}" pool-start default >/dev/null
upload() {  # upload NAME FILE, unless the volume exists
    if ! "${V[@]}" vol-info --pool default "$1" >/dev/null 2>&1; then
        "${V[@]}" vol-create-as default "$1" "$(stat -c %s "$2")" --format raw >/dev/null
        "${V[@]}" vol-upload --pool default "$1" "$2"
    fi
}
WIN_ISO=$(basename "$ISO")
upload "$WIN_ISO" "$ISO"
"${V[@]}" vol-delete --pool default ledvision-unattend.iso >/dev/null 2>&1 || true   # keys may have changed
upload ledvision-unattend.iso "$WORK/unattend.iso"
"${V[@]}" vol-info --pool default ledvision.qcow2 >/dev/null 2>&1 \
    || "${V[@]}" vol-create-as default ledvision.qcow2 64G --format qcow2 >/dev/null
"${V[@]}" net-info default | grep -qE 'Active:\s+yes' || "${V[@]}" net-start default >/dev/null

# 5. The VM: UEFI + Secure Boot, TPM 2.0, SATA only (no virtio drivers), NAT + the card port as macvtap ------
virt-install --connect "$URI" --name "$DOMAIN" --osinfo win11 --import --print-xml \
    --memory 8192 --vcpus 4 --cpu host-passthrough --machine q35 \
    --boot "loader=$OVMF_CODE,loader.readonly=yes,loader.type=pflash,loader.secure=yes,nvram.template=$WORK/OVMF_VARS.ms.4m.fd" \
    --features smm.state=on \
    --tpm backend.type=emulator,backend.version=2.0,model=tpm-crb \
    --disk vol=default/ledvision.qcow2,bus=sata,boot.order=1 \
    --disk "vol=default/$WIN_ISO,device=cdrom,bus=sata,boot.order=2" \
    --disk vol=default/ledvision-unattend.iso,device=cdrom,bus=sata \
    --network network=default,model=e1000e,mac=52:54:00:4c:ed:01 \
    --network "type=direct,source=$NIC,source.mode=passthrough,model=e1000e,mac=52:54:00:4c:ed:02" \
    --graphics vnc,listen=127.0.0.1 --video vga --input tablet,bus=usb \
    > "$WORK/ledvision.xml"
"${V[@]}" define "$WORK/ledvision.xml" >/dev/null
"${V[@]}" start "$DOMAIN" >/dev/null
echo "booting; pressing Enter for 'Press any key to boot from CD'"
for _ in $(seq 1 20); do sleep 1; "${V[@]}" send-key "$DOMAIN" KEY_ENTER >/dev/null 2>&1 || true; done

cat <<EOF
The installer is running on its own. Watch it with
  python -m tools.ledvision.vm shot --out shots/vm.png
In about 30 minutes 'python -m tools.ledvision.vm status' shows the guest's IP, and
  python -m tools.ledvision.vm guest 'Get-Content C:\\ledvision-setup.log -Tail 20'
shows the first-logon setup. No IP after 10 minutes on the desktop: see ufw above.
Next: install LEDVision (tools/ledvision/README.md, "Install LEDVision").
EOF
