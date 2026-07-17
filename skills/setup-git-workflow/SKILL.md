---
name: setup-git-workflow
description: Scaffold this repo's ship/land scripts, versioning, health endpoint, and branch topology — trunk, stage-promotion, or epic branches. Run once when starting a repo.
disable-model-invocation: true
---

# Setup Git Workflow

Scaffold the shipping path a repo's agents and humans both use:

- **`bin/ship`** — verify, branch, commit, push, open a PR. Never merges.
- **`bin/land`** — merge an open PR once CI is green, then sync the base.
- **`bin/hooks/pre-push`** — a push guard: blocks any push that didn't come through `ship`, so a bare `git push` can't skip verify + version-stamping and cost the PR a second CI run.
- **`bin/version`** + `VERSION` — the version the running app reports.
- **`GET /health`** — 200 + `{status, version}`, so a deploy is checkable from outside.
- **`docs/agents/git-workflow.md`** — the **topology**: which branch is the base, and when to pass `--base`.

The split is the point: `ship` stops at the PR so review happens; `land` is the deliberate second act. The push guard keeps that split honest — it stops a stray `git push` from opening or updating a PR behind ship's back, and with it the verify and version-stamping that make the PR pass CI on the first run. Preserve both in every variant you generate.

These join up: `bin/version` writes `VERSION`, `ship` stamps it with the PR number, and `/health` reports it — so `curl <host>/health` answers "which PR is live?" from outside the box.

This is prompt-driven, not a script. Explore, propose, confirm, then write.

## Process

### 1. Explore

Read the repo's real state — don't assume:

- `git remote -v`, `git branch -a` — is there a GitHub remote? Does a persistent `stage`/`develop`/`Users`-style branch already exist? Any `epic/*` branches?
- `bin/` — do `ship`, `land`, or `test` already exist? If so, this is a **re-run**: read them and propose edits, not overwrites.
- `git config core.hooksPath` and `.git/hooks/pre-push` — is a hooks path or pre-push hook already set? The push guard installs via `core.hooksPath bin/hooks`, which is all-or-nothing; if either is already in use, surface it and ask before redirecting, don't clobber another repo's hooks.
- Toolchain manifests — `composer.json`, `package.json`, `Cargo.toml`, `Makefile`, `pyproject.toml`. Read the actual `scripts`/task names; the lint and verify commands you generate must be ones this repo really has.
- `.github/workflows/` — do checks run on PRs? Which branches trigger them?
- `CLAUDE.md` / `AGENTS.md` — does either exist, and is there already a `## Shipping` section?
- `VERSION`, and any version already in a manifest or `config` — where does the app currently think its version comes from?
- The **route table** and any SPA catch-all or static mount — this decides where `/health` can go without being swallowed.

### 2. Present and ask, one section at a time

Summarise what you found, then walk the three decisions **in order**, waiting for an answer before the next. Assume the user hasn't thought about topology in these terms — each section opens with a short explainer, then the choices and a default.

**Section A — Topology.** Read [topologies.md](topologies.md) and present the three, with your recommendation based on step 1 (a `stage` branch already on the remote points at stage-promotion; a bare `main` points at trunk). The answer sets `DEFAULT_BASE` in the generated scripts.

**Section B — Epic branches.** Explainer: an epic is a long feature built from several PRs that shouldn't reach the base branch half-finished. Slices ship into `epic/<slug>` with `--base epic/<slug>`; the epic lands into the base as one PR. `--base` is already in both scripts, so this asks whether to *document* the epic convention and which prefix to use (default `epic/`).

**Section C — CI on the base branches.** Explainer: `bin/land` waits for `gh pr checks` to go green, but PRs into a `stage` or epic branch often have no checks configured — so land can't simply wait, or those merges hang forever. Instead it splits on the base: "no checks reported" on a base that *does* run CI means CI failed to register, and land refuses (`--no-checks` overrides); on one that doesn't, it proceeds. Confirm which branches actually run checks — the answer fills `{{CHECKED_BASES}}`, so a wrong answer here either blocks every land or silently un-gates one. Ask; don't run `gh api` to change branch protection.

