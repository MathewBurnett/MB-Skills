# Placeholders

Every `{{PLACEHOLDER}}` in the templates, and what fills it. Values come from the Explore step and the Section answers in `SKILL.md`. A fill is a command this repo really runs, or the block is deleted.

| Placeholder | Used in | Fill with |
| --- | --- | --- |
| `{{DEFAULT_BASE}}` | ship, land, check, pre-push, docs | Section A: `main` or `stage` |
| `{{PROTECTED_BRANCHES}}` | ship, pre-push, docs | Space-separated persistent branches |
| `{{CHECKED_BASES}}` | land, pre-push, docs | Section C, as a `case` pattern: `main\|epic/*` |
| `{{STAGE_BRANCH}}`, `{{PROD_BRANCH}}` | promote, version, docs | Stage-promotion branch names; for trunk, `{{PROD_BRANCH}}` is the base |
| `{{EPIC_PREFIX}}` | land, docs | Section B: default `epic/` |
| `{{EPIC_EXAMPLE}}` | ship, land, check | A sample branch: `epic/import` |
| `{{ADR_REF}}` | land, pre-push, version | Path of the versioning ADR, or `docs/agents/git-workflow.md` when the repo has no ADRs |
| `{{NO_CHECKS_NOTE}}` | land | One comment line on which bases legitimately report no checks here |
| `{{FORMATTER}}` | ship | Formatter name, for the comment: `Pint` |
| `{{SOURCE_DIR}}` | ship, check | Space-separated source paths: `app config database routes tests` |
| `{{SOURCE_EXT}}` | ship, check | Extension regex: `\.php$` |
| `{{LINT_COMMANDS}}` | ship, check | Format `$changed`, guarded so an empty list can't format the whole tree: `[ -z "$changed" ] \|\| ./vendor/bin/pint $changed` |
| `{{VERIFY_COMMANDS}}` | ship | Everything CI runs, joined with `&&`: `npm run build && npm test && php artisan test` |
| `{{CHECK_COMMANDS}}` | check | The tests, one per line, with `"$@"` on the scoped runner: `php artisan test "$@"` |
| `{{CHECK_FILTER_EXAMPLE}}` | check | A scoped-run argument: `--filter=SomeTest` |
| `{{VERSION_PREDICT_BLOCK}}`, `{{VERSION_VERIFY_BLOCK}}`, `{{GUARD_VERSION_BLOCK}}` | ship, pre-push | [version-bump.snippet](version-bump.snippet); delete for semver or no versioning |
| `{{SLOW_TESTS_BLOCK}}`, `{{SLOW_TESTS_PATHS}}`, `{{SLOW_TESTS_COMMAND}}` | ship | [slow-tests.snippet](slow-tests.snippet); delete without a slow tier. The paths are one regex of what the tier guards |
| `{{LFS_PRE_PUSH_BLOCK}}` | pre-push | [lfs-hooks.snippet](lfs-hooks.snippet); delete when the repo tracks no LFS files |
| `{{DEPLOY_MESSAGE_BLOCK}}` | land, promote | `echo` lines saying what this merge caused (deployed, built, or nothing); `$docs_only` and `$base` are in scope in land. Delete when a merge causes nothing |
| `{{DOCS_ONLY_CASE}}` | docs-only-paths | Section F, as a `case` pattern: `*.md\|docs/design/*\|graphify-out/*\|VERSION` |
| `{{RELEASE_TARGET}}` | version | What CI stamps from `VERSION`: `container image tag`, `git tag` |
| `{{MANIFEST_SYNC_NOTE}}` | version-semver | A step copying the version into `package.json` or similar; delete when nothing else carries it |
