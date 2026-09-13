import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Flow } from "../lib/api";
import { cn } from "../lib/utils";

export default function FlowsPage() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.flows.list().then(setFlows).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    setCreating(true);
    try {
      const flow = await api.flows.create({ name: "Untitled Flow" });
      navigate(`/flows/${flow.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create flow");
    } finally {
      setCreating(false);
    }
  }

  const statusColors: Record<string, string> = {
    active: "text-status-success",
    draft: "text-text-muted",
    paused: "text-status-warning",
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Flows</h1>
          <p className="text-sm text-text-secondary mt-1">Automation flows in your workspace</p>
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          {creating ? "Creating…" : "New Flow"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-950/50 border border-red-900 text-status-error text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-text-muted text-sm">Loading flows…</div>
      ) : flows.length === 0 ? (
        <div className="text-center py-24 text-text-muted">
          <p className="text-lg mb-2">No flows yet</p>
          <p className="text-sm">Create your first flow to get started.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {flows.map((flow) => (
            <button
              key={flow.id}
              onClick={() => navigate(`/flows/${flow.id}`)}
              className="flex items-start justify-between p-4 rounded-lg border border-border bg-surface-raised hover:border-accent/50 hover:bg-surface-overlay transition-all text-left group"
            >
              <div>
                <div className="font-medium text-text-primary group-hover:text-accent-hover transition-colors">
                  {flow.name}
                </div>
                {flow.description && (
                  <div className="text-sm text-text-secondary mt-0.5">{flow.description}</div>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-4 mt-0.5">
                <span className={cn("text-xs font-medium uppercase tracking-wide", statusColors[flow.status] ?? "text-text-muted")}>
                  {flow.status}
                </span>
                <span className="text-xs text-text-muted">v{flow.version}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
