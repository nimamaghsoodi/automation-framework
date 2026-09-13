import { useEffect, useState } from "react";
import { api, type Connector, type Credential } from "../lib/api";

interface CredentialField {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string;
  help_text?: string;
}

interface Props {
  onClose: () => void;
  onCreated: (cred: Credential) => void;
  /** When supplied the connector selector is hidden and this connector is pre-selected. */
  initialConnector?: Connector | null;
}

export default function AddCredentialModal({ onClose, onCreated, initialConnector }: Props) {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(
    initialConnector ?? null
  );
  const [fields, setFields] = useState<CredentialField[]>([]);
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only fetch full list when no initial connector provided
  useEffect(() => {
    if (!initialConnector) {
      api.connectors.list().then(setConnectors).catch(console.error);
    }
  }, [initialConnector]);

  // Load fields whenever selected connector changes
  useEffect(() => {
    if (!selectedConnector) { setFields([]); return; }
    setValues({});
    fetch(`/api/v1/connectors/${selectedConnector.key}/manifest`)
      .then((r) => r.json())
      .then((manifest) => setFields(manifest?.auth?.fields ?? []))
      .catch(() => setFields([]));
  }, [selectedConnector?.key]);

  async function handleSubmit() {
    if (!selectedConnector || !name.trim()) {
      setError("Connection name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const cred = await api.credentials.create({
        connector_id: selectedConnector.id,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-surface-raised border border-border rounded-xl w-[460px] max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h2 className="font-semibold text-text-primary">
              {initialConnector ? `Connect ${initialConnector.name}` : "Add Credential"}
            </h2>
            {initialConnector && (
              <p className="text-xs text-text-muted mt-0.5">
                Credentials are encrypted and never returned after creation
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary text-xl leading-none transition-colors"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          {error && (
            <p className="text-xs text-status-error bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Connector selector — only shown when no initialConnector */}
          {!initialConnector && (
            <div>
              <label className={labelCls}>Connector</label>
              <select
                value={selectedConnector?.id ?? ""}
                onChange={(e) => {
                  const c = connectors.find((x) => x.id === e.target.value) ?? null;
                  setSelectedConnector(c);
                }}
                className={inputCls}
              >
                <option value="">— select connector —</option>
                {connectors.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Connection name */}
          <div>
            <label className={labelCls}>Connection name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
              placeholder={
                initialConnector
                  ? `e.g. Production ${initialConnector.name}`
                  : "e.g. My Jira Workspace"
              }
              autoFocus
            />
          </div>

          {/* Auth fields from manifest */}
          {fields.length > 0 && (
            <div className="space-y-4 pt-1">
              <div className="text-xs font-semibold text-text-muted uppercase tracking-widest">
                Authentication
              </div>
              {fields.map((field) => (
                <div key={field.name}>
                  <label className={labelCls}>
                    {field.label}
                    {field.required && <span className="text-status-error ml-0.5">*</span>}
                  </label>
                  <input
                    type={field.type === "secret" ? "password" : "text"}
                    value={values[field.name] ?? ""}
                    onChange={(e) =>
                      setValues((v) => ({ ...v, [field.name]: e.target.value }))
                    }
                    className={inputCls}
                    placeholder={field.placeholder ?? field.label}
                    autoComplete="off"
                  />
                  {field.help_text && (
                    <p className="text-[11px] text-text-muted mt-1">{field.help_text}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {selectedConnector && fields.length === 0 && (
            <p className="text-xs text-text-muted italic">
              This connector requires no additional authentication fields.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={handleSubmit}
            disabled={saving || !selectedConnector}
            className="flex-1 py-2 text-sm font-medium bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save & Connect"}
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
  "placeholder-text-muted focus:outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/20 transition-colors";
