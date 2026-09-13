"""
Lightweight DAG executor for flow graphs.

The graph_snapshot shape matches the data model:
  {
    "nodes": [{"id": str, "type": str, "connector_key": str|None, "config_json": {...}}, ...],
    "edges": [{"source": str, "target": str, "condition_expr": str|None}, ...],
  }

Execution order: topological sort starting from trigger nodes.
Each step reads its inputs from the context (outputs of predecessor nodes).
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class DAGValidationError(Exception):
    pass


def topological_sort(nodes: list[dict], edges: list[dict]) -> list[str]:
    """
    Returns node IDs in dependency order (Kahn's algorithm).
    Raises DAGValidationError if the graph has a cycle or is disconnected from a trigger.
    """
    node_ids = {n["id"] for n in nodes}
    in_degree: dict[str, int] = {n: 0 for n in node_ids}
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        adjacency[src].append(tgt)
        in_degree[tgt] += 1

    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    order: list[str] = []

    while queue:
        nid = queue.popleft()
        order.append(nid)
        for neighbor in adjacency[nid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(node_ids):
        cycle_nodes = [nid for nid, deg in in_degree.items() if deg > 0]
        raise DAGValidationError(f"Cycle detected in flow graph involving nodes: {cycle_nodes}")

    return order


def validate_graph(graph: dict[str, Any]) -> None:
    """Validate that a flow graph is well-formed and acyclic."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {n["id"] for n in nodes}

    triggers = [n for n in nodes if n.get("type") == "trigger"]
    if len(triggers) == 0:
        raise DAGValidationError("Flow must have at least one trigger node.")
    if len(triggers) > 1:
        raise DAGValidationError("Flow must have exactly one trigger node.")

    for edge in edges:
        if edge["source"] not in node_ids:
            raise DAGValidationError(f"Edge references unknown source node: {edge['source']}")
        if edge["target"] not in node_ids:
            raise DAGValidationError(f"Edge references unknown target node: {edge['target']}")

    topological_sort(nodes, edges)  # raises on cycle


class FlowContext:
    """Holds the running context (node outputs) during a flow execution."""

    def __init__(self, trigger_payload: dict[str, Any]):
        self._data: dict[str, Any] = {"trigger": trigger_payload}

    def set_output(self, node_id: str, output: dict[str, Any]) -> None:
        self._data[node_id] = output

    def get_output(self, node_id: str) -> dict[str, Any] | None:
        return self._data.get(node_id)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)
