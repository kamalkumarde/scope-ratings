import logging
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self, project_root_path: str = None):
        load_dotenv()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if project_root_path is None:
            self.project_root = Path(__file__).resolve().parent.parent
        else:
            self.project_root = Path(project_root_path).resolve()
            
        print(f"[DEBUG] Project root is resolved to: {self.project_root}")

    def get_data_path(self) -> Path:
        if not self.project_root:
            raise ValueError("Project root is not set.")
        
        datapath = self.project_root / "data"
        datapath.mkdir(parents=True, exist_ok=True)
        return datapath    

    def get_config_path(self) -> Path:
        config_dir = self.project_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "schema.yml"

    def import_schema(self) -> dict:
        config_path = self.get_config_path()
        
        if not config_path.exists():
            self.logger.warning(f"Schema file not found at {config_path}.")
            return {}
            
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
