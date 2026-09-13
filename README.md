# PROJECT: Nexus — Connector-Based Automation Framework

## 0. How to use this file
This is the root context document for the project. Read it fully before writing any
code. It defines scope, architecture, data model, UI/UX requirements, connector
catalog, and a phased build plan. Treat Section 8 (Build Plan) as the literal order
of operations — do not jump ahead to connectors or UI polish before the core engine
in Phase 1 is working and tested.

When in doubt: favor a small number of **fully working, tested** things over a large
number of stubbed things. A framework with 5 real connectors and a working flow
engine is a successful v1. A framework with 40 fake connectors is not.

---

## 1. Origin & Context

This framework generalizes patterns observed in a real multi-carrier rail-ticketing
platform's system landscape (source: `Infrastructure_Architecture_Analysis.pdf`,
supplied separately, not part of the codebase). That platform used a central
integration hub ("eCore": S3 + API Gateway + Lambda + SQS) as a hub-and-spoke
message broker between a storefront and ~25 backend domains (commerce, payments,
carrier reservation systems via an InterSystems IRIS-based middleware layer,
identity, CRM/support, reporting, DevOps).

Nexus is NOT that platform. It is a **standalone, reusable automation framework**
that any engineering or CS team can point at their own stack: define connectors to
the systems you use, then compose them into automation flows (triggers → steps →
actions) via a visual builder — similar in spirit to n8n / Zapier / Workato, but
self-hosted, source-available, and built connector-first around the specific
enterprise/SaaS/cloud/rail-domain systems this team actually touches.

## 2. Goals for v1

1. A working **flow execution engine**: triggers (webhook, schedule, manual, event)
   → a directed graph of steps (connector actions, conditionals, transforms) →
   outputs, with retries, logging, and per-run history.
2. A **connector SDK**: a clear, documented pattern (interface + manifest schema)
   so that adding a new integration is a bounded, mechanical task — auth config,
   list of actions/triggers, input/output schemas, test harness.
3. **5–8 reference connectors built fully** (see Section 6, "P0") proving the SDK
   across different auth styles (API key, OAuth2, OAuth2 + refresh, basic auth,
   cloud SDK/IAM-based, webhook-only).
4. A **visual flow builder UI**: elegant, low-friction, node/canvas based, usable
   by both software engineers (writing custom scripts/expressions inside nodes)
   and CS/ops agents (dragging prebuilt connector actions together with no code).
5. A **credential vault**: encrypted at rest, scoped per-connector-instance, never
   exposed to the frontend after creation.
6. **Execution observability**: per-run timeline, per-step input/output payloads
   (redacted for secrets), error surfacing, manual retry/replay of a failed run.

## 3. Non-Goals for v1 (explicitly deferred)

- Multi-tenant SaaS billing / org-level RBAC beyond basic user roles (admin/editor/viewer).
- Building all 40+ connectors listed in Section 6 — only P0 ships fully in v1.
- A marketplace / connector plugin store with remote install.
- Horizontal, multi-node distributed execution (single-node with a job queue is fine
  for v1; design the execution interface so this is swappable later — see Section 5).
- Natural-language "describe a flow and AI builds it" — worth doing later, not v1.

---

## 4. Tech Stack

Chosen to match this team's existing stack (Python/FastAPI, Kubernetes, Terraform)
so the framework is deployable the same way everything else here is deployed.

