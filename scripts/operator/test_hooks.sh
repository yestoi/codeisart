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

# run <OPERATOR value or ""> <script> <json> [args...]; sets OUT, ERR, RC.
# RUN_CWD is the working directory (default: the project root). RUN_PROJECT is CLAUDE_PROJECT_DIR
# (default: the project root; "-" leaves it unset). The caller's own OPERATOR and CLAUDE_PROJECT_DIR
# never reach a script, so a test run inside a Claude session cannot touch the real workflow files.
run() {
  local op="$1" script="$2" json="$3"; shift 3
  local cwd="${RUN_CWD:-$ROOT}" project="${RUN_PROJECT:-$ROOT}"
  local -a envs=(env -u OPERATOR -u CLAUDE_PROJECT_DIR)
  [ -n "$op" ] && envs+=("OPERATOR=$op")
  [ "$project" != "-" ] && envs+=("CLAUDE_PROJECT_DIR=$project")
  OUT="$(cd "$cwd" && printf '%s' "$json" | "${envs[@]}" python3 "$HERE/$script" "$@" 2>"$TMP/err")"; RC=$?
  ERR="$(cat "$TMP/err")"
}
no_agent() { sed -i.bak 's/^in_flight: .*/in_flight: none/' "$WF/state.md"; rm -f "$WF/state.md.bak"; }

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
OUT="$(cd "$ROOT" && OPERATOR=1 CLAUDE_PROJECT_DIR="$ROOT" python3 "$HERE/precompact.py" < "$TMP/badjson" 2>/dev/null)"; RC=$?
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
check "says config.md's Loop rules override the skill" 'printf "%s" "$OUT" | grep -q "^config.md.s Loop rules override the workflow-loop skill"'
check "says never to change directory" 'printf "%s" "$OUT" | grep -q "Never change directory in a Bash command"'
check "after a compaction the agents are still there" '! printf "%s" "$OUT" | grep -q "every agent of the last session is gone"'
printf '# Gate\nQuestion: keep pong?\n' > "$WF/gate.md"
run 1 reinject.py "$SS_JSON" --fresh
check "--fresh prints the state file list" 'printf "%s" "$OUT" | grep -q "^- config.md: " && printf "%s" "$OUT" | grep -q "^- live-smoke.md: " && printf "%s" "$OUT" | grep -q "^- evidence/itNN/: "'
check "prints gate.md when present" 'printf "%s" "$OUT" | grep -q "Question: keep pong?"'
check "--fresh says the last session's agents are gone" 'printf "%s" "$OUT" | grep -q "every agent of the last session is gone" && printf "%s" "$OUT" | grep -q "set .in_flight. to none"'
check "--fresh prints the Loop rules note too" 'printf "%s" "$OUT" | grep -q "Loop rules override"'
check "--fresh opens as a new session, not as a compaction" '[ "$(printf "%s\n" "$OUT" | head -1)" = "You are the arcade operator, starting a new session. Enter the workflow loop at the phase in state.md. Do not redo an iteration the journal marks done and do not re-plan a committed plan. Files are truth." ]'
check "--fresh never says to SendMessage a lost agent" '! printf "%s" "$OUT" | grep -q "Context was compacted" && ! printf "%s" "$OUT" | grep -q "(SendMessage it instead)"'
rm "$WF/gate.md"; printf '# Iteration journal\n' > "$WF/journal.md"
python3 - "$WF/decisions.md" <<'P'
import sys; p=sys.argv[1]; s=open(p).read().replace("answer:\nstatus: open","answer: 1.2 s\nstatus: answered"); open(p,"w").write(s)
P
run 1 reinject.py "$SS_JSON"
check "notes empty journal" 'printf "%s" "$OUT" | grep -q "has no .## Iteration. entry yet"'
check "notes no open question" 'printf "%s" "$OUT" | grep -q "(no open question in decisions.md)"'

echo "# stop.py"
setup; no_agent
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

echo "# stop.py: stop-blocks sets the hook's cap apart from the iteration cap"
setup; no_agent
printf -- '# Workflow config\n- iterations-per-run: 2\n- stop-blocks: 5\n' > "$WF/config.md"
run 1 stop.py "$STOP_JSON"; check "stop-blocks wins over iterations-per-run" 'printf "%s" "$OUT" | grep -q "Block 1 of 5"'
echo 4 > "$WF/.blocks"; rm -f "$WF/.blocks-head"
run 1 stop.py "$STOP_JSON"; check "blocks up to stop-blocks" 'printf "%s" "$OUT" | grep -q "Block 5 of 5"'
run 1 stop.py "$STOP_JSON"; check "allows at stop-blocks" '[ -z "$OUT" ]'

