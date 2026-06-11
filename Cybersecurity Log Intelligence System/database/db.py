from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config.settings import DATABASE_URL
from database.models import Base


def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_engine(url: str = DATABASE_URL, testing: bool = False):
    if testing:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


_engine = None
_SessionLocal = None


def _init_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    _init_engine()
    session = _SessionLocal()
    return session


def create_all_tables(engine=None):
    if engine is None:
        _init_engine()
        engine = _engine
    Base.metadata.create_all(bind=engine)
