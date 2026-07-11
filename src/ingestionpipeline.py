import logging, os, hashlib
from pathlib import Path
import yaml
from typing import Tuple
import datetime

from src.ConfigManager import ConfigManager
from src.DatabaseManager import DatabaseManager
from psycopg2.extensions import connection
from src.WarehouseManager import WarehouseManager
from src.ExcelLineageExtractor import ExcelLineageExtractor
from src.SchemaValidator import SchemaValidator
from src.WarehouseLoader import WarehouseLoader


class IngestionPipeline:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
       
        self.configer = ConfigManager()        
        self.datapath = self.configer.get_data_path()        
        self.config_path = self.configer.get_config_path()
        self.logger.info("Pipe init")
        try:
            self.schema = self.configer.import_schema()
        except FileNotFoundError:
            self.logger.error("Schema not Found in the path  %s",self.config_path )
            self.schema = {}
        self.logger.info(f"conf init{self.config_path }") 

        self.dbmanager = DatabaseManager({
            "dbname": os.getenv("DB_NAME", "rating_warehouse"),
            "user": os.getenv("DB_USER", "rating_warehouse_user"),
            "password": os.getenv("DB_PASSWORD"), 
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432))
        })
        self.sub_whmanger= WarehouseManager()

        self.extractor = ExcelLineageExtractor()

        self.validator = SchemaValidator(self.schema)
        self.warehouseloader = WarehouseLoader()

       
        
        

    def get_file_list(self)->list:
        self.logger.info("Fetching Data Files")
        target_files = [f for f in Path(self.datapath).glob("*.xlsm") if not f.name.startswith("~$")]
        return target_files

    def process_all_files(self,file_list: list):
        log_conn = self.dbmanager.get_connection() 
        tran_conn =  self.dbmanager.get_connection()
        

        bid = 0
        fname = Path("")

        try:
            for batch_id, ifile in enumerate(file_list, start=1):
                bid, fname = batch_id,ifile
                self.logger.info("Started Processing %s",ifile)
                self._process_single_file(file_path=Path(ifile), batch_id=batch_id,lconn=log_conn,tconn=tran_conn )
                log_conn.commit()

        except:
            self.logger.exception("Exception Occurred at File No %s  File Name %s",bid,fname)
        finally:
            # 5. Always safely release connections back to the pool
            if log_conn:
                
                self.dbmanager.put_connection(log_conn)  
            if tran_conn:
                self.dbmanager.put_connection(tran_conn)    

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
    
    def _process_single_file(self, file_path: Path, batch_id: int,lconn: connection,tconn:connection):
        self.logger.info("Extraction Starting for %s",file_path)
        meta_data,file_hash = self._generate_file_fingerprint(file_path)

        submission_id = self.sub_whmanger.insert_submission(file_name=file_path.name,file_meta=meta_data, conn=lconn)

        self.logger.info("New Submission id Created %s",submission_id)
        extract, lineage = self.extractor.extract(file_path=file_path)
        self.logger.info("Data Extraction. Completed %s",submission_id)
        valid,errors,valid_data =  self.validator.validate(raw_data=extract)


        if len(errors) == 0 :
            self.logger.info("Schema Validation Success ")
            # Update Submission status sucess
            sub_final_status = "IN PROGRESS"
            sub_current_status = "VALIDATION SUCCESS" 

        else:
            self.logger.info("Schema Validation Failure ")
            sub_final_status = "FAILED"
            sub_current_status = "VALIDATION FAILURE" 


        #self.logger.info("Clean Data  %s", valid_data)    
        
        sid = self.sub_whmanger.update_submission_post_validate(conn=lconn,submission_id=submission_id, 
                                                               final_status= sub_final_status, current_status=sub_current_status,
                                                               parsed_data=valid_data,
                                                               lineage=lineage
                                                               )
        self.warehouseloader.load(tconn=tconn,submission_id=submission_id,lconn=lconn)
    
        tconn.commit()

        

        


    def run_pipe(self):
        files = self.get_file_list()
        self.process_all_files(file_list=files)

    
    

    
    
 

        
        


               
             

    