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

`ship` stops at the PR on purpose — review happens there. `land` is the separate,
deliberate merge. Branch names are derived from the title: `feat: add export` →
`feat/add-export`.

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

[M.R.V.f only:] `bin/ship` stamps `V` with the PR number automatically — the number
only exists once the PR is open, so ship bumps it *after* opening and amends it into
the same commit. That keeps CI running once, on the final SHA, which matters:
`bin/land` trusts `gh pr checks`, and a `[skip ci]` bump commit would leave the head
SHA with no checks for land to read — merging straight through. Don't reintroduce one.

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

[Which branches run checks, from the setup answer. This is load-bearing: `bin/land`
treats "no checks reported" as proceed, so a base branch with no configured checks
merges without waiting. Name the branches that do and don't have them.]

- PRs into `[main]`: [checks run — land waits for green]
- PRs into `[stage | epic/*]`: [no checks — land proceeds immediately]
