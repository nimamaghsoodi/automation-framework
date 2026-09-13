import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  type Connection,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, type Flow } from "../lib/api";
import NexusNode from "../components/NexusNode";

const nodeTypes = { nexus: NexusNode };

export default function FlowBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const [flow, setFlow] = useState<Flow | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    if (!id) return;
    api.flows.get(id).then((f) => {
      setFlow(f);
      const rfNodes: Node[] = f.graph_json.nodes.map((n) => ({
        id: n.id,
        type: "nexus",
        position: n.position,
        data: { label: n.config_json.label ?? n.type, nodeType: n.type, connectorKey: n.connector_key },
      }));
      const rfEdges: Edge[] = f.graph_json.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        style: { stroke: "#6366f1", strokeWidth: 1.5 },
        animated: false,
      }));
      setNodes(rfNodes);
      setEdges(rfEdges);
    });
  }, [id]);

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge({ ...connection, style: { stroke: "#6366f1", strokeWidth: 1.5 } }, eds)
      ),
    [setEdges]
  );

  async function handleSave() {
    if (!flow) return;
    setSaving(true);
    try {
      const apiNodes = nodes.map((n) => ({
        id: n.id,
        type: (n.data.nodeType as string) ?? "action",
        connector_key: (n.data.connectorKey as string) ?? undefined,
        config_json: { label: n.data.label, ...(n.data.config as object ?? {}) },
        position: n.position,
      }));
      const apiEdges = edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        condition_expr: undefined,
      }));
      const updated = await api.flows.update(flow.id, { nodes: apiNodes, edges: apiEdges });
      setFlow(updated);
      setStatus("Saved");
      setTimeout(() => setStatus(""), 2000);
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleRun() {
    if (!flow) return;
    setRunning(true);
    try {
      const run = await api.runs.trigger(flow.id, {});
      setStatus(`Run started: ${run.id.slice(0, 8)}…`);
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-raised shrink-0">
        <div>
          <span className="font-medium text-text-primary">{flow?.name ?? "…"}</span>
          {flow && <span className="ml-2 text-xs text-text-muted">v{flow.version} · {flow.status}</span>}
        </div>
        <div className="flex items-center gap-3">
          {status && <span className="text-xs text-text-secondary">{status}</span>}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 text-xs font-medium rounded border border-border text-text-secondary hover:text-text-primary hover:border-border transition-colors disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            onClick={handleRun}
            disabled={running}
            className="px-3 py-1.5 text-xs font-medium rounded bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {running ? "Starting…" : "Run Now"}
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          colorMode="dark"
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#2a2f45" />
          <Controls />
          <MiniMap nodeColor="#6366f1" maskColor="rgba(15,17,23,0.8)" />
        </ReactFlow>
      </div>
    </div>
  );
}
