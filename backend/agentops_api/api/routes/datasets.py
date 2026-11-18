import csv
import io
import json
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.orm import Session, selectinload
from agentops_api.auth.dependencies import get_current_user
from agentops_api.db.session import get_db
from agentops_api.db.repositories import find_dataset_case, find_owned_dataset
from agentops_api.models.dataset import Dataset, DatasetCase
from agentops_api.models.evaluation import EvalResult, EvalRun
from agentops_api.models.user import User
from agentops_api.schemas.entities import CaseCreate, CaseUpdate, DatasetCreate, DatasetUpdate

router = APIRouter(prefix='/datasets', tags=['datasets'])
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_CASES = 1000
CASE_FIELDS = ('id', 'dataset_id', 'input', 'expected_output', 'actual_output', 'reference_context', 'expected_tool', 'actual_tool', 'instructions', 'structured_schema', 'metadata_json', 'created_at')


def _case_out(case: DatasetCase) -> dict:
    return {field: getattr(case, field) for field in CASE_FIELDS}


def _dataset_out(dataset: Dataset, *, include_cases: bool = True) -> dict:
    result = {key: getattr(dataset, key) for key in ('id', 'name', 'description', 'created_at', 'updated_at')}
    result['cases'] = [_case_out(case) for case in dataset.cases] if include_cases else []
    return result


def owned_dataset(db: Session, user_id: str, dataset_id: str, include_cases: bool = False) -> Dataset:
    dataset = find_owned_dataset(db, user_id, dataset_id, include_cases=include_cases)
    if not dataset:
        raise HTTPException(status_code=404, detail='Dataset not found.')
    return dataset


def owned_case(db: Session, dataset_id: str, case_id: str) -> DatasetCase:
    case = find_dataset_case(db, dataset_id, case_id)
    if not case:
        raise HTTPException(status_code=404, detail='Test case not found.')
    return case


@router.get('')
def list_datasets(page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Dataset).where(Dataset.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.options(selectinload(Dataset.cases)).order_by(Dataset.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {'items': [_dataset_out(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size}


@router.post('', status_code=status.HTTP_201_CREATED)
def create_dataset(body: DatasetCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = Dataset(user_id=user.id, name=body.name.strip(), description=body.description.strip())
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return _dataset_out(dataset, include_cases=False)


@router.get('/{dataset_id}')
def get_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _dataset_out(owned_dataset(db, user.id, dataset_id, include_cases=True))


@router.patch('/{dataset_id}')
def update_dataset(dataset_id: str, body: DatasetUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = owned_dataset(db, user.id, dataset_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail='Provide at least one non-null dataset field to update.')
    for field, value in changes.items():
        setattr(dataset, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(dataset)
    return _dataset_out(dataset, include_cases=False)


@router.delete('/{dataset_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = owned_dataset(db, user.id, dataset_id)
    run_ids = select(EvalRun.id).where(EvalRun.dataset_id == dataset.id)
    db.execute(sql_delete(EvalResult).where(EvalResult.run_id.in_(run_ids)))
    db.execute(sql_delete(EvalRun).where(EvalRun.dataset_id == dataset.id))
    db.execute(sql_delete(DatasetCase).where(DatasetCase.dataset_id == dataset.id))
    db.delete(dataset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/{dataset_id}/cases', status_code=status.HTTP_201_CREATED)
def add_case(dataset_id: str, body: CaseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = owned_dataset(db, user.id, dataset_id)
    values = body.model_dump()
    values['metadata_json'] = values.pop('metadata')
    case = DatasetCase(dataset_id=dataset.id, **values)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.patch('/{dataset_id}/cases/{case_id}')
def update_case(dataset_id: str, case_id: str, body: CaseUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_dataset(db, user.id, dataset_id)
    case = owned_case(db, dataset_id, case_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes or ('input' in changes and changes['input'] is None):
        raise HTTPException(status_code=422, detail='Provide at least one case field; input cannot be null.')
    if 'metadata' in changes:
        changes['metadata_json'] = changes.pop('metadata')
    for field, value in changes.items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.delete('/{dataset_id}/cases/{case_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_case(dataset_id: str, case_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_dataset(db, user.id, dataset_id)
    case = owned_case(db, dataset_id, case_id)
    db.execute(sql_delete(EvalResult).where(EvalResult.case_id == case.id))
    db.delete(case)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/{dataset_id}/import')
async def import_cases(dataset_id: str, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = owned_dataset(db, user.id, dataset_id)
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail='Import file must be no larger than 5 MB.')
    try:
        text = raw.decode('utf-8-sig')
        if (file.filename or '').lower().endswith('.json') or (file.content_type or '').lower().endswith('json'):
            parsed = json.loads(text)
            items = parsed if isinstance(parsed, list) else parsed.get('cases', [])
        else:
            items = list(csv.DictReader(io.StringIO(text)))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
        raise HTTPException(status_code=400, detail=f'Could not parse import file: {error}') from None
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail='Import must contain a non-empty JSON array or CSV rows.')
    if len(items) > MAX_IMPORT_CASES:
        raise HTTPException(status_code=413, detail='An import may contain at most 1,000 cases.')
    allowed = {'input', 'expected_output', 'actual_output', 'reference_context', 'expected_tool', 'actual_tool', 'instructions', 'structured_schema', 'metadata'}
    cases = []
    for number, item in enumerate(items, 1):
        if not isinstance(item, dict) or not str(item.get('input', '')).strip():
            raise HTTPException(status_code=422, detail=f'Row {number} must include a non-empty input field.')
        payload = {key: item[key] for key in allowed if key in item and item[key] not in (None, '')}
        for key in ('structured_schema', 'metadata'):
            if isinstance(payload.get(key), str):
                try:
                    payload[key] = json.loads(payload[key])
                except json.JSONDecodeError:
                    raise HTTPException(status_code=422, detail=f'Row {number} has invalid JSON in {key}.') from None
        if payload.get('metadata') is not None and not isinstance(payload['metadata'], dict):
            raise HTTPException(status_code=422, detail=f'Row {number} metadata must be a JSON object.')
        try:
            case_data = CaseCreate.model_validate(payload).model_dump()
        except ValidationError as error:
            raise HTTPException(status_code=422, detail=f'Row {number} is invalid: {error.errors()}') from None
        case_data['metadata_json'] = case_data.pop('metadata')
        cases.append(DatasetCase(dataset_id=dataset.id, **case_data))
    db.add_all(cases)
    db.commit()
    return {'imported': len(cases), 'dataset_id': dataset.id}
