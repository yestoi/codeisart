# Runbook: the wall shimmers

For when the LED wall flickers or shimmers on a picture that passed before. It was built from the night of
2026-09-30, when the wall had just gone into its frame. The first lobby after the Pi's reboot shimmered, and
nothing after it did. The record is `docs/superpowers/reviews/2026-09-30-ghosting/10-wall-session-framed.md`.

Ground rules, from the wall sessions:
- Nothing goes to the card without the owner's "go". Every card step below starts after a 5 s dark lead.
- One run at a time. Let a run go dark before the next one starts.
- Nothing reconfigures the Pi while the wall runs: no Wi-Fi or NetworkManager changes, no `systemctl` reloads,
  no package installs. On 2026-09-30 a NetworkManager reload with Wi-Fi changes, made from another session,
  stalled the sender 14 ms in the middle of a run. On the card a stall like that is a blink.
- The driver's settings are not changed to chase a flicker: 60.00 frames a second, rows paced over 15.5 ms,
  the S2 sync first, the pinned real-time sender. Each was proven by eye at the wall.

Everything runs on the Pi through one script. From the Mac:

```
ssh trey@codeisart.local ./wall_triage <step>
```

Add `DRY=1` in front of the script to send a card step nowhere: `ssh trey@codeisart.local DRY=1 ./wall_triage sweep`.

## 1. Look at the Pi (no card, a few seconds)

```
ssh trey@codeisart.local ./wall_triage state
```

| It says | It means |
|---|---|
| up under 10 minutes | The first-boot window: the one shimmer came about 9 minutes after a boot. Go to step 2. |
| `throttled` other than `0x0` | The Pi was hot or under-volted. Fix the power or the cooling first. |
| a `Link is Down` line | The link to the card dropped that many seconds after boot. If that falls inside a run, reseat the cable and run again. On 2026-09-30 it dropped once at 195 s, while cables were handled, before any run. |
| something holding the card | Another program is driving the card. Stop it first, because two senders fight. |
| `NOT THE WALL-PROVEN SET` | The Pi's checkout is off main. Run `git -C ~/codeisart checkout main` before anything else. |

## 2. Is it the first-boot quirk?

The owner's reading of 2026-09-30 is that the Pi has a quirk in its first minutes after a boot, gone after
about 10 minutes of runtime. That rests on one sighting.

If `state` showed under 10 minutes, wait until the Pi has been up 10 minutes. Then run the same thing again.
If it is clean now, write down the uptime of both runs in the session's record and stop there. Each sighting
like that makes the reading stronger. If it still shimmers after 10 minutes, the quirk is not the answer: go on.

## 3. Is the flicker in the picture? (no card, 20 s)

```
ssh trey@codeisart.local ./wall_triage probe
```

This runs the lobby with no card and measures every frame. A healthy lobby reads:

| Line | Healthy, 2026-09-30 |
|---|---|
| brightness calls | one call, at 0.1 |
| max byte | 255 in every frame, 0 changes |
| lit pixels | 551 once the figure is up, 1 change |
| last 3 s, mean per frame | a smooth rise and fall about once a second: the lobby breathing on purpose |
| ticks | 30 a second, 0 late |

If the level is set again and again, or the lit pixels or the brightest byte jump, the picture itself is
flickering. That is a software matter, not the wall.

## 4. Split it on the card (about 2 minutes)

```
ssh trey@codeisart.local ./wall_triage sweep
```

Five segments with 3 s of dark between them. Give one word for each, "shimmer" or "clean".

| Segment | On the wall |
|---|---|
| A | the lobby, 20 s |
| B | the saved lobby picture as a still, straight into the driver, with no arcade running |
| C | the same still for 25 s, with a CPU load on the Pi from 8 s to 18 s |
| D | `steps`: a grey block, the card's level stepping up |
| E | `gamma`: a 128 grey patch, a checker, a ramp of 16 greys |

