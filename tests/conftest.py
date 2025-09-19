import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from src.backoffice.infrastructure.database import get_db
from src.backoffice.main import app

# Import models after app to ensure they are registered
from src.backoffice.infrastructure.models.ebook_model import Base  # noqa: E402


@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def test_engine(postgres_container):
    """Database engine using testcontainer."""
    engine = create_engine(
        postgres_container.get_connection_url(),
        pool_pre_ping=True,
    )

    # Force drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_db_session(test_engine):
    """Database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_client(postgres_container, test_db_session):
    """FastAPI test client with overridden database dependency."""
    import os

    # Set DATABASE_URL to testcontainer URL BEFORE any database imports happen
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_container.get_connection_url()

    # Clear any cached engine to force reload with new URL
    from src.backoffice.infrastructure.database import _get_engine

    _get_engine.cache_clear()

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    # Clean up dependency override and restore original URL
    app.dependency_overrides.clear()
    if original_db_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_db_url
