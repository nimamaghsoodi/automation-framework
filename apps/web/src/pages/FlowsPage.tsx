import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Flow } from "../lib/api";
import { cn } from "../lib/utils";

export default function FlowsPage() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.flows.list().then(setFlows).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await api.flows.delete(id);
      setFlows((fs) => fs.filter((f) => f.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete flow");
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  }

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
            <div
              key={flow.id}
              className="flex items-start justify-between p-4 rounded-lg border border-border bg-surface-raised hover:border-accent/50 hover:bg-surface-overlay transition-all group"
            >
              <button
                onClick={() => navigate(`/flows/${flow.id}`)}
                className="flex-1 text-left"
              >
                <div className="font-medium text-text-primary group-hover:text-accent-hover transition-colors">
                  {flow.name}
                </div>
                {flow.description && (
                  <div className="text-sm text-text-secondary mt-0.5">{flow.description}</div>
                )}
              </button>
              <div className="flex items-center gap-3 shrink-0 ml-4 mt-0.5">
                <span className={cn("text-xs font-medium uppercase tracking-wide", statusColors[flow.status] ?? "text-text-muted")}>
                  {flow.status}
                </span>
                <span className="text-xs text-text-muted">v{flow.version}</span>
                {confirmId === flow.id ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-text-secondary">Delete?</span>
                    <button
                      onClick={() => handleDelete(flow.id)}
                      disabled={deletingId === flow.id}
                      className="px-2 py-0.5 text-xs font-medium rounded bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 transition-colors"
                    >
                      {deletingId === flow.id ? "…" : "Yes"}
                    </button>
                    <button
                      onClick={() => setConfirmId(null)}
                      className="px-2 py-0.5 text-xs font-medium rounded border border-border text-text-secondary hover:text-text-primary transition-colors"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmId(flow.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded text-text-muted hover:text-status-error transition-all"
                    title="Delete flow"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
                    </svg>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
