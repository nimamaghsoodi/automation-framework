import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Flow(Base):
    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full graph snapshot — nodes + edges embedded; FlowNode/FlowEdge rows are source of truth
    graph_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|active|paused
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    nodes = relationship("FlowNode", back_populates="flow", cascade="all, delete-orphan")
    edges = relationship("FlowEdge", back_populates="flow", cascade="all, delete-orphan")
    creator = relationship("User", lazy="select")


class FlowNode(Base):
    __tablename__ = "flow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # trigger|action|condition|transform
    connector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("connectors.id"), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    position: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # {x, y}

    flow = relationship("Flow", back_populates="nodes")
    connector = relationship("Connector", lazy="joined")


class FlowEdge(Base):
    __tablename__ = "flow_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flows.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False)
    condition_expr: Mapped[str | None] = mapped_column(Text, nullable=True)

    flow = relationship("Flow", back_populates="edges")
    source_node = relationship("FlowNode", foreign_keys=[source_node_id], lazy="select")
    target_node = relationship("FlowNode", foreign_keys=[target_node_id], lazy="select")
