# Runbook: the arcade on the Pi 5

How the Pi is set up for the arcade and how a run is started and stopped. The wall's own faults are in
`wall-shimmer.md`. Ground rules, from the wall sessions:

- Nothing goes to the card without the owner's "go". One run at a time; let a run go dark before the next.
- Nothing reconfigures the Pi while a picture is on the wall: no package installs, no reboots, no network changes.
- While `docs/superpowers/workflow/pi-lock.md` exists, every command below runs under the Pi's lock, as that file
  says.
- A run ends by its own `--seconds` or by one SIGINT. Never `timeout`: its second signal skips the close.

## 1. Once: the camera's packages (the wall dark)

```
sudo apt update
sudo apt install -y imx500-all
sudo apt install -y --no-install-recommends python3-picamera2
sudo reboot
```

`imx500-all` brings the AI Camera's firmware files and models; `python3-picamera2` the capture library. The
ribbon goes in with the Pi off: the camera port is not hot-pluggable. After the boot, `rpicam-hello
--list-cameras` names `imx500`.

## 2. Once: the venv sees apt's picamera2

In `~/codeisart/.venv/pyvenv.cfg` set `include-system-site-packages = true`. The venv's own numpy, OpenCV and
MediaPipe stay in front of apt's. Then:

```
.venv/bin/pip install -e '.[pi,dev]'
.venv/bin/python -c "import picamera2, cv2, mediapipe, numpy; print(numpy.__version__, cv2.__version__)"
```

The pose model is `models/pose_landmarker_lite.task` (ignored by git). If it is missing:

```
mkdir -p models && curl -fL -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task
```

The pose runs on the AI Camera's sensor (PoseNet, `camera = "imx500"` in `arcade.pi.toml`): no model file on the
Pi; `imx500-all` put `/usr/share/imx500-models/imx500_network_posenet.rpk` there. MediaPipe stays installed as
the fallback (`camera = "mediapipe"`, `camera_fps = 15`).

## 3. Look before a run (no card)

```
rpicam-hello --list-cameras
.venv/bin/python -m arcade doctor --require camera,pose --camera imx500 --capture picamera2
systemctl is-active promptviz-party.service show.service
```

The camera's line names `imx500`; the doctor prints `camera  ok  imx500 posenet 30/s: 640x480` and the same for
`pose`. The first start after a power cycle, or after another network was on the sensor, uploads PoseNet to it:
the doctor prints "uploading the network to the sensor, up to 4 minutes" and waits (2 MB at about 9 kB/s). The
sensor then keeps the network across restarts. A unit that is active holds the card: the owner stops it
(`sudo systemctl stop <unit>`) and starts it again afterwards.

## 4. A run

```
sudo systemd-run --unit=arcade-wall --pipe --wait --collect --quiet --uid=trey \
  -p AmbientCapabilities='CAP_NET_RAW CAP_SYS_NICE' -p WorkingDirectory=/home/trey/codeisart \
  /home/trey/codeisart/.venv/bin/python -m arcade run --config arcade.pi.toml --seconds 300 -v
```

Over ssh under the lock the whole line is one command in double quotes after `flock -w 300 /tmp/pi5.lock `
(not inside `sh -c '...'`: the capabilities' single quotes would end it).

`--game NAME` (copyme, pong, quickdraw, dodge, flap, swat, jump, freeze) offers that one game. The run's last
line is the sender's: `0 late (over 1 ms)` is a clean run.

`-v` also logs two lines a second that together are the lag, the numbers for `live-smoke.md`:
`sensor to decode: median N ms` (the sensor's share: exposure, readout and the on-sensor inference, from the
frame's `SensorTimestamp` to the decode; the spike read 42 to 48 ms) and `capture age at push: median N ms` (from
the frame's arrival at the Pi to the push of the wall's frame: the tick and the sender). Add them for the whole
lag; the spike's expectation is a sum near 70 to 90 ms. A MediaPipe run (`camera = "mediapipe"`) has no sensor
line and its capture-age line holds the 56 ms inference, so the two paths are compared by the sum, not line by
line. A capture-age line stops when the camera is gone.

`calibrate --config arcade.pi.toml` takes the place of `run ...` for a calibration; it writes
`data/calibration.json`, which every later run loads. If the figure is gone or out of place after one, remove
that file: the defaults return.

A run holds the Pi's lock until it ends, so keep `--seconds` short. To end one early, once, at the owner's word,
the one command that is sent without the lock: `sudo systemctl kill -s INT arcade-wall`. The wall goes black as
the arcade closes.

## 5. The camera's place

Chest height, looking level, the hips in view when the player steps in; no lamp or bright fixture in the picture;
light on the player. The player stands 2 to 2.5 m away.