| Layer | Choice | Why |
|---|---|---|
| Backend API | Python 3.12, FastAPI | Matches existing skillset; async-friendly for I/O-heavy connector calls |
| Flow/job execution | Custom lightweight DAG executor on top of **Celery + Redis** — **decided**, no Temporal in v1 | Fastest to stand up and matches this team's existing ops experience. Design the executor behind a clean interface (`ExecutionBackend`) so a future migration to Temporal, if long-lived human-in-the-loop steps (like the source architecture's manual-fulfillment fallback) later demand durable execution, is a backend swap, not a rewrite |
| DB | PostgreSQL | Flow definitions, credentials (encrypted), run history, connector manifests |
| Secrets/credential encryption | Postgres + application-level envelope encryption (Fernet/AES-GCM) via a KMS-backed master key (cloud KMS in prod, local key in dev) | Avoids standing up Vault for v1; interface should allow swapping in Vault/cloud Secrets Manager later |
| Frontend | React + TypeScript, Vite | Standard, fast dev loop |
| Flow canvas | **React Flow** (`@xyflow/react`) | Purpose-built for node/edge editors, handles zoom/pan/minimap out of the box |
| UI styling | Tailwind CSS + a small custom design system (see Section 7) | Full control over "elegant" look, no generic Bootstrap feel |
| Auth (app users) | JWT session + optional OIDC/SSO (Azure AD / Okta) since the source org already standardizes on Onelogin + Azure AD | |
| Containerization | Docker, Helm chart for k8s deploy | Matches existing RKE/Rancher/EKS/AKS/OKE operational experience |
| Observability | OpenTelemetry traces on flow execution + Prometheus metrics (runs/sec, failure rate, connector latency) | Matches existing observability stack experience |

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + React Flow)                                  │
│  - Flow Builder canvas   - Connector marketplace (local)        │
│  - Credential vault UI   - Execution/run log viewer              │
└───────────────────────────┬───────────────────────────────────┘
                             │ REST + WebSocket (live run status)
┌───────────────────────────┴───────────────────────────────────┐
│  API Service (FastAPI)                                          │
│  - Flow CRUD, validation, versioning                            │
│  - Credential CRUD (encrypt on write, never return raw secret)  │
│  - Trigger registry (webhook receiver, schedule registrar)      │
│  - Run query API (list/filter runs, step-level payloads)        │
└───────────────────────────┬───────────────────────────────────┘
                             │ enqueue job
┌───────────────────────────┴───────────────────────────────────┐
│  Execution Engine (Celery workers, or Temporal workflow)        │
│  - Loads flow graph, walks nodes in dependency order            │
│  - Resolves each node to a Connector Action via the SDK         │
│  - Handles retries/backoff, conditionals, error branches        │
│  - Writes step results to DB, streams status over WS/pubsub     │
└───────────────────────────┬───────────────────────────────────┘
                             │ implements
