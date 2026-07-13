# tests/test_integration.py
import pytest
import psycopg2
from unittest.mock import MagicMock
from src.WarehouseLoader import WarehouseLoader
from src.WarehouseManager import WarehouseManager

def test_warehouse_manager_submission_lifecycle(db_transaction):
    manager = WarehouseManager()
    file_meta = {"file_size_bytes": 2048, "file_sha256_checksum": "xyz123"}
    
    # 1. Test entry ingestion mapping
    submission_id = manager.insert_submission(
        conn=db_transaction,
        run_id=1,
        file_name="test_sheet.xlsm",
        file_meta=file_meta,
        final_status="PROCESSING",
        current_status="START"
    )
    assert submission_id is not None
    assert submission_id > 0

    # 2. Test dynamic payload extraction binding updates
    parsed_payload = {"metadata": {"Rated entity": "Test Corp"}}
    lineage_payload = {"Test Corp": {"excel_row": 5}}
    
    update_success = manager.load_payload(
        conn=db_transaction,
        submission_id=submission_id,
        final_status="SUCCESS",
        current_status="VALIDATION SUCCESS",
        parsed_data=parsed_payload,
        lineage=lineage_payload
    )
    assert update_success


def test_warehouse_loader_scd2_cascade(db_transaction):
    mock_auditor = MagicMock()
    loader = WarehouseLoader(auditor=mock_auditor)
    manager = WarehouseManager()

    parsed_data = {
        "metadata": {
            "Rated entity": "Beta Global Inc",
            "Country of origin": "UK",
            "CorporateSector": "Energy",
            "Accounting principles": "IFRS",
            "Reporting Currency/Units": "GBP",
            "End of business year": "2025-12-31",
            "Industry risk": [
                {"sector": "Energy Infrastructure", "Industry risk score": "3", "Industry weight": "100%"}
            ]
        },
        "scopeCreditMetrics": {
            "years": ["2024", "2025"],
            "metrics": {
                "EBITDA": {"2024": 5000, "2025": 5500, "status": "Final"}
            }
        }
    }

    sub_id = manager.insert_submission(
        conn=db_transaction, run_id=1, file_name="beta_energy.xlsm",
        file_meta={}, final_status="PROCESSING", current_status="EXTRACTED"
    )
    manager.load_payload(db_transaction, sub_id, "PROCESSING", "STAGED", parsed_data, {})

    # Execute downstream star-schema load cascade logic pipelines directly
    load_outcome = loader.load(tconn=db_transaction, submission_id=sub_id)
    assert load_outcome is True

    # Validate that SCD2 entity dimensions tracked correctly inside target system layout
    with db_transaction.cursor() as cursor:
        cursor.execute("SELECT entity_key, is_current FROM dim_entities WHERE natural_key = %s", ("Beta Global Inc",))
        records = cursor.fetchall()
        assert len(records) == 1
        assert records[0][1] is True


def test_api_upload_file_streaming_lifecycle(db_transaction, api_client):
    """Tests the physical database integration using live Bytea stream downloads."""
    
    with db_transaction.cursor() as cursor:
        # 1. First insert a matching parent run record to satisfy the foreign key constraint
        cursor.execute("""
            INSERT INTO pipeline_runs (run_id, started_at, status)
            VALUES (1, NOW(), 'RUNNING')
            ON CONFLICT (run_id) DO NOTHING;
        """)
        
        # 2. Now stage the file asset detailing block safely
        cursor.execute("""
            INSERT INTO pipeline_file_details (id, run_id, file_name, processed_at, outcome, file_content)
            VALUES (999, 1, 'integration_test_sheet.xlsm', NOW(), 'SUCCESS', %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id;
        """, (psycopg2.Binary(b"FakeBinaryExcelContentsGoesHere"),))
    
    # Commit to cross connection lines safely so API container engine can see records
    db_transaction.commit()
    
    # 3. Execute target route fetch using our transaction-linked client
    response = api_client.get("/api/v1/uploads/999/file")
    
    # 4. Assert complete response binary mapping and mime layout validation
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.ms-excel.sheet.macroEnabled.12"
    assert "attachment; filename=integration_test_sheet.xlsm" in response.headers["content-disposition"]
    assert response.content == b"FakeBinaryExcelContentsGoesHere"