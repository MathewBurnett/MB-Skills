#!/usr/bin/env bash
# Wraps `graphify hook-guard <kind>` so its "MANDATORY: run graphify query
# first" reminder fires once per session instead of on every matching
# Read/Grep/Bash call. graphify's own soft nudge (the default, non-strict
# path) has no session-level dedup — only its opt-in --strict *deny* tracks
# "once per session" (see _mark_session_denied in graphify's cli.py). Without
# this wrapper the identical reminder text gets re-injected into context on
# every single matching tool call — measured at 150+ repeats in one long
# session, pure token overhead once the agent has already oriented itself.
#
# Usage (from settings.json): graphify-guard-once.sh search|read
set -euo pipefail

kind="${1:?usage: graphify-guard-once.sh <search|read>}"
input="$(cat)"
session_id="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null || true)"

# No session_id to key on (unexpected input shape) -> fall back to graphify's
# own behavior every time rather than silently dropping the guardrail.
if [ -z "$session_id" ]; then
    printf '%s' "$input" | exec graphify hook-guard "$kind"
fi

marker="/tmp/.graphify-nudged-${kind}-${session_id}"
if [ -f "$marker" ]; then
    exit 0
fi

output="$(printf '%s' "$input" | graphify hook-guard "$kind" || true)"
if [ -n "$output" ]; then
    touch "$marker" 2>/dev/null || true
    printf '%s' "$output"
fi
