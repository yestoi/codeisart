import argparse
import shlex

import pytest

from tools.ledvision import vm

LEASES = """ Expiry Time           MAC address         Protocol   IP address           Hostname    Client ID or DUID
-----------------------------------------------------------------------------------------------------------------
 2026-09-28 21:40:11   52:54:00:4c:ed:01   ipv4       192.168.122.119/24   LEDVISION   01:52:54:00:4c:ed:01
"""

ETHTOOL = """Settings for enp5s0:
\tSpeed: 1000Mb/s
\tDuplex: Full
\tAuto-negotiation: on
\tLink detected: yes
"""


def test_keystrokes_shift_capitals_and_symbols():
    assert vm.keystrokes("aB:\\") == [["KEY_A"], ["KEY_LEFTSHIFT", "KEY_B"], ["KEY_LEFTSHIFT", "KEY_SEMICOLON"],
                                      ["KEY_BACKSLASH"]]


def test_keystrokes_types_a_windows_path():
    chords = vm.keystrokes(r"C:\Users\led\Documents\card1.rcvbp")
    assert len(chords) == len(r"C:\Users\led\Documents\card1.rcvbp")
    assert chords[0] == ["KEY_LEFTSHIFT", "KEY_C"] and ["KEY_DOT"] in chords and ["KEY_1"] in chords


def test_keystrokes_refuse_what_the_layout_cannot_type():
    with pytest.raises(ValueError):
        vm.keystrokes("é")


@pytest.mark.parametrize("pixel,size,want", [(0, 1280, 0), (1279, 1280, 32767), (640, 1280, 16396),
                                              (-5, 800, 0), (900, 800, 32767)])
def test_abs_value_spans_the_screen_and_clamps(pixel, size, want):
    assert vm.abs_value(pixel, size) == want


def test_lease_ip_finds_the_nat_adapter():
    assert vm.lease_ip(LEASES) == "192.168.122.119"
    assert vm.lease_ip(LEASES, "52:54:00:00:00:99") is None
    assert vm.lease_ip("") is None


def test_parse_crop():
    assert vm.parse_crop("10,20,300,40") == (10, 20, 300, 40)
    for bad in ("1,2,3", "0,0,0,10", "a,b,c,d"):
        with pytest.raises((argparse.ArgumentTypeError, ValueError)):
            vm.parse_crop(bad)


def test_link_summary():
    assert vm.link_summary(ETHTOOL) == "1000Mb/s Full, link yes"
    assert vm.link_summary("") == "? ?, link ?"


def test_host_runs_locally_or_over_ssh():
    assert vm.Host(None).argv(["virsh", "list"]) == ["virsh", "list"]
    remote = vm.Host("trey@omarchy").argv(["virsh", "-c", "qemu:///system", "qemu-monitor-command", "ledvision",
                                           '{"execute": "x"}'])
    assert remote[:4] == ["ssh", "-o", "BatchMode=yes", "trey@omarchy"]
    assert shlex.split(remote[4])[-1] == '{"execute": "x"}'   # the JSON survives the remote shell


def test_click_is_one_round_trip(monkeypatch):
    runs = []
    monkeypatch.setattr(vm.subprocess, "run", lambda argv, **kw: runs.append(argv))
    vm.Host("trey@omarchy").click(640, 400)
    assert len(runs) == 1
    remote_sh = shlex.split(runs[0][4])
    assert remote_sh[:2] == ["sh", "-c"] and remote_sh[2].count("qemu-monitor-command") == 3


def test_desktop_run_ps_registers_an_elevated_interactive_task():
    ps = vm.desktop_run_ps(vm.LEDVISION_EXE)
    assert "'C:\\Program Files (x86)\\ColorLight\\LEDVISION\\LEDVISION.exe'" in ps
    assert "-RunLevel Highest" in ps and "-LogonType Interactive" in ps and "Start-ScheduledTask" in ps
    with pytest.raises(ValueError):
        vm.desktop_run_ps("C:\\it's.exe")


def test_authorize_key_ps_takes_one_key_line():
    ps = vm.authorize_key_ps("ssh-ed25519 AAAAC3Nza+/= trey@mac\n")
    assert ps.endswith("-Value 'ssh-ed25519 AAAAC3Nza+/= trey@mac'")
    for bad in ("not a key", "ssh-ed25519 AAAA x'; Remove-Item C:\\ -Recurse #"):
        with pytest.raises(ValueError):
            vm.authorize_key_ps(bad)


def test_scp_jumps_through_the_host_and_maps_guest_paths(monkeypatch):
    runs = []
    monkeypatch.setattr(vm.subprocess, "run", lambda argv, **kw: runs.append(argv) or type("R", (), {"returncode": 0}))
    host = vm.Host("trey@omarchy")
    monkeypatch.setattr(host, "require_ip", lambda: "192.168.122.119")
    host.scp("guest:C:/Users/led/Documents/card1.rcvbp", "./guest:odd-but-local")
    argv = runs[0]
    assert argv[0] == "scp" and argv[argv.index("-J") + 1] == "trey@omarchy"
    assert argv[-2:] == ["led@192.168.122.119:C:/Users/led/Documents/card1.rcvbp", "./guest:odd-but-local"]
