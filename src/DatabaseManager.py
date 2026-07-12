from  psycopg2  import pool  
import logging 


class DatabaseManager:
    def __init__(self, db_config: dict, min_conn: int = 1, max_conn: int = 10):
        self.logger = logging.getLogger(self.__class__.__name__)
        try:
            self.logger.info("Creating Connection Pool")
            self.pool = pool.ThreadedConnectionPool(min_conn, max_conn, **db_config)
            self.logger.info("Database connection pool initialized.")
        except Exception as e:
            self.logger.error("Pool initialization failed: %s", e)
            raise e

    def get_connection(self): return self.pool.getconn()
    def put_connection(self, conn): self.pool.putconn(conn)
    def close_all(self): self.pool.closeall()
    