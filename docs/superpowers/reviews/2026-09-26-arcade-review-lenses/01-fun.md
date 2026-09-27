# Wall arcade review: game design and fun, 2026-09-26

Scope: spec sections 5, 7 and 8, and plan Tasks 3, 8, 9, 10, 11 and 17. Nothing in the repo was edited.

**Scale drives everything.** The 64x64 wall is 32 cm square. At 4 m it looks smaller than a phone at
arm's length. The 128x32 wall is a 64 by 16 cm banner. Every game must read as a thumbnail: one or
two big moving things, strong colour, and full-screen events. There is no sound to carry game feel.

**Did we pick the right games?** About half of them. Four entries are toys or visualisers, not
games: puppet, life, ambient and beat. Two use inputs that fail at a festival: flappy on audio
onsets, and scream on an auto-gained level. The strongest entries, holewall and pong, need
normalisation work to be fair. The worst problems sit in the play loop around the list. Nothing
defines who the player is, how a session ends, or what the wall does when the player leaves.

## Blockers

**B1. An abandoned game leaves the wall dark.** In Task 8, `Runner.tick` checks idle attract only
when the menu is current. Paint, puppet, life, ambient, scream and beat never return `done()`. If a
painter walks off, the canvas clears after 30 s and stays black until someone raises both hands.
Fix: a runner rule sends any game to attract after 8 s with nobody in the play zone (B3). Test it by
launching paint, feeding 10 s of empty input, and asserting `in_attract`.

**B2. Attract never starts at a burn, and cannot react when it does.** Spec 7.2 needs 60 s with no
bodies and no blobs, and any body or blob exits attract. At a night burn a blob is always present:
headlamps, LED coats, phones, a floodlit white shirt. Task 15 always keeps the brightest 0.5 percent
above a floor. So the wall shows the static icon grid all night. Ambient's reactive modes can also
never be seen, because the first person they could react to exits attract. Fix: presence is not
engagement. Attract stays up and reacts to passers-by, and hands over only when someone steps into
the play zone. Blobs never count toward idle.

**B3. There is no concept of "the player".** Sections 5 and 7.3 use `sensed.primary`, the most
confident body this tick, in raw frame coordinates. In a crowd that body changes from tick to tick,
so control hops between strangers.

The menu also breaks geometrically. Assume the Pi AI Camera, about 66 by 52 degrees, 3 m away and
1.2 m high. An adult's nose lands near y 0.36 of the frame and their box centre near 0.60.
`raised_wrist` exists only above the nose, so the hand cursor reaches only the top third of the
wall. On 128x32 that is the top row of tiles only. Below that, the cursor falls back to body centre,
which sits on a bottom-row tile. Anyone who pauses for one second launches the game under their
torso. A hand crossing nose height teleports the cursor and resets dwell. The laptop smoke test
cannot show this, because you sit 60 cm from the webcam.

Fixes, all in the core plan:
- **Play zone.** A body is a candidate only if its box is taller than about 0.45 of the frame
  (within about 3.5 m) and centred in a central band.
- **Player lock.** The first candidate to raise a hand holds the player slot by tracker id until
  lost for 1 s. Games read `sensed.players`, at most two, ordered left to right.
- **Body-relative reach box.** This is Kinect's "physical interaction zone". A box around the
  shoulders maps onto the whole wall, so children and tall adults get the same reach.
- **Smoothing.** Add a One Euro filter per keypoint. The plan smooths nothing today.
- **No body-centre cursor fallback.**

**B4. The exit gesture is the victory pose.** Spec 7.2 exits when both wrists are above the nose
for 1.5 s. Players do exactly that when they win, jump, or block a high pong ball. Holewall's "Y"
and touchdown targets ask for it. Fix: games end themselves (S1), and walking away hands over (B1).
Keep a deliberate operator exit that no game asks for: forearms crossed in an X for 2 s.

**B5. Scream always scores 100 percent.** Task 17 divides RMS by a running maximum that decays 0.5
percent per tick, a half-life of about 4.6 s. Any scream louder than the last few seconds sets the
reference, so `level` reads 1.0 and the first yell maxes the night's best. Fix: score calibrated raw
loudness in dBFS, and test that two screams of different amplitude score differently.

