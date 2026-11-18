from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from agentops_api.db.base import Base, IdMixin, TimestampMixin


class Dataset(IdMixin, TimestampMixin, Base):
    __tablename__ = 'datasets'
    __table_args__ = (Index('ix_datasets_owner_created', 'user_id', 'created_at'),)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    cases = relationship('DatasetCase', back_populates='dataset', cascade='all, delete-orphan', order_by='DatasetCase.created_at')


class DatasetCase(IdMixin, TimestampMixin, Base):
    __tablename__ = 'dataset_cases'
    __table_args__ = (Index('ix_dataset_cases_dataset', 'dataset_id'),)
    dataset_id: Mapped[str] = mapped_column(ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False, index=True)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_tool: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actual_tool: Mapped[str | None] = mapped_column(String(120), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict] = mapped_column('metadata', JSON, default=dict, nullable=False)
    dataset = relationship('Dataset', back_populates='cases')
