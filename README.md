# Nexus — Automation Framework

A self-hosted, connector-based automation platform. Build flows visually from trigger → steps → actions using reusable connectors to any API, database, or cloud service. Similar in spirit to n8n / Zapier, but self-hosted and built code-first.

---

## Quick start

```bash
# 1. Generate secrets (run once)
make gen-env

# 2. Start everything
docker compose up --build

# 3. Open the UI
open http://localhost:5173
```

Default login: `admin@nexus.local` / `admin`

API docs: `http://localhost:8000/api/docs`

---

## What's built

| Area | Status |
|---|---|
| Flow builder UI (canvas, node config, edge drawing) | ✅ |
| Flow CRUD + graph persistence | ✅ |
| Execution engine (Celery DAG walker) | ✅ |
| Run history with per-step input/output | ✅ |
| Webhook trigger | ✅ |
| Cron / schedule trigger (via celery-redbeat) | ✅ |
| Schedules management page | ✅ |
| Credential vault (encrypted at rest, test-connection) | ✅ |
| Scripts page (Python scripts as scheduled flows) | ✅ |
| Connector SDK + manifest system | ✅ |
| JWT auth + OAuth2 (Google, GitHub) + SAML | ✅ |
| User management (admin/editor/viewer roles) | ✅ |
| 5 zero-config demo flows (public APIs, work out of the box) | ✅ |

### Connectors (P0)

| Connector | Auth | Notes |
|---|---|---|
| `webhook` | none | Inbound trigger |
| `http_rest` | API key / bearer / basic | Generic outbound HTTP |
| `code` | none | Run arbitrary Python inline |
| `cron` | none | Schedule trigger |
| `jira` | API token | Requires `base_url` + token |
| `postgres` | connection string | Requires host (no default) |
| `teams` | webhook URL | Incoming webhook |
| `aws` | access key / IAM | SQS + Lambda |
| `kubernetes` | kubeconfig / SA token | Requires `server_url` |
| `zendesk` | API token | Requires `subdomain` |

### Demo flows (zero-config, run immediately)

1. **Cat Fact of the Day** — cron daily 9 AM → catfact.ninja → Python transform
2. **Bitcoin Price Pulse** — cron every 15 min → blockchain.info/ticker → Python transform
3. **ISS Live Position Tracker** — cron every 5 min → wheretheiss.at → Python transform
4. **Webhook Joke & Cat Fact Combo** — webhook trigger → jokeapi.dev + catfact.ninja (parallel) → merge
5. **SpaceX Next Launch Brief** — cron Monday 8 AM → spacexdata.com → Python transform

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| Job execution | Celery + Redis, celery-redbeat for cron scheduling |
| Database | PostgreSQL 16 |
| Credential encryption | Fernet (AES-128-CBC) |
| Frontend | React 18, TypeScript, Vite |
| Flow canvas | `@xyflow/react` (React Flow) |
| Styling | Tailwind CSS with custom design tokens |
| Auth | JWT + optional OAuth2 (Google, GitHub) + SAML |
| Container | Docker Compose (dev), Helm chart (k8s) |

---

## Repo layout

```
AutomationFramework/
├── apps/
│   ├── api/                    FastAPI backend + Celery worker
│   │   ├── app/
│   │   │   ├── api/routes/     REST endpoints (flows, runs, connectors, credentials, schedules, auth, users)
│   │   │   ├── execution/      ExecutionBackend interface + CeleryExecutionBackend
│   │   │   ├── models/         SQLAlchemy ORM models
│   │   │   ├── services/       auth, connector_sync (startup seeding), credential_service
│   │   │   ├── worker/         Celery tasks + DAG walker + connector registry
│   │   │   ├── celery_app.py
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   └── main.py
│   │   └── migrations/         Alembic migration scripts
│   └── web/                    React frontend
│       └── src/
│           ├── components/     ConnectorPalette, NodeConfigPanel, AddCredentialModal, ProtectedRoute, NexusNode, RunModal
│           ├── hooks/          useRunStatus (WebSocket live run status)
│           ├── lib/
│           │   ├── api.ts      Single authenticated API client — ALL fetch calls go through here
│           │   └── utils.ts    cn() helper
│           ├── pages/          FlowsPage, FlowBuilderPage, RunsPage, ScriptsPage, SchedulesPage, CredentialsPage, ConnectorsPage, UsersPage, LoginPage
│           ├── store/          authStore (Zustand + persist), flowBuilderStore
│           └── App.tsx         Router + sidebar nav
├── packages/
│   ├── connectors/             Connector implementations
│   │   └── nexus_connectors/   One subdirectory per connector (connector.py + tests/)
│   └── sdk/                    Connector base interface + manifest registry
├── infra/helm/                 Helm chart for k8s deployment
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Development

### Environment variables

Copy `.env.example` to `apps/api/.env` and fill in:

```bash
SECRET_KEY=<32 random chars>   # JWT signing
ENCRYPTION_KEY=<Fernet key>    # Credential encryption

