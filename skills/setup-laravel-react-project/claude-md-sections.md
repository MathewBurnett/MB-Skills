# CLAUDE.md sections

Loaded in Step 6, after every prior step has run — the sections below name things (`composer setup`, `graphify-out/`, the deploy job) that must already exist before pointing at them.

`setup-git-workflow` and `setup-matt-pocock-skills` write their own `## Shipping` and `## Agent skills` blocks in place — don't duplicate those here. This file covers only the two sections neither of them owns.

## Detect the target file

Same rule as `setup-git-workflow`: edit `CLAUDE.md` if it exists, else `AGENTS.md`, else ask which to create. If Step 0 chose defaults, create `CLAUDE.md` without asking (matches `setup-matt-pocock-skills`'s own default).

## `## Setup`

Laravel's own installer always ships a `composer.json` `scripts.setup` entry (install deps, copy `.env`, generate key, migrate, build assets) — this section exists on every project bootstrapped by Step 1, no branch needed:

```markdown
## Setup

On a fresh checkout run `composer setup` — installs PHP + JS deps, copies `.env.example` to `.env`, generates the app key, migrates the database, and builds frontend assets. For the full Docker stack see `docker compose up --build` in the README instead.
```

## `## graphify`

```markdown
## graphify

This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost) — this also runs automatically via the `.git/hooks/post-commit` hook installed for this repo.
```

If `graphify-out/wiki/index.md` exists (only if `--wiki` was run separately — Step 5 doesn't do this by default), add a line pointing at it for broad navigation, above the `GRAPH_REPORT.md` line.

## If the CI deploy job was added (Step 4)

Append this to whatever `## Shipping` section `setup-git-workflow` already wrote, rather than a new heading — it's a consequence of shipping, not a separate topic:

```markdown
**Merging into `main` deploys.** CI builds and pushes a Docker image tagged `v<VERSION>` and moves `:live` on every merge — a Watchtower-style host polling `:live` picks it up. To hold a change back from deploying, hold it back from `main`.
```

## What not to carry over

When adapting a CLAUDE.md from a reference project (this file, or another project's), check each candidate section against what actually exists here before including it:

- A section naming a file, script, or convention that Step 1–6 didn't create — don't reference it.
- A token-budget / tool-specific line (`@RTK.md` or similar) already covered by the user's global `~/.claude/CLAUDE.md` — don't duplicate it project-side.
- LFS or `core.hooksPath` setup instructions — only relevant if this project actually adopted those (see `graphify-hooks.md`'s closing note); most won't have.
- Domain-specific sections from the reference project (a data-ingestion guide, a screenshots convention) — these belong to that project's domain, not this one's.
