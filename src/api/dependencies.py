# src/api/dependencies.py
from fastapi import Depends, HTTPException
from src.DatabaseManager import DatabaseManager
from .services import WarehouseAnalyticalService
import os
import psycopg2

db_manager = DatabaseManager({
    "dbname": os.getenv("DB_NAME", "rating_warehouse"),
    "user": os.getenv("DB_USER", "rating_warehouse_user"),
    "password": os.getenv("DB_PASSWORD", "rating_warehouse_pass"), 
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", 5432))
})

def get_db_connection():
    try:
        conn = db_manager.get_connection()
        yield conn
    except Exception as e:
        # Prevent ASGI hard crashes by catching connection problems cleanly
        raise HTTPException(
            status_code=503, 
            detail=f"Database connectivity layer failure: {str(e)}"
        )
    finally:
        try:
            db_manager.put_connection(conn)
        except NameError:
            pass # Connection was never established

def get_analytical_service(conn=Depends(get_db_connection)) -> WarehouseAnalyticalService:
    """Instantiates the object-oriented analytical service worker."""
    return WarehouseAnalyticalService(conn)