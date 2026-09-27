#!/usr/bin/env bash
# Tests for the arcade operator hooks. Runs each script with sample hook JSON on stdin
# inside a throwaway project root holding its own copy of docs/superpowers/workflow/.
# Usage: bash scripts/operator/test_hooks.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/operator-hooks.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
ROOT="$TMP/root"
WF="$ROOT/docs/superpowers/workflow"
PASS=0; FAIL=0

ok()  { PASS=$((PASS+1)); echo "ok   - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; [ -n "${2:-}" ] && printf '       %s\n' "$2"; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "${3:-}"; fi; }

setup() {
  rm -rf "$ROOT"; mkdir -p "$WF"
  cat > "$WF/state.md" <<'S'
# Operator state
iteration: 2
phase: implement
plan: docs/superpowers/plans/example.md
base: abc1234
orchestrator: it02-orch
in_flight: implementer for task 2
carried: none
next_gate: none
last_compaction: none
S
  cat > "$WF/config.md" <<'S'
# Workflow config — test
- Deploy: none
- iterations-per-run: 3
S
  cat > "$WF/roadmap.md" <<'S'
# Roadmap — test
## Milestones
- [x] M0: done
- [ ] M1: open
- [ ] GATE A (human): later
## Carried fixes
(none)
S
  cat > "$WF/journal.md" <<'S'
# Iteration journal — test
(append-only; newest entry last; format defined in SKILL.md)

## Iteration 1 — 2026-10-01
- Shipped: FIRST-ENTRY-MARKER

## Iteration 2 — 2026-10-02
- Shipped: SECOND-ENTRY-MARKER
- Status: done
S
  cat > "$WF/decisions.md" <<'S'
# Decisions
Block format:
```
### Q<n>: <question>
answer:
```

### Q1: Layout?
asked: it0
answer: 128x32
status: answered

### Q2: Dwell time?
asked: it1
default: 1.2 s
deadline: it4
answer:
status: open

### Q3: Brightness ceiling?
asked: it2
default: 0.08
deadline: it5
answer: 0.1
status: answered
S
  ( cd "$ROOT" && git init -q && git -c user.email=t@t -c user.name=t add -A \
      && git -c user.email=t@t -c user.name=t commit -qm init )
  HEAD_SHA="$(cd "$ROOT" && git rev-parse --short HEAD)"
}

# run <OPERATOR value or ""> <script> <json> [args...]; sets OUT, ERR, RC
run() {
  local op="$1" script="$2" json="$3"; shift 3
  if [ -n "$op" ]; then
    OUT="$(cd "$ROOT" && printf '%s' "$json" | OPERATOR="$op" python3 "$HERE/$script" "$@" 2>"$TMP/err")"; RC=$?
  else
    OUT="$(cd "$ROOT" && printf '%s' "$json" | env -u OPERATOR python3 "$HERE/$script" "$@" 2>"$TMP/err")"; RC=$?
  fi
  ERR="$(cat "$TMP/err")"
}

bash_json() { python3 -c 'import json,sys; print(json.dumps({"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
STOP_JSON='{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"Stop","stop_hook_active":false}'
STOP_ACTIVE='{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"Stop","stop_hook_active":true}'
PRE_AUTO='{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"PreCompact","trigger":"auto","custom_instructions":""}'
PRE_MANUAL='{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"PreCompact","trigger":"manual","custom_instructions":""}'
SS_JSON='{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"SessionStart","source":"compact"}'

echo "# inert unless OPERATOR=1 and state.md exists"
setup
BEFORE="$(cat "$WF/state.md")"
run "" stop.py "$STOP_JSON";            check "stop inert without OPERATOR" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ ! -e "$WF/.blocks" ]'
run "" reinject.py "$SS_JSON" --fresh;  check "reinject inert without OPERATOR" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
run "" precompact.py "$PRE_AUTO";       check "precompact inert without OPERATOR" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ "$(cat "$WF/state.md")" = "$BEFORE" ]'
run "" guard_bash.py "$(bash_json 'git push origin main')"; check "guard inert without OPERATOR" '[ $RC -eq 0 ] && [ -z "$ERR" ]'
run 0 stop.py "$STOP_JSON";             check "stop inert with OPERATOR=0" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
rm "$WF/state.md"
run 1 stop.py "$STOP_JSON";             check "stop inert without state.md" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
run 1 guard_bash.py "$(bash_json 'git push origin main')"; check "guard inert without state.md" '[ $RC -eq 0 ]'
run 1 reinject.py "$SS_JSON";           check "reinject inert without state.md" '[ $RC -eq 0 ] && [ -z "$OUT" ]'