**B6. The menu is the front door, and it misses the ten-second goal.** A stranger sees eleven 8x8
icons, each 5 cm wide at 4 m, and a 2 px cursor. They must discover the hand-cursor, decode an icon,
and hold still. Expect 20 to 40 s to first play, and many walk-offs. The replacement flow is below.

## Serious

- **S1. No session structure.** Section 8 gives no game a length, end card or replay, and five never
  end. Flappy exits to the menu on every death, so each retry needs the menu again. Frogger has no
  fail state. Fix: every game ends in 45 to 90 s or on a clear result. Show a 4 s end card with the
  score, "BEST!" on a record, and "HAND UP = AGAIN". This also keeps a line moving.
- **S2. Non-uniform keypoint scale.** Task 11 maps x and y independently. On 128x32 a 4:3 frame
  stretches figures three times wide; on 64x64 it squashes them. Holewall targets and live figures
  won't match. Fix: a shared `to_wall(body, rect)` that scales uniformly by body height. On 128x32,
  give each player a 64x32 half.
- **S3. Scores ignore distance.** Jump measures nose rise in frame units, so standing at 2 m roughly
  doubles the score of 4 m. Holewall's mean frame-space distance penalises position and height, and
  includes cropped legs. Fix: centre on the hips, scale by torso length, and score limb angles
  weighted by confidence.
- **S4. The nose is the anchor, and burns mask it.** Task 3's `raised_wrist` and `both_hands_up`
  never check nose confidence. Goggles, dust masks and hoods are normal at a burn. Fix: use a line
  above the shoulder midpoint, 0.3 torso lengths up, and fall back to the nose only without
  shoulders.
- **S5. No play spot, and the crowd can't see.** Section 2 omits where the player stands and where
  the wall hangs. A small wall draws people to 1 m, where the camera loses their hips. At head height
  the player blocks everyone behind. Fix: bottom edge at about 2.1 m, camera just below and angled
  down, a lit floor spot at 2.5 to 3 m.
- **S6. Pong assigns players by id order.** The person on the right can get the left paddle. Fix:
  assign sides by x.
- **S7. No way to learn what works.** Fix: write one JSON line per session to
  `data_dir/sessions.jsonl` with game, duration, players, score and end reason (done, abandoned,
  exit, crash). Add `arcade stats`. This answers the owner's question after night one. Effort S.
- **S8. Two aspect ratios halve design quality.** Pick 128x32 as the design layout, because
  side-by-side two-player play is where crowd energy is. At 64x64, games must only run and stay
  legible.
- **S9. Dwell resets on jitter.** Task 9 zeroes the hold timer on any tick outside the tile. With
  1 to 2 px of jitter at an edge, the ring never fills. Fix: grow the hovered tile 2 px and decay
  dwell over 0.3 s instead of resetting it.

## Minor

- **Best of the night never resets.** Task 7's `Scores` keeps the best forever. Roll it over at noon.
- **No strobe limit.** Cap full-field flashes at 3 Hz for a public piece. Enforce it in the juice
  toolkit.
- **Flashes feed back into motion.** A wall flash lights the players, and the motion grid fires
  everywhere. Drop motion frames whose mean brightness jumps.
- **Frogger contradicts itself.** Row 4 lets both body x and a raised wrist move the frog across
  lanes. Walking right makes hopping pointless.
- **Gorilla arm.** Steering with a raised hand tires people in about 20 s. Use it only to confirm.

## Per-game verdicts