┌───────────────────────────┴───────────────────────────────────┐
│  Connector SDK  (packages/connectors/<name>/)                   │
│  - manifest.yaml  (auth type, actions, triggers, schemas)       │
│  - client.py      (thin wrapper over the vendor SDK/REST API)   │
│  - actions.py     (one function per action, typed in/out)       │
│  - triggers.py    (webhook parser / polling logic)              │
│  - tests/         (recorded-cassette or mocked integration test)│
└───────────────────────────────────────────────────────────────┘
```

Key design decision: **connectors are Python packages that implement a shared
`Connector` interface, discovered via a manifest**, not config-only. Config-only
(pure JSON/YAML describing REST calls) is tempting but breaks down fast for
anything with OAuth refresh, pagination quirks, or SDK-based auth (AWS/GCP/Azure,
IRIS). Use manifest+code, with the manifest driving what the UI renders (auth form
fields, action list, input schema) and the code doing the actual work.

## 6. Connector Catalog

### Tier P0 — build fully in v1, prove the SDK across auth styles
| Connector | Auth style | Why it's P0 |
|---|---|---|
| Webhook (generic inbound trigger) | none | Needed for almost every flow's trigger |
| HTTP / REST (generic outbound) | API key / bearer / basic | Escape hatch for anything without a dedicated connector yet |
| Slack **or** Microsoft Teams | OAuth2 | Notification pattern, proves OAuth2 flow — build MS Teams first since it's explicitly required |
| Zendesk | API token | CS-agent-facing flows (ticket triage, auto-reply) — explicitly required |
| Jira | OAuth2 / API token | Engineering workflow trigger/action — explicitly required |
| AWS (SQS + Lambda invoke, as a first slice) | IAM role / access key | Proves cloud-SDK-based auth, mirrors the source "eCore" pattern |
| Kubernetes (apply manifest / get pod status on a target cluster) | kubeconfig / service account token | Matches this team's core expertise, high daily value |
| PostgreSQL/MySQL (generic DB query/insert) | connection string | Very common "sink" for flows |

### Tier P1 — next, after P0 is stable (build 2–4 per sprint using the same SDK pattern)
Explicitly required by you, plus direct components from the source architecture:

- **InterSystems IRIS** (middleware — REST/JDBC or Native API bridge; treat as a
  "custom integration engine" connector since IRIS talks to Trenitalia/NMBS/LinkOn-
  style carrier systems in the source diagram — build this as a generic
  request/response adapter with configurable endpoint mapping, since IRIS
  deployments are usually bespoke per org)
- **ClickUp** (API token)
- **GitLab** (API token — matches source architecture's CI/CD system)
- **GitHub** (OAuth2/App token)
- **Microsoft Azure** (Resource Manager + AD — mirrors source's Azure AD usage)
- **Google Cloud Platform** (service account)
- **Google Workspace** (Gmail, Drive, Calendar, Analytics/GTM — mirrors source)
- **Adyen** (payments — mirrors source)
- **Adobe Experience Manager** (content publish/replicate — mirrors source)
- **Adobe Campaign** / **Mandrill** / **SendGrid** (transactional + bulk email — mirrors source's dual-provider pattern)
- **CommerceTools** (commerce/orders — mirrors source)
- **Cognito** (user pool admin actions — mirrns source)
- **Okta / Onelogin / Azure AD SSO** (identity — mirrors source)
- **PagerDuty** / **Opsgenie** (incident automation)
- **Datadog** / **Grafana** (observability hooks — matches team's daily tooling)
- **Terraform Cloud/Enterprise** (trigger runs — matches IaC background)

### Tier P2 — backlog, add opportunistically
Salesforce, HubSpot, ServiceNow, Notion, Confluence, Stripe, Twilio, DynamoDB,
S3 (generic object ops beyond the AWS P0 slice), Power BI (dataset refresh),
Snowflake, Exact Online, Smartling, HotJar/GA4 export, Docker Hub, ArgoCD, Harbor,
WSO2 (matches team's existing identity tooling experience), generic SOAP/XML,
generic GraphQL.

> Rule of thumb when adding a new connector: if it needs OAuth2, copy the Teams or
> Jira connector as a template. If it's a cloud provider SDK, copy the AWS or k8s
> connector. If it's a simple API-key REST API, copy Zendesk or ClickUp. This
> should make each new P1/P2 connector a 0.5–1.5 day task once the pattern is proven.

## 7. UI/UX Requirements

Audience is dual: **software engineers** (want keyboard shortcuts, raw JSON/expression
editing, git-diffable flow exports) and **CS/ops agents** (want drag-and-drop,
plain-language node labels, no code visible by default).

Design direction:
- Clean, dark-mode-first, low-chrome canvas (inspired by the clarity of Linear/
  Temporal UI/n8n — not a generic Bootstrap admin template). Generous whitespace,
  a restrained accent color, monospace only where code/expressions actually appear.
- **Flow canvas**: nodes are cards with a connector icon, short label, and a status
  ring (idle/running/success/error) once a run is live. Edges show data flow, not
  just control flow — hovering an edge previews the payload shape passing through it.
- **Progressive disclosure**: every node opens a right-side panel with two modes —
  "Simple" (dropdown fields matching the manifest's input schema) and "Advanced"
  (raw JSON + expression editor with autocomplete over previous nodes' outputs).
  Default to Simple; CS agents never need to see Advanced.
- **Connector marketplace panel**: searchable/filterable grid of installed
  connectors (icon, name, category, auth status: connected/not connected).
- **Credential vault page**: list of stored credentials by connector, masked
  values, "test connection" button, last-used timestamp, revoke button.
- **Run history view**: timeline per flow, expandable per-step with input/output
  (secrets redacted), duration, retry count, a one-click "replay from this step."
- Use `frontend-design` skill guidance (design tokens, spacing, typography) when
  scaffolding — don't default to unstyled shadcn boilerplate.

## 8. Data Model (initial)

```
User(id, email, role[admin|editor|viewer], sso_subject)
Connector(id, key, name, category, manifest_version, icon_url)
CredentialInstance(id, connector_id, name, owner_id, encrypted_payload, status, last_tested_at)
Flow(id, name, description, graph_json, version, status[draft|active|paused], created_by)
FlowNode(id, flow_id, type[trigger|action|condition|transform], connector_id?, config_json, position)
FlowEdge(id, flow_id, source_node_id, target_node_id, condition_expr?)
Run(id, flow_id, flow_version, trigger_source, status, started_at, finished_at)
RunStep(id, run_id, node_id, status, input_json, output_json, error, duration_ms, attempt)
```

## 9. Security Requirements (v1 baseline)

- All credentials encrypted at rest; decrypted only inside the worker process for
  the duration of a step execution, never logged, never sent to the frontend after
  initial save.
- Webhook trigger endpoints require a per-flow signing secret; verify HMAC before
  enqueueing.
- Outbound connector calls run with per-connector least-privilege scopes (document
  the minimum required OAuth scopes / IAM policy per P0 connector in its manifest).
- Redact known secret-shaped fields (tokens, passwords, keys) from run logs by
  default, with an explicit opt-in to show for debugging in non-prod.

---

## Build Plan (do this in order)

### Phase 0 — Scaffold
- Monorepo: `/apps/api`, `/apps/web`, `/packages/connectors`, `/packages/sdk`, `/infra`.
- FastAPI skeleton with health check; Postgres via SQLAlchemy + Alembic migrations;
  Docker Compose for local dev (api, celery worker, redis, postgres, web).
- Execution backend: Celery + Redis, implemented behind an `ExecutionBackend`
  interface (submit_run, get_status, cancel) so it stays swappable later.
- Define the `Connector` SDK interface and `manifest.yaml` schema (this is the
  most important file in the repo — get it reviewed/stable before building
  connectors against it).

### Phase 1 — Core Engine
- Flow CRUD API + graph validation (no cycles, all nodes reachable from a trigger).
- Execution engine: given a flow + trigger payload, walk the DAG, call connector
  actions, persist RunStep records, handle retries/timeouts.
- Build the Webhook and HTTP/REST generic connectors first — they let you build
  and test the engine end-to-end without needing OAuth from a third party yet.
- CLI or minimal API-only flow creation (no UI yet) to prove the engine works.

### Phase 2 — Flow Builder UI (MVP)
- React Flow canvas: add/connect/delete nodes, save/load a flow's `graph_json`.
- Node config panel in "Simple" mode only (Advanced mode can follow in Phase 3).
- Manual "Run now" with a trigger payload form, live status via WebSocket.
- Run history list + step detail view.

### Phase 3 — P0 Connectors + Credential Vault UI
- Build remaining P0 connectors (Teams or Slack, Zendesk, Jira, AWS slice, k8s,
  Postgres). Each gets: manifest, client, actions, tests, and a marketplace card.
- Credential vault CRUD UI with "test connection."
- Advanced node mode (expression editor with autocomplete).

### Phase 4 — Hardening & First P1 Wave
- OTel tracing + Prometheus metrics on the execution engine.
- Helm chart + CI pipeline (GitLab, matching source org's tooling) for deploy.
- Pick 3–4 P1 connectors most useful to your actual day-to-day (likely: IRIS,
  ClickUp, GitLab, Azure) and build them.

---

## Definition of Done for v1
- [ ] A flow can be built entirely through the UI by a non-engineer, using at
      least 3 different P0 connectors, and executed successfully end-to-end.
- [ ] A failed run can be inspected (per-step payloads visible, secrets redacted)
      and replayed from the failing step.
- [ ] Adding a 9th connector (first P1 pick) takes a single engineer under 2 days
      using only the SDK docs and an existing connector as a template — this is
      the real test of whether the SDK abstraction is right.
- [ ] Whole stack runs via `docker compose up` locally and deploys via the Helm
      chart to a k8s cluster.
