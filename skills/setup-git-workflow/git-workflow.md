# Git workflow

<!-- Seed template. Fill the bracketed parts from the setup answers, delete the
     sections that don't apply, and delete this comment. -->

## Topology

**[Trunk | Stage-promotion]** — the default base branch is **`{{DEFAULT_BASE}}`**.

[One diagram or two sentences: what each persistent branch means, and what a merge into it causes (a deploy? a release?).]

Persistent branches — never deleted, never committed to directly: [`main`, `stage`].

## Shipping a change

```bash
bin/ship "feat: short title"     # verify → branch → commit → push → PR into {{DEFAULT_BASE}}
bin/land [<pr>]                  # merge once CI is green, then sync {{DEFAULT_BASE}}
```

`ship` takes the work however it's presented: uncommitted changes it commits
under the title, commits you already prepared on the branch it ships *untouched*
(the title is optional then — borrowed from your first commit), and a mix of both
it commits the leftovers on top. It stops at the PR on purpose — review happens
there. `land` is the separate, deliberate merge. Branch names are derived from
the title: `feat: add export` → `feat/add-export`.

### Push guard

A `pre-push` hook (`bin/hooks/pre-push`, wired in via `core.hooksPath bin/hooks`)
stops two pushes from happening behind `ship`'s back:

1. **A direct push to a persistent deploy branch** (`{{PROTECTED_BRANCHES}}`) —
   those build and ship on merge, so nothing reaches them except a reviewed PR.
2. **A push to a feature branch whose open PR runs checks** (base in
   `{{CHECKED_BASES}}`) — it re-runs that PR's CI on an unstamped, unverified
   commit.

The aim is a **one-run PR**: `ship` stamps `VERSION` and runs verify *before* it
pushes, so CI runs once, green, on a commit that's already right. A bare
`git push` skips that and costs a second CI run — or a red one. `ship` sets
`GIT_SHIP=1` so its own pushes pass; everything else that would trigger CI is
stopped with a reminder.

A push that *wouldn't* trigger CI — a feature branch with no PR yet, or a PR into
a base that runs no checks — is let straight through.

```bash
git push --no-verify    # deliberate escape hatch, for the rare genuine case
```

The guard only runs once `core.hooksPath` points at `bin/hooks`, and that's
per-checkout local config git never tracks — so a fresh clone starts with it
**inactive**. Two activators turn it back on for you:

- a Claude **`SessionStart`** hook (`.claude/settings.json`) — runs on every
  session, no dependencies. On the session that first adds it, open `/hooks`
  once (or restart) so the config is loaded; automatic on every checkout after.
- an **install-time** step ([`postinstall` | `post-install-cmd` | `make setup`])
  that rides on the install a fresh checkout runs anyway — covers humans and CI.

If neither has run yet, activate it by hand — the one line both automate:

```bash
git config core.hooksPath bin/hooks
```

### Large files (git-lfs)

[Delete this section if the repo has no large binaries.]

This repo stores large binaries (images, media, datasets, model weights), so
install [git-lfs](https://git-lfs.com) — it keeps them out of git history:

```bash
[brew install git-lfs | apt-get install git-lfs] && git lfs install
```

The push guard doesn't use git-lfs. But if you ever chain `git lfs pre-push`
into `bin/hooks/pre-push`, guard that step so a machine without git-lfs warns
instead of blocking every push — put `command -v git-lfs || exit 0` ahead of it.
The hook's job is to never wedge a push.

## Epic branches

[Delete this section if epics aren't in use.]

An epic is a feature too big for one PR but incoherent in slices. It gets a
persistent-until-landed branch, `{{EPIC_PREFIX}}<slug>`, cut from `{{DEFAULT_BASE}}`.

```bash
git checkout -b {{EPIC_PREFIX}}<slug> {{DEFAULT_BASE}}   # once, at the start
bin/ship --base {{EPIC_PREFIX}}<slug> "feat: first slice"
bin/land --base {{EPIC_PREFIX}}<slug>                    # slice → epic
# …repeat…
bin/land                                                 # finally: epic → {{DEFAULT_BASE}}
```

**Pass `--base` on every slice.** Without it both scripts target `{{DEFAULT_BASE}}` and
half-finished work reaches it.

Merge `{{DEFAULT_BASE}}` into the epic regularly — an epic that drifts for weeks
lands as one enormous conflict.

## Promoting to production

[Stage-promotion topology only — delete otherwise.]

```bash
bin/promote            # open the release PR: {{STAGE_BRANCH}} → {{PROD_BRANCH}}
bin/promote --merge    # merge it once CI is green
```

A promotion is a batch: everything merged into `{{STAGE_BRANCH}}` since the last
release ships together, so a bad change blocks the ones behind it. Promote often.

## Versioning

`VERSION` is the single source of truth: **[M.R.V.f | semver]**. [Legend, or a link
to the ADR.]

[M.R.V.f only:] `bin/ship` stamps `V` with the PR number automatically. The number
doesn't exist before the PR opens, so ship predicts it — one past the newest issue
or PR, which share a number sequence — stamps it before the first push, then checks
the real number once the PR is open and amends only if the guess lost a race. Normal
case: CI runs once, on a commit that already carries the right version.

What ship must never do is bump in a follow-up `[skip ci]` commit. That leaves the
head SHA with *no checks at all*, and `bin/land` trusts `gh pr checks` — it would
read "no checks reported" and merge straight through, gating on nothing. Don't
reintroduce one.

Bump the rest by hand: `bin/version epic` when an epic lands, `bin/version major` for
a milestone, `bin/version fix` for a commit with no PR.

[Semver only:] `bin/ship` never bumps it — the number is a compatibility promise, so
`bin/version {major|minor|patch}` is your call before shipping.

## Health

`GET /health` → 200, `{"status":"ok","version":"…"}`. Liveness only: no database,
no auth. Check what's actually deployed with:

```bash
curl -fsS https://<host>/health
```

The version it reports comes from `VERSION` via [config path], so it names the PR
that shipped the running code.

## CI

Two tiers — **checks** on PRs, and a **container build** on merge — and they're
different sets:

- **PR checks** (lint/tests/verify): run on PRs into `[main, epic/*]`. `bin/land`
  waits for these; the push guard blocks a stray push that would re-run them.
  Slices run checks so an epic slice is tested before it lands. A `[stage]`
  promotion is a batch merge and runs **no** PR checks.
- **Container build** (the heavy deploy job on a push to the branch): only
  `[main, stage]`. It's not a `land` concern — it happens after merge — but it's
  why the guard refuses a *direct* push to those branches.

The checks set is load-bearing: it's compiled into `bin/land`'s `base_runs_checks`
and the push guard's `runs_checks` — keep all three in step. "No checks reported"
means opposite things either side of the line: on a base that runs checks it can
only mean CI failed to register, so land refuses; on one that doesn't, it's normal,
so land proceeds rather than hanging forever.

- PRs into `[main, epic/*]`: [checks run — land waits for green, and refuses if none report]
- PRs into `[stage]`: [no checks — land proceeds immediately]

`bin/land --no-checks <pr>` overrides the refusal, for when CI is genuinely and
knowingly absent on a base that normally runs it. Deliberate and visible, once —
if you're typing it every time, `base_runs_checks` is wrong, so fix that instead.
