import logging
import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

load_dotenv()

# Base moved to models/ebook_model.py to avoid circular imports


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    """Create database engine with caching - can be cleared for tests"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Please set it to your PostgreSQL connection string."
        )

    logger.info(f"Creating database engine for URL: {database_url[:50]}...")

    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=True,
    )


def get_db() -> Generator[Session, None, None]:
    """Get database session (synchronous)"""
    engine = _get_engine()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        logger.debug("Nouvelle connexion à la base de données établie")
        yield db
    except Exception as e:
        logger.error(f"Erreur de base de données: {str(e)}")
        raise
    finally:
        logger.debug("Fermeture de la connexion à la base de données")
        db.close()
