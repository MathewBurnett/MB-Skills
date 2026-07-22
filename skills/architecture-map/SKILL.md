---
name: architecture-map
description: Generate (or refresh) a new-developer architecture map — one self-contained HTML page: what the app is, its modules and patterns as diagrams, and how to run it. `--update` re-checks an existing map against the repo and refreshes only what drifted.
disable-model-invocation: true
---

# Architecture Map

A **first-day map**: one self-contained HTML page a developer reads on day one and comes away knowing what the app is, how it's shaped, which patterns they must follow, what will surprise them, and how to run it.

The map is *derived*, not authored from scratch — it reads the repo's own orientation docs and code, then renders the shape as Mermaid diagrams. It points back at the sources of truth (`CONTEXT.md`, ADRs, the README); it never replaces them.

Two branches:

- **Generate** (default) — build the map from the repo.
- **Update** (`--update`) — check an existing map against the repo and refresh only the sections whose sources drifted.

The bar: a map worth reading answers a newcomer's questions and surfaces the non-obvious. A file-tree restated in prose is worthless — the **surprises** (Q4) and the **seams** (Q6) are the highest-value content on the page. Chase them.

## The newcomer's questions

Every section earns its place by answering one question a new developer has on day one. This is the spine of the map — cover, in order, each question the project actually answers:

1. **What is this?** — one sentence naming the app and what it does, then the 4–6 load-bearing facts (the stack, the personas/actors, where logic lives, the one scoping/tenancy rule, where data lives, what the tests are). A top-level system flowchart.
2. **How is it shaped?** — the major modules/clusters as diagrams: an ER/data-model diagram for the domain, and a component/module flowchart for the code. Every cluster named in a diagram also appears in a table, so nothing is diagram-only.
3. **What patterns must I follow?** — the layering rule (what goes in which directory and why) and the shared building blocks a newcomer will reuse.
4. **What will surprise me?** — the non-obvious: nullable-where-you-wouldn't-expect, freeze/lock rules, "set this by hand in the seeder" gotchas. At least 3, each grounded in a real file or symbol. This section is the proof the map was written by reading the code, not the directory listing.
5. **How does a request flow, end to end?** — one worked vertical slice as a sequence diagram, from entrypoint through the layers to the store.
6. **What are the key seams?** — the deep modules that own a behaviour (the only-way-to-change-X services), each with what it owns and the ADR/why behind it.
7. **How do I run it, and where do I start?** — the real, verified run command, and an ordered first-day path (read the docs → run it → trace one slice → run the tests → ship).

A library has no personas, a CLI no SPA. Drop a question the project doesn't answer; never pad one with filler.

## Process

### 1. Derive the model

Read the repo before drawing anything. Prefer the project's own orientation docs as the sources of truth, and read code to fill gaps and verify:

- **Orientation docs** — `CONTEXT.md`, `docs/adr/`, `docs/agents/*`, `README`, `CLAUDE.md`/`AGENTS.md`. Where they exist they define the vocabulary and the "why"; the map cites them and must not contradict them.
- **The shape** — the domain models/entities and their relations; the route table / entrypoints; the directory layering (controllers/services/actions/models, or this stack's equivalent); the shared front-end or library building blocks.
- **The surprises** — read enough real code to name ≥3 things not visible from file names (a global query scope, a lifecycle seam, an anaemic-model rule, a "migrations run unattended so must be additive" constraint).
- **How it runs** — the real dev command from `package.json` / `Makefile` / `composer.json` / `README`. Confirm it's a task the repo actually defines; don't invent one.

Completion: you can name the app in one sentence, list its major clusters, state its layering rule, name ≥3 non-obvious conventions with the file/symbol each lives in, and give the verified run command. If you can't, keep reading.

### 2. Adopt the project's visual language

The map should look like it belongs to the project. Discover the established styles and reuse them; don't invent a palette a project already owns:

- Find design tokens: CSS custom properties (`:root{--…}`), a `tailwind.config`, theme/`*.css` files, a design-system doc, an existing HTML report.
- Map the discovered colours, fonts, and radii onto the template's variables.
- **Themes:** if the project defines both a light and a dark theme, wire up both (the template ships dual-theme and re-renders Mermaid on toggle); if it defines only one, honour that one and drop the other set; if none, keep the template's default palette.

Completion: the template's `--base`/`--surface`/`--accent`/`--ink` (both theme sets, if both are used) are filled from real project values — or deliberately left at the default because the project has no established style.

### 3. Draft the map

Copy [architecture-map.template.html](architecture-map.template.html) to the output path (default `docs/architecture-map.html`, or the project's docs home) and fill it:

- One `<section>` per newcomer's question the project answers, in order, with the sidebar nav matching.
- Diagrams as Mermaid (`erDiagram`, `flowchart`, `sequenceDiagram`) inside `.diagram` blocks; the surprises go in a `.callout`.
- Stamp the provenance comment at the top of `<body>` with `git rev-parse HEAD`, the ISO date, and the source paths you drew from — `--update` reads it.

Completion: every major cluster from step 1 appears in both a diagram and a table; the surprises callout has ≥3 grounded items; the run command is the verified one; no `{{PLACEHOLDER}}` or `FILL:` marker remains.

### 4. Verify it renders

- No `{{…}}` placeholder or `<!-- FILL` marker survives.
- Every Mermaid block parses — a stray `-->` inside a label or an unbalanced bracket breaks the whole diagram, so check each.
- Open it in a browser to confirm the diagrams draw and both themes read, if a browser is available; otherwise say you validated syntax only.

Then tell the user the path and one line on what the map covers.

## Updating (`--update`)

The map carries its own provenance, so a refresh is a diff, not a rewrite:

1. Read the provenance comment for the recorded SHA and source paths. If it's missing (a hand-made or pre-provenance map), treat this as a Generate that preserves any hand-written prose you can — and say so.
2. `git diff --stat <sha>..HEAD -- <sources>`, plus a scan for new files under the model/route/ADR dirs.
3. **Nothing relevant changed** → report the map is still valid, change nothing, leave the stamp.
4. **Something changed** → refresh only the affected sections (a new model → the ER diagram + table; a new ADR → the seams/why; a changed run script → the run section), advance the provenance SHA and date, and report what you changed and why.

Completion: either you reported "still valid" and touched nothing, or every source change since the recorded SHA is reflected in a section and the provenance stamp is advanced.
