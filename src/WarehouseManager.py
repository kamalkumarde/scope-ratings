
import logging, json
from psycopg2.extensions import connection
from psycopg2.extras import execute_values
from psycopg2 import sql
from typing import Dict,Any,List

class WarehouseManager:
    def __init__(self):
         self.logger = logging.getLogger(self.__class__.__name__)

    def insert_submission(self, conn: connection, file_name: str,file_meta: Dict,final_status: str,current_status:str) -> int:
        # 1. Added "RETURNING id" so fetchone() actually has something to grab
        fm = json.dumps(file_meta)  
        sql = """
            INSERT INTO submissions (filename, final_status, current_status, execution_duration_seconds,file_metadata)
            VALUES (%s, %s, %s, %s,%s)
            RETURNING id;
        """
        try:
            with conn:
                with conn.cursor() as cur:
                    # 2. Package ALL four parameters into a single tuple argument
                    cur.execute(sql, (file_name, final_status, current_status, "0",fm))
                    
                    # 3. Safely extract the returned ID
                    submission_id = cur.fetchone()[0]
                    self.logger.info("Created New Submission Id  %s for the file %s",submission_id,file_name)
                    return submission_id
        except Exception as e:
            self.logger.error("Failed to initialize submission for file %s: %s", file_name, e)
            raise e
    

    def load_payload(self, conn: connection, submission_id: int, final_status: str,current_status:str,parsed_data:any,lineage:Any) ->bool:
            
            ps = json.dumps(parsed_data)
            ln = json.dumps(lineage) 

            query = sql.SQL("""     UPDATE submissions 
                    SET final_status = %s ,
                        current_status = %s , 
                        parsed_data = %s , 
                        lineage_trace = %s,                                   
                        current_status_time = NOW()              WHERE id = %s
                    RETURNING id;
        """)
            try:
                    
                with conn:
                    with conn.cursor() as cur:
                        # The execution tuple remains unchanged as NOW() requires no input parameters
                        cur.execute(query, (final_status,current_status,ps,ln, submission_id))
                        updated_id = cur.fetchone()
                        self.logger.info("Sucessfully updated Column %s of submission id  %s", final_status, submission_id)
                        return updated_id
                    return True    
            except Exception as e:                    
                    self.logger.error("Failed to update column %s for ID %s: %s", final_status, submission_id, e)
                    return False
                    #raise e


    def update_submission(self, conn: connection, submission_id: int, final_status: str,current_status:str) ->bool:
                   
          query = sql.SQL("""     UPDATE submissions 
                    SET final_status = %s ,
                        current_status = %s , 
                        current_status_time = NOW() ,
                        execution_duration_seconds =   EXTRACT(EPOCH FROM (NOW() - submitted_at))             
                          WHERE id = %s
                    RETURNING id;
        """)
          try:
                                   
                with conn:
                    with conn.cursor() as cur:
                        # The execution tuple remains unchanged as NOW() requires no input parameters
                        cur.execute(query, (final_status,current_status, submission_id))
                        updated_id = cur.fetchone()
                        self.logger.info("Sucessfully updated Column %s of submission id  %s", final_status, submission_id)
                        return updated_id
                    return True 
                   
          except Exception as e:
                        
                    self.logger.error("Failed to update column %s for ID %s: %s", final_status, submission_id, e)
                    return False
          
                         

        
    def insert_submission_errors(self, conn: connection, submission_id: int,errors: List[str]):
        try:
             with conn.cursor() as cursor:
                  
                  execute_values(cursor,
                                 "INSERT INTO public.submission_errors (submission_id, error_message) VALUES %s;",
                                 [(submission_id, str(e)) for e in errors]) 
                                 
                  
        except Exception as e:
             self.logger.error("Error Inserting Error Logs for submission id %s Exception %s",submission_id,e)