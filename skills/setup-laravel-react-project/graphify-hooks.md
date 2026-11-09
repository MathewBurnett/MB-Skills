# graphify hooks

Loaded in Step 5, after `/graphify` has built `graphify-out/graph.json`. Wires the guard nudge and the auto-rebuild hook — always, no question to ask here (the graphify step itself is unconditional per Step 5).

## Guard hooks (PreToolUse)

Copy `graphify-guard-once.sh` (bundled next to this file) to `.claude/hooks/graphify-guard-once.sh` in the target project, `chmod +x` it, and merge this into `.claude/settings.json` (via the `update-config` skill, or directly if the file is simple — **merge**, never overwrite: `settings.json` already carries the `permissions.deny` block from Step 2):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Grep",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/graphify-guard-once.sh\" search" }
        ]
      },
      {
        "matcher": "Read|Glob",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/graphify-guard-once.sh\" read" }
        ]
      }
    ]
  }
}
```

This is a deliberate improvement over graphify's own native `graphify claude install` (which wires the same matchers but calls `graphify hook-guard <kind>` directly, with no session dedup) — use the wrapper, not the raw command.

Verify before moving on, the same way any hook install is verified: `jq .` the settings file for valid JSON, then pipe-test the wrapper directly —

```bash
echo '{"session_id":"test","tool_name":"Bash","tool_input":{}}' | .claude/hooks/graphify-guard-once.sh search   # emits the reminder
echo '{"session_id":"test","tool_name":"Bash","tool_input":{}}' | .claude/hooks/graphify-guard-once.sh search   # silent — same session, deduped
rm -f /tmp/.graphify-nudged-search-test
```

## Auto-rebuild hook (git)

```bash
graphify hook install
```

Installs `post-commit` and `post-checkout` into the directory `core.hooksPath` names — `bin/hooks/`, set by `/setup-git-workflow` in Step 3 — and registers a `graphify-out/graph.json merge=graphify` line in `.gitattributes` so future merges union the graph instead of conflicting on raw JSON. Confirm with `graphify hook status`, and commit the two new hooks so every clone shares them.