| Entry | Verdict | Reason |
|---|---|---|
| menu | REWORK | Too many choices, and the cursor can't reach half the tiles (B3, B6). |
| paint | KEEP, fix | Burners carry lights, and trails are fun to watch. Draw segments between tracked positions, because stamping at 30 Hz leaves 7 px gaps. Take colour from the blob halo, since LED cores saturate white. Let a raised wrist paint when nobody has a light. End with a 5 s gallery freeze. |
| puppet | REWORK | The mirror is the strongest "it sees me" moment but has nothing to do. Make it the runner's presence layer and drop the tile. |
| frogger | CUT | The controls conflict and nothing is at stake. Dodge keeps "jump to act" in a known form. |
| pong | KEEP, fix | Hand-height paddles are a proven camera game and great to watch. Fix sides (S6), use body-relative height, start the ball slow and speed it up. Give solo players a beatable CPU paddle, and let a second player join by stepping in. |
| jump | REWORK, merge | A three-second novelty with unfair measurement (S3). Merge with scream into a Strongman high striker with bell and overshoot. |
| holewall | KEEP, hero | People copy a figure unprompted, failures are funny, and the crowd reads it. Needs S2, S3 and B4. |
| life | CUT | Input becomes chaos, so players can't see cause and effect. Move it into attract. |
| ambient | REWORK | The right attract, not a game. Drop the tile and fix B2. |
| scream | REWORK, merge | Crowd roaring is fun, but the meter is broken (B5). Becomes "3, 2, 1, ROAR" in Strongman. |
| flappy | REWORK | Kick drums flap the bird, and retries go through the menu. Replace with arm flapping (Flap). |
| beat | CUT | No player agency. Its music-reactive look belongs in attract. |

This frees five tiles.

## Hero game

**Holewall, renamed Copy Me.** A mirror makes people stop walking, and a challenge makes them stay.
Copy Me is both. Matching a figure needs no words, it works with one or two players, and a stranger
failing a flamingo pose is the best thing a crowd can watch.

Draw the player's live figure in their colour, and the target as a cyan outline that grows toward
them over 3 s. Each limb turns green when its angle is within tolerance, so feedback is constant.
At zero, flash, pop the score, and freeze the round's best frame for 1.5 s.

To make it 2x better:
- **Pose relay.** The round winner has 3 s to strike a pose, saved to `data_dir` as a future target.
  Strangers set challenges for each other, and people come back to see if their pose survives.
- **Two players at once** in split halves on 128x32, head to head.
- **A pose ladder** from easy to silly, so round one is always a success.

## New and replacement games

| Game | Inputs | Effort |
|---|---|---|
| Flap | wrist vertical velocity | S |
| Dodge | shoulder height against standing baseline, torso-normalised | M |
| Swat | wrist positions and swept segments | M |
| Quick Draw | raised hand per player, sides by x | S |
| Freeze | keypoint speed, or motion grid by region | S to M |
| Tug | motion grid, left half against right half | S |

- **Flap.** Both wrists sweeping from above to below the shoulders within 0.4 s is one flap. Use wide
  gaps (at least 10 px of 32), gentle gravity, and restart by flapping again. People flapping like
  birds is the best spectator image here, and a flap is too big for latency to matter.
  `debug_state`: `y, vy, flaps, score, alive`.
- **Dodge.** The Chrome dinosaur game with your body. Jump low obstacles and duck high ones. Hitboxes
  forgive 2 px, speed ramps, and a run lasts until the first hit or 90 s. Everyone knows the rules.
  `debug_state`: `stance, baseline, next_gap_px, score, alive`.
- **Swat.** Fruit Ninja on a thumbnail. Bright 5 px fruit arc in, and a hand's path between two ticks
  cuts them. Bombs flash red, rounds last 60 s, and two players cooperate. It is the showcase for
  juice. `debug_state`: `score, combo, live_objects, misses, time_left`.
- **Quick Draw.** Two players keep hands low. "WAIT..." shows for 2 to 6 s, then "DRAW!" flashes, and
  the first hand up wins. An early hand loses. Best of five at about 10 s per round. Both players
  share a camera frame, so latency is fair. Solo players chase the night's fastest reaction.
  `debug_state`: `phase, p1_ms, p2_ms, false_start, score`.
- **Freeze.** Freeze dance to the neighbouring sound camp. On red, anyone moving after a 0.5 s grace
  is out and their figure topples. Stillness is easy to detect, and latency is irrelevant.
  `debug_state`: `phase, alive, round, winner`.
- **Tug.** The crowd game. Whichever half of the camera view moves more pulls a knot toward its side.
  It needs no pose, so it survives costumes, darkness and ten people, and the spectators are the
  players. `debug_state`: `knot, left_energy, right_energy, winner`.

Build order to ship: Copy Me, Pong, Quick Draw, Dodge, Tug, Flap, Swat, Paint, Strongman, Freeze.

## Juice toolkit

The spec has no hit feedback, anticipation, tweening, celebration or step-in acknowledgement. With no
sound, visuals do all of it. Add `arcade/juice.py` to the core plan so every second-plan game uses it.

