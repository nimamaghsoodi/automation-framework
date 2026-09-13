import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "../lib/utils";

const typeColors: Record<string, string> = {
  trigger: "border-status-running bg-blue-950/30",
  action: "border-border bg-surface-raised",
  condition: "border-status-warning bg-yellow-950/20",
  transform: "border-accent/50 bg-indigo-950/20",
};

const typeLabels: Record<string, string> = {
  trigger: "Trigger",
  action: "Action",
  condition: "Condition",
  transform: "Transform",
};

export default function NexusNode({ data }: NodeProps) {
  const nodeType = (data.nodeType as string) ?? "action";
  const label = (data.label as string) || typeLabels[nodeType] || "Node";
  const connector = data.connectorKey as string | undefined;

  return (
    <div
      className={cn(
        "px-4 py-3 rounded-lg border min-w-[160px] max-w-[240px] shadow-lg",
        typeColors[nodeType] ?? "border-border bg-surface-raised"
      )}
    >
      {nodeType !== "trigger" && (
        <Handle type="target" position={Position.Top} className="!bg-accent !border-accent/50" />
      )}

      <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-0.5">
            {typeLabels[nodeType]}
            {connector && ` · ${connector}`}
          </div>
          <div className="text-sm font-medium text-text-primary truncate">{label}</div>
        </div>
        {/* Status ring — idle by default; will show live state during run */}
        <div className="w-2 h-2 rounded-full bg-status-idle shrink-0" />
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-accent !border-accent/50" />
    </div>
  );
}
