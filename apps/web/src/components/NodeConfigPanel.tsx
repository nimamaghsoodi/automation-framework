import { useEffect, useState } from "react";
import type { Node } from "@xyflow/react";
import { cn } from "../lib/utils";
import type { Credential } from "../lib/api";

interface SchemaProperty {
  type: string;
  title?: string;
  description?: string;
  default?: unknown;
  enum?: string[];
}

interface ActionManifest {
  key: string;
  name: string;
  description?: string;
  input_schema: { properties: Record<string, SchemaProperty>; required?: string[] };
}

interface ConnectorManifest {
  key: string;
  name: string;
  actions: ActionManifest[];
  triggers: { key: string; name: string }[];
}

interface Props {
  node: Node;
  onUpdate: (id: string, data: Record<string, unknown>) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

export default function NodeConfigPanel({ node, onUpdate, onDelete, onClose }: Props) {
  const nodeType = (node.data.nodeType as string) ?? "action";
  const connectorKey = node.data.connectorKey as string | undefined;

  const [manifest, setManifest] = useState<ConnectorManifest | null>(null);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [config, setConfig] = useState<Record<string, unknown>>({
    ...(node.data.config as object ?? {}),
    label: node.data.label,
    action_key: node.data.actionKey,
    credential_instance_id: node.data.credentialInstanceId,
  });

  useEffect(() => {
    if (!connectorKey) return;
    fetch(`/api/v1/connectors/${connectorKey}/manifest`)
      .then((r) => r.json())
      .then(setManifest)
      .catch(console.error);
    fetch("/api/v1/credentials/")
      .then((r) => r.json())
      .then(setCredentials)
      .catch(console.error);
  }, [connectorKey]);

  const selectedAction = manifest?.actions.find((a) => a.key === config.action_key);
  const schemaProps = selectedAction?.input_schema?.properties ?? {};
  const requiredFields = selectedAction?.input_schema?.required ?? [];

  function set(key: string, value: unknown) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function handleApply() {
    onUpdate(node.id, {
      ...node.data,
      label: config.label ?? node.data.label,
      actionKey: config.action_key,
      credentialInstanceId: config.credential_instance_id,
      config: config,
    });
  }

  const actionOptions = nodeType === "trigger"
    ? (manifest?.triggers ?? [])
    : (manifest?.actions ?? []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">
            {nodeType} config
          </div>
          <div className="text-sm font-medium text-text-primary mt-0.5">
            {connectorKey ?? "No connector"}
          </div>
        </div>
        <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors text-lg leading-none">×</button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Label */}
        <Field label="Label">
          <input
            type="text"
            value={(config.label as string) ?? ""}
            onChange={(e) => set("label", e.target.value)}
            className={inputCls}
            placeholder="Node label"
          />
        </Field>

        {/* Action / Trigger selector */}
        {manifest && (
          <Field label={nodeType === "trigger" ? "Trigger" : "Action"}>
            <select
              value={(config.action_key as string) ?? ""}
              onChange={(e) => set("action_key", e.target.value)}
              className={inputCls}
            >
              <option value="">— select —</option>
              {actionOptions.map((a) => (
                <option key={a.key} value={a.key}>{a.name}</option>
              ))}
            </select>
          </Field>
        )}

        {/* Credential selector for actions */}
        {nodeType === "action" && credentials.length > 0 && (
          <Field label="Credential">
            <select
              value={(config.credential_instance_id as string) ?? ""}
              onChange={(e) => set("credential_instance_id", e.target.value)}
              className={inputCls}
            >
              <option value="">— none —</option>
              {credentials.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </Field>
        )}

        {/* Dynamic action input fields */}
        {selectedAction && Object.entries(schemaProps).map(([key, prop]) => {
          // Skip internal fields managed by the engine
          if (["action_key", "credential_instance_id"].includes(key)) return null;
          const isRequired = requiredFields.includes(key);
          const label = prop.title ?? key;
          const val = (config[key] ?? prop.default ?? "") as string;

          if (prop.enum) {
            return (
              <Field key={key} label={label} required={isRequired}>
                <select value={val} onChange={(e) => set(key, e.target.value)} className={inputCls}>
                  <option value="">— select —</option>
                  {prop.enum.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                </select>
                {prop.description && <p className="text-[10px] text-text-muted mt-1">{prop.description}</p>}
              </Field>
            );
          }

          if (prop.type === "boolean") {
            return (
              <Field key={key} label={label}>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(config[key] ?? prop.default)}
                    onChange={(e) => set(key, e.target.checked)}
                    className="accent-accent"
                  />
                  <span className="text-xs text-text-secondary">{prop.description ?? label}</span>
                </label>
              </Field>
            );
          }

          if (prop.type === "object") {
            return (
              <Field key={key} label={label} required={isRequired}>
                <textarea
                  value={typeof config[key] === "object" ? JSON.stringify(config[key], null, 2) : (config[key] as string ?? "{}")}
                  onChange={(e) => { try { set(key, JSON.parse(e.target.value)); } catch { set(key, e.target.value); } }}
                  className={cn(inputCls, "font-mono text-[11px] min-h-[80px] resize-y")}
                  placeholder="{}"
                />
                {prop.description && <p className="text-[10px] text-text-muted mt-1">{prop.description}</p>}
              </Field>
            );
          }

          return (
            <Field key={key} label={label} required={isRequired}>
              <input
                type="text"
                value={val}
                onChange={(e) => set(key, e.target.value)}
                className={inputCls}
                placeholder={prop.description ?? label}
              />
            </Field>
          );
        })}

        {/* Condition expression */}
        {nodeType === "condition" && (
          <Field label="Expression">
            <textarea
              value={(config.expression as string) ?? ""}
              onChange={(e) => set("expression", e.target.value)}
              className={cn(inputCls, "font-mono text-[11px] min-h-[60px] resize-y")}
              placeholder='e.g. trigger["body"]["status"] == "open"'
            />
            <p className="text-[10px] text-text-muted mt-1">
              Python expression evaluated with node outputs in scope.
            </p>
          </Field>
        )}

        {/* Transform mapping */}
        {nodeType === "transform" && (
          <Field label="Output Mapping (JSON)">
            <textarea
              value={typeof config.mapping === "object" ? JSON.stringify(config.mapping, null, 2) : (config.mapping as string ?? "{}")}
              onChange={(e) => { try { set("mapping", JSON.parse(e.target.value)); } catch { set("mapping", e.target.value); } }}
              className={cn(inputCls, "font-mono text-[11px] min-h-[100px] resize-y")}
              placeholder='{"output_key": "trigger[\"body\"][\"id\"]"}'
            />
          </Field>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-border shrink-0">
        <button
          onClick={handleApply}
          className="flex-1 py-1.5 text-xs font-medium bg-accent text-white rounded hover:bg-accent-hover transition-colors"
        >
          Apply
        </button>
        <button
          onClick={() => onDelete(node.id)}
          className="px-3 py-1.5 text-xs text-status-error border border-red-900/50 rounded hover:bg-red-950/30 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-text-secondary mb-1">
        {label}{required && <span className="text-status-error ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls =
  "w-full bg-surface text-text-primary text-xs px-2.5 py-1.5 rounded border border-border " +
  "placeholder-text-muted focus:outline-none focus:border-accent/60 transition-colors";
