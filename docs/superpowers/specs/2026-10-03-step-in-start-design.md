# Step-in start: with `--game`, the arcade starts the game when a player stands in the zone

Date: 2026-10-03. Status: approved by the owner in conversation. One bounded change for the night of 2026-10-04.
The context is promptviz's `docs/superpowers/specs/2026-10-03-night-one-menu-design.md`: a conductor runs
`python -m arcade run --config arcade.pi.toml --game dodge --seconds 180` after a guest picks DODGE on the
wall. That guest is already standing on the square and has just jumped twice; a raised hand to start the game is a
third instruction nobody gives them, and the owner has rejected the raised hand as a trigger (2026-10-03).

## Change

In `arcade/attract/lobby.py`, when the runner was given `--game` (the lobby's games are that one game), the lobby's
request fires when the locked player has been present for `STEP_IN_SECONDS = 2.0` seconds, instead of on the
raised wrist's edge. Everything else about the lobby stays: the mirror figure, the card after a session, the
priming per player id and per card end (a player who stays on the square after the card gets the game again
after another 2.0 s, which is "again" without a gesture), the attract title when nobody is near.

Without `--game` nothing changes: the raised hand stays the trigger of the full lobby until M8 replaces it.

## Where

- `arcade/main.py`: `--game` already restricts the games; it also sets `lobby.start_on_step_in = True` (or passes it
  to the `Lobby` constructor). The help text changes from "a raised hand starts it" to "a player standing in the
  zone for 2 s starts it".
- `arcade/attract/lobby.py`: a `Hold(STEP_IN_SECONDS, grace=self.grace)` on `player is not None`, read in `update`
  where `fired` is set today; with `start_on_step_in` the `fired` value is that hold's rising edge, primed exactly
  where the raised-hand edge is primed (`_prime`). The invite pictogram is not drawn in this mode (there is no hand
  to ask for); the mirror figure is.
- Tests in `tests/arcade/test_lobby.py` (or beside the lobby's existing tests): with the flag, a player present
  1.9 s does not start the game and 2.0 s does; a player who leaves at 1.0 s and returns restarts the count; after
  the card the count starts again and a player who stayed gets the game at 2.0 s; a raised hand in this mode does
  nothing on its own; without the flag the existing tests pass unchanged. The rows 60 to 63 test and the degraded
  mover test the loop's rules ask of every lobby change.

## Not changed

The runner, the games, the sources, the calibration, the governor, `deploy/`, anything on the Pi. The Pi's
checkout is updated by the owner (`git pull` on `wall-bringup` or main, as they choose) before the conductor's
first run.
