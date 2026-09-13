import { useEffect, useState } from "react";
import { api, type Credential } from "../lib/api";
import AddCredentialModal from "../components/AddCredentialModal";
import { cn } from "../lib/utils";

const STATUS_COLORS: Record<string, string> = {
  active: "text-status-success",
  invalid: "text-status-error",
  testing: "text-status-running",
};

export default function CredentialsPage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, string>>({});

  useEffect(() => {
    api.credentials.list().then(setCredentials).finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    if (!confirm("Revoke this credential? This cannot be undone.")) return;
    await api.credentials.delete(id);
    setCredentials((prev) => prev.filter((c) => c.id !== id));
  }

  async function handleTest(id: string) {
    setTesting((t) => ({ ...t, [id]: true }));
    setTestResults((r) => ({ ...r, [id]: "" }));
    try {
      const result = await fetch(`/api/v1/credentials/${id}/test`, { method: "POST" }).then((r) => r.json());
      const msg = result.ok !== false ? "✓ Connection successful" : `✗ ${result.error ?? "Failed"}`;
      setTestResults((r) => ({ ...r, [id]: msg }));
      // Refresh status
      setCredentials((prev) =>
        prev.map((c) => c.id === id ? { ...c, status: result.ok !== false ? "active" : "invalid" } : c)
      );
    } catch {
      setTestResults((r) => ({ ...r, [id]: "✗ Request failed" }));
    } finally {
      setTesting((t) => ({ ...t, [id]: false }));
    }
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold">Credential Vault</h1>
          <p className="text-sm text-text-secondary mt-1">
            Connector credentials — encrypted at rest, never returned after creation
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover transition-colors"
        >
          Add Credential
        </button>
      </div>

      {loading ? (
        <div className="text-text-muted text-sm">Loading…</div>
      ) : credentials.length === 0 ? (
        <div className="text-center py-24 text-text-muted">
          <p className="text-lg mb-2">No credentials yet</p>
          <p className="text-sm">Add a credential to connect your first integration.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {credentials.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between p-4 rounded-lg border border-border bg-surface-raised"
            >
              <div>
                <div className="font-medium text-text-primary">{c.name}</div>
                <div className="text-xs text-text-muted mt-0.5 flex items-center gap-2">
                  <span className={cn(STATUS_COLORS[c.status] ?? "text-text-muted")}>{c.status}</span>
                  {c.last_tested_at && (
                    <span>· tested {new Date(c.last_tested_at).toLocaleDateString()}</span>
                  )}
                  {testResults[c.id] && (
                    <span className={testResults[c.id].startsWith("✓") ? "text-status-success" : "text-status-error"}>
                      · {testResults[c.id]}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleTest(c.id)}
                  disabled={testing[c.id]}
                  className="text-xs px-3 py-1.5 rounded border border-border text-text-secondary hover:text-text-primary hover:border-accent/50 transition-colors disabled:opacity-50"
                >
                  {testing[c.id] ? "Testing…" : "Test"}
                </button>
                <button
                  onClick={() => handleDelete(c.id)}
                  className="text-xs px-3 py-1.5 rounded border border-red-900/50 text-status-error hover:bg-red-950/30 transition-colors"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <AddCredentialModal
          onClose={() => setShowModal(false)}
          onCreated={(cred) => setCredentials((prev) => [...prev, cred])}
        />
      )}
    </div>
  );
}
