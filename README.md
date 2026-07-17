# MB-Skills

My agent skills for [Claude Code](https://claude.com/claude-code) — the ones that make shipping software run smoother.

Every repo needs the same unglamorous plumbing: a way to get a change reviewed, a way to merge it once CI agrees, a version the running app can report back. Most of it gets rebuilt from memory each time, slightly differently, and the details that matter get lost. These skills write it down once and scaffold it on demand, so the path from a change to production is the same one every time — and one an agent can follow as readily as you can.

## Install

Pick one — installing twice leaves two copies of a skill competing.

**`npx`** — copies the skill into the repo you're standing in, yours to edit. Works with Claude Code and any other Agent Skills harness:

```bash
npx skills add MathewBurnett/MB-Skills
```

Add `-g` to install into `~/.claude/skills/` for every project instead, `--skill=setup-git-workflow` to skip the picker, and `npx skills update setup-git-workflow` to pull a newer version.

**Claude Code plugin** — auto-updating, read-only, nothing to clone:

```
/plugin marketplace add MathewBurnett/MB-Skills
/plugin install mb-skills@mathewburnett
```

Either way, run `/setup-git-workflow` in the repo you want to scaffold.

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

## Writing more skills

To work on the skills rather than just use them, clone and link instead of installing. Each skill becomes a symlink into the clone, so `git pull` updates every skill at once and edits land straight in the repo:

```bash
git clone git@github.com:MathewBurnett/MB-Skills.git ~/linux-repos/MB-Skills
~/linux-repos/MB-Skills/scripts/link-skills.sh
```

Links into `~/.claude/skills/`; set `CLAUDE_SKILLS_DIR` to point somewhere else.

The house style follows Matt Pocock's [`writing-great-skills`](https://github.com/mattpocock): keep `SKILL.md` short and push reference behind pointers, keep each meaning in one place, prune lines the model already obeys by default, and prompt for the behaviour you want rather than against the one you don't.
