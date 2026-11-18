from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from agentops_api.db.base import Base, IdMixin, TimestampMixin


class PromptVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = 'prompt_versions'
    __table_args__ = (UniqueConstraint('agent_id', 'version', name='uq_prompt_agent_version'), Index('ix_prompts_owner_agent', 'user_id', 'agent_id'))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    regression_threshold: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default='', nullable=False)
