import { useState } from "react";
import { api, type Run } from "../lib/api";
import { cn } from "../lib/utils";

interface Props {
  flowId: string;
  onClose: () => void;
  onRunStarted: (run: Run) => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "text-text-muted",
  running: "text-status-running",
  success: "text-status-success",
  failed: "text-status-error",
  cancelled: "text-text-muted",
};

export default function RunModal({ flowId, onClose, onRunStarted }: Props) {
  const [payload, setPayload] = useState("{}");
  const [payloadError, setPayloadError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [run, setRun] = useState<Run | null>(null);

  function validatePayload(): Record<string, unknown> | null {
    try {
      const parsed = JSON.parse(payload);
      setPayloadError(null);
      return parsed;
    } catch {
      setPayloadError("Invalid JSON");
      return null;
    }
  }

  async function handleRun() {
    const parsed = validatePayload();
    if (!parsed) return;
    setRunning(true);
    try {
      const r = await api.runs.trigger(flowId, parsed);
      setRun(r);
      onRunStarted(r);
    } catch (e: unknown) {
      setPayloadError(e instanceof Error ? e.message : "Failed to start run");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-surface-raised border border-border rounded-xl w-[480px] max-h-[80vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold text-text-primary">Run Flow</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">
              Trigger Payload (JSON)
            </label>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              disabled={run !== null}
              className={cn(
                "w-full bg-surface font-mono text-xs text-text-primary px-3 py-2 rounded border placeholder-text-muted",
                "focus:outline-none focus:border-accent/60 transition-colors min-h-[120px] resize-y",
                payloadError ? "border-status-error" : "border-border"
              )}
              placeholder='{"event": "order.created", "data": {}}'
            />
            {payloadError && (
              <p className="text-xs text-status-error mt-1">{payloadError}</p>
            )}
          </div>

          {run && (
            <div className="rounded-lg border border-border bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary font-mono">{run.id.slice(0, 16)}…</span>
                <span className={cn("text-xs font-medium", STATUS_COLORS[run.status] ?? "")}>
                  {run.status}
                </span>
              </div>
              <p className="text-xs text-text-muted">
                Watching live — node status rings on the canvas update in real time.
                Close this modal to keep working while the run completes.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={handleRun}
            disabled={running || run !== null}
            className="flex-1 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {running ? "Starting…" : run ? "Run started" : "Run Now"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary border border-border rounded-lg hover:text-text-primary transition-colors"
          >
            {run ? "Close" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
