from sqlalchemy import Boolean, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentops_api.db.base import Base, IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_json: Mapped[dict] = mapped_column('settings', JSON, default=dict, nullable=False)
    agents = relationship('Agent', back_populates='owner', cascade='all, delete-orphan')
    api_keys = relationship('ApiKey', back_populates='owner', cascade='all, delete-orphan')


class ApiKey(IdMixin, TimestampMixin, Base):
    __tablename__ = 'api_keys'
    __table_args__ = (Index('ix_api_keys_owner_active', 'user_id', 'active'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    owner = relationship('User', back_populates='api_keys')
