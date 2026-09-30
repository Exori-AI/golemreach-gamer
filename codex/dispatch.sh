#!/bin/bash
# Host-side dispatcher for the Codex play arm. Run it every minute from cron.
# The gamer container asks for a Codex window by dropping <slot>.req (end=<epoch>)
# and <slot>.prompt into <workspace>/.codex/; this script claims the request
# (atomic mv), starts one gr-codex container for it and writes <slot>.status:
#   running | played | exhausted (usage/rate limit) | error <rc> | busy | refused <why>
# The container gets only: the Codex login (copied in, never bind-mounted),
# that slot's game token (env, never argv), /gamer read-only and that slot's
# notebook directory. Required env:
#   GR_WS_HOST     host path of the gamer workspace volume
#   GR_ENV_FILE    the runner's .env (GAMER_SLOTS, GAMERn_API_KEY, GAMERn_CHARACTER_ID)
#   GR_GAMER_DIR   host path of gamer/ (mounted read-only as /gamer)
set -u
WS_HOST="${GR_WS_HOST:?}"; ENV_FILE="${GR_ENV_FILE:?}"; GAMER_DIR="${GR_GAMER_DIR:?}"
AUTH="${CODEX_AUTH:-$HOME/.codex/auth.json}"
IMAGE="${CODEX_IMAGE:-gr-codex:local}"
MODEL="${CODEX_MODEL:-gpt-5.6-terra}"
MAXC="${CODEX_MAX_CONCURRENT:-2}"      # leave Codex headroom for its other users
MAX_WINDOW="${CODEX_MAX_WINDOW:-7800}"
Q="$WS_HOST/.codex"
log() { echo "[gr-codex] $(date -u '+%F %T') $*"; }

envval() {   # envval KEY -> value from the .env file, quotes stripped
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -1 | sed "s/^[\"']//; s/[\"']\$//"
}

status() { printf '%s at=%s\n' "$2" "$(date +%s)" > "$Q/$1.status.tmp"; chown 1000:1000 "$Q/$1.status.tmp"; mv "$Q/$1.status.tmp" "$Q/$1.status"; }

worker() {
    local slot="$1" i=0 idx=0 s end now left cname="gr-codex-$1" tmp rc
    for s in $(envval GAMER_SLOTS); do i=$(( i + 1 )); [ "$s" = "$slot" ] && idx=$i; done
    [ "$idx" -gt 0 ] || { status "$slot" "refused unknown-slot"; return; }
    end=$(sed -n 's/^end=\([0-9]*\)$/\1/p' "$Q/$slot.taken"); now=$(date +%s)
    case "$end" in ''|*[!0-9]*) status "$slot" "refused bad-request"; return ;; esac
    left=$(( end - now ))
    { [ "$left" -ge 120 ] && [ "$left" -le "$MAX_WINDOW" ]; } || { status "$slot" "refused window-${left}s"; return; }
    [ -f "$Q/$slot.prompt" ] && [ "$(wc -c < "$Q/$slot.prompt")" -lt 100000 ] || { status "$slot" "refused prompt"; return; }
    [ -d "$WS_HOST/$slot" ] || { status "$slot" "refused no-notebook-dir"; return; }
    [ -r "$AUTH" ] || { status "$slot" "error no-codex-login"; return; }
    exec 8>/tmp/gr-codex-start.lock; flock 8   # count + create atomically across workers
    if docker ps -a -q --filter "name=^${cname}\$" | grep -q .; then status "$slot" "busy already-running"; return; fi
    if [ "$(docker ps -a -q --filter 'name=^gr-codex-' | wc -l)" -ge "$MAXC" ]; then status "$slot" "busy max-$MAXC"; return; fi

    GR_TOKEN=$(envval "GAMER${idx}_API_KEY"); GR_CHARACTER=$(envval "GAMER${idx}_CHARACTER_ID")
    GR_BASE=$(envval GAMER_BASE_URL); GR_BASE=${GR_BASE:-https://play.golemreach.com}
    [ -n "$GR_TOKEN" ] && [ -n "$GR_CHARACTER" ] || { status "$slot" "refused no-token"; return; }
    export GR_TOKEN GR_CHARACTER GR_BASE GR_SLOT="$slot" GR_END="$end" CODEX_MODEL="$MODEL" \
        GR_EVENTS_FILE="/home/hermes/workspace/$slot/DEATHS.tsv"
    if ! docker create --name "$cname" --user 1000:1000 --cap-drop ALL \
            --security-opt no-new-privileges --memory 1g --pids-limit 256 \
            -e GR_TOKEN -e GR_CHARACTER -e GR_BASE -e GR_SLOT -e GR_END -e CODEX_MODEL -e GR_EVENTS_FILE \
            -v "$GAMER_DIR:/gamer:ro" -v "$WS_HOST/$slot:/home/hermes/workspace/$slot" \
            "$IMAGE" >/dev/null; then
        status "$slot" "error create"; return
    fi
    exec 8>&-
    unset GR_TOKEN
    tmp=$(mktemp -d); mkdir -p "$tmp/home/.codex"
    cp "$AUTH" "$tmp/home/.codex/auth.json"; cp "$Q/$slot.prompt" "$tmp/home/prompt.txt"
    tar -C "$tmp" -c --owner=1000 --group=1000 --numeric-owner home | docker cp - "$cname:/tmp" >/dev/null
    rm -rf "$tmp"
    status "$slot" "running"
    log "slot $slot: codex ($MODEL) window until $(date -u -d "@$end" '+%T') UTC"
    timeout $(( left + 300 )) docker start -a "$cname" > "$Q/$slot.container.log" 2>&1
    rc=$?
    docker rm -f "$cname" >/dev/null 2>&1
    case "$rc" in
        0|124) status "$slot" "played" ;;
        3) status "$slot" "exhausted" ;;
        *) status "$slot" "error rc$rc" ;;
    esac
    log "slot $slot: codex container exited rc=$rc"
}

if [ "${1:-}" = "--worker" ]; then worker "$2"; exit 0; fi

exec 9>/tmp/gr-codex-dispatch.lock
flock -n 9 || exit 0
[ -d "$Q" ] || exit 0
for req in "$Q"/*.req; do
    [ -e "$req" ] || continue
    slot=$(basename "$req" .req)
    case "$slot" in *[!a-z0-9_-]*|'') rm -f "$req"; continue ;; esac
    mv "$req" "$Q/$slot.taken" 2>/dev/null || continue   # the runner may have cancelled it
    setsid bash "$0" --worker "$slot" 9>&- < /dev/null &
done
