from collections.abc import Generator
from typing import Any
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from agentops_api.config import settings

_url = settings.effective_database_url
_engine_args: dict[str, Any] = {'pool_pre_ping': True}
if _url.startswith('sqlite'):
    _engine_args['connect_args'] = {'check_same_thread': False}

engine = create_engine(_url, **_engine_args)
if _url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
