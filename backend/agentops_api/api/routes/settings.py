from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.config import settings
from agentops_api.db.session import get_db
from agentops_api.models.user import User
from agentops_api.schemas.entities import SettingsUpdate

router = APIRouter(prefix='/settings', tags=['settings'])


@router.get('')
def read_settings(user: User = Depends(get_current_user)):
    saved = user.settings_json or {}
    return {'full_name': user.full_name, 'email': user.email, 'cost_input_per_1k': saved.get('cost_input_per_1k', settings.cost_per_1k_input_tokens), 'cost_output_per_1k': saved.get('cost_output_per_1k', settings.cost_per_1k_output_tokens), 'evaluation_threshold': saved.get('evaluation_threshold', 0.7), 'providers': {'groq_configured': bool(settings.groq_api_key), 'gemini_configured': bool(settings.gemini_api_key)}}


@router.patch('')
def update_settings(body: SettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = body.model_dump(exclude_unset=True)
    if 'display_name' in values and values['display_name']:
        user.full_name = values.pop('display_name').strip()
    user.settings_json = {**(user.settings_json or {}), **values}
    db.commit()
    db.refresh(user)
    return read_settings(user)