echo "# precompact.py"
setup
run 1 precompact.py "$PRE_AUTO"
S1="$(cat "$WF/state.md")"
check "precompact exits 0 silently" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
check "footer written" 'grep -q "^## Compaction footer 20..-..-..T..:..:..Z" "$WF/state.md"'
check "footer has trigger auto" 'grep -q "^- trigger: auto" "$WF/state.md"'
check "footer has HEAD sha" 'grep -q "^- head: $HEAD_SHA" "$WF/state.md"'
check "footer has last journal heading" 'grep -q "^- last journal entry: ## Iteration 2 — 2026-10-02" "$WF/state.md"'
check "footer has gate.md absent" 'grep -q "^- gate.md: absent" "$WF/state.md"'
check "footer has git status block" 'grep -q "^- git status --short" "$WF/state.md"'
check "state body preserved" 'grep -q "^phase: implement" "$WF/state.md" && grep -q "^in_flight: implementer for task 2" "$WF/state.md"'
touch "$WF/gate.md"; echo change >> "$ROOT/dirty.txt"
run 1 precompact.py "$PRE_MANUAL"
check "second run keeps exactly one footer" '[ "$(grep -c "^## Compaction footer" "$WF/state.md")" -eq 1 ]'
check "footer replaced: trigger manual" 'grep -q "^- trigger: manual" "$WF/state.md" && ! grep -q "^- trigger: auto" "$WF/state.md"'
check "footer replaced: gate.md present" 'grep -q "^- gate.md: present" "$WF/state.md"'
check "footer lists dirty file" 'grep -q "dirty.txt" "$WF/state.md"'
check "state body still preserved once" '[ "$(grep -c "^phase: implement" "$WF/state.md")" -eq 1 ]'
printf '{not json' > "$TMP/badjson"
OUT="$(cd "$ROOT" && OPERATOR=1 python3 "$HERE/precompact.py" < "$TMP/badjson" 2>/dev/null)"; RC=$?
check "precompact survives bad stdin (exit 0)" '[ $RC -eq 0 ] && grep -q "^- trigger: unknown" "$WF/state.md"'

echo "# reinject.py"
setup
run 1 reinject.py "$SS_JSON"
check "reinject exits 0" '[ $RC -eq 0 ]'
check "banner first line" '[ "$(printf "%s\n" "$OUT" | head -1)" = "You are the arcade operator. Context was compacted. Re-enter the workflow loop at the phase in state.md. Do not restart the iteration, do not re-plan a committed plan, do not re-spawn an agent named in \`in_flight\` (SendMessage it instead). Files are truth." ]'
check "prints state.md" 'printf "%s" "$OUT" | grep -q "^phase: implement" && printf "%s" "$OUT" | grep -q "^orchestrator: it02-orch"'
check "prints last journal entry" 'printf "%s" "$OUT" | grep -q "SECOND-ENTRY-MARKER"'
check "omits earlier journal entry" '! printf "%s" "$OUT" | grep -q "FIRST-ENTRY-MARKER"'
check "prints open question Q2" 'printf "%s" "$OUT" | grep -q "^### Q2: Dwell time?"'
check "omits answered Q1/Q3 and fenced example" '! printf "%s" "$OUT" | grep -q -e "^### Q1" -e "^### Q3" -e "^### Q<n>"'
check "no gate section without gate.md" '! printf "%s" "$OUT" | grep -q "^## gate.md"'
check "last line is the skill instruction" '[ "$(printf "%s\n" "$OUT" | tail -1)" = "Invoke the workflow-loop skill with the Skill tool and resume at the phase in state.md." ]'
check "no file list without --fresh" '! printf "%s" "$OUT" | grep -q "^- live-smoke.md:"'
printf '# Gate\nQuestion: keep pong?\n' > "$WF/gate.md"
run 1 reinject.py "$SS_JSON" --fresh
check "--fresh prints the state file list" 'printf "%s" "$OUT" | grep -q "^- config.md: " && printf "%s" "$OUT" | grep -q "^- live-smoke.md: " && printf "%s" "$OUT" | grep -q "^- evidence/itNN/: "'
check "prints gate.md when present" 'printf "%s" "$OUT" | grep -q "Question: keep pong?"'
rm "$WF/gate.md"; printf '# Iteration journal\n' > "$WF/journal.md"
python3 - "$WF/decisions.md" <<'P'
import sys; p=sys.argv[1]; s=open(p).read().replace("answer:\nstatus: open","answer: 1.2 s\nstatus: answered"); open(p,"w").write(s)
P
run 1 reinject.py "$SS_JSON"
check "notes empty journal" 'printf "%s" "$OUT" | grep -q "has no .## Iteration. entry yet"'
check "notes no open question" 'printf "%s" "$OUT" | grep -q "(no open question in decisions.md)"'

