"""Database setup and session management for SteelWorks.

This module reads the database URL from an environment variable (``DATABASE_URL``)
and configures a SQLAlchemy ``Engine`` and ``Session`` factory. Using a
centralized session factory simplifies testing by allowing us to override the
engine with an in-memory SQLite database.

Resource management: sessions are created with context managers to ensure they
are closed after use; engines are module-scoped and persist for the lifetime of
the process.

Complexity notes:
* Creating an engine is O(1).
* Acquiring a session is amortized O(1).
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# optionally load environment variables from a .env file (development convenience).
# ``load_dotenv()`` searches the current working directory and its parents,
# so ensure your ``.env`` lives at the repository root (not inside ``src/``).
try:
    from dotenv import load_dotenv
    _ = load_dotenv()
except ImportError:
    # python-dotenv is a dependency so this should always succeed; guard just in case
    pass

from .models import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
"""Connection string for the database.  Defaults to a transient in-memory
SQLite database for simplicity if none is provided via environment.
"""


# ``future`` flag gives us the up-to-date 2.x style API, which influences
# typing and behavior of sessions/queries.
engine = create_engine(DATABASE_URL, echo=False, future=True)
"""SQLAlchemy engine used for all database interactions.  To change the
backend (e.g. PostgreSQL), update ``DATABASE_URL`` in environment.
"""

# create a session factory bound to the engine
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Create all tables in the database according to our models.

    This is a no-op if the tables already exist.  It's safe to call multiple
times (idempotent).
    """

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Session:
    """Provide a transactional scope around a series of operations.

    Usage::

        with get_session() as sess:
            ...

    The session is committed if the context exits normally; it is rolled back on
    exception.  The session is closed in all cases to avoid connection leaks.
    """

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
