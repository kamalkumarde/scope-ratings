
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
    @staticmethod
    def clean_cell(value: Any) -> Optional[Any]:
        if pd.isna(value):
            return None
        if isinstance(value, float):
            return int(value) if value.is_integer() else round(value, 2)
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() in ("no data", "n/a", "na"):
                return None
            return value
        return value    
    def pandasextract(self, file_path: Path) -> pd.DataFrame:
        raw_df = pd.read_excel(file_path, sheet_name="MASTER", engine="openpyxl", header=None)
        return raw_df
    def getscopeidx(self,raw_df: pd.DataFrame)->int:
        scope_start = raw_df[raw_df[1] == self.ANCHOR_KEYS["SCOPE_METRICS"]].index
        if scope_start.empty:
            raise ExtractionError(f"Anchor '{self.ANCHOR_KEYS['SCOPE_METRICS']}' not found in {file_path.name}")
        
        scope_idx = scope_start[0]
        return scope_idx
    
    def _extract_metadata_rows(self, raw_df: pd.DataFrame, scope_start_idx: int) -> Tuple[Dict, Dict]:
        """Extracts key-value pairs before the scope metrics anchor."""
        metadata = {}
        lineage = {}
        
        for idx in range(scope_start_idx):
            key = self.clean_cell(raw_df.iat[idx, 1])
            if not key: continue
            
            # Capture all values in the row starting from column 2
            row_values = [self.clean_cell(raw_df.iat[idx, c]) for c in range(2, len(raw_df.columns)) 
                          if self.clean_cell(raw_df.iat[idx, c]) is not None]

            lineage[str(key)] = {
                "source_sheet": "MASTER",
                "excel_row": int(idx + 1),
                "excel_columns": [int(c + 1) for c in range(2, 2 + len(row_values))]
            }
            metadata[key] = row_values[0] if len(row_values) == 1 else (row_values if row_values else None)
            
        return metadata, lineage
    def getyears(self,raw_df:pd.DataFrame,idx:int)->List:
        years = [self.clean_cell(raw_df.iat[idx, c]) for c in range(2, len(raw_df.columns)) 
                 if self.clean_cell(raw_df.iat[idx, c]) is not None]
        return years
    
    def getmetrics(self,raw_df:pd.DataFrame,idx:int,years:List)->Dict:
        metrics = {}
        for row_idx in range(idx + 1, len(raw_df)):
            metric_name = self.clean_cell(raw_df.iat[row_idx, 1])
            if not metric_name: break
            
            metric_values = {str(year): self.clean_cell(raw_df.iat[row_idx, i + 2]) 
                             for i, year in enumerate(years)}
            metric_values["status"] = self.clean_cell(raw_df.iat[row_idx, 2 + len(years)])
            metrics[metric_name] = metric_values
        return metrics  
    
    



    def extract(self, file_path: Path) ->Tuple[Dict,Dict]:
        self.logger.info("Starting to Extract Data from %s using Pandas", file_path) 
        df = self.pandasextract(file_path=file_path)
        self.logger.info("Read Data to Data Frame Shape of data %s", df.shape) 
        scope_idx = self.getscopeidx(raw_df=df)
        self.logger.info("Index of the metrics %s", scope_idx) 
        meta_data, lineage = self._extract_metadata_rows(raw_df=df, scope_start_idx=scope_idx)
        
        years = self.getyears(raw_df=df,idx = scope_idx)

        metrics = self.getmetrics(raw_df=df,idx=scope_idx,years=years)

        result = {"metadata": meta_data, "scopeCreditMetrics": {"years": years, "metrics": metrics}}
        self.logger.info("Extraction Successful ") 
        return result,lineage
    

        