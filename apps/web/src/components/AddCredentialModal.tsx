import { useEffect, useState } from "react";
import { api, type Credential } from "../lib/api";
import { cn } from "../lib/utils";

interface CredentialField {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string;
  help_text?: string;
}

interface ConnectorOption {
  id: string;
  key: string;
  name: string;
}

interface Props {
  onClose: () => void;
  onCreated: (cred: Credential) => void;
}

export default function AddCredentialModal({ onClose, onCreated }: Props) {
  const [connectors, setConnectors] = useState<ConnectorOption[]>([]);
  const [selectedConnectorId, setSelectedConnectorId] = useState("");
  const [selectedConnectorKey, setSelectedConnectorKey] = useState("");
  const [fields, setFields] = useState<CredentialField[]>([]);
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.connectors.list().then(setConnectors).catch(console.error);
  }, []);

  async function handleConnectorChange(connectorId: string, connectorKey: string) {
    setSelectedConnectorId(connectorId);
    setSelectedConnectorKey(connectorKey);
    setValues({});
    if (!connectorKey) { setFields([]); return; }
    try {
      const manifest = await fetch(`/api/v1/connectors/${connectorKey}/manifest`).then((r) => r.json());
      setFields(manifest?.auth?.fields ?? []);
    } catch {
      setFields([]);
    }
  }

  async function handleSubmit() {
    if (!selectedConnectorId || !name.trim()) {
      setError("Connector and name are required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const cred = await api.credentials.create({
        connector_id: selectedConnectorId,
        name: name.trim(),
        payload: values,
      });
      onCreated(cred);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save credential");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-surface-raised border border-border rounded-xl w-[440px] max-h-[80vh] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-semibold">Add Credential</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-xl leading-none">×</button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {error && <p className="text-xs text-status-error">{error}</p>}

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Connector</label>
            <select
              value={selectedConnectorId}
              onChange={(e) => {
                const opt = connectors.find((c) => c.id === e.target.value);
                handleConnectorChange(e.target.value, opt?.key ?? "");
              }}
              className={inputCls}
            >
              <option value="">— select connector —</option>
              {connectors.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
              placeholder="e.g. Production Zendesk"
            />
          </div>

          {fields.map((field) => (
            <div key={field.name}>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                {field.label}
                {field.required && <span className="text-status-error ml-0.5">*</span>}
              </label>
              <input
                type={field.type === "secret" ? "password" : "text"}
                value={values[field.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
                className={inputCls}
                placeholder={field.placeholder ?? field.label}
              />
              {field.help_text && (
                <p className="text-[10px] text-text-muted mt-1">{field.help_text}</p>
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save Credential"}
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

const inputCls =
  "w-full bg-surface text-text-primary text-xs px-2.5 py-1.5 rounded border border-border " +
  "placeholder-text-muted focus:outline-none focus:border-accent/60 transition-colors";