| What you saw | It points at |
|---|---|
| A shimmers, B to E clean | The arcade process: read its ticks line, then run the probe |
| A and B shimmer, D and E clean | That picture on the card: its colours and greys, not the arcade |
| C shimmers only while the load runs | The Pi's work reaches the wall: a power supply or ground shared with the wall |
| everything shimmers | The card or the panels for any picture: power, ribbons, the card's saved settings |
| everything clean | It does not reproduce now: go to step 5 |

## 5. Try the order it came in (about 2 minutes)

```
ssh trey@codeisart.local ./wall_triage video-lobby
```

This is the video for 30 s, 25 s of dark, then the lobby for 40 s. On 2026-09-30 the shimmer came on the first
lobby after the video. The same order run again later was stable.

## 6. Confirm with the soak (5 minutes)

```
ssh trey@codeisart.local ./wall_triage soak
```

This is the lobby for five minutes, with the Pi's temperature every 30 s. Tell the operator roughly when, if
anything shows. The 2026-09-30 soak was clean for the whole five minutes. The sender read 17,999 frames, worst
sync 14 us and 0 rows off their slot. The Pi ran at 60 to 66 °C and never throttled.

## After any physical change

After the frame, the cables or the power change, run the wall-proven runs in order. That takes about 4 minutes.

```
ssh trey@codeisart.local ./wall_triage checks
```

| Run | Verdict on 2026-09-30 |
|---|---|
| rgb | R G B W from the left, letters upright |
| border | all four edges lit, visible inside the frame |
| video | "perfect" |
| lobby | stable; one blink in 40 s is known and accepted |
| line picture | no copy, no shimmer |
| rgb at 0.4 | good |
| lobby at 0.4 | a few blinks, within acceptable levels, no shimmer |

## Reading the sender's line

Every card run prints the sender's own line at its close. A healthy one reads: worst sync under 20 us, sync to
sync sd 0 to 2 us, 0 rows off their slot, 0 slips, 0 send errors, 0 restarts, `real-time yes`.

If the line shows a late sync or rows off their slot, the sender was disturbed. The script then prints what
the Pi logged during that run: look for network changes, `systemctl` reloads or installs. On 2026-09-30 a dry
run read `1 late (over 1 ms), worst 13919 us, sync to sync sd 346 us, 135 rows off their slot` while another
session reloaded NetworkManager twice and changed the Wi-Fi connections.

If the wall flickers while that line is healthy, the Pi sent a clean stream. The fault is past the Pi: the
card, the cable or the panels. That was the case for the one shimmer on 2026-09-30.

## Ruled out on 2026-09-30

Don't chase these again without new evidence:
- **The Pi's DHCP retries on the card's link.** They come every 45 s, then go quiet for 5 minutes. None fell
  inside the shimmering run.
- **A `systemd` process at 56% CPU in `ps`.** That was the measuring ssh session's own user manager, seconds
  old, so its average was meaningless.
- **The Pi's CPU load.** A burst load on three cores beside a still changed nothing.
- **Greys on the card.** The `steps` and `gamma` stills were clean.
- **`sched: DL replenish lagged too much` in the kernel log.** It came 138 s after boot, before any run.
- **A different program or setting.** The Pi ran the same code, script, config and level as the clean
  afternoon soak, with no bench knobs.

## Where things are

| What | Where |
|---|---|
| a self-test of the script, no card | `./wall_triage selftest` |
| the script | `docs/superpowers/reviews/2026-09-30-ghosting/bench/wall_triage.sh`, linked as `~/wall_triage` on the Pi |
| the probes it calls | `lobby_probe.py`, `burst_load.py`, `arcade_load.py`, `direct_play.py` in the same `bench/` folder |
| the media | `~/bench` on the Pi, not in git: `rick.mp4`, `lobby.png`, `person.jpg` |
| full logs | `/tmp/wall_triage/` on the Pi, one file per step, cleared at reboot |

Setup, once (done 2026-09-30):

```
ssh trey@codeisart.local 'git -C ~/codeisart pull --ff-only && ln -sf ~/codeisart/docs/superpowers/reviews/2026-09-30-ghosting/bench/wall_triage.sh ~/wall_triage'
```
