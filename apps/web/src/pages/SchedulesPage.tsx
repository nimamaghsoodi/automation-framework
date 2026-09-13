import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type ScheduleItem } from "../lib/api";
import { cn } from "../lib/utils";

const CRON_PRESETS = [
  { label: "Every minute",          value: "* * * * *" },
  { label: "Every 5 minutes",       value: "*/5 * * * *" },
  { label: "Every 15 minutes",      value: "*/15 * * * *" },
  { label: "Every hour",            value: "0 * * * *" },
  { label: "Daily at 9 AM",         value: "0 9 * * *" },
  { label: "Mon–Fri at 9 AM",       value: "0 9 * * 1-5" },
  { label: "Every Monday at 8 AM",  value: "0 8 * * 1" },
];

function humanCron(expr: string): string {
  const match = CRON_PRESETS.find((p) => p.value === expr);
  if (match) return match.label;
  return expr;
}

function StatusBadge({ enabled, status }: { enabled: boolean; status: string }) {
  if (enabled) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full bg-emerald-900/40 text-emerald-400 border border-emerald-800/50">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Active
      </span>
    );
  }
  if (status === "paused") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-900/30 text-amber-400 border border-amber-800/50">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        Paused
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
      <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
      Not running
    </span>
  );
}

interface EditState {
  flowId: string;
  expr: string;
}

export default function SchedulesPage() {
  const [items, setItems] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [editing, setEditing] = useState<EditState | null>(null);
  const navigate = useNavigate();

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    try {
      setItems(await api.schedules.list());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(item: ScheduleItem) {
    setToggling(item.flow_id);
    try {
      if (item.enabled) {
        await api.schedules.delete(item.flow_id);
        setItems((prev) => prev.map((s) =>
          s.flow_id === item.flow_id ? { ...s, enabled: false, flow_status: "paused" } : s
        ));
      } else {
        const updated = await api.schedules.set(item.flow_id, item.cron_expression);
        setItems((prev) => prev.map((s) =>
          s.flow_id === item.flow_id ? { ...s, ...updated } : s
        ));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to toggle schedule");
    } finally {
      setToggling(null);
    }
  }

  async function handleSaveExpression() {
    if (!editing) return;
    setToggling(editing.flowId);
    try {
      const updated = await api.schedules.set(editing.flowId, editing.expr);
      setItems((prev) => prev.map((s) =>
        s.flow_id === editing.flowId ? { ...s, ...updated } : s
      ));
      setEditing(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update schedule");
    } finally {
      setToggling(null);
    }
  }

  const flows = items.filter((i) => !i.is_script);
  const scripts = items.filter((i) => i.is_script);

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-xl font-semibold">Schedules</h1>
        <p className="text-sm text-text-secondary mt-1">
          All flows and scripts with a cron trigger — enable, pause, or adjust their schedule.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-950/50 border border-red-900 text-status-error text-sm flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-text-muted hover:text-text-primary">✕</button>
        </div>
      )}

      {loading ? (
        <div className="text-text-muted text-sm">Loading schedules…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-24 text-text-muted">
          <p className="text-lg mb-2">No scheduled flows yet</p>
          <p className="text-sm">Add a cron trigger node to a flow to see it here.</p>
        </div>
      ) : (
        <div className="space-y-10">
          {flows.length > 0 && (
            <Section
              title="Flows"
              subtitle="Automation flows triggered on a schedule"
              items={flows}
              onToggle={handleToggle}
              toggling={toggling}
              editing={editing}
              onEdit={(id, expr) => setEditing({ flowId: id, expr })}
              onEditChange={(expr) => setEditing((e) => e ? { ...e, expr } : e)}
              onEditSave={handleSaveExpression}
              onEditCancel={() => setEditing(null)}
              onOpen={(id) => navigate(`/flows/${id}`)}
            />
          )}
          {scripts.length > 0 && (
            <Section
              title="Scripts"
              subtitle="Python scripts triggered on a schedule"
              items={scripts}
              onToggle={handleToggle}
              toggling={toggling}
              editing={editing}
              onEdit={(id, expr) => setEditing({ flowId: id, expr })}
              onEditChange={(expr) => setEditing((e) => e ? { ...e, expr } : e)}
              onEditSave={handleSaveExpression}
              onEditCancel={() => setEditing(null)}
              onOpen={(id) => navigate(`/flows/${id}`)}
            />
          )}
        </div>
      )}
    </div>
  );
}

