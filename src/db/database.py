"""Database engine and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fba_agent.db")


class Base(DeclarativeBase):
    pass


def get_engine(url: str | None = None):
    return create_engine(url or DATABASE_URL)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)
