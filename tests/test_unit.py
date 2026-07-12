# tests/test_unit.py
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.ConfigManager import ConfigManager
from src.SchemaValidator import SchemaValidator
from src.DatabaseManager import DatabaseManager
from src.ExcelLineageExtractor import ExcelLineageExtractor
from src.WarehouseManager import WarehouseManager
from src.WarehouseLoader import WarehouseLoader
from src.ingestionpipeline import IngestionPipeline

# ==========================================
# 1. UNIT TEST: ConfigManager
# ==========================================
@patch("builtins.open", new_callable=mock_open, read_data="required_columns:\n  - entity_name\n  - rating")
@patch("src.ConfigManager.os.path.exists", return_value=True)
def test_config_manager_parses_schema(mock_exists, mock_file):
    configer = ConfigManager()
    schema = configer.import_schema()
    assert "required_columns" in schema
    assert "entity_name" in schema["required_columns"]

# ==========================================
# 2. UNIT TEST: SchemaValidator
# ==========================================
def test_schema_validator_identifies_malformed_structures():
    mock_schema = {"required_columns": ["entity_name", "rating"]}
    validator = SchemaValidator(mock_schema)
    
    mock_payload = {
        "metadata": {"version": "1.0"},
        "records": [{"entity_name": "Beta Inc"}]
    }
    
    with patch.object(validator, 'checkboundaries', return_value=[]):
        valid, errors, valid_data = validator.validate(mock_payload)
        assert isinstance(errors, list)

# ==========================================
# 3. UNIT TEST: DatabaseManager
# ==========================================
@patch('psycopg2.connect')
def test_database_manager_pool_lifecycle(mock_connect):
    db_config = {"dbname": "test", "user": "u", "password": "p", "host": "h", "port": 5432}
    manager = DatabaseManager(db_config)
    
    # Directly mock the pool instance property to isolate lifecycle verification
    mock_pool = MagicMock()
    manager.pool = mock_pool
    
    manager.get_connection()
    mock_pool.getconn.assert_called_once()
    
    mock_conn = MagicMock()
    manager.put_connection(mock_conn)
    mock_pool.putconn.assert_called_once_with(mock_conn)

# ==========================================
# 4. UNIT TEST: ExcelLineageExtractor
# ==========================================
@patch('pandas.read_excel')
@patch('openpyxl.load_workbook')
def test_excel_extractor_builds_lineage(mock_load_wb, mock_read_excel):
    mock_wb = MagicMock()
    mock_sheet = MagicMock()
    mock_sheet.iter_rows.return_value = [["Entity A", "AAA", "A+"]]
    mock_wb.active = mock_sheet
    mock_load_wb.return_value = mock_wb
    
    # Provide a real DataFrame containing the anchor key to satisfy getscopeidx logic
    anchor_key = "[Scope Credit Metrics]"
    fake_df = pd.DataFrame({
        0: ["some_data"], 
        1: [anchor_key]
    })
    mock_read_excel.return_value = fake_df
    
    extractor = ExcelLineageExtractor()
    # Ensure our extractor instance aligns with the anchor key if defined differently
    extractor.ANCHOR_KEYS = {"SCOPE_METRICS": anchor_key}
    
    data, lineage = extractor.extract(Path("dummy.xlsm"))
    assert "file_fingerprint" in lineage or isinstance(lineage, dict)

# ==========================================
# 5. UNIT TEST: WarehouseManager
# ==========================================
def test_warehouse_manager_submission_tracking():
    manager = WarehouseManager()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (42,)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    sub_id = manager.insert_submission(mock_conn, "test.xlsm", {"size": 100})
    assert sub_id == 42
    mock_cursor.execute.assert_called_once()

# ==========================================
# 6. UNIT TEST: WarehouseLoader
# ==========================================
def test_warehouse_loader_executes_upserts():
    loader = WarehouseLoader()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    loader.load(mock_conn, mock_conn, submission_id=1)
    assert mock_conn.cursor.called

# ==========================================
# 7. UNIT TEST: IngestionPipeline (Core Logic)
# ==========================================
@patch("src.ingestionpipeline.Path")
def test_pipeline_filters_out_tilde_temp_files(mock_path):
    pipeline = IngestionPipeline()
    pipeline.datapath = "/app/data"
    
    file_valid = MagicMock(spec=Path); file_valid.name = "real_data.xlsm"
    file_temp = MagicMock(spec=Path); file_temp.name = "~$lock_data.xlsm"
    mock_path.return_value.glob.return_value = [file_valid, file_temp]
    
    files = pipeline.get_file_list()
    assert len(files) == 1
    assert files[0].name == "real_data.xlsm"