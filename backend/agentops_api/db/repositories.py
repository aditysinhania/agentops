"""Ownership-scoped database reads shared by API route modules."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agentops_api.models.agent import Agent
from agentops_api.models.dataset import Dataset, DatasetCase
from agentops_api.models.evaluation import EvalRun


def find_owned_agent(db: Session, user_id: str, agent_id: str) -> Agent | None:
    return db.scalar(select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id))


def find_owned_dataset(db: Session, user_id: str, dataset_id: str, *, include_cases: bool = False) -> Dataset | None:
    stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id)
    if include_cases:
        stmt = stmt.options(selectinload(Dataset.cases))
    return db.scalar(stmt)


def find_dataset_case(db: Session, dataset_id: str, case_id: str) -> DatasetCase | None:
    return db.scalar(select(DatasetCase).where(DatasetCase.dataset_id == dataset_id, DatasetCase.id == case_id))


def find_owned_evaluation(db: Session, user_id: str, run_id: str) -> EvalRun | None:
    stmt = select(EvalRun).options(selectinload(EvalRun.results)).where(EvalRun.id == run_id, EvalRun.user_id == user_id)
    return db.scalar(stmt)
