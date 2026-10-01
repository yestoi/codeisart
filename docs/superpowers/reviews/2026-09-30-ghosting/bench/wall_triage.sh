#!/usr/bin/env bash
# Wall triage (2026-09-30 night, the framed-wall session): the checks that split a flicker on the LED wall, in
# the order that worked. Runs ON THE PI. The runbook that says what each answer means:
#   docs/runbooks/wall-shimmer.md
#
# From the Mac:   ssh trey@codeisart.local ./wall_triage <step>      (~/wall_triage links here)
#
#   state        no card: uptime, clock, temperature, throttling, the card's link, what holds the card, the driver
#   probe        no card: the lobby run dry, every frame measured (is the flicker in the picture?)
#   sweep        CARD, ~2 min: lobby 20 s | still lobby picture 20 s | the same still under a CPU load | steps | gamma
#   video-lobby  CARD, ~2 min: the video 30 s, 25 s dark, the lobby 40 s (the order the one shimmer came in)
#   soak         CARD, ~5 min: the lobby for 300 s, the Pi's temperature every 30 s
#   checks       CARD, ~4 min: the wall-proven runs in order: rgb, border, video, lobby, line picture, rgb and
#                lobby at level 0.4
#   selftest     no card: the run wrapper on a healthy line, a disturbed line and a failing command
#
# Every CARD step starts after a dark lead (LEAD, 5 s) and puts 3 s of dark between segments. DRY=1 sends every
# step to nowhere (no card). Full output: /tmp/wall_triage/<time>-<step>.log; the screen gets the sender's line,
# the arcade's ticks, and the last lines of any run that fails.
set -u
REPO=/home/trey/codeisart
HERE=$REPO/docs/superpowers/reviews/2026-09-30-ghosting
BENCH=$HERE/bench
MEDIA=/home/trey/bench                 # rick.mp4, lobby.png, person.jpg: on the Pi only, not in git
PY="sudo $REPO/.venv/bin/python"
DRY=${DRY:-0}
LEAD=${LEAD:-5}
STEP=${1:-}
cd "$REPO" || { echo "no $REPO"; exit 1; }
mkdir -p /tmp/wall_triage
LOG=/tmp/wall_triage/$(date +%Y%m%d-%H%M%S)-${STEP:-none}.log
if [ "$DRY" = 1 ]; then WALL=""; DRYF="--dry-run"; else WALL="--wall"; DRYF=""; fi

say() { echo "== $(date +%T) $*"; }

run() {   # label, command...: the output to the log; the key lines and any failure to the screen
    local label=$1; shift
    say "$label"
    local part rc since sender
    since=$(date '+%F %T')
    part=$(mktemp)
    "$@" >"$part" 2>&1
    rc=$?
    { echo "### $(date +%T) $label: $*"; cat "$part"; } >>"$LOG"
    grep -E "ticks:|colorlight sender|pushed [0-9]+ frames" "$part" | sed -E 's/^ */   /' | cut -c1-210
    sender=$(grep -m1 "colorlight sender" "$part")
    if [ -n "$sender" ] && ! echo "$sender" | grep -qE ", 0 late \(over 1 ms\).*, 0 rows off their slot"; then
        echo "   THE SENDER WAS DISTURBED (a late sync or rows off their slot). What the Pi logged during the run:"
        journalctl --no-pager -o short --since "$since" --until "$(date '+%F %T')" 2>/dev/null \
            | grep -vE "pam_unix|sudo|session-[0-9]+\.scope|New session|Removed session|logged out|Accepted publickey|Received disconnect|Disconnected from|user@1000|user-runtime" \
            | tail -12 | cut -c1-160 | sed 's/^/     /'
        echo "   (2026-09-30: a NetworkManager reload with Wi-Fi changes stalled the sender 14 ms; see the runbook)"
    fi
    if [ $rc -ne 0 ]; then
        echo "   EXIT $rc. The last lines:"
        grep -vE "^(W0000|I0000|INFO)" "$part" | tail -8 | sed 's/^/   /'
    fi
    rm -f "$part"
    return $rc
}

lead() {
    [ "$DRY" = 1 ] && say "DRY: nothing goes to the card" || say "ON THE CARD in $LEAD s"
    sleep "$LEAD"
}
dark() { sleep "${1:-3}"; }

pattern() { run "$1 ${2}s ${3:-}" $PY tools/wall_pattern.py "$1" --iface eth0 --seconds "$2" ${3:-} $DRYF; }
lobby()   { run "lobby ${1}s ${2:-}" $PY "$BENCH/arcade_load.py" $WALL --seconds "$1" --picture "$MEDIA/person.jpg" ${2:-}; }
still()   { run "still lobby picture ${1}s" $PY "$BENCH/direct_play.py" slide --png "$MEDIA/lobby.png" --speed 0.001 --seconds "$1" $DRYF; }
video()   { run "video ${1}s" $PY "$BENCH/direct_play.py" video --file "$MEDIA/rick.mp4" --seconds "$1" $DRYF; }
line()    { run "line picture ${1}s" $PY "$HERE/ghost_map.py" 8 --step 0 --row 18 --iface eth0 --seconds "$1" $DRYF; }

