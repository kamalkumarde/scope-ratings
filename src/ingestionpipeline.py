import logging
from pathlib import Path
import yaml
from dotenv import load_dotenv
import os


class ConfigManager:
    def __init__(self, script_path: str = __file__):
        load_dotenv()
        self.src_dir = Path(script_path).resolve().parent.parent
        self.project_root = self.src_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        

    def get_config_path(self) -> Path:
        if not self.project_root:
            self.logger.error("Project root is not set.")
            raise ValueError("Project root is not set.")
        
        return self.project_root / "config" / "schema.yml"

    def get_data_path(self) -> Path:
        if not self.project_root:
            self.logger.error("Project root is not set.")
            raise ValueError("Project root is not set.")
        return self.project_root / "data"

    def import_schema(self) -> dict:
        with open(self.get_config_path(), "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
  
class IngestionPipeline:

    def __init__(self):
        self.configer = ConfigManager()
        self.projectroot = self.configer.get_config_path()
        self.datapath = self.configer.get_data_path()
        self.schema = self.configer.import_schema()
        
    