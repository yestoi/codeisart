from configparser import ConfigParser
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"


def _unit():
    cp = ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read_string((DEPLOY / "show.service").read_text())
    return cp


def test_unit_never_gives_up_and_is_watched():
    unit = _unit()
    assert unit["Unit"]["StartLimitIntervalSec"] == "0"
    assert unit["Unit"]["After"] == "network-online.target"
    assert unit["Unit"]["Wants"] == "network-online.target"
    svc = unit["Service"]
    assert svc["Type"] == "notify"
    assert svc["NotifyAccess"] == "main"
    assert svc["WatchdogSec"] == "15"
    assert svc["Restart"] == "always"
    assert svc["RestartSec"] == "2"
    assert "KillMode" not in svc
    assert "-m show --config show.toml" in svc["ExecStart"]
    assert unit["Install"]["WantedBy"] == "multi-user.target"


def test_unit_is_read_only_but_entries_and_tmp():
    svc = _unit()["Service"]
    assert svc["ProtectSystem"] == "strict"
    assert svc["PrivateTmp"] == "yes"
    assert svc["ReadWritePaths"] == svc["WorkingDirectory"] + "/entries"
    assert "LG_WD=/tmp" in svc["Environment"]
    assert "PYTHONUNBUFFERED=1" in svc["Environment"]
    assert svc["AmbientCapabilities"] == "CAP_NET_RAW"
    assert svc["SupplementaryGroups"].split() == ["audio", "gpio"]
    assert svc["User"] == "pi"


def test_readme_names_the_unit_and_watchdog():
    text = (DEPLOY / "README.md").read_text()
    for word in ("show.service", "RuntimeWatchdogSec", "brightness_cap",
                 "LEDVision", "overlay", "Falcon Player", "User="):
        assert word in text, word


def test_readme_says_what_stop_and_the_watchdog_do():
    text = (DEPLOY / "README.md").read_text()
    for word in ("every second", "SIGTERM", "black", "network-online", "NRestarts"):
        assert word in text, word
    assert "every few seconds" not in text


def test_readme_names_the_soak_and_the_pattern_tool():
    text = (DEPLOY / "README.md").read_text()
    assert "python -m tools.show_soak" in text
    assert "wall_pattern.py --config show.toml" in text