state() {
    say "state"
    local up; up=$(cut -d. -f1 /proc/uptime)
    echo "   up $((up / 60)) min $((up % 60)) s; clock $(date '+%F %T %Z'), NTP synced: $(timedatectl show -p NTPSynchronized --value)"
    echo "   $(vcgencmd measure_temp), $(vcgencmd get_throttled) (0x0: never throttled or under-volted)"
    echo "   load $(cut -d' ' -f1-3 /proc/loadavg)"
    echo "   eth0 $(cat /sys/class/net/eth0/operstate), $(cat /sys/class/net/eth0/speed 2>/dev/null) Mb/s, link changes since boot: $(cat /sys/class/net/eth0/carrier_changes)"
    sudo dmesg | grep -E "eth0: Link is" | tail -4 | sed 's/^/   /'
    echo "   kernel errors and warnings this boot (last 4):"
    sudo dmesg --level=err,warn | tail -4 | sed 's/^/     /'
    echo "   holding the card now:"
    pgrep -af "colorlight_sender|arcade_load|direct_play|wall_pattern|ghost_map|show\.main|-m show|-m arcade|promptviz" \
        | grep -vE "pgrep|wall_triage" | cut -c1-120 | sed 's/^/     /' || true
    pgrep -f "colorlight_sender" >/dev/null || echo "     nothing"
    echo "   codeisart $(git rev-parse --short HEAD), $(git status --short | grep -vc '^??') files changed"
    .venv/bin/python -c "
from show.display import colorlight_sender as s
ok = s.OUTPUT_FPS == 60.0 and s.ROW_SPREAD_NS == 15_500_000
print(f'   driver: OUTPUT_FPS {s.OUTPUT_FPS}, ROW_SPREAD_NS {s.ROW_SPREAD_NS}:', 'the wall-proven set' if ok else 'NOT THE WALL-PROVEN SET')"
    if [ "$up" -lt 600 ]; then
        echo "   NOTE: up under 10 minutes. The one shimmer of 2026-09-30 came about 9 minutes after a boot (the"
        echo "   owner's reading: a first-boot quirk that goes away after about 10 minutes of runtime)."
    fi
}

case "$STEP" in
state)
    state ;;
probe)
    say "probe: the lobby dry for 20 s, every frame measured (no card)"
    $PY "$BENCH/lobby_probe.py" 20 2>&1 | tee -a "$LOG" | grep -E "^(frames|max byte|mean|lit pixels|brightness|last 3 s)|ticks:|colorlight sender" | cut -c1-210 ;;
sweep)
    state
    say "sweep: A lobby 20 s | B still lobby picture 20 s | C still + CPU load from 8 to 18 s, 25 s | D steps 10 s | E gamma 10 s"
    lead
    lobby 20; dark
    still 20; dark
    ( sleep 8; say "   C: load on"; python3 "$BENCH/burst_load.py" 10 >/dev/null; say "   C: load off" ) &
    run "still lobby picture 25s, the load from 8 to 18 s" $PY "$BENCH/direct_play.py" slide --png "$MEDIA/lobby.png" --speed 0.001 --seconds 25 $DRYF
    wait
    dark
    pattern steps 10; dark
    pattern gamma 10 ;;
video-lobby)
    state
    say "video-lobby: the video 30 s, 25 s dark, the lobby 40 s"
    lead
    video 30; dark 25
    lobby 40 ;;
soak)
    state
    say "soak: the lobby 300 s, the temperature every 30 s"
    lead
    ( for _ in $(seq 1 11); do sleep 30; echo "   $(date +%T) $(vcgencmd measure_temp) $(vcgencmd get_throttled)"; done ) &
    logger=$!
    lobby 300
    kill "$logger" 2>/dev/null; wait 2>/dev/null ;;
checks)
    state
    say "checks: rgb 10 s | border 10 s | video 30 s | lobby 40 s | line picture 54 s | rgb at 0.4 10 s | lobby at 0.4 20 s"
    lead
    pattern rgb 10; dark
    pattern border 10; dark
    video 30; dark
    lobby 40; dark
    line 54; dark
    pattern rgb 10 "--brightness 0.4"; dark
    lobby 20 "--brightness 0.4" ;;
selftest)
    say "selftest: the run wrapper on a healthy and a disturbed sender line (no card)"
    run "healthy" echo "  colorlight sender: 599 frames, 0 late (over 1 ms), worst 3 us, sync to sync sd 0 us, 0 rows off their slot"
    run "disturbed" echo "  colorlight sender: 3239 frames, 1 late (over 1 ms), worst 13919 us, sync to sync sd 346 us, 135 rows off their slot"
    run "a failing command" false ;;
*)
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
    exit 2 ;;
esac
say "done. Full output: $LOG"
