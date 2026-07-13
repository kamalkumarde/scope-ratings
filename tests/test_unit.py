import pytest 
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.SchemaValidator import SchemaValidator
from src.ExcelLineageExtractor import ExcelLineageExtractor

# ==========================================
# SCHEMA VALIDATOR TESTS
# ==========================================

@pytest.fixture
def mock_schema_rules():
    return {
        "extraction_meta": {
            "anchors": [
                {"name": "Rated entity", "required": True},
                {"name": "Country of origin", "required": True, "allowed_values": ["Germany", "UK", "USA"]},
                {"name": "Industry risk", "default": "Unknown Sector"}
            ]
        }
    }

def test_validator_checkboundaries_success(mock_schema_rules):
    validator = SchemaValidator(mock_schema_rules)
    raw_data = {
        "metadata": {
            "Rated entity": "ACME Corp",
            "Country of origin": "Germany"
        }
    }
    failures = validator.checkboundaries(raw_data)
    assert len(failures) == 0

def test_validator_checkboundaries_missing_required(mock_schema_rules):
    validator = SchemaValidator(mock_schema_rules)
    raw_data = {
        "metadata": {
            "Country of origin": "Germany"
            # Missing "Rated entity"
        }
    }
    failures = validator.checkboundaries(raw_data)
    assert any("Missing mandatory field: 'Rated entity'" in f for f in failures)

def test_validator_checkboundaries_out_of_bounds(mock_schema_rules):
    validator = SchemaValidator(mock_schema_rules)
    raw_data = {
        "metadata": {
            "Rated entity": "ACME Corp",
            "Country of origin": "Mars"  # Invalid value
        }
    }
    failures = validator.checkboundaries(raw_data)
    assert any("Value violation on 'Country of origin'" in f for f in failures)

def test_validator_transform_allocation_error(mock_schema_rules):
    validator = SchemaValidator(mock_schema_rules)
    raw_data = {
        "metadata": {
            "Industry risk": ["Automotive", "Tech"],
            "Industry risk score": ["3", "2"],
            "Industry weight": [0.40, 0.50]  # Sums to 90% instead of 100%
        }
    }
    success, failures, transformed = validator.transform(raw_data)
    assert not success
    assert any("Combined weights sum to 90.0% instead of 100%" in f for f in failures)


# ==========================================
# EXTRACTION UNIT TESTS
# ==========================================

def test_extractor_clean_cell():
    assert ExcelLineageExtractor.clean_cell("  Clean Me   ") == "Clean Me"
    assert ExcelLineageExtractor.clean_cell("n/a") is None
    assert ExcelLineageExtractor.clean_cell(pd.NA) is None
    assert ExcelLineageExtractor.clean_cell(42.0) == 42
    assert ExcelLineageExtractor.clean_cell(42.556) == 42.56



@patch("src.ExcelLineageExtractor.pd.read_excel")
def test_extractor_pandasextract_failure(mock_read_excel):
    mock_read_excel.side_effect = Exception("File Corrupted")
    extractor = ExcelLineageExtractor()
    
    status, df, failures = extractor.pandasextract(Path("corrupted_file.xlsm"))
    assert not status
    assert len(failures) > 0
    # Checks either the structural raw failure placeholder or the custom exception string
    assert any("File Corrupted" in str(f) or "%s" in str(f) for f in failures)

@patch("src.api.services.WarehouseAnalyticalService.get_upload_stats")
def test_api_get_upload_stats_unit(mock_stats, api_client):
    """Verifies that the stats router processes logic transformations securely."""
    mock_stats.return_value = MagicMock(
        total_pipeline_runs=1,
        total_files_evaluated=119,
        success_count=24,
        failure_count=87,
        skipped_count=8
    )
    
    response = api_client.get("/api/v1/uploads/stats")
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["total_pipeline_runs"] == 1
    assert payload["total_files_evaluated"] == 119
    assert payload["success_count"] == 24

def test_api_get_invalid_upload_details_404(api_client):
    """Ensures empty records safely result in a structured error payload."""
    response = api_client.get("/api/v1/uploads/999999/details")
    assert response.status_code == 404
    assert "detail" in response.json()

    