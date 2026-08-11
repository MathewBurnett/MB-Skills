# Bootstrap: Dockerized Laravel + React skeleton

Loaded only in Step 1, and only when no skeleton exists yet (`composer.json` absent). Produces a Laravel app with React wired in via Vite, Dockerized, tested, and documented — nothing business-specific.

## Detect: fresh or existing

`composer.json` present → skeleton already exists. Skip straight to verifying it still boots (`composer test`, `npm run build`) and report what's missing rather than re-running the steps below.

## Scaffold Laravel

```bash
composer create-project laravel/laravel <scratch-dir> --prefer-dist --no-interaction
```

Merge the scratch dir into the repo root (`rsync -a <scratch-dir>/ . --exclude vendor`) rather than creating in place — `composer create-project` refuses a non-empty target, and this repo already has docs/history in it. Then `composer install` locally so `artisan` works.

## Wire React via Vite

Laravel's installer already ships `vite.config.js` + `resources/js/app.js` + Tailwind. Add React on top:

- `package.json`: add `react`, `react-dom` (deps) and `@vitejs/plugin-react` (devDep). **Check the installed Vite major first** (`cat package.json | grep '"vite"'`) and pick the plugin-react major that declares that Vite version in its peerDependencies (`npm view @vitejs/plugin-react@latest peerDependencies`) — Vite ships new majors often enough that the plugin-react version pinned in any older copy of this doc can lag and produce an `ERESOLVE` on install. Don't reach for `--legacy-peer-deps` to paper over a real mismatch; bump the plugin version instead.
- `vite.config.js`: add `react()` to the plugins array, change the JS entry from `app.js` to `app.jsx`.
- `resources/js/app.jsx`: mounts a React root into `#admin-root`.
- `resources/js/admin/AdminShell.jsx`: placeholder component — this is what proves the pipeline works, not a real screen yet.
- `resources/views/admin.blade.php`: `@vite([...])` + `<div id="admin-root"></div>`.
- `routes/web.php`: `Route::get('/admin', fn () => view('admin'))`.
- Fix `resources/views/welcome.blade.php`'s `@vite()` call too — it still points at the old `app.js`.

Completion criterion: `npm run build` succeeds, and `php artisan serve` + `curl` on `/`, `/admin`, and `/up` all return 200.

## Database

Ask before writing `docker-compose.yml` — this is genuinely problem-specific, not a fixed preference:

> Database for this project: SQLite (no container, simplest — recommended for most), MySQL 8.4 (container, for anything needing a real RDBMS in dev), or PostgreSQL (container, same reasoning as MySQL when the project prefers Postgres)?

**SQLite** — no `db` service. `docker-compose.yml` has just `app`, with `storage/database.sqlite` on a named volume so data survives rebuilds. `DB_CONNECTION=sqlite` throughout, no `DB_HOST`/`DB_PORT`/credentials to wire.

**MySQL / PostgreSQL** — a `db` service with a healthcheck (`mysqladmin ping` / `pg_isready`), `app` depends on it with `condition: service_healthy`, and the entrypoint's migrate step waits on `php artisan db:show` succeeding (capped retry loop — see below, never an unbounded one).

## Docker

Multi-stage `Dockerfile`: a `node:22-alpine` stage runs `npm ci` (not `npm install` — the lockfile is the contract between what CI tested and what the image ships) and `npm run build`, then a `php:8.4-cli` stage does `composer install --no-dev`, copies the built `public/build` over from the node stage, and runs as `docker/entrypoint.sh`.

`docker/entrypoint.sh`:
- Copies `.env.example` → `.env` if missing.
- Generates `APP_KEY` on first boot if unset — **never hardcode a key in `docker-compose.yml`**; a committed key is shared across every clone and every encrypted cookie/session becomes forgeable across them.
- Waits for the database (skip if SQLite) with a **capped** retry loop — 30 attempts, then exit 1. An uncapped `until` loop hangs silently forever on a real outage instead of failing loudly.
- Runs `php artisan migrate --force`, then execs the CMD (`php artisan serve --host=0.0.0.0`).

`.dockerignore` mirrors `.gitignore`'s noise (`.git`, `.env`, `node_modules`, `vendor`, `public/build`) so the image build context stays small and the container gets a fresh `.env`.

Completion criterion: `docker compose config` validates. If the Docker daemon is reachable, `docker compose up --build` boots cleanly and `/up` returns 200 — actually run this; don't just validate the YAML if a daemon is available. If no daemon is reachable in this environment, say so explicitly rather than claiming the stack works — validate everything that doesn't need the daemon (build steps run locally, config validates) and tell the human to confirm `docker compose up` themselves.

## Tests, health check, README

Laravel ships `/up` (in `bootstrap/app.php`'s `health:` option) for free — don't reinvent it. Replace the default `tests/Feature/ExampleTest.php` with a `HealthCheckTest` asserting `/up` returns 200; delete `tests/Unit/ExampleTest.php` too (placeholder, not a real test). README documents both the `docker compose up --build` path and the host-only path (`composer install && npm install && composer setup`).

CI is **not** written here — see Step 4 / `ci.md`, which needs `VERSION` (from Step 3) to exist first if the deploy job is wanted.

## Close

Run `/code-review` on the diff before moving to Step 2. Fix what it finds — this is exactly where the Dockerfile's `npm install` vs `npm ci` drift, an uncapped retry loop, or a hardcoded `APP_KEY` get caught if the steps above were followed loosely.
