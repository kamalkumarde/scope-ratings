# tests/test_api/test_api.py
import pytest
from unittest.mock import MagicMock, patch

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