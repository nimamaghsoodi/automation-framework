# Nexus — Claude Code Context

Read this fully before touching any code. It records every architectural decision, invariant, and gotcha discovered during development. Violating any of the rules in the "Do not break" section will silently break production behaviour.

---

## What this project is

Nexus is a self-hosted automation framework (think n8n / Zapier). Users build flows visually — a directed graph of connector nodes (triggers → actions) — which are executed by a Celery DAG walker. Everything runs via `docker compose up --build`.

Default login: `admin@nexus.local` / `admin`

---

## Running the stack

```bash
make gen-env          # generate apps/api/.env with random SECRET_KEY + ENCRYPTION_KEY (run once)
docker compose up --build   # start all services
```

Services:
- `api` — FastAPI on :8000 (also runs `alembic upgrade head` on start)
- `worker` — Celery worker (executes flows)
- `beat` — Celery beat with redbeat scheduler (fires cron flows)
- `web` — Vite dev server on :5173
- `postgres` — PostgreSQL 16 on :5432
- `redis` — Redis 7 on :6379

API docs: `http://localhost:8000/api/docs`

---

## Repo layout

```
apps/api/app/
  api/routes/         flows.py, runs.py, connectors.py, credentials.py, schedules.py, auth.py, users.py, ws.py
  execution/          ExecutionBackend interface, CeleryExecutionBackend
  models/             Flow, Run, RunStep, Connector, CredentialInstance, User (SQLAlchemy ORM)
  services/           auth.py, connector_sync.py (startup seeding), credential_service.py
  worker/             tasks.py (Celery tasks), dag.py (DAG walker), connector_registry.py
  celery_app.py       Celery app instance (used by worker + beat + routes/schedules.py)
  main.py             FastAPI app, lifespan, CORS, route registration

apps/web/src/
  lib/api.ts          ← THE ONLY PLACE fetch() is called. All API methods + types live here.
  store/authStore.ts  Zustand persist store — token, user, _hasHydrated
  components/
    ProtectedRoute.tsx  Guards _hasHydrated before checking token (Zustand hydration guard)
    ConnectorPalette.tsx
    NodeConfigPanel.tsx
    AddCredentialModal.tsx
    NexusNode.tsx
    RunModal.tsx
  pages/              FlowsPage, FlowBuilderPage, RunsPage, ScriptsPage, SchedulesPage,
                      CredentialsPage, ConnectorsPage, UsersPage, LoginPage
  hooks/useRunStatus.ts  WebSocket hook for live run status

packages/connectors/nexus_connectors/
  code/, cron/, http_rest/, jira/, kubernetes/, postgres/, teams/, webhook/, zendesk/, aws/
  Each has connector.py + tests/

packages/sdk/nexus_sdk/
  Connector base class, manifest registry (all_manifests())
```

---

## Critical invariants — do not break these

### 1. All API calls go through `apps/web/src/lib/api.ts`

Never use raw `fetch()` in any React component or hook. Always use:
- `api.<resource>.<method>()` for typed calls
- `authFetch(path, init?)` (named export from `api.ts`) for raw-Response cases

The `request()` function in `api.ts` injects the Bearer token from Zustand's in-memory store, handles 401 → `clearAuth()` + `nexus:unauthorized` event, and throws on non-OK responses. Raw fetch bypasses auth and will get 401 on every protected endpoint.

### 2. Zustand hydration guard in ProtectedRoute

`authStore` uses Zustand v5 `persist`. On page load there is a gap between JS executing and localStorage being rehydrated. `ProtectedRoute` **must** return `null` while `!_hasHydrated`. The `_hasHydrated` flag is set by `onRehydrateStorage` in the store config. Removing this guard causes authenticated users to get bounced to `/login` on every hard refresh.

```typescript
// authStore.ts — do not change this pattern
onRehydrateStorage: () => (state) => { state?.setHasHydrated(true); }

// ProtectedRoute.tsx — do not remove the _hasHydrated check
if (!_hasHydrated) return null;
if (!token) return <Navigate to="/login" replace />;
```

### 3. Code connector uses stdin, not `-c`

`packages/connectors/nexus_connectors/code/connector.py` runs user Python via:
```python
proc = await asyncio.create_subprocess_exec(sys.executable, "-", stdin=PIPE, ...)
await proc.communicate(input=wrapper_bytes)
```

**Do not change this to `-c`**. The `-c` approach hits OS argument-length limits and raises `UnicodeEncodeError: surrogates not allowed` when HTTP response bodies contain surrogate characters. The stdin approach also uses `json.dumps(..., ensure_ascii=True, default=str)` throughout.

### 4. Connector credential validation

Every connector that requires a configured field (host, base_url, subdomain, server_url) must validate it at the start of `_client()` / `_dsn()` and raise `ConnectorError` with a clear message **before** attempting any network call. Do not fall back to `localhost` or empty string. Current connectors that do this: `postgres` (host), `jira` (base_url), `kubernetes` (server_url), `zendesk` (subdomain).

### 5. Demo flow seeding

`connector_sync.py` seeds 5 demo flows on API startup. To update a demo flow:
1. Add its current name to `_OLD_DEMO_NAMES` (so startup deletes the old version)
2. Update the spec in `_DEMO_FLOWS`

The seed function cascade-deletes RunStep → Run → Flow to avoid FK constraint failures.

### 6. Demo flows must use Docker-accessible public APIs

All demo flow HTTP nodes must use APIs that:
- Require no authentication
- Resolve from inside Docker (i.e., no Docker egress IP blocking)