**Section D — Versioning.** Explainer: a version is only useful if the running app reports the same string the repo does, so `VERSION` is the single source of truth and everything else reads it. Two schemes:

- **M.R.V.f** (default) — major.revision.PR.fix. `V` is the PR number, so a deployed version names the PR that shipped it, and `R` maps onto closing an epic. Right for an app you deploy.
- **Semver** — for anything consumers depend on, where the number is a compatibility promise.

The choice changes `ship`: M.R.V.f stamps `V` automatically (predicting the PR number, then confirming it once the PR is open), while semver is a judgement call `ship` must never make for you.

**Section E — Health endpoint.** Explainer: `GET /health` returns 200 and `{"status":"ok","version":"…"}` — no auth, no database. It makes a deploy verifiable from outside (`curl <host>/health`) and tells you *which* version is actually live. Confirm the path is free, and ask whether existing overlapping endpoints should fold into it. Read [health-endpoint.md](health-endpoint.md) before writing any of it.

### 3. Confirm

Show the user the full generated `bin/ship`, `bin/land`, the `docs/agents/git-workflow.md`, and the `## Shipping` block — before writing anything. Let them edit.

### 4. Write

Fill the templates and write the files:

- [ship.template](ship.template) → `bin/ship`, `chmod +x`
- [land.template](land.template) → `bin/land`, `chmod +x`
- [pre-push.template](pre-push.template) → `bin/hooks/pre-push`, `chmod +x`; then `git config core.hooksPath bin/hooks` — unless the Explore step found an existing hooks path to reconcile first. `ship` already exports the `GIT_SHIP=1` sentinel the hook waits for; no placeholder to fill. A fresh clone re-runs the one `git config` line, so note it in `git-workflow.md`.
- [promote.template](promote.template) → `bin/promote`, `chmod +x` — **stage-promotion topology only**
- [version-mrvf.template](version-mrvf.template) or [version-semver.template](version-semver.template) → `bin/version`, `chmod +x`; seed `VERSION`
- [version-bump.snippet](version-bump.snippet) → two blocks, spliced into ship's `{{VERSION_PREDICT_BLOCK}}` (before the commit) and `{{VERSION_VERIFY_BLOCK}}` (after the PR opens) — **M.R.V.f only**; for semver or no versioning, delete both placeholder lines. They're a pair: the predict block sets `$predicted`, which the verify block reads.
- The health route, its config wiring, and its test — per [health-endpoint.md](health-endpoint.md)
- [git-workflow.md](git-workflow.md) → `docs/agents/git-workflow.md`

Every `{{PLACEHOLDER}}` gets replaced with a command this repo really runs, or its block deleted. A generated script that shells out to a task the repo doesn't define is worse than no script.

Record the versioning scheme as an ADR if the repo keeps `docs/adr/` — it's a decision with consequences, and `bin/version` should cite it.

Edit `CLAUDE.md` if it exists, else `AGENTS.md`, else ask which to create — never create the second when the first is there. Update an existing `## Shipping` block in place:

```markdown
## Shipping

`bin/ship [--base <branch>] "<title>"` opens a PR ([verify steps]); `bin/land [--base <branch>] [<pr>]` merges it. [One line on the topology and when to pass `--base`.] See `docs/agents/git-workflow.md`.
```

### 5. Verify

The scripts run against a live remote, so prove what you can before the user trusts them, and report exactly what you ran:

- `bash -n` every generated script.
- `bin/ship` with no arguments — prints usage, exits 2.
- The push guard, without touching the remote: `bin/hooks/pre-push </dev/null` exits 1 and prints the reminder; `GIT_SHIP=1 bin/hooks/pre-push </dev/null` exits 0 silently. Confirm `git config core.hooksPath` now reads `bin/hooks`.
- `bin/version show` — prints the seeded version.
- Boot the app and `curl -fsS localhost:<port>/health` — assert on the **body**, not just the status. A catch-all serving the SPA shell returns a cheerful 200 of HTML, so a status-only check proves nothing.
- Run the health test.

Leave the first real PR to the user: an end-to-end proof needs a live remote, and `ship`'s force-push path is not something to rehearse on their repo.
