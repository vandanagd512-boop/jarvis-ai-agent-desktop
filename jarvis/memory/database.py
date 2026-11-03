"""Database connection and session management for JARVIS."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from jarvis.core.config import get_settings
from jarvis.core.logger import get_logger
from jarvis.memory.models import Base

logger = get_logger("JARVIS.Database")

_engine = None
_SessionFactory = None


def get_engine():
    """Get or create singleton SQLAlchemy engine with SQLite pragmas."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.effective_database_url
        logger.info(f"Connecting to database: {db_url}")

        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

        # Enable foreign keys and WAL mode for SQLite
        if db_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Ensure tables exist
        Base.metadata.create_all(bind=_engine)
        logger.info("Database schema verified/created successfully.")

    return _engine


def get_session_factory():
    """Get or create the sessionmaker factory."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory


def init_db(engine=None) -> None:
    """Create all database tables."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("Database tables initialized successfully")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for providing transactional database sessions."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {exc}")
        raise
    finally:
        session.close()
