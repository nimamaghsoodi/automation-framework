"""
Flow CRUD endpoints.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.flow import Flow, FlowEdge, FlowNode
from app.worker.dag import validate_graph, DAGValidationError

router = APIRouter(prefix="/flows", tags=["flows"])


# --- Schemas ---

class FlowNodeIn(BaseModel):
    id: str
    type: str
    connector_key: str | None = None
    config_json: dict[str, Any] = {}
    position: dict[str, float] = {}


class FlowEdgeIn(BaseModel):
    id: str
    source: str
    target: str
    condition_expr: str | None = None


class FlowCreateRequest(BaseModel):
    name: str
    description: str | None = None
    nodes: list[FlowNodeIn] = []
    edges: list[FlowEdgeIn] = []


class FlowUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    nodes: list[FlowNodeIn] | None = None
    edges: list[FlowEdgeIn] | None = None


class FlowResponse(BaseModel):
    id: str
    name: str
    description: str | None
    version: int
    status: str
    graph_json: dict[str, Any]

    model_config = {"from_attributes": True}


# --- Helpers ---

def _build_graph_json(nodes: list[FlowNodeIn], edges: list[FlowEdgeIn]) -> dict[str, Any]:
    return {
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }


# --- Routes ---

@router.get("/", response_model=list[FlowResponse])
async def list_flows(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Flow).order_by(Flow.created_at.desc()))
    return rows.scalars().all()


@router.post("/", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
async def create_flow(body: FlowCreateRequest, db: AsyncSession = Depends(get_db)):
    graph = _build_graph_json(body.nodes, body.edges)
    if body.nodes:
        try:
            validate_graph(graph)
        except DAGValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # Placeholder owner — replace with current user once auth middleware is wired
    placeholder_owner = uuid.uuid4()
    flow = Flow(
        name=body.name,
        description=body.description,
        graph_json=graph,
        created_by=placeholder_owner,
    )
    db.add(flow)
    await db.flush()

    for n in body.nodes:
        db.add(FlowNode(
            id=uuid.UUID(n.id) if _is_valid_uuid(n.id) else uuid.uuid4(),
            flow_id=flow.id,
            type=n.type,
            config_json=n.config_json,
            position=n.position,
        ))
    for e in body.edges:
        db.add(FlowEdge(
            id=uuid.UUID(e.id) if _is_valid_uuid(e.id) else uuid.uuid4(),
            flow_id=flow.id,
            source_node_id=uuid.UUID(e.source),
            target_node_id=uuid.UUID(e.target),
            condition_expr=e.condition_expr,
        ))

    await db.commit()
    await db.refresh(flow)
    return flow


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(flow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    flow = await db.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.patch("/{flow_id}", response_model=FlowResponse)
async def update_flow(flow_id: uuid.UUID, body: FlowUpdateRequest, db: AsyncSession = Depends(get_db)):
    flow = await db.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    if body.name is not None:
        flow.name = body.name
    if body.description is not None:
        flow.description = body.description
    if body.status is not None:
        flow.status = body.status

    if body.nodes is not None and body.edges is not None:
        graph = _build_graph_json(body.nodes, body.edges)
        try:
            validate_graph(graph)
        except DAGValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        flow.graph_json = graph
        flow.version += 1

        # Replace nodes and edges (cascade delete handles old rows)
        existing_nodes = await db.execute(select(FlowNode).where(FlowNode.flow_id == flow_id))
        for node in existing_nodes.scalars():
            await db.delete(node)
        existing_edges = await db.execute(select(FlowEdge).where(FlowEdge.flow_id == flow_id))
        for edge in existing_edges.scalars():
            await db.delete(edge)

        for n in body.nodes:
            db.add(FlowNode(
                id=uuid.UUID(n.id) if _is_valid_uuid(n.id) else uuid.uuid4(),
                flow_id=flow.id,
                type=n.type,
                config_json=n.config_json,
                position=n.position,
            ))
        for e in body.edges:
            db.add(FlowEdge(
                id=uuid.UUID(e.id) if _is_valid_uuid(e.id) else uuid.uuid4(),
                flow_id=flow.id,
                source_node_id=uuid.UUID(e.source),
                target_node_id=uuid.UUID(e.target),
                condition_expr=e.condition_expr,
            ))

    await db.commit()
    await db.refresh(flow)
    return flow


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(flow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    flow = await db.get(Flow, flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await db.delete(flow)
    await db.commit()


def _is_valid_uuid(v: str) -> bool:
    try:
        uuid.UUID(v)
        return True
    except ValueError:
        return False
