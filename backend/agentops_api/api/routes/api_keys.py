from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.auth.security import issue_api_key
from agentops_api.db.session import get_db
from agentops_api.models.user import ApiKey, User
from agentops_api.schemas.entities import ApiKeyCreate

router = APIRouter(prefix='/api-keys', tags=['API keys'])


def key_view(key: ApiKey) -> dict:
    return {'id': key.id, 'name': key.name, 'key_prefix': key.key_prefix, 'active': key.active, 'last_used_at': key.last_used_at, 'created_at': key.created_at}


@router.get('')
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.scalars(select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())).all()
    return {'items': [key_view(key) for key in keys]}


@router.post('', status_code=status.HTTP_201_CREATED)
def create_key(body: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw, digest, prefix = issue_api_key()
    key = ApiKey(user_id=user.id, name=body.name.strip(), key_prefix=prefix, key_hash=digest)
    db.add(key)
    db.commit()
    db.refresh(key)
    return {**key_view(key), 'key': raw, 'warning': 'This key is shown once. Copy it now; it cannot be retrieved later.'}


@router.delete('/{key_id}', status_code=204)
def revoke_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    if not key:
        raise HTTPException(status_code=404, detail='API key not found.')
    key.active = False
    key.updated_at = datetime.now(timezone.utc)
    db.commit()
