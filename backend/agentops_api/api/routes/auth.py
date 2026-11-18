from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from agentops_api.auth.dependencies import get_current_user
from agentops_api.auth.security import create_access_token, hash_password, verify_password
from agentops_api.db.session import get_db
from agentops_api.models.user import User
from agentops_api.schemas.entities import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix='/auth', tags=['authentication'])


@router.post('/register', response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = str(body.email).lower().strip()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail='An account with this email already exists.')
    user = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='An account with this email already exists.') from None
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.email), user=user)


@router.post('/login', response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower().strip()))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Email or password is incorrect.', headers={'WWW-Authenticate': 'Bearer'})
    return TokenOut(access_token=create_access_token(user.id, user.email), user=user)


@router.get('/me', response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