```python
class Juice:                        # one per launch, runner-owned, seeded rng
    def shake(self, px=2, seconds=0.2): ...       # integer frame offset, decays
    def flash(self, color, seconds=0.1): ...      # additive, at most 3 per second
    def burst(self, x, y, color, n=12): ...       # particle pool capped at 96
    def pop(self, text, x, y, color): ...         # rises 6 px over 0.8 s, fades
    def banner(self, text, seconds=1.0): ...      # "3", "2", "1", "GO!", "BEST!"
    def freeze(self, seconds=0.07): ...           # hit-stop: skip update, keep drawing
    def celebrate(self, color): ...               # ring burst, flash, banner
    def echo(self, player, kind): ...             # glyph over the player's marker, same tick
    def debug_state(self) -> dict: ...            # fx_shake, fx_flash, fx_particles, fx_banner, fx_freeze
ease_out_quad, ease_out_back, lerp
```

- **Wiring.** `reset(size, rng, fx)` passes it in. The runner renders effects after `draw`, applies
  shake as a slice copy, then the brightness cap.
- **Presence.** On player lock, the runner draws a 0.3 s sweep from the player's x. A 2 px marker in
  their colour stays on the bottom row under them in every game, which answers "which one am I?".
- **The 100 ms rule.** Camera to LED takes 150 to 200 ms, so gameplay will lag. The acknowledgement
  must not add more: `echo` draws on the tick a gesture is recognised.
- **Testable.** It is deterministic, and `fx_*` keys merge into `runner.state()`. A Swat test asserts
  `fx_particles > 0` the tick after a scripted hit.
- **Budget.** Particles are numpy arrays with one indexed write, and shake is one array copy. Expect
  under 0.5 ms at 64x64. Add a perf test with a full pool.
- **Feel tests in the Task 20 soak.** A random-moving actor scores within 30 s. An idle actor reaches
  the end card within the session cap. The first `echo` lands within one tick of a scripted gesture.

## Menu and the first ten seconds

Hover-and-dwell with a raised wrist is the wrong front door for a crowd. I would ship this:

1. **Attract, nobody in the zone.** Ambient cycles rain, fire, boids, Life and beat, reacting to
   passers-by. Every 20 s, show a 5 s demo replayed from a recorded scenario. Then show tonight's
   best with the holder's frozen stick figure, an anonymous but recognisable name.
2. **0 s: someone steps onto the spot.** Their mirror figure appears on the next tick. This is what
   stops people.
3. **0.5 s:** a hand glyph pulses above the figure's head.
4. **Hand up opens three doors.** On 128x32, three 40 px panels show a 2x icon and one verb: COPY,
   DODGE, FLAP. Standing under a door selects it, because body x is our most stable signal and the
   crowd can see it. The door fills over 1.2 s while the hand stays up. Unselected doors slide every
   5 s.
5. **The ten-second guarantee.** A player who does nothing for 5 s gets Copy Me, or Pong for two
   people, after a countdown. Standing still means playing by second eight.
6. **After the end card,** a raised hand replays, and walking off returns to attract.

## Regrets after a week of nights

- **No session log (S7).** You will be guessing which games worked.
- **Costumes.** Wings, fur and EL wire break pose. Keep at least two pose-free games (Tug, Paint).
- **Sameness.** Randomise poses, obstacles and spawns from the injected rng, so second plays differ
  and tests stay deterministic.
- **Hogging.** Without the session cap and end card, one painter owns the wall for twenty minutes.
- **The sound camp.** A stranger's first game should never depend on the mic. Keep audio for crowd
  games like the Strongman roar, where noise is the point.

## Checked and found OK

- A fixed 30 Hz tick with clamped `dt`, injected clock and injected rng.
- `debug_state`-first testing, which extends cleanly to `fx_*` keys.
- The crash guard's one-second glitch frame, which reads as intentional.
- The motion grid as a pose-free input, the backbone of the crowd games.
- Stable, never-reused tracker ids, which make player lock simple.
- Pass-through never launches, and unavailable games dim with a reason.
- Paint's owned float trail with an exact fade.
- Mirroring once at the source, and a brightness cap no game can raise.
