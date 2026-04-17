from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from planreview.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.db_path}",
        connect_args={"check_same_thread": False},
    )


def init_db() -> None:
    from planreview import models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_sqlite_migrations(engine)


def _apply_sqlite_migrations(engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("reviewjob"):
        return

    columns = {item["name"] for item in inspector.get_columns("reviewjob")}
    with engine.begin() as connection:
        if "phase" not in columns:
            connection.execute(
                text("ALTER TABLE reviewjob ADD COLUMN phase VARCHAR DEFAULT 'queued'")
            )


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
