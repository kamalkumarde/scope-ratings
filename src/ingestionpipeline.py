import logging, os
from pathlib import Path
import yaml

from src.ConfigManager import ConfigManager
from src.DatabaseManager import DatabaseManager
from psycopg2.extensions import connection
from src.WarehouseManager import WarehouseManager


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
        self.whmanger = WarehouseManager()

        self.extractor = ExcelLineageExtractor()
       
        
        

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


    def _process_single_file(self, file_path: Path, batch_id: int,lconn: connection,tconn:connection):
        self.logger.info("Extraction Starting for %s",file_path)
        submission_id = self.whmanger.insert_submission(file_name=file_path.name,conn=lconn)
        self.logger.info("New Submission id Created %s",submission_id)







    def run_pipe(self):
        files = self.get_file_list()
        self.process_all_files(file_list=files)


import logging
import pandas as pd
from typing import Any, Tuple, Dict, List, Optional
from pathlib import Path
import hashlib
import datetime
        

class ExcelLineageExtractor:

    """E - Phase 1: Extracts raw layouts from cells and compiles asset audit fingerprints."""
    
    # Configuration-driven anchors to avoid hardcoding in logic
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ANCHOR_KEYS = {
        "SCOPE_METRICS": "[Scope Credit Metrics]"
    }
        

              
        
    
    

    
    
 

        
        


               
             

    