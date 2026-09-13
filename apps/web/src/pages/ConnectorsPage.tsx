import { useEffect, useState } from "react";
import { api, type Connector } from "../lib/api";

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.connectors.list().then(setConnectors).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Connectors</h1>
        <p className="text-sm text-text-secondary mt-1">Installed connector integrations</p>
      </div>
      {loading ? (
        <div className="text-text-muted text-sm">Loading…</div>
      ) : connectors.length === 0 ? (
        <div className="text-text-muted text-sm">No connectors installed yet.</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {connectors.map((c) => (
            <div key={c.id} className="p-4 rounded-lg border border-border bg-surface-raised">
              {c.icon_url && <img src={c.icon_url} alt="" className="w-8 h-8 mb-3" />}
              <div className="font-medium text-text-primary">{c.name}</div>
              <div className="text-xs text-text-muted mt-0.5">{c.category}</div>
              {c.description && <div className="text-xs text-text-secondary mt-2">{c.description}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
