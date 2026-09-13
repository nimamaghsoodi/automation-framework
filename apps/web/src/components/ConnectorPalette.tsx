import { useEffect, useState } from "react";
import { cn } from "../lib/utils";

const CATEGORY_COLORS: Record<string, string> = {
  trigger: "text-status-running",
  generic: "text-text-secondary",
  communication: "text-purple-400",
  ticketing: "text-yellow-400",
  cloud: "text-blue-400",
  database: "text-green-400",
  devops: "text-orange-400",
};

interface Manifest {
  key: string;
  name: string;
  category: string;
  description?: string;
}

interface Props {
  onAddNode: (connectorKey: string, connectorName: string, nodeType: "trigger" | "action") => void;
}

export default function ConnectorPalette({ onAddNode }: Props) {
  const [manifests, setManifests] = useState<Record<string, Manifest>>({});
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/v1/connectors/manifests/all")
      .then((r) => r.json())
      .then(setManifests)
      .catch(console.error);
  }, []);

  const filtered = Object.values(manifests).filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-border">
        <input
          type="text"
          placeholder="Search connectors…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface text-text-primary text-xs px-2 py-1.5 rounded border border-border placeholder-text-muted focus:outline-none focus:border-accent/60"
        />
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {filtered.length === 0 && (
          <div className="p-3 text-xs text-text-muted">No connectors found.</div>
        )}
        {filtered.map((m) => {
          const hasTriggers = (manifests[m.key] as any)?.triggers?.length > 0;
          const hasActions = (manifests[m.key] as any)?.actions?.length > 0;
          return (
            <div key={m.key} className="px-2 py-1">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted px-1 mb-0.5">
                {m.name}
                <span className={cn("ml-1.5", CATEGORY_COLORS[m.category] ?? "text-text-muted")}>
                  {m.category}
                </span>
              </div>
              <div className="flex gap-1">
                {hasTriggers && (
                  <button
                    onClick={() => onAddNode(m.key, m.name, "trigger")}
                    className="flex-1 text-[11px] py-1 px-2 rounded border border-status-running/30 text-status-running hover:bg-blue-950/30 transition-colors text-left"
                  >
                    + Trigger
                  </button>
                )}
                {hasActions && (
                  <button
                    onClick={() => onAddNode(m.key, m.name, "action")}
                    className="flex-1 text-[11px] py-1 px-2 rounded border border-border text-text-secondary hover:text-text-primary hover:border-accent/50 transition-colors text-left"
                  >
                    + Action
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
