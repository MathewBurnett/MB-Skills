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

### [`architecture-map`](skills/architecture-map/)

Generates an architectural map of the repository, useful for understanding dependencies and components for new features or refactors.

### [setup-git-workflow](skills/setup-git-workflow/)

Scaffolds the necessary Git workflow plumbing in a repository (e.g., PR review structure, CI integration points) to ensure consistent development practices from feature branch to merge.

### [starmap](skills/starmap/)

Render a wayfinder map as a pannable star-map — tickets as stars coloured by status, blocking as flowing edges, fog at the rim. Use when the user wants to see, view, visualise or "serve" a wayfinder map, asks what the frontier looks like, or types /starmap.

## Writing more skills

To work on the skills rather than just use them, clone and link instead of installing. Each skill becomes a symlink into the clone, so `git pull` updates every skill at once and edits land straight in the repo:

```bash
git clone git@github.com:MathewBurnett/MB-Skills.git ~/linux-repos/MB-Skills
~/linux-repos/MB-Skills/scripts/link-skills.sh
```

Links into `~/.claude/skills/`; set `CLAUDE_SKILLS_DIR` to point somewhere else.

The house style follows Matt Pocock's [`writing-great-skills`](https://github.com/mattpocock): keep `SKILL.md` short and push reference behind pointers, keep each meaning in one place, prune lines the model already obeys by default, and prompt for the behaviour you want rather than against the one you don't.
