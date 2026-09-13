import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { api, type Flow, type Run } from "../lib/api";
import NexusNode from "../components/NexusNode";
import NodeConfigPanel from "../components/NodeConfigPanel";
import ConnectorPalette from "../components/ConnectorPalette";
import RunModal from "../components/RunModal";
import { useFlowBuilderStore } from "../store/flowBuilderStore";
import { useRunStatus } from "../hooks/useRunStatus";
import { cn } from "../lib/utils";

const nodeTypes = { nexus: NexusNode };

function toRfNode(n: { id: string; type: string; connector_key?: string; config_json: Record<string, unknown>; position: { x: number; y: number } }): Node {
  return {
    id: n.id,
    type: "nexus",
    position: n.position,
    data: {
      label: (n.config_json.label as string) ?? n.type,
      nodeType: n.type,
      connectorKey: n.connector_key,
      actionKey: n.config_json.action_key,
      credentialInstanceId: n.config_json.credential_instance_id,
      config: n.config_json,
    },
  };
}

function toRfEdge(e: { id: string; source: string; target: string }): Edge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    style: { stroke: "#6366f1", strokeWidth: 1.5 },
    animated: false,
  };
}

export default function FlowBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [flow, setFlow] = useState<Flow | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const nodeIdCounter = useRef(1);

  const {
    selectedNodeId,
    isPanelOpen,
    isPaletteOpen,
    runModalOpen,
    activeRunId,
    selectNode,
    closePanel,
    togglePalette,
    openRunModal,
    closeRunModal,
    setActiveRun,
    resetRunStates,
  } = useFlowBuilderStore();

  useRunStatus(activeRunId);

  useEffect(() => {
    if (!id) return;
    api.flows.get(id).then((f) => {
      setFlow(f);
      setNodes(f.graph_json.nodes.map(toRfNode));
      setEdges(f.graph_json.edges.map(toRfEdge));
    });
  }, [id]);

  const onConnect = useCallback(
    (connection: Connection) =>
      setEdges((eds) =>
        addEdge({ ...connection, style: { stroke: "#6366f1", strokeWidth: 1.5 } }, eds)
      ),
    [setEdges]
  );

  const onNodeClick: NodeMouseHandler = useCallback((_evt, node) => {
    selectNode(node.id);
  }, [selectNode]);

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  function addNode(connectorKey: string, connectorName: string, nodeType: "trigger" | "action") {
    const id = `node-${Date.now()}-${nodeIdCounter.current++}`;
    const newNode: Node = {
      id,
      type: "nexus",
      position: { x: 200 + Math.random() * 200, y: 100 + Math.random() * 200 },
      data: {
        label: connectorName,
        nodeType,
        connectorKey,
        actionKey: undefined,
        credentialInstanceId: undefined,
        config: {},
      },
    };
    setNodes((nds) => [...nds, newNode]);
  }

  function updateNodeData(nodeId: string, data: Record<string, unknown>) {
    setNodes((nds) => nds.map((n) => n.id === nodeId ? { ...n, data } : n));
    setStatus("Unsaved changes");
  }

  function deleteNode(nodeId: string) {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    selectNode(null);
  }

  function setStatus(msg: string) {
    setStatusMsg(msg);
    if (msg !== "Unsaved changes") setTimeout(() => setStatusMsg(""), 2500);
  }

  async function handleSave() {
    if (!flow) return;
    setSaving(true);
    try {
      const apiNodes = nodes.map((n) => ({
        id: n.id,
        type: (n.data.nodeType as string) ?? "action",
        connector_key: (n.data.connectorKey as string) ?? undefined,
        config_json: {
          label: n.data.label,
          action_key: n.data.actionKey,
          credential_instance_id: n.data.credentialInstanceId,
          ...(n.data.config as object ?? {}),
        },
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
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function handleRunStarted(run: Run) {
    resetRunStates();
    setActiveRun(run.id);
    closeRunModal();
    setStatus(`Run ${run.id.slice(0, 8)}… started`);
  }

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-surface-raised shrink-0">
        <button
          onClick={() => navigate("/")}
          className="text-text-muted hover:text-text-primary text-sm transition-colors"
        >
          ← Flows
        </button>
        <div className="w-px h-4 bg-border" />
        <div className="flex-1">
          <span className="font-medium text-text-primary">{flow?.name ?? "…"}</span>
          {flow && <span className="ml-2 text-xs text-text-muted">v{flow.version} · {flow.status}</span>}
        </div>
        {statusMsg && <span className="text-xs text-text-secondary">{statusMsg}</span>}
        <button
          onClick={togglePalette}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded border transition-colors",
            isPaletteOpen
              ? "border-accent/50 text-accent"
              : "border-border text-text-secondary hover:text-text-primary"
          )}
        >
          Connectors
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1.5 text-xs font-medium rounded border border-border text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={openRunModal}
          className="px-3 py-1.5 text-xs font-medium rounded bg-accent text-white hover:bg-accent-hover transition-colors"
        >
          ▶ Run
        </button>
      </div>

      {/* Canvas area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Connector palette */}
        {isPaletteOpen && (
          <div className="w-52 shrink-0 border-r border-border bg-surface-raised overflow-hidden flex flex-col">
            <div className="px-3 py-2 border-b border-border">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">Add Node</span>
            </div>
            <ConnectorPalette onAddNode={addNode} />
          </div>
        )}

        {/* React Flow canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            fitView
            colorMode="dark"
            deleteKeyCode="Delete"
          >
            <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#2a2f45" />
            <Controls />
            <MiniMap nodeColor="#6366f1" maskColor="rgba(15,17,23,0.8)" />
          </ReactFlow>
        </div>

        {/* Node config panel */}
        {isPanelOpen && selectedNode && (
          <div className="w-72 shrink-0 border-l border-border bg-surface-raised overflow-hidden flex flex-col">
            <NodeConfigPanel
              node={selectedNode}
              onUpdate={updateNodeData}
              onDelete={deleteNode}
              onClose={closePanel}
            />
          </div>
        )}
      </div>

      {/* Run modal */}
      {runModalOpen && flow && (
        <RunModal
          flowId={flow.id}
          onClose={closeRunModal}
          onRunStarted={handleRunStarted}
        />
      )}
    </div>
  );
}
