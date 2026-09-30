#!/bin/bash
# Plays one window of one slot with Codex, until GR_END (epoch seconds).
# Started by the host dispatcher; the prompt is the gamer runner's own
# build_prompt text, so both model arms get identical instructions.
# Exit: 0 played, 3 usage/rate limit (runner falls back to the free model), 4 error.
set -u
MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
DIR="/home/hermes/workspace/$GR_SLOT"
PROMPT="$HOME/prompt.txt"
RES="$DIR/.codex-result"
TMP="$HOME/run"; mkdir -p "$TMP"
LIMIT_RE='usage limit|usage_limit|rate.?limit|Too Many Requests|429|quota|insufficient_quota'
AUTH_RE='401|Unauthorized|unauthorized|refresh.?token|not logged in|log ?in again'
sessions=0; stalls=0; errors=0; fails=0; short=0; outcome=played; detail=
now() { date +%s; }

while :; do
    left=$(( GR_END - $(now) ))
    [ "$left" -lt 120 ] && break
    t0=$(now); sessions=$(( sessions + 1 ))
    timeout "$left" codex exec -m "$MODEL" --json --ephemeral --skip-git-repo-check \
        --dangerously-bypass-approvals-and-sandbox -C "$DIR" - < "$PROMPT" \
        > "$TMP/s.jsonl" 2> "$TMP/s.err"
    rc=$?; dur=$(( $(now) - t0 ))
    { printf '\n===== session codex-%s %s (exit %s, %ss) =====\n' "$sessions" "$(date -u '+%F %T')" "$rc" "$dur"
      python3 /opt/gr-codex/codex_digest.py "$TMP/sum" < "$TMP/s.jsonl"; } >> "$DIR/WINDOW_TRANSCRIPT.txt"
    ncmd=$(sed -n 's/.*commands=\([0-9]*\).*/\1/p' "$TMP/sum" 2>/dev/null); ncmd=${ncmd:-0}
    errtxt=$(grep -hE '"type":"(error|turn.failed)"' "$TMP/s.jsonl" | tail -3; tail -5 "$TMP/s.err")
    if [ "$ncmd" -eq 0 ] && printf '%s' "$errtxt" | grep -qiE "$LIMIT_RE"; then
        outcome=exhausted; detail=$(printf '%s' "$errtxt" | grep -iE "$LIMIT_RE" | head -1 | tr -d '\t' | head -c 200)
        errors=$(( errors + 1 )); break
    fi
    if [ "$ncmd" -eq 0 ] && printf '%s' "$errtxt" | grep -qE "$AUTH_RE"; then
        outcome=error; detail="auth: $(printf '%s' "$errtxt" | grep -E "$AUTH_RE" | head -1 | tr -d '\t' | head -c 160)"
        errors=$(( errors + 1 )); break
    fi
    if printf '%s' "$errtxt" | grep -qiE "$LIMIT_RE"; then
        # limit hit mid-session after real play: stop here, the runner falls back
        outcome=exhausted; detail="mid-window: $(printf '%s' "$errtxt" | grep -iE "$LIMIT_RE" | head -1 | tr -d '\t' | head -c 160)"
        break
    fi
    if [ "$dur" -lt 90 ] || [ "$ncmd" -eq 0 ]; then
        stalls=$(( stalls + 1 )); short=$(( short + 1 ))
        if [ "$ncmd" -eq 0 ] || { [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ]; }; then
            errors=$(( errors + 1 )); fails=$(( fails + 1 ))
        fi
        # never loop on errors: 2 failed or 4 short sessions in a row end the codex arm
        if [ "$fails" -ge 2 ] || [ "$short" -ge 4 ]; then
            outcome=error; detail="$short short / $fails failed sessions in a row (rc $rc): $(printf '%s' "$errtxt" | grep -v WARNING | tail -1 | tr -d '\t' | head -c 160)"
            break
        fi
        sleep 30
    else
        fails=0; short=0; sleep 5
    fi
done
printf 'outcome=%s\tsessions=%s\tstalls=%s\terrors=%s\tdetail=%s\n' \
    "$outcome" "$sessions" "$stalls" "$errors" "$detail" > "$RES"
case "$outcome" in played) exit 0 ;; exhausted) exit 3 ;; *) exit 4 ;; esac
