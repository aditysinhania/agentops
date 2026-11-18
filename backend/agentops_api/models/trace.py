from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentops_api.db.base import Base, IdMixin, TimestampMixin, utcnow


class Trace(IdMixin, TimestampMixin, Base):
    __tablename__ = 'traces'
    __table_args__ = (
        UniqueConstraint('user_id', 'trace_id', name='uq_trace_user_trace_id'),
        Index('ix_traces_owner_started', 'user_id', 'started_at'),
        Index('ix_traces_agent_status', 'agent_id', 'status'),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), default='agent.run', nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='success', nullable=False)
    input: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    metadata_json: Mapped[dict] = mapped_column('metadata', JSON, default=dict, nullable=False)
    agent = relationship('Agent', back_populates='traces')
    spans = relationship('Span', back_populates='trace', cascade='all, delete-orphan', order_by='Span.started_at')


class Span(IdMixin, TimestampMixin, Base):
    __tablename__ = 'spans'
    __table_args__ = (Index('ix_spans_trace_parent', 'trace_pk', 'parent_span_id'),)
    trace_pk: Mapped[str] = mapped_column(ForeignKey('traces.id', ondelete='CASCADE'), nullable=False, index=True)
    span_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default='agent', nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='success', nullable=False)
    input: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    trace = relationship('Trace', back_populates='spans')
