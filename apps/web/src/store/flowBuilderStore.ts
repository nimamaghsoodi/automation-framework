import { create } from "zustand";
import type { FlowNode, FlowEdge } from "../lib/api";

export type RunStatus = "idle" | "running" | "success" | "failed";

interface NodeRunState {
  status: RunStatus;
  error?: string;
  duration_ms?: number;
}

interface FlowBuilderState {
  selectedNodeId: string | null;
  isPanelOpen: boolean;
  isPaletteOpen: boolean;
  runModalOpen: boolean;
  activeRunId: string | null;
  nodeRunStates: Record<string, NodeRunState>;

  selectNode: (id: string | null) => void;
  openPanel: () => void;
  closePanel: () => void;
  togglePalette: () => void;
  openRunModal: () => void;
  closeRunModal: () => void;
  setActiveRun: (runId: string | null) => void;
  updateNodeRunState: (nodeId: string, state: NodeRunState) => void;
  resetRunStates: () => void;
}

export const useFlowBuilderStore = create<FlowBuilderState>((set) => ({
  selectedNodeId: null,
  isPanelOpen: false,
  isPaletteOpen: true,
  runModalOpen: false,
  activeRunId: null,
  nodeRunStates: {},

  selectNode: (id) => set({ selectedNodeId: id, isPanelOpen: id !== null }),
  openPanel: () => set({ isPanelOpen: true }),
  closePanel: () => set({ isPanelOpen: false, selectedNodeId: null }),
  togglePalette: () => set((s) => ({ isPaletteOpen: !s.isPaletteOpen })),
  openRunModal: () => set({ runModalOpen: true }),
  closeRunModal: () => set({ runModalOpen: false }),
  setActiveRun: (runId) => set({ activeRunId: runId }),
  updateNodeRunState: (nodeId, state) =>
    set((s) => ({ nodeRunStates: { ...s.nodeRunStates, [nodeId]: state } })),
  resetRunStates: () => set({ nodeRunStates: {} }),
}));
