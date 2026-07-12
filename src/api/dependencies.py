# src/api/dependencies.py
from fastapi import Depends
from src.DatabaseManager import DatabaseManager
from .services import WarehouseAnalyticalService
import os

# Initialize your core manager instance from your parent directory logic
#db_manager = DatabaseWarehouseManager(db_config={"dbname": "your_db"}) # Replace config as necessary
db_manager = DatabaseManager({
            "dbname": os.getenv("DB_NAME", "rating_warehouse"),
            "user": os.getenv("DB_USER", "rating_warehouse_user"),
            "password": os.getenv("DB_PASSWORD", "rating_warehouse_pass"), 
            "host": "db" ,#os.getenv("DB_HOST", "db"),
            "port": int(os.getenv("DB_PORT", 5432))
        })
def get_db_connection():
    conn = db_manager.get_connection()
    try:
        yield conn
    finally:
        db_manager.put_connection(conn)

def get_analytical_service(conn=Depends(get_db_connection)) -> WarehouseAnalyticalService:
    """Instantiates the object-oriented analytical service worker."""
    return WarehouseAnalyticalService(conn)