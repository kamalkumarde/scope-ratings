import logging, os, hashlib
import shutil
from pathlib import Path
import datetime
from typing import Tuple, List

from src.ConfigManager import ConfigManager
from src.DatabaseManager import DatabaseManager
from psycopg2.extensions import connection
from src.WarehouseManager import WarehouseManager
from src.ExcelLineageExtractor import ExcelLineageExtractor
from src.SchemaValidator import SchemaValidator
from src.WarehouseLoader import WarehouseLoader
from src.audit import AuditLogger
from src.PipelineRunManager import PipelineRunManager


class IngestionPipeline:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.configer = ConfigManager()        
        self.datapath = self.configer.get_data_path()        
        self.config_path = self.configer.get_config_path()
        
        self.schema = self.configer.import_schema()
        
        # Define storage directories explicitly relative to configuration
        self.archive_dir = Path(self.datapath).parent / "archive"
        self.dlq_dir = Path(self.datapath).parent / "dlq"
        
        # Ensure targeted tracking directories physically exist on deployment
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.dlq_dir.mkdir(parents=True, exist_ok=True)
        
        self.dbmanager = DatabaseManager({
            "dbname": os.getenv("DB_NAME", "rating_warehouse"),
            "user": os.getenv("DB_USER", "rating_warehouse_user"),
            "password": os.getenv("DB_PASSWORD", "rating_warehouse_pass"), 
            "host": "db",
            "port": int(os.getenv("DB_PORT", 5432))
        })
        self.auditor = AuditLogger(self.dbmanager)

        self.sub_whmanager = WarehouseManager()
        self.extractor = ExcelLineageExtractor()
        self.validator = SchemaValidator(self.schema)
        self.warehouseloader = WarehouseLoader(self.auditor)
        self.run_manager = PipelineRunManager()

    def get_file_list(self) -> list:
        self.logger.info("Fetching Data Files from %s",self.datapath)
        target_files = [f for f in Path(self.datapath).glob("*.xlsm") if not f.name.startswith("~$")]
        self.logger.info("Fetched %s Data Files", len(target_files))
        return target_files

    def process_all_files(self, file_list: list):
        """Creates the run structure from the DB and loops through targets under that generated context."""
        conn = self.dbmanager.get_connection()
        stats = {"success": 0, "failure": 0, "skipped": 0}
        
        try:
            # 1. Initialize macro batch tracking record and fetch the auto-generated identity from the DB
            #self.logger.info("*****************")
            run_id = self.run_manager.insert_run(conn, len(file_list))
            #self.logger.info("*********22222222222********")
             
            
            
            conn.commit()


            for ifile in file_list:
                file_path = Path(ifile)

                self.logger.info(f"Processing File {file_path} under DB Run ID: {run_id}")
                
                # 2. Extract and Validate the file
                outcome, stage, sub_id, error_desc = self._process_single_file(file_path, run_id, conn)
                stats[outcome] += 1
                
                # 3. Save raw file asset and structural execution states tied to the new run_id
                #self.logger.info("**********333333333333*******")
                self.run_manager.insert_file_detail(
                    conn=conn, 
                    run_id=run_id, 
                    file_path=file_path, 
                    outcome=outcome, 
                    stage=stage, 
                    submission_id=sub_id, 
                    error_msg=error_desc
                )
                
                self.logger.info(f"Completed File {file_path} with outcome: {outcome.upper()}")
                conn.commit()
                
                # NEW ROUTING INJECTION: Move the parent asset directory to Archive or DLQ depending on run outcome
                self._route_processed_file(file_path=file_path, outcome=outcome)
                
            # 4. Finalize runtime status metrics across parent tracking entity
            self.run_manager.update_run_stats(conn, run_id, stats)
            conn.commit()

            self.logger.info(
                f"=== RUN {run_id} SUMMARY ===\n"
                f"Total Processed: {len(file_list)}\n"
                f"Successes: {stats['success']}\n"
                f"Failures:  {stats['failure']}\n"
                f"Skipped:   {stats['skipped']}\n"
                f"==========================="
            )
            
        finally:
            self.dbmanager.put_connection(conn)

    def _route_processed_file(self, file_path: Path, outcome: str):
        """Moves raw ingestion files or parent asset directories into valid/invalid directories."""
        # Check if the file is part of a sub-folder tracking pattern or just a flat file asset
        target_item = file_path.parent if file_path.parent != Path(self.datapath) else file_path
        
        if outcome == "success":
            destination = self.archive_dir / target_item.name
            label = "ARCHIVE"
        else:
            destination = self.dlq_dir / target_item.name
            label = "DLQ"

        try:
            if target_item.exists():
                shutil.move(str(target_item), str(destination))
                self.logger.info("Successfully moved asset '%s' to %s directory.", target_item.name, label)
        except Exception as e:
            self.logger.error("Failed executing post-load storage route layout for '%s': %s", target_item.name, e)

    def _process_single_file(self, file_path: Path, run_id: int, conn: connection) -> Tuple[str, str, int, str]:
        """Processes a single file. Returns outcome tuple details."""
        stage = '1.Initial'
        try:
            meta_data, file_hash = self._generate_file_fingerprint(file_path)
            
            # Deduplication Check (Skipped Flow Logic)
            if self._is_duplicate(file_hash, conn):
                self.logger.info(f"Skipping duplicate file: {file_path.name}")
                self.auditor.log(status="SKIPPED", submission_id=None, filename=file_path.name, error="Duplicate file checksum detected")
                return "skipped", stage, None, "Duplicate file checksum detected"

            valid_data = {}
            lineage = {}
            sub_final_status = "SUCCESS"
            sub_current_status = "BEFORE EXTRACT"
            valid = False
            failures: List[str] = []

            submission_id = self.sub_whmanager.insert_submission(
                conn=conn, file_name=file_path.name, file_meta=meta_data, current_status=sub_current_status, final_status=sub_final_status, 
                run_id=run_id
            )
            self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error=sub_current_status)   

            # Extraction Stage
            self.logger.info(f"Extracting File {file_path}")
            stage = '2.Extraction'

            extaction_status, extract, lineage, failures = self.extractor.extract(file_path)
            self.logger.info("***********************************")         
            self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error="Extraction Completed")             
       
            if not extaction_status:
                err_text = "; ".join(failures) if failures else "Extraction failed"
                self.sub_whmanager.insert_submission_errors(conn=conn, submission_id=submission_id, errors=failures)
                self.sub_whmanager.update_submission(conn=conn, submission_id=submission_id, final_status="FAILURE", current_status="EXTRACTION FAILURE")
                self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error="EXTRACTION FAILURE")
                return "failure", stage, submission_id, err_text

            # Validation Stage
            sub_current_status = "EXTRACTION SUCCESS"
            self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error=sub_current_status)
            stage = "3.Validation"

            valid, failures, valid_data = self.validator.validate(extract)
            
            if len(failures) == 0:                    
                sub_current_status = "VALIDATION SUCCESS"
                valid = True
            else:
                err_text = "; ".join(failures)
                self.sub_whmanager.insert_submission_errors(conn=conn, submission_id=submission_id, errors=failures)
                self.sub_whmanager.update_submission(conn=conn, submission_id=submission_id, final_status="FAILURE", current_status="VALIDATION FAILURE")
                self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error="VALIDATION FAILURE")
                return "failure", stage, submission_id, err_text
            
            self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error=sub_current_status)
            
            # Load Target Warehouse Stage
            stage = "4.Load" 
            load_status = self.sub_whmanager.load_payload(
                conn=conn, submission_id=submission_id, final_status=sub_final_status,
                current_status=sub_current_status, parsed_data=valid_data, lineage=lineage
            )
            
            if not load_status:
                self.sub_whmanager.update_submission(conn=conn, submission_id=submission_id, final_status="FAILURE", current_status="LOAD FAILURE")
                self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error="LOAD FAILURE")
                return "failure", stage, submission_id, "Staging loading target failure"

            # Transformation Layer Stage
            stage = "5.Transform" 
            self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error=sub_current_status)

            if valid and load_status:
                load_status = self.warehouseloader.load(tconn=conn, submission_id=submission_id)

            if load_status and valid:
                sub_current_status = "SUBMISSION SUCCESS"
                self.sub_whmanager.update_submission(
                    conn=conn, submission_id=submission_id, final_status="SUCCESS", current_status=sub_current_status
                ) 
                self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error=sub_current_status)
                return "success", stage, submission_id, None
            else:
                self.sub_whmanager.update_submission(
                    conn=conn, submission_id=submission_id, final_status="FAILURE", current_status="TRANSFORM FAILURE"
                ) 
                self.auditor.log(status=stage, submission_id=submission_id, filename=file_path.name, error="TRANSFORM FAILURE")
                return "failure", stage, submission_id, "Warehouse transformer script invocation failure"

        except Exception as e:
            self.logger.error("Error Processing File %s: %s", file_path.name, e)
            conn.rollback()
            return "failure", stage, locals().get('submission_id'), str(e)

    def _is_duplicate(self, file_hash: str, conn) -> bool:
        with conn.cursor() as cur:
            #self.logger.info("************* %s",file_hash)
            cur.execute(
                "SELECT id FROM submissions WHERE file_metadata->>'file_sha256_checksum' = %s AND final_status = %s", 
                (file_hash, "SUCCESS")
            )
            duplicate = cur.fetchone()
            return duplicate is not None

    def _generate_file_fingerprint(self, file_path: Path) -> Tuple[dict, str]:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()
        
        stat_info = file_path.stat()
        return {
            "file_size_bytes": stat_info.st_size,
            "file_sha256_checksum": file_hash,
            "last_modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "absolute_path": str(file_path.resolve())
        }, file_hash

    def run_pipe(self):
        self.auditor.log(status="STARTED", error="Pipeline engine initialized execution")
        files = self.get_file_list()
        
        if not files:
            self.logger.info("No .xlsm files found in data directory")
            return
            
        self.process_all_files(file_list=files)
        self.logger.info(f"Pipeline completed. Processed {len(files)} files.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = IngestionPipeline()
    pipeline.run_pipe()