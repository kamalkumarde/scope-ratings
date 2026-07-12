# tests/conftest.py
import os
import pytest
import psycopg2
from src.DatabaseManager import DatabaseManager

@pytest.fixture(scope="session")
def db_config():
    """Provides test database configuration mapping."""
    return {
        "dbname": os.getenv("DB_NAME", "rating_warehouse"),
        "user": os.getenv("DB_USER", "rating_warehouse_user"),
        "password": os.getenv("DB_PASSWORD", "rating_warehouse_pass"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432))
    }

@pytest.fixture(scope="function")
def test_db_conn(db_config):
    """Provides a transactional database connection that rolls back changes automatically."""
    conn = psycopg2.connect(**db_config)
    yield conn
    # Forces a rollback so test inserts never leak into the physical database tables permanently
    conn.rollback()
    conn.close()