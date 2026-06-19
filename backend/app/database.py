from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _ensure_sqlite_parent_dir() -> None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        return
    db_path = url.removeprefix("sqlite:////") if url.startswith("sqlite:////") else url.removeprefix("sqlite:///")
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir()

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    pool_pre_ping=not settings.database_url.startswith("sqlite"),
    connect_args=_connect_args,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
