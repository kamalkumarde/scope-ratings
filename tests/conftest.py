# tests/conftest.py
import os
import pytest
import psycopg2
from fastapi.testclient import TestClient

from src.api.dependencies import get_db_connection
from src.api.main import app  # Matches your tree: src/api/main.py

@pytest.fixture(scope="session")
def db_config():
    """Provides test database configuration mapping, resolving localhost or db container host."""
    return {
        "dbname": os.getenv("DB_NAME", "rating_warehouse"),
        "user": os.getenv("DB_USER", "rating_warehouse_user"),
        "password": os.getenv("DB_PASSWORD", "your_secure_password"),
        "host": os.getenv("DB_HOST", "db"),  # Defaults to compose network DB link
        "port": int(os.getenv("DB_PORT", 5432))
    }

@pytest.fixture(scope="session")
def db_connection(db_config):
    """Establishes connection to the database container."""
    conn = psycopg2.connect(**db_config)
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def db_transaction(db_connection):
    """Wraps each execution thread inside an isolated transaction rollback cycle."""
    yield db_connection
    db_connection.rollback()  # Guarantees complete operational cleanup per execution round

@pytest.fixture(scope="function")
def test_db_conn(db_config):
    """Provides a transactional database connection that rolls back changes automatically."""
    conn = psycopg2.connect(**db_config)
    yield conn
    # Forces a rollback so test inserts never leak into the physical database tables permanently
    conn.rollback()
    conn.close()

@pytest.fixture(scope="function")
def api_client(test_db_conn):
    """
    Overloads the live router endpoints to execute deep inside the 
    isolated transactional rollback cycle fixture.
    """
    def _get_db_override():
        yield test_db_conn

    # Inject the rollback connection directly into FastAPI dependency injection
    app.dependency_overrides[get_db_connection] = _get_db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()