import { useEffect, useState } from "react";
import { api, type Flow } from "../lib/api";
import { cn } from "../lib/utils";

const CRON_PRESETS = [
  { label: "Every minute",    value: "* * * * *" },
  { label: "Every 5 minutes", value: "*/5 * * * *" },
  { label: "Every hour",      value: "0 * * * *" },
  { label: "Every day at midnight", value: "0 0 * * *" },
  { label: "Every Monday at 9 AM",  value: "0 9 * * 1" },
  { label: "Custom…",         value: "" },
];

const DEFAULT_SCRIPT = `# Available variables:
#   inputs  — dict of previous node outputs (empty for scheduled scripts)
#   trigger — {"scheduled_at": "...", "source": "cron"}
#
# Set the 'output' variable to return data.

import datetime

output = {
    "message": "Script ran successfully",
    "timestamp": str(datetime.datetime.utcnow()),
}
`;

interface Script extends Flow {
  cron_expression?: string;
  schedule_enabled: boolean;
}

export default function ScriptsPage() {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  async function loadScripts() {
    const flows = await api.flows.list().catch(() => [] as Flow[]);
    // Scripts are flows tagged with script=true in graph_json
    const s = flows
      .filter((f) => (f.graph_json as Record<string, unknown>).is_script)
      .map((f) => {
        const g = f.graph_json as Record<string, unknown>;
        return {
          ...f,
          cron_expression: (g.cron_expression as string) || undefined,
          schedule_enabled: f.status === "active" && Boolean(g.cron_expression),
        };
      });
    setScripts(s);
    setLoading(false);
  }

  useEffect(() => { loadScripts(); }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete this script?")) return;
    // Disable schedule first if active
    await fetch(`/api/v1/schedules/${id}`, { method: "DELETE" }).catch(() => null);
    await api.flows.delete(id);
    setScripts((prev) => prev.filter((s) => s.id !== id));
  }

  async function handleToggle(script: Script) {
    if (script.schedule_enabled) {
      await fetch(`/api/v1/schedules/${script.id}`, { method: "DELETE" });
    } else if (script.cron_expression) {
      await fetch(`/api/v1/schedules/${script.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cron_expression: script.cron_expression }),
      });
    }
    loadScripts();
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold">Scripts</h1>
          <p className="text-sm text-text-secondary mt-1">
            Paste Python code, optionally schedule it — no flow builder required.
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover transition-colors"
        >
          New Script
        </button>
      </div>

      {loading ? (
        <div className="text-text-muted text-sm">Loading…</div>
      ) : scripts.length === 0 ? (
        <div className="text-center py-24 text-text-muted">
          <p className="text-lg mb-2">No scripts yet</p>
          <p className="text-sm">Create a script to run Python code on a schedule.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {scripts.map((s) => (
            <ScriptRow
              key={s.id}
              script={s}
              onDelete={() => handleDelete(s.id)}
              onToggle={() => handleToggle(s)}
              onRunNow={() => api.runs.trigger(s.id).then(() => alert("Run triggered!"))}
            />
          ))}
        </div>
      )}

      {showNew && (
        <NewScriptModal
          onClose={() => setShowNew(false)}
          onCreated={() => { setShowNew(false); loadScripts(); }}
        />
      )}
    </div>
  );
}

function ScriptRow({
  script,
  onDelete,
  onToggle,
  onRunNow,
}: {
  script: Script;
  onDelete: () => void;
  onToggle: () => void;
  onRunNow: () => void;
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg border border-border bg-surface-raised">
      <div className="min-w-0">
        <div className="font-medium text-text-primary text-sm">{script.name}</div>
        {script.description && (
          <div className="text-xs text-text-secondary mt-0.5">{script.description}</div>
        )}
        <div className="flex items-center gap-3 mt-1.5">
          {script.cron_expression ? (
            <span className="text-[11px] font-mono text-text-muted bg-surface px-2 py-0.5 rounded border border-border">
              {script.cron_expression}
            </span>
          ) : (
            <span className="text-[11px] text-text-muted">Manual only</span>
          )}
          {script.schedule_enabled && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-900/40 text-emerald-400 font-medium">
              Running
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 ml-4">
        <button
          onClick={onRunNow}
          className="text-xs px-3 py-1.5 rounded border border-border text-text-secondary hover:text-text-primary hover:border-accent/50 transition-colors"
        >
          Run now
        </button>
        {script.cron_expression && (
          <button
            onClick={onToggle}
            className={cn(
              "text-xs px-3 py-1.5 rounded border transition-colors",
              script.schedule_enabled
                ? "border-amber-900/50 text-amber-400 hover:bg-amber-950/30"
                : "border-emerald-900/50 text-emerald-400 hover:bg-emerald-950/30"
            )}
          >
            {script.schedule_enabled ? "Pause" : "Enable"}
          </button>
        )}
        <button
          onClick={onDelete}
          className="text-xs px-3 py-1.5 rounded border border-red-900/50 text-status-error hover:bg-red-950/30 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

function NewScriptModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState(DEFAULT_SCRIPT);
  const [scheduleMode, setScheduleMode] = useState<"manual" | "cron">("manual");
  const [cronPreset, setCronPreset] = useState(CRON_PRESETS[1].value);
  const [cronCustom, setCronCustom] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cronExpression = scheduleMode === "cron"
    ? (cronPreset || cronCustom)
    : "";

  async function handleSave() {
    if (!name.trim()) { setError("Name is required"); return; }
    if (scheduleMode === "cron" && !cronExpression) {
      setError("Enter a cron expression or choose a preset");
      return;
    }
    setSaving(true);
    setError(null);

    try {
      // Create flow with is_script marker and embedded code in graph_json
      const flow = await api.flows.create({
        name: name.trim(),
        description: description.trim() || undefined,
        // Pack the code and schedule into graph_json via a "virtual" node
        // The graph_json.is_script flag lets ScriptsPage filter these from normal flows
      });

      // Patch the graph_json to include the code and script marker
      await fetch(`/api/v1/flows/${flow.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          graph: {
            is_script: true,
            source_code: code,
            nodes: [
              ...(cronExpression ? [{
                id: "trigger-1",
                type: "trigger",
                connector_key: "cron",
                config_json: { cron_expression: cronExpression },
                position: { x: 100, y: 100 },
              }] : []),
              {
                id: "code-1",
                type: "action",
                connector_key: "code",
                config_json: { action_key: "run_python", source_code: code },
                position: { x: 100, y: cronExpression ? 250 : 100 },
              },
            ],
            edges: cronExpression ? [{ id: "e1", source: "trigger-1", target: "code-1" }] : [],
          },
        }),
      });

      // Enable scheduling if cron configured
      if (cronExpression) {
        const res = await fetch(`/api/v1/schedules/${flow.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ cron_expression: cronExpression }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? "Failed to set schedule");
        }
      }

      onCreated();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create script");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-surface-raised border border-border rounded-xl w-[640px] max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold">New Script</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {error && (
            <p className="text-xs text-status-error bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Name + description */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Script name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputCls}
                placeholder="e.g. Daily Report"
                autoFocus
              />
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={inputCls}
                placeholder="Optional note"
              />
            </div>
          </div>

          {/* Code editor */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className={labelCls}>Python script</label>
              <span className="text-[10px] text-text-muted font-mono">Tab = 4 spaces</span>
            </div>
            <div className="rounded-lg border border-border overflow-hidden">
              <div className="flex items-center px-3 py-1.5 bg-zinc-900 border-b border-border">
                <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">python</span>
              </div>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Tab") {
                    e.preventDefault();
                    const el = e.currentTarget;
                    const start = el.selectionStart;
                    const end = el.selectionEnd;
                    const next = code.substring(0, start) + "    " + code.substring(end);
                    setCode(next);
                    requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = start + 4; });
                  }
                }}
                spellCheck={false}
                className="w-full bg-zinc-950 text-emerald-300 font-mono text-[12px] leading-relaxed px-3 py-3 min-h-[220px] resize-y focus:outline-none whitespace-pre"
              />
            </div>
            <p className="text-[10px] text-text-muted mt-1.5">
              Variables: <code className="text-accent/80">inputs</code> (previous step outputs),{" "}
              <code className="text-accent/80">trigger</code> (schedule info). Set{" "}
              <code className="text-accent/80">output</code> to pass data forward.
            </p>
          </div>

          {/* Schedule */}
          <div>
            <label className={labelCls}>Schedule</label>
            <div className="flex gap-2 mb-3">
              {(["manual", "cron"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setScheduleMode(m)}
                  className={cn(
                    "px-3 py-1.5 text-xs rounded-lg border transition-colors",
                    scheduleMode === m
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border text-text-secondary hover:text-text-primary"
                  )}
                >
                  {m === "manual" ? "Run manually" : "On a schedule (cron)"}
                </button>
              ))}
            </div>

            {scheduleMode === "cron" && (
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1.5">
                  {CRON_PRESETS.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => { setCronPreset(p.value); if (p.value) setCronCustom(""); }}
                      className={cn(
                        "text-[11px] px-2.5 py-1 rounded border transition-colors",
                        cronPreset === p.value && p.value
                          ? "border-accent bg-accent/10 text-accent"
                          : "border-border text-text-secondary hover:border-accent/50"
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={cronPreset || cronCustom}
                    onChange={(e) => { setCronPreset(""); setCronCustom(e.target.value); }}
                    className={cn(inputCls, "font-mono")}
                    placeholder="* * * * *  (minute hour day month weekday)"
                  />
                  <a
                    href="https://crontab.guru"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-accent whitespace-nowrap hover:underline"
                  >
                    crontab.guru ↗
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-40"
          >
            {saving ? "Creating…" : scheduleMode === "cron" ? "Create & Schedule" : "Create Script"}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-text-secondary border border-border rounded-lg hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

const labelCls = "block text-xs font-medium text-text-secondary mb-1";
const inputCls =
  "w-full bg-surface text-text-primary text-sm px-3 py-2 rounded-lg border border-border " +
  "placeholder-text-muted focus:outline-none focus:border-accent/60 transition-colors";
