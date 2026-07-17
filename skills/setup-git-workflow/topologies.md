# Topologies

Three shapes. All three use the same two scripts — the topology only decides `DEFAULT_BASE` and when a run passes `--base`.

## Trunk

```
main ──●────────●────────●──
        \      /  \     /
         feature    feature
```

`DEFAULT_BASE=main`. Every feature branches off `main` and lands back into it. `main` is always releasable; a merge is a release.

**Pick it when** CI is trustworthy and deploys follow `main`. It's the default — the other two are answers to problems this one doesn't have.

**Cost:** no staging rehearsal. Whatever lands is live.

## Stage-promotion

```
main  ──●──────────────────●──   (releases)
         \                /
stage ────●────●────●────●───    (persistent, always ahead)
           \  /  \  /
          feature  feature
```

`DEFAULT_BASE=stage`. Features land into `stage`, which is deployed to a staging environment and accumulates work. Promoting is a separate `stage → main` PR — that's `bin/promote`.

**Pick it when** a change needs to be seen running somewhere real before it reaches production.

**Cost:** the promotion PR is a batch — several features land as one release, and a bad one blocks the others behind it. `stage` also drifts from `main` between promotions, so promote often.

**The trap:** `stage` is persistent and never deleted. `bin/land --delete-branch` is right for a feature branch and wrong for `stage` — that's why `bin/promote` exists as its own script rather than a `--base main` land.

## Epic branches

Orthogonal to the other two — it layers onto either.

```
base  ────●────────────────────●──
           \                  /
epic/backup ●────●────●──────●     (one PR into base)
             \  /  \  /
            slice   slice
```

An epic collects several PRs' worth of work that shouldn't reach the base half-finished. Cut `epic/<slug>` from the base; ship each slice with `--base epic/<slug>`; land the epic into the base as one PR when it's whole.

**Pick it when** a feature is too big for one PR but incoherent in pieces.

**Cost:** the epic drifts from its base the whole time it's open. Merge the base into the epic regularly — the alternative is one enormous conflict at the end. Epic PRs usually carry no CI checks, which is the "no checks reported" path in `bin/land`.
