import logging, os, hashlib
from pathlib import Path
import yaml
from typing import Tuple,List
import datetime

from src.ConfigManager import ConfigManager
from src.DatabaseManager import DatabaseManager
from psycopg2.extensions import connection
from src.WarehouseManager import WarehouseManager
from src.ExcelLineageExtractor import ExcelLineageExtractor
from src.SchemaValidator import SchemaValidator
from src.WarehouseLoader import WarehouseLoader
from src.audit import AuditLogger


class IngestionPipeline:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.configer = ConfigManager()        
        self.datapath = self.configer.get_data_path()        
        self.config_path = self.configer.get_config_path()
        
        self.schema = self.configer.import_schema()
        
        self.dbmanager = DatabaseManager({
            "dbname": os.getenv("DB_NAME", "rating_warehouse"),
            "user": os.getenv("DB_USER", "rating_warehouse_user"),
            "password": os.getenv("DB_PASSWORD", "rating_warehouse_pass"), 
            "host": "db" ,#os.getenv("DB_HOST", "db"),
            "port": int(os.getenv("DB_PORT", 5432))
        })
        self.auditor = AuditLogger(self.dbmanager)

        self.sub_whmanager = WarehouseManager()
        self.extractor = ExcelLineageExtractor()
        self.validator = SchemaValidator(self.schema)
        self.warehouseloader = WarehouseLoader( self.auditor)

    def get_file_list(self) -> list:
        self.logger.info("Fetching Data Files")
        target_files = [f for f in Path(self.datapath).glob("*.xlsm") if not f.name.startswith("~$")]
        self.logger.info("Fetched %s Data Files",len(target_files))
        return target_files

    def process_all_files(self, file_list: list):
        conn = self.dbmanager.get_connection()
        try:
            for batch_id, ifile in enumerate(file_list, start=1):
                self.logger.info(f"Processing File {ifile}")
                self._process_single_file(Path(ifile), batch_id, conn)
                self.logger.info(f"Completed Processing File {ifile}")
                conn.commit()
        finally:
            self.dbmanager.put_connection(conn)

    def _process_single_file(self, file_path: Path, batch_id: int, conn: connection):
        try:
                
            meta_data, file_hash = self._generate_file_fingerprint(file_path)
            
            # Deduplication
            #if self._is_duplicate(file_hash, conn):
            #   self.logger.info(f"Skipping duplicate file: {file_path.name}")
            #  return
            valid_data ={}
            lineage ={}
            sub_final_status = "SUCCESS"
            sub_current_status = "BEFORE EXTRACT"
            stage = '1.Initial'
            valid = False
            failures: List[str] = []


            submission_id = self.sub_whmanager.insert_submission(
                conn=conn, file_name=file_path.name, file_meta=meta_data,current_status=sub_current_status,final_status=sub_final_status
            )
            self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)   

            


            self.logger.info(f"Extracting File {file_path}")
            stage = '2.Extraction'
            #self.auditor.log(status= "Before Extraction",submission_id=submission_id,filename=file_path.name,error="Befor Exxtraction")   

            extaction_status, extract, lineage,failures = self.extractor.extract(file_path)
            self.logger.info("***********************************")         

            self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error="Exxtraction Completed")             
            self.logger.info(f"File Extraction Complete for  {file_path} status {extaction_status}")
       
            if not extaction_status:
                sub_final_status = "FAILURE"                
                sub_current_status = "EXTRACTION FAILURE"
                self.logger.info("***********************************")
                self.sub_whmanager.insert_submission_errors(conn=conn,submission_id=submission_id,errors=failures)
                self.logger.info("***********************************")
                self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)


            if extaction_status:                
                sub_current_status = "EXTRACTION SUCCESS"
                self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)
                stage = "3.Validation"

                valid, failures, valid_data = self.validator.validate(extract)

                
                if len(failures) == 0:                    
                    sub_current_status = "VALIDATION SUCCESS"
                    valid = True
                else:
                    sub_final_status = "FAILURE"
                    sub_current_status = "VALIDATION FAILURE"                    
                    self.sub_whmanager.insert_submission_errors(conn=conn,submission_id=submission_id,errors=failures)
                    valid = False
                self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)
            
            
            stage = "4.Load" 
               
            load_status = self.sub_whmanager.load_payload( conn=conn, submission_id=submission_id,final_status=sub_final_status,
                                                                    current_status=sub_current_status,parsed_data=valid_data,lineage=lineage
                                                                    )
            
            if load_status:
                pass
            else:
                sub_final_status = "FAILURE"
                sub_current_status ="LOAD FAILURE" 

            self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)


            
            stage = "4.TRANFORM" 
            #sub_current_status = "BEFORE LOAD START"

            self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)


            if valid and load_status:
                    load_status = self.warehouseloader.load(tconn= conn, submission_id=submission_id)

            if load_status and valid:

                sub_current_status = "SUBMISSION SUCCESS"
            else:
                sub_final_status = "FAILURE"
                #sub_current_status = "SUBMISSION FAILED"
            update_status = self.sub_whmanager.update_submission(
                conn=conn,submission_id=submission_id,final_status=sub_final_status,current_status=sub_current_status) 
               



            self.auditor.log(status= stage,submission_id=submission_id,filename=file_path.name,error=sub_current_status)

        # self.auditor.log()


        except Exception as e:
             self.logger.error("Error Processing File %s",e)




        
            

        

        
            

    def _is_duplicate(self, file_hash: str, conn) -> bool:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM submissions WHERE file_metadata->>'file_sha256_checksum' = %s and final_status = %s ", (file_hash,"SUCCESS"))
            self.logger.info("SQL is. SELECT id FROM submissions WHERE file_metadata->>'file_sha256_checksum' = %s and final_status = %s ",file_hash,"SUCCESS")
            duplicate = cur.fetchone()
            self.logger.info("Fetch of duplicates: %s", duplicate)
            return cur.fetchone() is not None

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
        audit_id = self.auditor.log( status="STARTED",error="Started Run")
        files = self.get_file_list()
        if not files:
            self.logger.info("No .xlsm files found in data directory")
            return
        self.process_all_files(file_list=files)
        self.logger.info(f"Pipeline completed Processed {len(files)} files.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pipeline = IngestionPipeline()
    pipeline.run_pipe()