from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentops_api.db.base import Base, IdMixin, TimestampMixin


class Agent(IdMixin, TimestampMixin, Base):
    __tablename__ = 'agents'
    __table_args__ = (Index('ix_agents_owner_status', 'user_id', 'status'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    environment: Mapped[str] = mapped_column(String(40), default='production', nullable=False)
    framework: Mapped[str] = mapped_column(String(60), default='custom', nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active', nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner = relationship('User', back_populates='agents')
    traces = relationship('Trace', back_populates='agent', cascade='all, delete-orphan')
