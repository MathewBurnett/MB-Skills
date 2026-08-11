# CI

Loaded in Step 4, after Step 3 (`setup-git-workflow`) so `VERSION` exists if the deploy job below is wanted. Writes `.github/workflows/ci.yml`.

## Detect: existing workflow

`.github/workflows/ci.yml` present → read it before touching it. Add the missing pieces below (Pint check, concurrency group) rather than replacing a workflow the human may have already customized.

## The `tests` job — always

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: shivammathur/setup-php@v2
        with:
          php-version: "8.4"
          extensions: mbstring, pdo_sqlite, zip
          coverage: none

      - name: Cache Composer dependencies
        uses: actions/cache@v4
        with:
          path: vendor
          key: composer-${{ hashFiles('composer.lock') }}

      - name: Install PHP dependencies
        run: composer install --no-interaction --prefer-dist --no-progress

      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm

      - name: Install JS dependencies
        run: npm ci

      - name: Build frontend assets
        run: npm run build

      - name: Prepare environment
        run: |
          cp .env.example .env
          php artisan key:generate

      - name: Check formatting
        run: ./vendor/bin/pint --test

      - name: Run test suite
        run: php artisan test
```

**Frontend tests:** add a `run: npm test` step (after the build step) only if `package.json` declares a `test` script. Bootstrap (Step 1) doesn't scaffold a JS test runner, so on a fresh project there's nothing to run yet — don't add a step that fails on `npm error missing script`. Add it later, by hand, once Vitest or similar is wired up.

The concurrency group cancels a superseded PR run but never a deploy already in flight — `cancel-in-progress` is keyed off `pull_request`, so a push to `main` always runs to completion.

Completion criterion: this job is the one gate every PR passes through — `bin/land` (from `setup-git-workflow`) trusts `gh pr checks` against it. Confirm it actually runs clean on a throwaway branch/PR, not just that the YAML is well-formed.

## The `build` job — ask first

Only add this if the project has (or will soon have) somewhere to deploy *to*. It builds and pushes a Docker image to GHCR, tagged from `VERSION`, and moves a `:live` tag — the convention a Watchtower-style host polls to pull and redeploy. Ask:

> Should CI also build and push a Docker image on merge to `main` (GHCR, tagged `v<VERSION>` + `:live` for a Watchtower-style pull-based deploy)? Say no if there's nowhere deploying from this repo yet — add it later, once there is.

If yes:

```yaml
  build:
    needs: tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Read the version from VERSION
        id: version
        run: echo "value=$(tr -d '[:space:]' < VERSION)" >> "$GITHUB_OUTPUT"

      - name: Work out the tags
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          # latest=false: there is exactly one tag meaning "what the box runs" (:live).
          # metadata-action's default `:latest` would leave two tags both claiming to
          # be current, inviting an operator to pin the wrong one.
          flavor: latest=false
          tags: |
            type=sha,prefix=sha-,format=short
            type=raw,value=v${{ steps.version.outputs.value }}
            type=raw,value=live

      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

`needs: tests` is the gate — a red suite means no image, `:live` never moves. `if:` restricts it to a push to `main`, so a PR only ever runs `tests`.

If this job is added, say so explicitly in the `## Shipping` CLAUDE.md section (Step 6) — "merging into main deploys" changes what a merge *means* and belongs next to the shipping instructions, not buried in a workflow file nobody reads before pushing.
