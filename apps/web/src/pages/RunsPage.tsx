import { useEffect, useState } from "react";
import { api, type Run } from "../lib/api";
import { cn } from "../lib/utils";

const STATUS_COLORS: Record<string, string> = {
  success: "text-status-success",
  failed: "text-status-error",
  running: "text-status-running",
  pending: "text-text-muted",
  cancelled: "text-text-muted",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.runs.list().then(setRuns).finally(() => setLoading(false));
  }, []);

  async function handleSelect(run: Run) {
    const detail = await api.runs.get(run.id);
    setSelected(detail);
  }

  return (
    <div className="flex h-full">
      {/* Run list */}
      <div className="w-80 border-r border-border overflow-y-auto">
        <div className="px-4 py-4 border-b border-border">
          <h1 className="font-semibold">Run History</h1>
        </div>
        {loading ? (
          <div className="p-4 text-sm text-text-muted">Loading…</div>
        ) : runs.length === 0 ? (
          <div className="p-4 text-sm text-text-muted">No runs yet.</div>
        ) : (
          runs.map((run) => (
            <button
              key={run.id}
              onClick={() => handleSelect(run)}
              className={cn(
                "w-full text-left px-4 py-3 border-b border-border hover:bg-surface-overlay transition-colors",
                selected?.id === run.id && "bg-surface-overlay"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary truncate">{run.flow_name}</span>
                <span className={cn("text-xs font-medium shrink-0", STATUS_COLORS[run.status] ?? "text-text-muted")}>
                  {run.status}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[11px] text-text-muted">{new Date(run.started_at).toLocaleString()}</span>
                <span className="text-[11px] font-mono text-text-muted">#{run.id.slice(0, 8)}</span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Step detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selected ? (
          <div className="text-text-muted text-sm">Select a run to inspect its steps.</div>
        ) : (
          <>
            <div className="mb-4">
              <div className="text-lg font-semibold">{selected.flow_name}</div>
              <div className="text-sm text-text-secondary mt-0.5">
                <span className="font-mono text-text-muted">#{selected.id.slice(0, 8)}</span>
                {" · "}{selected.trigger_source} · v{selected.flow_version} ·{" "}
                <span className={STATUS_COLORS[selected.status] ?? ""}>{selected.status}</span>
              </div>
            </div>
            <div className="space-y-3">
              {selected.steps.length === 0 && <div className="text-sm text-text-muted">No steps recorded.</div>}
              {selected.steps.map((step) => (
                <div key={step.id} className="rounded-lg border border-border bg-surface-raised p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-text-secondary">{step.node_id.slice(0, 8)}…</span>
                    <div className="flex items-center gap-3">
                      {step.duration_ms != null && (
                        <span className="text-xs text-text-muted">{step.duration_ms}ms</span>
                      )}
                      <span className={cn("text-xs font-medium", STATUS_COLORS[step.status] ?? "")}>
                        {step.status}
                      </span>
                    </div>
                  </div>
                  {step.error && (
                    <div className="text-xs text-status-error font-mono bg-red-950/30 rounded p-2 mb-2">
                      {step.error}
                    </div>
                  )}
                  {step.output_json && (
                    <pre className="text-xs font-mono text-text-secondary bg-surface p-2 rounded overflow-auto max-h-40">
                      {JSON.stringify(step.output_json, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
