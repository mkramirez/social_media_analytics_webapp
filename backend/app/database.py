"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DEBUG  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.

    Usage in FastAPI endpoints:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    # Import all models here to ensure they're registered with Base
    from app.models import user, profile, platform_entities, collected_data, jobs
    from app.models import twitch_models  # Phase 2: Twitch models
    from app.models import twitter_models  # Phase 3: Twitter models
    from app.models import youtube_models  # Phase 3: YouTube models
    from app.models import reddit_models  # Phase 3: Reddit models
    from app.models import analytics_models  # Phase 4: Analytics models

    Base.metadata.create_all(bind=engine)
