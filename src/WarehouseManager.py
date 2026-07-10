

import logging
from psycopg2.extensions import connection
from psycopg2 import sql

class WarehouseManager:
    def __init__(self):
         self.logger = logging.getLogger(self.__class__.__name__)

    def insert_submission(self, conn: connection, file_name: str) -> int:
        # 1. Added "RETURNING id" so fetchone() actually has something to grab
        sql = """
            INSERT INTO submissions (filename, final_status, current_status, execution_duration_seconds)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        try:
            with conn:
                with conn.cursor() as cur:
                    # 2. Package ALL four parameters into a single tuple argument
                    cur.execute(sql, (file_name, "IN PROGRESS", "INIT_SUBMIT", "0"))
                    
                    # 3. Safely extract the returned ID
                    submission_id = cur.fetchone()[0]
                    self.logger.info("Created New Submission Id  %s for the file %s",submission_id,file_name)
                    return submission_id
        except Exception as e:
            self.logger.error("Failed to initialize submission for file %s: %s", file_name, e)
            raise e
    
    def update_submission_single_column(self, conn: connection, submission_id: int, column_name: str, column_value: any) -> int:
        query = sql.SQL("""     UPDATE submissions 
                SET {col} = %s ,
                    updated_at = NOW()              WHERE id = %s
                RETURNING id;
    """).format(col=sql.Identifier(column_name))
        try:
                
            with conn:
                with conn.cursor() as cur:
                    # The execution tuple remains unchanged as NOW() requires no input parameters
                    cur.execute(query, (column_value, submission_id))
                    updated_id = cur.fetchone()
                    self.logger.info("Sucessfully updated Column %s of submission id  %s", column_name, submission_id)
                    return updated_id
                    
        except Exception as e:
                
                self.logger.error("Failed to update column %s for ID %s: %s", column_name, submission_id, e)
                raise e
        
        