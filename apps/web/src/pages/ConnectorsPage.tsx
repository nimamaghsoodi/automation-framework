import { useEffect, useState } from "react";
import { api, type Connector, type Credential } from "../lib/api";
import AddCredentialModal from "../components/AddCredentialModal";

// Simple Icons CDN slugs + brand colors for known connectors
const CONNECTOR_META: Record<string, { slug: string; color: string }> = {
  aws:        { slug: "amazonaws",       color: "FF9900" },
  jira:       { slug: "jira",            color: "0052CC" },
  teams:      { slug: "microsoftteams",  color: "6264A7" },
  zendesk:    { slug: "zendesk",         color: "03363D" },
  kubernetes: { slug: "kubernetes",      color: "326CE5" },
  postgres:   { slug: "postgresql",      color: "4169E1" },
};

function ConnectorIcon({ connectorKey, size = 36 }: { connectorKey: string; size?: number }) {
  const meta = CONNECTOR_META[connectorKey];
  if (meta) {
    return (
      <img
        src={`https://cdn.simpleicons.org/${meta.slug}/${meta.color}`}
        alt={connectorKey}
        width={size}
        height={size}
        className="object-contain"
      />
    );
  }
  // Fallback generic icons
  if (connectorKey === "webhook") return <WebhookIcon size={size} />;
  return <HttpIcon size={size} />;
}

function WebhookIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
      <path d="M12 7c0 3-4 5-4 8h8c0-3-4-5-4-8z" />
      <path d="M8 19h8" />
    </svg>
  );
}

function HttpIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <path d="M6 10h2m0 0v4m0-4h2M14 10v4m0-4h2m0 0v4" />
    </svg>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  cloud: "Cloud",
  ticketing: "Ticketing",
  communication: "Communication",
  devops: "DevOps",
  database: "Database",
  trigger: "Trigger",
  generic: "Generic",
};

const CATEGORY_COLORS: Record<string, string> = {
  cloud:         "bg-orange-900/40 text-orange-300",
  ticketing:     "bg-blue-900/40 text-blue-300",
  communication: "bg-purple-900/40 text-purple-300",
  devops:        "bg-sky-900/40 text-sky-300",
  database:      "bg-emerald-900/40 text-emerald-300",
  trigger:       "bg-indigo-900/40 text-indigo-300",
  generic:       "bg-zinc-800 text-zinc-400",
};

interface ConnectorWithCreds extends Connector {
  credCount: number;
}

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<ConnectorWithCreds[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectTarget, setConnectTarget] = useState<Connector | null>(null);

  async function load() {
    const [cs, creds] = await Promise.all([
      api.connectors.list(),
      api.credentials.list().catch((): Credential[] => []),
    ]);
    const credsByConnector: Record<string, number> = {};
    for (const c of creds) {
      credsByConnector[c.connector_id] = (credsByConnector[c.connector_id] ?? 0) + 1;
    }
    setConnectors(cs.map((c) => ({ ...c, credCount: credsByConnector[c.id] ?? 0 })));
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-xl font-semibold">Connectors</h1>
        <p className="text-sm text-text-secondary mt-1">
          Click a connector to add credentials and start using it in your flows.
        </p>
      </div>

      {loading ? (
        <div className="text-text-muted text-sm">Loading connectors…</div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {connectors.map((c) => (
            <ConnectorCard
              key={c.id}
              connector={c}
              onConnect={() => setConnectTarget(c)}
            />
          ))}
        </div>
      )}

      {connectTarget && (
        <AddCredentialModal
          initialConnector={connectTarget}
          onClose={() => setConnectTarget(null)}
          onCreated={() => {
            setConnectTarget(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function ConnectorCard({
  connector,
  onConnect,
}: {
  connector: ConnectorWithCreds;
  onConnect: () => void;
}) {
  return (
    <div className="flex flex-col p-5 rounded-xl border border-border bg-surface-raised hover:border-accent/40 transition-all group">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 flex items-center justify-center rounded-lg bg-surface p-1.5">
          <ConnectorIcon connectorKey={connector.key} size={28} />
        </div>
        {connector.credCount > 0 && (
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-900/40 text-emerald-400">
            {connector.credCount} connected
          </span>
        )}
      </div>

      <div className="flex-1">
        <div className="font-medium text-text-primary text-sm">{connector.name}</div>
        <span
          className={`inline-block mt-1.5 text-[10px] font-medium px-2 py-0.5 rounded-full ${
            CATEGORY_COLORS[connector.category] ?? CATEGORY_COLORS.generic
          }`}
        >
          {CATEGORY_LABELS[connector.category] ?? connector.category}
        </span>
        {connector.description && (
          <p className="text-[11px] text-text-secondary mt-2.5 leading-relaxed line-clamp-2">
            {connector.description}
          </p>
        )}
      </div>

      <button
        onClick={onConnect}
        className="mt-4 w-full py-1.5 text-xs font-medium rounded-lg border border-border text-text-secondary
          hover:border-accent hover:text-accent hover:bg-accent/5 transition-all"
      >
        {connector.credCount > 0 ? "Add another connection" : "Connect"}
      </button>
    </div>
  );
}
