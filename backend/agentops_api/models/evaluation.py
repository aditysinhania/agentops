from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentops_api.db.base import Base, IdMixin, TimestampMixin


class EvalRun(IdMixin, TimestampMixin, Base):
    __tablename__ = 'evaluation_runs'
    __table_args__ = (Index('ix_eval_runs_owner_created', 'user_id', 'created_at'), Index('ix_eval_runs_status', 'status'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id', ondelete='SET NULL'), nullable=True)
    prompt_version_id: Mapped[str | None] = mapped_column(ForeignKey('prompt_versions.id', ondelete='SET NULL'), nullable=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='queued', nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    results = relationship('EvalResult', back_populates='run', cascade='all, delete-orphan')


class EvalResult(IdMixin, TimestampMixin, Base):
    __tablename__ = 'evaluation_results'
    __table_args__ = (Index('ix_eval_results_run', 'run_id'),)
    run_id: Mapped[str] = mapped_column(ForeignKey('evaluation_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey('dataset_cases.id', ondelete='CASCADE'), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default='', nullable=False)
    run = relationship('EvalRun', back_populates='results')
