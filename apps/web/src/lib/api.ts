import { useAuthStore } from "../store/authStore";

const BASE = "/api/v1";

/** Authenticated fetch — use this instead of raw fetch() for all API calls. */
export async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = useAuthStore.getState().token;
  const res = await fetch(path.startsWith("/api") ? path : `${BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    useAuthStore.getState().clearAuth();
    window.dispatchEvent(new CustomEvent("nexus:unauthorized"));
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Read from in-memory Zustand store — always up-to-date, no localStorage race
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers ?? {}) as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    useAuthStore.getState().clearAuth();
    // Use React Router navigation to avoid a full-page reload that would
    // clear Zustand's in-memory store before rehydration completes
    window.dispatchEvent(new CustomEvent("nexus:unauthorized"));
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; user: AuthUser }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<AuthUser>("/auth/me"),
  },
  users: {
    list: () => request<UserRecord[]>("/users/"),
    create: (body: { email: string; password: string; role: string }) =>
      request<UserRecord>("/users/", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: { role?: string; is_active?: boolean; password?: string }) =>
      request<UserRecord>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/users/${id}`, { method: "DELETE" }),
  },
  flows: {
    list: () => request<Flow[]>("/flows/"),
    get: (id: string) => request<Flow>(`/flows/${id}`),
    create: (body: FlowCreateRequest) =>
      request<Flow>("/flows/", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: Partial<FlowCreateRequest>) =>
      request<Flow>(`/flows/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/flows/${id}`, { method: "DELETE" }),
  },
  runs: {
    list: (flowId?: string) => request<Run[]>(`/runs/${flowId ? `?flow_id=${flowId}` : ""}`),
    get: (id: string) => request<Run>(`/runs/${id}`),
    trigger: (flowId: string, payload?: Record<string, unknown>) =>
      request<Run>("/runs/", {
        method: "POST",
        body: JSON.stringify({ flow_id: flowId, trigger_payload: payload ?? {} }),
      }),
    cancel: (id: string) => request<void>(`/runs/${id}/cancel`, { method: "POST" }),
  },
  connectors: {
    list: () => request<Connector[]>("/connectors/"),
    get: (key: string) => request<Connector>(`/connectors/${key}`),
    manifest: (key: string) => request<ConnectorManifest>(`/connectors/${key}/manifest`),
    allManifests: () => request<Record<string, ConnectorManifest>>("/connectors/manifests/all"),
  },
  credentials: {
    list: () => request<Credential[]>("/credentials/"),
    create: (body: CredentialCreateRequest) =>
      request<Credential>("/credentials/", { method: "POST", body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/credentials/${id}`, { method: "DELETE" }),
    test: (id: string) => request<{ ok: boolean; error?: string }>(`/credentials/${id}/test`, { method: "POST" }),
  },
  schedules: {
    list: () => request<ScheduleItem[]>("/schedules/"),
    get: (flowId: string) => request<ScheduleItem>(`/schedules/${flowId}`),
    set: (flowId: string, cronExpression: string) =>
      request<ScheduleItem>(`/schedules/${flowId}`, {
        method: "PUT",
        body: JSON.stringify({ cron_expression: cronExpression }),
      }),
    delete: (flowId: string) => request<void>(`/schedules/${flowId}`, { method: "DELETE" }),
  },
};

// Types
export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "editor" | "viewer";
  is_active: boolean;
}

export interface UserRecord {
  id: string;
  email: string;
  role: "admin" | "editor" | "viewer";
  is_active: boolean;
  sso_subject: string | null;
  created_at: string;
}

export interface Flow {
  id: string;
  name: string;
  description: string | null;
  version: number;
  status: "draft" | "active" | "paused";
  graph_json: FlowGraph;
}

export interface FlowGraph {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface FlowNode {
  id: string;
  type: "trigger" | "action" | "condition" | "transform";
  connector_key?: string;
  config_json: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  condition_expr?: string;
}

export interface FlowCreateRequest {
  name: string;
  description?: string;
  nodes?: FlowNode[];
  edges?: FlowEdge[];
}

export interface Run {
  id: string;
  flow_id: string;
  flow_name: string;
  flow_version: number;
  trigger_source: string;
  status: "pending" | "running" | "success" | "failed" | "cancelled";
  started_at: string;
  finished_at: string | null;
  steps: RunStep[];
}

export interface RunStep {
  id: string;
  node_id: string;
  status: string;
  input_json: Record<string, unknown> | null;
  output_json: Record<string, unknown> | null;
  error: string | null;
  duration_ms: number | null;
  attempt: number;
}

export interface Connector {
  id: string;
  key: string;
  name: string;
  category: string;
  manifest_version: string;
  icon_url: string | null;
  description: string | null;
}

export interface ConnectorManifest {
  key: string;
  name: string;
  category: string;
  description?: string;
  triggers: { key: string; name: string }[];
  actions: {
    key: string;
    name: string;
    description?: string;
    input_schema: { properties: Record<string, unknown>; required?: string[] };
  }[];
  auth?: { fields: { name: string; label: string; type: string; required?: boolean; placeholder?: string; help_text?: string }[] };
}

export interface Credential {
  id: string;
  connector_id: string;
  name: string;
  status: string;
  last_tested_at: string | null;
}

export interface CredentialCreateRequest {
  connector_id: string;
  name: string;
  payload: Record<string, unknown>;
}

export interface ScheduleItem {
  flow_id: string;
  flow_name: string;
  flow_status: string;
  cron_expression: string;
  enabled: boolean;
  is_script: boolean;
}