echo "# stop.py"
setup
run 1 stop.py "$STOP_JSON"
check "blocks when loop unfinished (exit 0)" '[ $RC -eq 0 ] && [ -n "$OUT" ]'
check "block output is valid JSON" 'printf "%s" "$OUT" | python3 -c "import json,sys; json.load(sys.stdin)"'
check "block JSON has decision=block and reason" 'printf "%s" "$OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d[\"decision\"]==\"block\" and \"Block 1 of 3 this run.\" in d[\"reason\"] and \"state.md\" in d[\"reason\"]"'
check "counter created at 1" '[ "$(cat "$WF/.blocks")" = "1" ]'
run 1 stop.py "$STOP_JSON"
check "counter incremented to 2" '[ "$(cat "$WF/.blocks")" = "2" ] && printf "%s" "$OUT" | grep -q "Block 2 of 3"'
run 1 stop.py "$STOP_JSON"
check "third block reaches cap 3" '[ "$(cat "$WF/.blocks")" = "3" ] && [ -n "$OUT" ]'
run 1 stop.py "$STOP_JSON"
check "allows when counter at cap" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ "$(cat "$WF/.blocks")" = "3" ]'
rm "$WF/.blocks"; touch "$WF/gate.md"
run 1 stop.py "$STOP_JSON";  check "allows when gate.md exists" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ ! -e "$WF/.blocks" ]'
rm "$WF/gate.md"; touch "$WF/STOP"
run 1 stop.py "$STOP_JSON";  check "allows when STOP exists" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
rm "$WF/STOP"; sed -i.bak 's/- \[ \] M1/- [x] M1/' "$WF/roadmap.md"
run 1 stop.py "$STOP_JSON";  check "allows when roadmap has no '- [ ] M' (gate lines ignored)" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
mv "$WF/roadmap.md.bak" "$WF/roadmap.md"
sed -i.bak 's/^phase: implement/phase: gated/' "$WF/state.md"
run 1 stop.py "$STOP_ACTIVE"; check "allows when stop_hook_active and phase gated" '[ $RC -eq 0 ] && [ -z "$OUT" ]'
run 1 stop.py "$STOP_JSON";   check "still blocks when gated but stop_hook_active false" '[ -n "$OUT" ]'
mv "$WF/state.md.bak" "$WF/state.md"; rm -f "$WF/.blocks"
run 1 stop.py "$STOP_ACTIVE"; check "blocks when stop_hook_active but not gated" '[ -n "$OUT" ]'
rm -f "$WF/.blocks"; printf '# config without cap\n' > "$WF/config.md"; echo 5 > "$WF/.blocks"
run 1 stop.py "$STOP_JSON";   check "default cap is 6" 'printf "%s" "$OUT" | grep -q "Block 6 of 6"'
run 1 stop.py "$STOP_JSON";   check "allows at default cap 6" '[ -z "$OUT" ]'