**Known broken APIs (do not use in demo flows):**
- `api.coingecko.com` — blocks Docker/cloud IPs on the free tier
- `api.coincap.io` — DNS resolution fails in Docker

**Working alternatives confirmed in Docker:**
- `blockchain.info/ticker` — Bitcoin price
- `catfact.ninja/fact`
- `api.wheretheiss.at/v1/satellites/25544`
- `v2.jokeapi.dev`
- `api.spacexdata.com/v5/launches/next`

### 7. Flow graph_json shape

```json
{
  "nodes": [
    {
      "id": "string",
      "type": "trigger|action|condition|transform",
      "connector_key": "cron|webhook|http_rest|code|...",
      "config_json": {},
      "position": {"x": 0, "y": 0}
    }
  ],
  "edges": [{"id": "string", "source": "node-id", "target": "node-id"}],
  "cron_expression": "*/15 * * * *",   // only present when schedule is active
  "cron_trigger_payload": {},
  "is_script": false
}
```

A schedule is "enabled" iff `graph_json.cron_expression` is set AND `flow.status == "active"`. This is the source of truth — not a separate schedules table.

### 8. Runs API includes flow_name

`RunResponse` includes `flow_name` populated via `joinedload(Run.flow)`. The `Run` model has a `flow = relationship("Flow", lazy="select")` already. The `_serialize_run()` function reads `run.flow.name` and falls back to a truncated ID if the flow was deleted.

### 9. Schedules list endpoint

`GET /api/v1/schedules/` scans all flows for any node with `connector_key == "cron"`. It does NOT require a schedule to be active — it lists everything with a cron trigger node so the Schedules UI can show all schedulable flows, not just enabled ones.

---

## Key patterns

### Adding a new page

1. Create `apps/web/src/pages/NewPage.tsx`
2. Import it in `App.tsx`
3. Add a `{ to: "/new-path", label: "Label" }` entry to the `NAV` array in `App.tsx`
4. Add `<Route path="/new-path" element={<NewPage />} />` inside the protected routes block

### Adding a new API method

Add to `apps/web/src/lib/api.ts`:
```typescript
// In the api object
resource: {
  doThing: (id: string) => request<ReturnType>(`/resource/${id}/thing`, { method: "POST" }),
}

// Add the interface if needed
export interface ReturnType { ... }
```

### Adding a new connector

1. `packages/connectors/nexus_connectors/<name>/connector.py` — implement `Connector` base
2. `packages/connectors/nexus_connectors/<name>/__init__.py` — export class + manifest
3. Auto-registered on startup via `connector_registry.autodiscover()` + `sync_connectors()`
4. Copy `http_rest` or `webhook` as a template for simple connectors

### Adding a DB migration

```bash
make migration MSG="describe what changed"
# review the generated file in apps/api/migrations/versions/
make migrate
```

---

## Auth flow

- Standard login: `POST /api/v1/auth/login` → `{access_token, user}` → stored in Zustand
- OAuth2 (Google/GitHub): redirects to `/api/v1/auth/oauth/{provider}`, callback sets `?token=<jwt>` on the frontend URL, `LoginPage._applyToken()` picks it up
- `_applyToken` sets a placeholder user in Zustand first (so `api.auth.me()` can send the Authorization header), then fetches the real user and overwrites
- SAML: `SAML_ENABLED=true` + IdP config required

---

## Environment variables

Required:
```
SECRET_KEY          JWT signing key (32+ random chars)
ENCRYPTION_KEY      Fernet key for credential encryption
DATABASE_URL        asyncpg DSN (used by FastAPI + Celery)
DATABASE_URL_SYNC   psycopg2 DSN (used by Alembic)
REDIS_URL           Redis DSN
```

Optional (social login):
```
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET
OAUTH_REDIRECT_BASE   (default: http://localhost:8000)
FRONTEND_URL          (default: http://localhost:5173)
```

Optional (SAML):
```
SAML_ENABLED=true
SAML_IDP_ENTITY_ID
SAML_IDP_SSO_URL
SAML_IDP_CERT
```

Admin bootstrap (created on first startup):
```
ADMIN_EMAIL     (default: admin@nexus.local)
ADMIN_PASSWORD  (default: admin)
```

---

## What has been built and validated

- Flow builder: create, name, edit, delete flows; drag connector nodes from palette onto canvas; draw edges; configure nodes via right panel; save
- Execution: manual trigger, live WebSocket status updates, per-step input/output in Runs page
- Runs page: shows flow name (not just UUID), timestamp, status; detail panel with step-level output/errors
- Scripts page: create/edit Python scripts, schedule with cron, enable/disable schedules
- Schedules page: lists all flows+scripts with a cron trigger node; Enable/Pause toggle; inline cron editor with presets
- Credentials page: add/test/delete credentials per connector
- Connectors page: view installed connectors and their manifests
- Users page (admin only): create/edit/delete users, assign roles
- Auth: JWT login, Google OAuth2, GitHub OAuth2, SAML SSO

---

## Known issues / watch-outs

- `blockchain.info/ticker` occasionally returns 429 if polled too fast. The 15-minute cron is fine.
- The `beat` service must use `redbeat.RedBeatScheduler` (configured in `celery_app.py`) for dynamic cron entries registered via `PUT /api/v1/schedules/{flow_id}` to be picked up. A plain beat scheduler won't see entries added at runtime.
- React Flow (`@xyflow/react`) requires nodes to have stable IDs. Changing a node's ID after it's been saved will orphan the corresponding RunStep records (node_id FK).
- The `code` connector subprocess inherits no environment variables from the host — `os.environ` is empty inside user scripts. This is intentional for security.
