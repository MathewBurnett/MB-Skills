---
name: starmap
description: Render a wayfinder map as a pannable star-map — tickets as stars coloured by status, blocking as flowing edges, fog at the rim. Use when the user wants to see, view, visualise or "serve" a wayfinder map, asks what the frontier looks like, or types /starmap.
---

# Star-map

A read-only view of a **wayfinder map**: tickets as stars in a pannable field, status
as the star itself, blocking as directed edges, fog drifting at the rim.

Everything is **derived at generation time** from the tracker — status, edges, counts.
Nothing is written down, and the page is stamped with the moment it was read. It is a
snapshot, not a server: re-run it to refresh.

## Adapter

This renders the **GitHub issues** adapter — the shape Matt Pocock's `wayfinder` skill
uses when a repo tracks its map on an issue tracker:

- **map** — one issue (conventionally labelled `wayfinder:map`)
- **tickets** — that issue's **sub-issues**
- **blocking** — GitHub's **native issue dependencies** (`blocked_by`)
- **type** — a `wayfinder:<type>` label (`grilling` / `prototype` / `research` / `task`)

It does **not** read `.plan/` markdown maps. If the repo stores its map that way, say so
rather than guessing — the shapes are different and a wrong guess renders a wrong map.

## Run it

```bash
python3 ~/.claude/skills/starmap/starmap.py <map-issue> [--repo owner/name] [--out path.html]
```

`--repo` defaults to the current clone's remote; `--out` defaults to `/tmp/starmap-<n>.html`.
It prints the derived tally and every ticket's rank, status and type, then the path.

Open it afterwards — `xdg-open` on Linux, `open` on macOS, `start` on Windows. Run the
open in the background; it holds the terminal while the browser lives.

## How to read it

| Star | Meaning |
|---|---|
| dim blue-white | resolved |
| **bright gold, pulsing** | **frontier** — open, unblocked, unclaimed: takeable now |
| amber | claimed — someone is on it |
| small dim red | blocked — waiting on an open ticket |
| cold grey | out of scope |
| dashed red halo | undermined — resolved on a premise that later broke |

Edges run blocker → dependent. A **satisfied** edge glows and flows; an **unsatisfied** one
stays a faint dashed thread, so cleared paths are visible at a glance. Ring distance from
the centre is dependency depth — roots inward, deepest at the rim.

Drag to pan, scroll to zoom, click a star for the full ticket body, Esc to dismiss.

## Reporting it back

The canvas cannot be verified from a headless session — there is no browser to screenshot.
Confirm the **data** (the printed tally and ranks) and say plainly that the look is the
user's to judge. Do not claim it renders correctly.

State the frontier in prose too, by **name** rather than by number — a wall of `#119, #120`
is illegible where names read at a glance. The id rides inside the name as its link.

## Credit

The wayfinder method and its skills are Matt Pocock's
(https://github.com/mattpocock/skills). The star-map's visual language — status as the
whole star, type in the label, flowing satisfied edges, fog as rim nebulae, deterministic
seeded layout — follows the design record in rengwu/wayfinder-maps, reimplemented here
against the issue-tracker adapter.
