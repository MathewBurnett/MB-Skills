# MB-Skills

Agent skills for [Claude Code](https://claude.com/claude-code).

## Skills

### [`setup-git-workflow`](skills/setup-git-workflow/)

Scaffolds a repo's shipping path — the scripts, the versioning, and the branch topology that ties them together.

It generates:

- **`bin/ship`** — verify, branch, commit, push, open a PR. Never merges.
- **`bin/land`** — merge an open PR once CI is green, then sync the base.
- **`bin/promote`** — `stage → main` release PR (stage-promotion topology only).
- **`bin/version`** + `VERSION` — the version the running app reports.
- **`GET /health`** — 200 + `{"status":"ok","version":"…"}`.
- **`docs/agents/git-workflow.md`** — the topology, written down for humans and agents.

Three topologies, described in [topologies.md](skills/setup-git-workflow/topologies.md): **trunk** (`main → feature`), **stage-promotion** (a persistent staging line, promoted in batches), and **epic branches** (long features built from several PRs), which layer onto either.

The skill is prompt-driven: it reads the repo, proposes commands it can see the repo actually defines, confirms with you, then writes. It's user-invoked (`disable-model-invocation: true`), so it costs no context until you ask for it.

## Design notes

A few things these scripts get right that are easy to get wrong:

**ship never merges.** The ship/land split exists so review has somewhere to happen. Every generated variant preserves it.

**The version bump is amended, not appended.** A PR number only exists once the PR is open, so `ship` opens it, stamps `V`, and amends the change into the same commit. The obvious alternative — a follow-up `chore: version [skip ci]` commit — quietly breaks the safety gate: with `[skip ci]` the head SHA has *no check runs*, `gh pr checks` reports "no checks reported", and `land` reads that as permission to merge. CI would stop gating anything. Amending keeps one commit and one honest CI run on the final SHA.

**Force-push only onto a PR ship just opened.** A re-run pushes onto a branch someone may already have reviewed, and its version is already correct — so there's nothing to rewrite. `--force-with-lease` refuses if the remote moved.

**promote is its own script.** `land` passes `--delete-branch`, which is right for a feature branch and would delete a persistent `stage` line.

**/health is liveness, not readiness.** No database, no auth. A health check that touches the DB turns a transient blip into a restart loop, killing an app that was serving fine. If a root-level `/health` sits behind an SPA catch-all, it must be registered *before* it — otherwise a probe gets a cheerful 200 of HTML, and passes on a check that means nothing. Assert on the body.

## Install

Clone, then symlink the skills you want into a project (or into `~/.claude/skills/` for every project):

```bash
git clone git@github.com:MathewBurnett/MB-Skills.git ~/linux-repos/MB-Skills

# per-project
ln -s ~/linux-repos/MB-Skills/skills/setup-git-workflow <repo>/.claude/skills/setup-git-workflow

# or globally
ln -s ~/linux-repos/MB-Skills/skills/setup-git-workflow ~/.claude/skills/setup-git-workflow
```

Then run `/setup-git-workflow` in the repo you want to scaffold.

## Writing more skills

The house style follows Matt Pocock's [`writing-great-skills`](https://github.com/mattpocock): keep `SKILL.md` short and push reference behind pointers, keep each meaning in one place, prune lines the model already obeys by default, and prompt for the behaviour you want rather than against the one you don't.