echo "# stop.py: the counter starts again when a commit lands"
setup; no_agent
run 1 stop.py "$STOP_JSON"; run 1 stop.py "$STOP_JSON"; run 1 stop.py "$STOP_JSON"
run 1 stop.py "$STOP_JSON"
check "at the cap with no new commit the stop is allowed" '[ -z "$OUT" ] && [ "$(cat "$WF/.blocks")" = "3" ]'
( cd "$ROOT" && echo work > work.txt && git add work.txt && git -c user.email=t@t -c user.name=t commit -qm work )
run 1 stop.py "$STOP_JSON"
check "after a commit the count starts again at 1" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ] && printf "%s" "$OUT" | grep -q "Block 1 of 3"'
run 1 stop.py "$STOP_JSON"
check "and counts on from there" '[ "$(cat "$WF/.blocks")" = "2" ]'
check "the counter's commit is kept beside it" '[ "$(cat "$WF/.blocks-head")" = "$(cd "$ROOT" && git rev-parse HEAD)" ]'
rm -f "$WF/.blocks-head"; echo 3 > "$WF/.blocks"
run 1 stop.py "$STOP_JSON"
check "a counter with no recorded commit is not reset" '[ -z "$OUT" ] && [ "$(cat "$WF/.blocks")" = "3" ]'

echo "# stop.py while an agent is in flight"
setup
run 1 stop.py "$STOP_JSON"
check "allows, uncounted, while state.md names an agent in flight" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ ! -e "$WF/.blocks" ]'
run 1 stop.py "$STOP_ACTIVE"
check "allows in flight with stop_hook_active too" '[ $RC -eq 0 ] && [ -z "$OUT" ] && [ ! -e "$WF/.blocks" ]'
touch -t 202601010000 "$WF/state.md"
run 1 stop.py "$STOP_JSON"
check "blocks and counts when the in-flight state is stale" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ]'
check "stale block tells the operator to check the agent" 'printf "%s" "$OUT" | python3 -c "import json,sys; r=json.load(sys.stdin)[\"reason\"]; assert \"ListAgents\" in r and \"in_flight\" in r, r"'
for v in "none" "none (it05 done at a1320bc; state committed)" "None" ""; do
  setup; sed -i.bak "s/^in_flight: .*/in_flight: $v/" "$WF/state.md"; rm -f "$WF/state.md.bak"
  run 1 stop.py "$STOP_JSON"; check "blocks when in_flight is '$v'" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ]'
done
setup; sed -i.bak '/^in_flight:/d' "$WF/state.md"; rm -f "$WF/state.md.bak"
run 1 stop.py "$STOP_JSON"; check "blocks when state.md has no in_flight line" '[ -n "$OUT" ]'
setup; touch "$WF/gate.md"
run 1 stop.py "$STOP_JSON"; check "gate.md still allows with an agent in flight" '[ -z "$OUT" ] && [ ! -e "$WF/.blocks" ]'

echo "# a drifted working directory"
setup; no_agent
mkdir -p "$ROOT/scripts/operator"
RUN_CWD="$ROOT/scripts/operator"
run 1 stop.py "$STOP_JSON"
check "stop finds the workflow dir from a subdirectory" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ] && [ ! -e "$RUN_CWD/docs" ]'
run 1 guard_bash.py "$(bash_json 'git push origin main')"
check "bash guard still blocks from a subdirectory" '[ $RC -eq 2 ] && [ -n "$ERR" ]' "rc=$RC err=$ERR"
run 1 guard_write.py "$(write_json Write ../../tests/arcade/fixtures/real/x.jsonl.gz)"
check "write guard still blocks from a subdirectory" '[ $RC -eq 2 ]' "rc=$RC"
run 1 precompact.py "$PRE_AUTO"
check "precompact writes the footer to the project's state.md" 'grep -q "^- head: $HEAD_SHA" "$WF/state.md"'
run 1 reinject.py "$SS_JSON"
check "reinject prints state.md from a subdirectory" 'printf "%s" "$OUT" | grep -q "^phase: implement"'
RUN_PROJECT="-"; rm -f "$WF/.blocks"
run 1 stop.py "$STOP_JSON"
check "without CLAUDE_PROJECT_DIR the root is found by walking up" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ]'
run 1 guard_bash.py "$(bash_json 'git push origin main')"
check "bash guard blocks from a subdirectory without CLAUDE_PROJECT_DIR" '[ $RC -eq 2 ]' "rc=$RC"
RUN_PROJECT="$TMP/no-such-dir"; rm -f "$WF/.blocks"
run 1 stop.py "$STOP_JSON"
check "a CLAUDE_PROJECT_DIR that does not exist falls back to walking up" '[ -n "$OUT" ] && [ "$(cat "$WF/.blocks")" = "1" ]'
unset RUN_CWD RUN_PROJECT
check "every hook command in settings.json is anchored to the project dir" 'python3 - "$HERE/../../.claude/settings.json" <<"P"
import json, sys
hooks = json.load(open(sys.argv[1]))["hooks"]
cmds = [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]
ours = [c for c in cmds if "scripts/operator/" in c]
assert len(ours) == 6, ours
bad = [c for c in ours if not c.startswith("python3 \"$CLAUDE_PROJECT_DIR/scripts/operator/")]
assert not bad, bad
# the hooks of other tools (graft, 2026-09-30) must be anchored too; the :-. fallback is anchored in a hook
others = [c for c in cmds if c not in ours]
bad = [c for c in others if "$CLAUDE_PROJECT_DIR/" not in c and "${CLAUDE_PROJECT_DIR:-.}/" not in c]
assert not bad, bad
P'
check "worktrees of subagents start from the local HEAD, not the remote's" 'python3 - "$HERE/../../.claude/settings.json" <<"P"
import json, sys
assert json.load(open(sys.argv[1])).get("worktree", {}).get("baseRef") == "head"
P'

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
