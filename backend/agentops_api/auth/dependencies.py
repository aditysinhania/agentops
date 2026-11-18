from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from agentops_api.auth.security import ALGORITHM, digest_api_key
from agentops_api.config import settings
from agentops_api.db.session import get_db
from agentops_api.models.user import ApiKey, User

oauth_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login', auto_error=False)


def get_current_user(token: str | None = Depends(oauth_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Sign in to continue.', headers={'WWW-Authenticate': 'Bearer'})
    if not token:
        raise unauthorized
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = claims.get('sub')
        if not user_id:
            raise unauthorized
    except JWTError:
        raise unauthorized from None
    user = db.get(User, user_id)
    if not user or not user.active:
        raise unauthorized
    return user


def get_api_key_user(authorization: str | None = None, db: Session = Depends(get_db)) -> tuple[User, ApiKey]:
    if not authorization or not authorization.lower().startswith('bearer ao_live_'):
        raise HTTPException(status_code=401, detail='A valid AgentOps API key is required.')
    raw = authorization.split(' ', 1)[1]
    key = db.scalar(select(ApiKey).where(ApiKey.key_hash == digest_api_key(raw), ApiKey.active.is_(True)))
    if not key:
        raise HTTPException(status_code=401, detail='Invalid or revoked AgentOps API key.')
    owner = db.get(User, key.user_id)
    if not owner or not owner.active:
        raise HTTPException(status_code=401, detail='The API key owner is inactive.')
    return owner, key