interface SectionProps {
  title: string;
  subtitle: string;
  items: ScheduleItem[];
  toggling: string | null;
  editing: EditState | null;
  onToggle: (item: ScheduleItem) => void;
  onEdit: (id: string, expr: string) => void;
  onEditChange: (expr: string) => void;
  onEditSave: () => void;
  onEditCancel: () => void;
  onOpen: (id: string) => void;
}

function Section({
  title, subtitle, items, toggling, editing,
  onToggle, onEdit, onEditChange, onEditSave, onEditCancel, onOpen,
}: SectionProps) {
  return (
    <div>
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
        <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
      </div>
      <div className="border border-border rounded-lg overflow-hidden divide-y divide-border">
        {items.map((item) => {
          const isEditing = editing?.flowId === item.flow_id;
          const isBusy = toggling === item.flow_id;
          return (
            <div key={item.flow_id} className="bg-surface hover:bg-surface-raised transition-colors p-4">
              <div className="flex items-start justify-between gap-4">
                {/* Left: name + schedule info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={() => onOpen(item.flow_id)}
                      className="font-medium text-sm text-text-primary hover:text-accent-hover transition-colors text-left"
                    >
                      {item.flow_name}
                    </button>
                    <StatusBadge enabled={item.enabled} status={item.flow_status} />
                  </div>

                  {/* Cron expression row */}
                  {isEditing ? (
                    <div className="mt-2 space-y-2">
                      <div className="flex flex-wrap gap-1">
                        {CRON_PRESETS.map((p) => (
                          <button
                            key={p.value}
                            onClick={() => onEditChange(p.value)}
                            className={cn(
                              "text-[11px] px-2 py-0.5 rounded border transition-colors",
                              editing.expr === p.value
                                ? "border-accent bg-accent/10 text-accent"
                                : "border-border text-text-muted hover:border-accent/50 hover:text-text-secondary"
                            )}
                          >
                            {p.label}
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={editing.expr}
                          onChange={(e) => onEditChange(e.target.value)}
                          className="font-mono text-xs px-2 py-1.5 bg-surface border border-border rounded focus:outline-none focus:ring-1 focus:ring-accent w-44"
                          placeholder="* * * * *"
                        />
                        <button
                          onClick={onEditSave}
                          disabled={isBusy || !editing.expr}
                          className="text-xs px-3 py-1.5 bg-accent text-white rounded hover:bg-accent-hover disabled:opacity-50 transition-colors"
                        >
                          {isBusy ? "Saving…" : "Save"}
                        </button>
                        <button
                          onClick={onEditCancel}
                          className="text-xs px-3 py-1.5 border border-border text-text-secondary rounded hover:text-text-primary transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-1.5">
                      <code className="text-[11px] font-mono text-text-muted bg-surface-overlay px-2 py-0.5 rounded border border-border">
                        {item.cron_expression}
                      </code>
                      <span className="text-xs text-text-muted">
                        {humanCron(item.cron_expression)}
                      </span>
                      <button
                        onClick={() => onEdit(item.flow_id, item.cron_expression)}
                        className="text-[11px] text-text-muted hover:text-accent transition-colors"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                </div>

                {/* Right: toggle button */}
                {!isEditing && (
                  <button
                    onClick={() => onToggle(item)}
                    disabled={isBusy}
                    className={cn(
                      "shrink-0 text-xs px-3 py-1.5 rounded border transition-colors disabled:opacity-50",
                      item.enabled
                        ? "border-amber-800/60 text-amber-400 hover:bg-amber-950/30"
                        : "border-emerald-800/60 text-emerald-400 hover:bg-emerald-950/30"
                    )}
                  >
                    {isBusy ? "…" : item.enabled ? "Pause" : "Enable"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
