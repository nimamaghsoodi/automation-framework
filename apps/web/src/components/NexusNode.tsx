import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "../lib/utils";
import { useFlowBuilderStore } from "../store/flowBuilderStore";
import type { RunStatus } from "../store/flowBuilderStore";

const typeColors: Record<string, string> = {
  trigger: "border-status-running",
  action: "border-border",
  condition: "border-status-warning",
  transform: "border-accent/50",
};

const typeBg: Record<string, string> = {
  trigger: "bg-blue-950/40",
  action: "bg-surface-raised",
  condition: "bg-yellow-950/20",
  transform: "bg-indigo-950/20",
};

const typeLabels: Record<string, string> = {
  trigger: "Trigger",
  action: "Action",
  condition: "Condition",
  transform: "Transform",
};

const statusRingColors: Record<RunStatus, string> = {
  idle: "bg-status-idle",
  running: "bg-status-running animate-pulse",
  success: "bg-status-success",
  failed: "bg-status-error",
};

export default function NexusNode({ id, data, selected }: NodeProps) {
  const { nodeRunStates } = useFlowBuilderStore();
  const nodeType = (data.nodeType as string) ?? "action";
  const label = (data.label as string) || typeLabels[nodeType] || "Node";
  const connector = data.connectorKey as string | undefined;
  const runState = nodeRunStates[id];
  const runStatus: RunStatus = runState?.status ?? "idle";

  return (
    <div
      className={cn(
        "px-4 py-3 rounded-lg border min-w-[180px] max-w-[260px] shadow-lg transition-all",
        typeColors[nodeType] ?? "border-border",
        typeBg[nodeType] ?? "bg-surface-raised",
        selected && "ring-2 ring-accent/60 ring-offset-1 ring-offset-surface"
      )}
    >
      {nodeType !== "trigger" && (
        <Handle
          type="target"
          position={Position.Top}
          className="!bg-accent !border-accent !w-2 !h-2"
        />
      )}

      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-0.5">
            {typeLabels[nodeType]}
            {connector && (
              <span className="text-accent/70 ml-1">· {connector}</span>
            )}
          </div>
          <div className="text-sm font-medium text-text-primary truncate">{label}</div>
          {runState?.error && (
            <div className="text-[10px] text-status-error mt-0.5 truncate">{runState.error}</div>
          )}
          {runState?.duration_ms != null && runStatus === "success" && (
            <div className="text-[10px] text-text-muted mt-0.5">{runState.duration_ms}ms</div>
          )}
        </div>
        <div
          className={cn(
            "w-2.5 h-2.5 rounded-full shrink-0 transition-colors",
            statusRingColors[runStatus]
          )}
        />
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-accent !border-accent !w-2 !h-2"
      />
    </div>
  );
}