# Optional — OAuth2 social login
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Optional — SAML SSO
SAML_ENABLED=false
```

Or run `make gen-env` to auto-generate `apps/api/.env` with random keys.

### Make targets

```bash
make up               # docker compose up
make down             # docker compose down
make logs             # follow all logs
make migrate          # alembic upgrade head
make migration MSG="add foo"   # generate a new migration
make install-backend  # pip install sdk + connectors + api in editable mode
make install-frontend # npm install in apps/web
make test             # pytest packages/connectors
make lint             # ruff check
make gen-env          # generate apps/api/.env with random secrets
```

### Running services individually (without Docker)

```bash
# Terminal 1 — API
make api          # uvicorn on :8000

# Terminal 2 — Celery worker (executes flows)
make worker

# Terminal 3 — Celery beat (fires cron schedules)
cd apps/api && celery -A app.celery_app beat --scheduler redbeat.RedBeatScheduler --loglevel=info

# Terminal 4 — Web
make web          # vite on :5173
```

Requires local Postgres and Redis. Update `apps/api/.env` connection strings accordingly.

### Adding a new connector

1. Create `packages/connectors/nexus_connectors/<name>/connector.py` — implement the `Connector` base class from `nexus_sdk`.
2. Create `packages/connectors/nexus_connectors/<name>/__init__.py` — export the class and the manifest dict.
3. Add tests under `packages/connectors/nexus_connectors/<name>/tests/`.
4. The connector auto-registers on API startup via `connector_registry.autodiscover()` + `sync_connectors()`.

Use an existing simple connector (e.g. `http_rest` or `webhook`) as the template.

---

## Architecture notes

### API authentication

All API calls from the frontend go through `apps/web/src/lib/api.ts`. The `request()` function injects the Bearer token from Zustand's in-memory store. **Never use raw `fetch()` in components** — always use `api.*` methods or the `authFetch()` named export for cases that need the raw `Response` object.

### Zustand auth store

`authStore` uses Zustand v5 `persist` middleware. There is a hydration race on first load: `ProtectedRoute` returns `null` until `_hasHydrated` is true (set by `onRehydrateStorage` callback). Do not remove this guard — removing it causes false redirects to `/login` for already-authenticated users.

### Credential encryption

Credentials are encrypted with Fernet using `ENCRYPTION_KEY`. The raw secret is decrypted only inside the Celery worker for the duration of a step execution. The API never returns decrypted credential payloads to the frontend.

### Flow graph shape

A flow's `graph_json` is a plain dict stored as JSONB:
```json
{
  "nodes": [{ "id": "...", "type": "trigger|action|...", "connector_key": "...", "config_json": {}, "position": {"x": 0, "y": 0} }],
  "edges": [{ "id": "...", "source": "node-id", "target": "node-id" }],
  "cron_expression": "*/15 * * * *",   // present only when a schedule is active
  "cron_trigger_payload": {},
  "is_script": false                   // true for flows created from the Scripts page
}
```

### Cron scheduling

`PUT /api/v1/schedules/{flow_id}` registers the flow with celery-redbeat and stores `cron_expression` in `graph_json`. `DELETE /api/v1/schedules/{flow_id}` removes it from redbeat and clears the key. A schedule is considered *enabled* when `graph_json.cron_expression` is set AND `flow.status == "active"`.

### Code connector

The `code` connector runs user Python in a subprocess via `python -` (stdin), not `-c`, to avoid OS argument-length limits and Unicode surrogate issues from HTTP response bodies. Input data is round-tripped through `json.dumps(..., ensure_ascii=True, default=str)` before embedding. Do not change this to `-c`.

### Demo flow seeding

`seed_demo_flows()` runs at API startup. It deletes flows whose names appear in `_OLD_DEMO_NAMES`, then inserts any missing demo flows by name. To update a demo flow: add its current name to `_OLD_DEMO_NAMES` and update the spec in `_DEMO_FLOWS`.

### Demo flow API choices

All demo flows use public, auth-free APIs that resolve inside Docker:
- `catfact.ninja` — cat facts
- `blockchain.info/ticker` — Bitcoin price (not CoinGecko, not CoinCap — both fail in Docker)
- `api.wheretheiss.at/v1/satellites/25544` — ISS position
- `v2.jokeapi.dev` — jokes
- `api.spacexdata.com/v5/launches/next` — SpaceX launches

Do not replace these with APIs that require keys or have Docker IP restrictions (CoinGecko free tier blocks Docker egress IPs).

### Connector credential validation

Connectors that require a configured credential field (host, base_url, subdomain, server_url) validate it at the top of their `_client()` / `_dsn()` method and raise `ConnectorError` with a clear human-readable message before attempting any network call. Do not silently fall back to defaults like `localhost`.

---

## Deployment (k8s)

A Helm chart is in `infra/helm/`. Set the following values in `values.yaml` or via `--set`:

```
image.tag=<version>
env.SECRET_KEY=<prod secret>
env.ENCRYPTION_KEY=<prod fernet key>
env.DATABASE_URL=<prod postgres DSN>
env.REDIS_URL=<prod redis DSN>
```

---

## Roadmap

**Next (P1 connectors):**
- InterSystems IRIS (REST adapter)
- GitLab / GitHub
- Azure AD / Microsoft Graph
- Google Workspace (Gmail, Drive, Calendar)
- PagerDuty / Opsgenie

**Engine improvements:**
- OpenTelemetry tracing on flow execution
- Per-step replay ("retry from step N")
- Advanced node mode (expression editor with autocomplete over upstream outputs)
- Multi-tenant / org-level RBAC
