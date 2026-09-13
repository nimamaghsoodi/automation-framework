import { useEffect, useState } from "react";
import { api, type Credential } from "../lib/api";

export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.credentials.list().then(setCredentials).finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete this credential?")) return;
    await api.credentials.delete(id);
    setCredentials((prev) => prev.filter((c) => c.id !== id));
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Credential Vault</h1>
        <p className="text-sm text-text-secondary mt-1">Stored connector credentials — values are encrypted at rest</p>
      </div>
      {loading ? (
        <div className="text-text-muted text-sm">Loading…</div>
      ) : credentials.length === 0 ? (
        <div className="text-text-muted text-sm">No credentials stored yet.</div>
      ) : (
        <div className="space-y-2">
          {credentials.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between p-4 rounded-lg border border-border bg-surface-raised"
            >
              <div>
                <div className="font-medium text-text-primary">{c.name}</div>
                <div className="text-xs text-text-muted mt-0.5">
                  {c.status}
                  {c.last_tested_at && ` · tested ${new Date(c.last_tested_at).toLocaleDateString()}`}
                </div>
              </div>
              <button
                onClick={() => handleDelete(c.id)}
                className="text-xs text-text-muted hover:text-status-error transition-colors px-2 py-1 rounded hover:bg-red-950/30"
              >
                Revoke
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
