import logging
from pathlib import Path
from typing import Tuple, Dict
from psycopg2.extensions import connection

class PipelineRunManager:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def insert_run(self, conn: connection, total_files: int) -> int:
       
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_runs (status, total_files)
                VALUES ('PROCESSING', %s)
                RETURNING run_id;
                """,
                (total_files,)
            )
            run_id = cur.fetchone()[0]
            self.logger.info("Initialized pipeline run recording. Database assigned Run ID: %s", run_id)
            return run_id

    def insert_file_detail(self, conn: connection, run_id: int, file_path: Path, 
                           outcome: str, stage: str, submission_id: int = None, error_msg: str = None):
       
        file_binary = None
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    file_binary = f.read()
            except Exception as e:
                self.logger.error("Failed to read raw file binary for database storage: %s", e)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_file_details 
                (run_id, file_name, outcome, execution_stage, submission_id, error_message, file_content)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (run_id, file_path.name, outcome.upper(), stage, submission_id, error_msg, file_binary)
            )
            self.logger.info("Recorded file detail for %s under Run ID %s with outcome: %s", file_path.name, run_id, outcome.upper())

    def update_run_stats(self, conn: connection, run_id: int, stats: Dict[str, int]):
       
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_runs 
                SET status = 'COMPLETED',
                    success_count = %s,
                    failure_count = %s,
                    skipped_count = %s
                WHERE run_id = %s;
                """,
                (stats['success'], stats['failure'], stats['skipped'], run_id)
            )
            self.logger.info("Finalized batch execution statistics for Run ID: %s", run_id)