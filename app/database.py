from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

# Standard synchronous SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

# Standard synchronous session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a standard database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