echo "# guard_bash.py"
setup
expect_block() { run 1 guard_bash.py "$(bash_json "$1")"; check "blocks: $1" '[ $RC -eq 2 ] && [ -n "$ERR" ] && [ "$(printf "%s\n" "$ERR" | wc -l | tr -d " ")" = "1" ]' "rc=$RC err=$ERR"; }
expect_allow() { run 1 guard_bash.py "$(bash_json "$1")"; check "allows: $1" '[ $RC -eq 0 ] && [ -z "$ERR" ]' "rc=$RC err=$ERR"; }
expect_block 'git push origin main'
expect_block 'git -C /Users/trey/dev/codeisart push'
expect_block 'bash -c "git push --force"'
expect_block 'git status && git push'
expect_block 'gh pr create --fill'
expect_block 'git reset --hard HEAD~1'
expect_block 'git checkout -- .'
expect_block 'git checkout .'
expect_block 'git restore .'
expect_block 'git clean -fdx'
expect_block 'git branch -D feature'
expect_block 'rm -rf tests/arcade/fixtures/real'
expect_block 'rm -rf /'
expect_block 'rm -rf ~/dev'
expect_block 'rm -fr build'
expect_block 'rm -r -f docs'
expect_block 'rm --recursive --force arcade'
expect_block 'rm -rf /tmp/../Users/trey'
expect_block 'rm -rf /tmp'
expect_block 'rm -rf "$HOME/x"'
expect_block 'cd /tmp && rm -rf /private/tmp/ok arcade'
expect_block 'rm tests/arcade/fixtures/real/empty-room.jsonl'
expect_block 'mv x.jsonl tests/arcade/fixtures/real/'
expect_block 'echo hi > tests/arcade/fixtures/real/a.jsonl'
expect_block 'echo hi >> tests/arcade/fixtures/real/a.jsonl'
expect_block 'cp /private/tmp/a.jsonl tests/arcade/fixtures/real/a.jsonl'
expect_block 'sed -i "" s/a/b/ tests/arcade/fixtures/real/a.jsonl'
expect_allow 'git status'
expect_allow 'pytest -q'
expect_allow 'rm -rf /private/tmp/x'
expect_allow 'rm -rf /tmp/arcade-scratch'
expect_allow 'rm -rf .venv'
expect_allow 'rm -rf /Users/trey/dev/codeisart/.venv/lib'
expect_allow 'rm stray.pyc'
expect_allow 'git commit -m "Record push notification step"'
expect_allow 'git checkout -b it03'
expect_allow 'git branch -d merged-branch'
expect_allow 'git log --oneline -5'
expect_allow 'cp tests/arcade/fixtures/real/empty-room.jsonl /private/tmp/x.jsonl'
expect_allow 'SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -rs'
run 1 guard_bash.py '{"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"PreToolUse","tool_name":"Write","tool_input":{"file_path":"x"}}'
check "ignores non-Bash tools" '[ $RC -eq 0 ]'
touch "$WF/push-allowed"
expect_allow 'git push origin main'
expect_block 'git reset --hard HEAD~1'

echo "# guard_write.py"
setup
write_json() { python3 -c 'import json,sys; print(json.dumps({"session_id":"s","transcript_path":"/x","cwd":".","hook_event_name":"PreToolUse","tool_name":sys.argv[1],"tool_input":{"file_path":sys.argv[2]}}))' "$1" "$2"; }
run 1 guard_write.py "$(write_json Write tests/arcade/fixtures/real/empty-room.jsonl.gz)"; check "write guard blocks Write to fixtures/real" '[ $RC -eq 2 ] && [ -n "$ERR" ]' "rc=$RC err=$ERR"
run 1 guard_write.py "$(write_json Edit "$ROOT/tests/arcade/fixtures/real/x.jsonl.gz")"; check "write guard blocks absolute Edit to fixtures/real" '[ $RC -eq 2 ]' "rc=$RC"
run 1 guard_write.py "$(write_json Write tests/arcade/fixtures/realish/x.txt)"; check "write guard allows a sibling dir" '[ $RC -eq 0 ] && [ -z "$ERR" ]' "rc=$RC err=$ERR"
run 1 guard_write.py "$(write_json Write arcade/games/pong.py)"; check "write guard allows game files" '[ $RC -eq 0 ] && [ -z "$ERR" ]' "rc=$RC err=$ERR"
run 1 guard_write.py "$(bash_json 'rm -rf tests/arcade/fixtures/real')"; check "write guard ignores Bash" '[ $RC -eq 0 ] && [ -z "$ERR" ]' "rc=$RC"
run "" guard_write.py "$(write_json Write tests/arcade/fixtures/real/x)"; check "write guard inert without OPERATOR" '[ $RC -eq 0 ] && [ -z "$ERR" ]'

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
