"""Database configuration and transaction helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def create_sqlite_engine(database: str | Path = "grading.db", *, echo: bool = False) -> Engine:
    """Create an SQLite engine with foreign-key enforcement enabled."""
    raw = str(database)
    if raw == ":memory:":
        database_url = "sqlite:///:memory:"
    elif raw.startswith("sqlite:"):
        database_url = raw
        if raw.startswith("sqlite:///") and not raw.endswith(":memory:"):
            location = Path(raw.removeprefix("sqlite:///"))
            location.parent.mkdir(parents=True, exist_ok=True)
    else:
        path = Path(database)
        path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{path}"
    engine = create_engine(database_url, echo=echo, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    """Create all tables described by ORM metadata."""
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a configured SQLAlchemy session factory."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit on success and rollback the complete transaction on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
