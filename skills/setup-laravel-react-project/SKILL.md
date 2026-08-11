---
name: setup-laravel-react-project
description: Bootstrap a Laravel + React project the way Mathew likes it — Dockerized skeleton, CI, git workflow, engineering-skill config, and a graphify knowledge graph. Run once when starting a new Laravel + React project, or to bring an existing one up to the same standard.
disable-model-invocation: true
---

# Setup Laravel React Project

Scaffolds the full stack, in order:

- A Dockerized Laravel + React skeleton (Vite, a chosen database, a health check, tests) — `bootstrap.md`.
- Claude settings that deny reads into `vendor/`, `node_modules/`, and other build noise.
- **`bin/ship`** / **`bin/land`** / **`bin/version`**, via `/setup-git-workflow`.
- CI — a `tests` job always, an optional image-build-and-deploy job — `ci.md`.
- Issue tracker, triage labels, and domain-doc conventions, via `/setup-matt-pocock-skills`.
- A **graphify** knowledge graph plus the guard and auto-rebuild hooks — `graphify-hooks.md`.
- The `## Setup` and `## graphify` sections of `CLAUDE.md` — `claude-md-sections.md`.

Each step's own file states its own completion criterion; treat "the step's file said what to check" as the bar, not "I ran the commands."

**Step 1 is optional.** Ask first: was this project's skeleton already built — by hand, or to requirements this skill's generic `bootstrap.md` doesn't cover (a different auth setup, a non-standard directory layout, business logic already in place)? If so, skip Step 1 and start at Step 2 against the skeleton as it stands; don't try to reconcile it with what `bootstrap.md` would have produced. If there's no skeleton yet, run Step 1 as written.

## Step 0 — Defaults or ask

`/setup-git-workflow` and `/setup-matt-pocock-skills` each ask their own questions (topology, versioning, issue tracker, triage labels, domain docs). Ask once, up front:

> Use the usual defaults for the interactive steps ahead (trunk topology, M.R.V.f versioning, keep both `/up` and `/health`, epic branches documented now; GitHub issue tracker, default triage labels, single-context domain docs, `CLAUDE.md`), or answer each sub-skill's questions yourself as they come up?

**Defaults** — when `/setup-git-workflow` or `/setup-matt-pocock-skills` reach a question covered by the list above, answer it yourself with that answer instead of surfacing `AskUserQuestion`. Any question *not* covered by the list (there shouldn't be many — the sub-skills mostly ask exactly these things) still goes to the human.

**Ask** — run both sub-skills exactly as their own SKILL.md prescribes; every question surfaces normally.

The database question in `bootstrap.md` and the CI-deploy-job question in `ci.md` are **not** covered by this toggle — both are answered fresh every run regardless, because both are genuinely project-specific rather than a standing preference.

## Step 1 — Bootstrap the skeleton (optional — see above)

See `bootstrap.md`.

## Step 2 — Claude settings: deny build noise

Invoke the `update-config` skill with this payload — adjust the list only if the project's actual directory names differ (check what Step 1 produced first):

```
Create or merge into .claude/settings.json a permissions.deny list:
Read(./vendor/**), Read(./node_modules/**), Read(./dist/**), Read(./build/**),
Read(./coverage/**), Read(./public/build/**), Read(./storage/framework/**),
Read(./bootstrap/cache/**)
```

## Step 3 — Git workflow

Invoke `/setup-git-workflow`. Apply the Step 0 answer to its questions.

## Step 4 — CI

See `ci.md`. Runs after Step 3 because the optional deploy job reads `VERSION`.

## Step 5 — Engineering skill config

Invoke `/setup-matt-pocock-skills`. Apply the Step 0 answer to its questions.

## Step 6 — graphify

Run `/graphify` (no args — current directory) to build the graph, then see `graphify-hooks.md` for the guard and auto-rebuild hooks. Always — this isn't optional the way the CI deploy job is.

## Step 7 — CLAUDE.md sections

See `claude-md-sections.md`.

## Step 8 — Verify

Re-check, don't assume the per-step criteria still hold after later steps touched shared files (`CLAUDE.md`, `.claude/settings.json`):

- `composer test && npm run build` green.
- `jq .` on `.claude/settings.json` — still valid after every step that touched it.
- `docker compose config` validates; `docker compose up --build` actually boots if a daemon is reachable, otherwise say so explicitly rather than claiming it works.
- `git status` reviewed before offering to commit — nothing unexpected staged, no `.env` or secret leaked into what's about to be tracked.

Report what got skipped (no daemon, deploy job declined, defaults vs. asked) alongside what got built — the goal is an accurate account of the resulting project, not a checklist of steps run.
