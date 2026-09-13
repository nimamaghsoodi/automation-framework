import { useEffect, useRef } from "react";
import { useFlowBuilderStore } from "../store/flowBuilderStore";

export function useRunStatus(runId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const { updateNodeRunState, setActiveRun } = useFlowBuilderStore();

  useEffect(() => {
    if (!runId) return;

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/runs/${runId}`);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data as string);

        if (payload.event === "step_update" && payload.node_id) {
          updateNodeRunState(payload.node_id, {
            status: payload.step_status,
            error: payload.error ?? undefined,
            duration_ms: payload.duration_ms ?? undefined,
          });
        }

        if (payload.event === "run_finished") {
          setActiveRun(null);
          ws.close();
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => ws.close();

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [runId, updateNodeRunState, setActiveRun]);
}
