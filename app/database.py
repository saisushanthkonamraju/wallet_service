from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import DATABASE_URL

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=25,
    max_overflow=35,
    pool_timeout=30,
    pool_pre_ping=True,
    echo=False,
)

# session factory
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
