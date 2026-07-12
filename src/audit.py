from typing import TYPE_CHECKING

# This prevents circular imports at runtime but lets your IDE/Linter see the type
if TYPE_CHECKING:
    from src.DatabaseManager import DatabaseManager

class AuditLogger:
    """A globally reusable service for tracking execution audits in the database."""
    
    def __init__(self, db_manager: "DatabaseManager"):
        # Store the shared database manager instance
        self.db_manager = db_manager
    def log(self, status: str, filename: str = "Master ", records_count: int = 0, error: str = None, audit_id: int = None,submission_id : int = 0) -> int:
 
        conn = self.db_manager.get_connection()

        try:
            with conn.cursor() as cursor:
                if audit_id is None:
                    # Create a new "STARTED" log entry
                    cursor.execute("""
                        INSERT INTO public.pipeline_audit_logs (filename, execution_status,submission_id, processed_records, error_message, started_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id;
                    """, (filename, status,submission_id, records_count, error))
                    generated_id = cursor.fetchone()[0]
                    conn.commit()
                    return generated_id
                else:
                    # Update an existing entry to "SUCCESS" or "FAILURE"
                    cursor.execute("""
                        UPDATE public.pipeline_audit_logs
                        SET execution_status = %s,
                            processed_records = %s,
                            error_message = %s,
                            completed_at = CURRENT_TIMESTAMP
                        WHERE id = %s;
                    """, (status, records_count, error, audit_id))
                    conn.commit()
                    return audit_id
        except Exception as e:
            conn.rollback()
            print(f"CRITICAL: Failed to write to pipeline_audit_logs: {e}")
            return None
        finally:
            self.db_manager.put_connection(conn)    