import hashlib
import secrets
from datetime import timedelta
import bcrypt
from jose import jwt
from agentops_api.config import settings
from agentops_api.db.base import utcnow

ALGORITHM = 'HS256'


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('ascii')


def verify_password(password: str, encoded: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), encoded.encode('ascii'))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str) -> str:
    expires = utcnow() + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({'sub': user_id, 'email': email, 'exp': expires}, settings.secret_key, algorithm=ALGORITHM)


def issue_api_key() -> tuple[str, str, str]:
    raw = 'ao_live_' + secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest(), raw[:15]


def digest_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
