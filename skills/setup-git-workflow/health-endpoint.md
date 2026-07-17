# Health endpoint

`GET /health` → **200** with a liveness body:

```json
{ "status": "ok", "version": "0.1.198.0" }
```

**Liveness, not readiness.** It calls no database, cache, or queue. The process answering *is* the check. This is deliberate: the endpoint is what a container healthcheck polls, and a check that touches the database turns a transient DB blip into a restart loop — killing an app that was fine and could have served cached traffic. Keep dependency checks out; add a separate `/health/ready` later if a load balancer needs one.

**Public and unauthenticated** — a probe has no session. Keep it out of auth middleware and off any rate limiter.

## Wiring the version

The `VERSION` file is the single source of truth. Read it into config **once at boot**, not per request, and let an env var override it for images that bake the version in at build time. Fall back to `dev` so a missing file degrades to a wrong-but-serving version rather than a 500 on the healthcheck.

## The catch-all trap

A root-level `/health` sits in the same namespace an SPA fallback claims. If the app serves a client-rendered shell from `/{any}`, **the health route must be registered before the catch-all** — routers match in registration order, so a late `/health` returns HTML to a probe expecting JSON. The probe then passes or fails on a 200 that means nothing.

Verify by asserting on the *body*, never just the status:

```bash
curl -fsS localhost:8000/health | grep -q '"status":"ok"'
```

## Laravel

`routes/web.php` — above the SPA catch-all:

```php
// Liveness probe: no DB, no session, no auth. Registered above the SPA
// catch-all below, which would otherwise serve the shell for /health.
Route::get('/health', fn () => response()->json([
    'status' => 'ok',
    'version' => config('app.version'),
]));

Route::get('/{path?}', fn () => view('app'))->where('path', '^(?!api).*$');
```

`config/app.php`:

```php
/*
| Application version. The VERSION file (bumped via bin/version, mirrored by a
| git tag) is the source of truth. Read here so it's resolved once at boot and
| cached with the rest of config. APP_VERSION overrides it for prebuilt images;
| falls back to "dev" when the file is absent.
*/
'version' => env('APP_VERSION', trim(@file_get_contents(base_path('VERSION'))) ?: 'dev'),
```

Note Laravel already ships a health route at `/up` (configured in `bootstrap/app.php` via `withRouting(health: '/up')`). It returns HTML and no version. Point `health:` at `null` if `/health` supersedes it, or leave both and document which one probes hit — two health endpoints that disagree is worse than either alone.

Keep `VERSION` out of `.dockerignore`, or the image falls back to `dev`.

## Express

```js
// Liveness probe: no DB, no auth. Mounted before the SPA fallback below.
const version =
  process.env.APP_VERSION ??
  fs.readFileSync(path.join(__dirname, 'VERSION'), 'utf8').trim();

app.get('/health', (_req, res) => res.json({ status: 'ok', version }));

app.get('*', (_req, res) => res.sendFile(indexHtml)); // must stay last
```

## FastAPI

```python
# Liveness probe: no DB, no auth. Declared before the SPA StaticFiles mount.
VERSION = os.getenv("APP_VERSION") or Path("VERSION").read_text().strip()

@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}

app.mount("/", StaticFiles(directory="dist", html=True))  # must stay last
```

## Test

Generate a test with the endpoint — an untested probe is one the SPA catch-all silently eats on the next refactor. Assert the status, the body, and that it works unauthenticated.

```php
public function test_health_returns_ok_and_version(): void
{
    $this->getJson('/health')
        ->assertOk()
        ->assertJson(['status' => 'ok'])
        ->assertJsonStructure(['status', 'version']);
}
```
