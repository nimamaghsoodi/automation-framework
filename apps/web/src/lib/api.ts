const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
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
  },
  credentials: {
    list: () => request<Credential[]>("/credentials/"),
    create: (body: CredentialCreateRequest) =>
      request<Credential>("/credentials/", { method: "POST", body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/credentials/${id}`, { method: "DELETE" }),
  },
};

// Types
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
