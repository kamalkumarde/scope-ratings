#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
BASE_URL="http://localhost:8000/api/v1"
HEADER="accept: application/json"
OUTPUT_DIR="test_outputs"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Text Styling Helpers
log_section() {
    echo -e "\n========================================================================"
    echo -e "🚀 MODULE: $1"
    echo -e "========================================================================"
}

log_call() {
    echo -e "\n✨ Testing Endpoint: $1"
    echo -e "👉 Command: curl -s '$2' | jq"
    echo -e "💾 Saving to: $OUTPUT_DIR/$3"
    echo -e "------------------------------------------------------------------------"
}

# Ensure jq is installed before running
if ! command -v jq &> /dev/null; then
    echo "❌ Error: 'jq' is required but not installed. Please run: brew install jq"
    exit 1
fi

clear
echo "🧪 Starting Data Warehouse API End-to-End Verification Suite 🧪"
echo "📂 All programmatic JSON responses will be captured in the '$OUTPUT_DIR/' directory."


log_section "ENTITY MANAGEMENT CLUSTER (/companies)"

log_call "List & Paginate Companies" "$BASE_URL/companies?limit=10&offset=0" "companies_list.json"
curl -s -X 'GET' "$BASE_URL/companies?limit=10&offset=0" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/companies_list.json"

log_call "Get Master Company Details (ID: 43)" "$BASE_URL/companies/43" "company_43_details.json"
curl -s -X 'GET' "$BASE_URL/companies/43" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/company_43_details.json"

log_call "Get Company Version Dimensions (Company A)" "$BASE_URL/companies/Company%20A/versions" "company_A_versions.json"
curl -s -X 'GET' "$BASE_URL/companies/Company%20A/versions" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/company_A_versions.json"

log_call "Get Historical Audit Timeline (Company A)" "$BASE_URL/companies/Company%20A/history" "company_A_history.json"
curl -s -X 'GET' "$BASE_URL/companies/Company%20A/history" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/company_A_history.json"

log_call "Point-in-Time Peer Comparison Analysis" "$BASE_URL/companies/compare?company_ids=Company%20A&company_ids=Company%20B&as_of_date=2026-07-13" "companies_comparison.json"
curl -s -X 'GET' "$BASE_URL/companies/compare?company_ids=Company%20A&company_ids=Company%20B&as_of_date=2026-07-13" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/companies_comparison.json"


log_section "STATE SNAPSHOTS CLUSTER (/snapshots)"

log_call "Filter Snapshots for Company A" "$BASE_URL/snapshots?company_id=Company%20A" "snapshots_company_A.json"
curl -s -X 'GET' "$BASE_URL/snapshots?company_id=Company%20A" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/snapshots_company_A.json"

log_call "Get Isolated Structural Snapshot (ID: 25)" "$BASE_URL/snapshots/25" "snapshot_25_detail.json"
curl -s -X 'GET' "$BASE_URL/snapshots/25" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/snapshot_25_detail.json"

log_call "Get Absolute Latest State Matrix Across Portfolio" "$BASE_URL/snapshots/latest" "snapshots_latest.json"
curl -s -X 'GET' "$BASE_URL/snapshots/latest" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/snapshots_latest.json"


log_section "INGESTION AUDIT & LINEAGE CLUSTER (/uploads)"

log_call "Fetch Aggregate Pipeline Processing Metrics" "$BASE_URL/uploads/stats" "uploads_stats.json"
curl -s -X 'GET' "$BASE_URL/uploads/stats" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/uploads_stats.json"

log_call "List Recent Pipeline File Details Logs (Limit 5)" "$BASE_URL/uploads?limit=5" "uploads_list.json"
curl -s -X 'GET' "$BASE_URL/uploads?limit=5" -H "$HEADER" | jq '.' > "$OUTPUT_DIR/uploads_list.json"

echo -e "\n📥 Testing Endpoint: Download Original Ingestion Asset (ID: 568)"
echo -e "👉 Command: curl -X 'GET' '$BASE_URL/uploads/568/file' -o $OUTPUT_DIR/submission_013_valid.xlsm"
echo -e "------------------------------------------------------------------------"
curl -s -X 'GET' "$BASE_URL/uploads/568/file" -H "$HEADER" -o "$OUTPUT_DIR/submission_013_valid.xlsm"

if [ -f "$OUTPUT_DIR/submission_013_valid.xlsm" ]; then
    echo -e "✅ Success: Asset binary downloaded cleanly into $OUTPUT_DIR/submission_013_valid.xlsm!"
    ls -lh "$OUTPUT_DIR/submission_013_valid.xlsm"
else
    echo -e "❌ Error: File asset failed to stream into workspace."
fi

echo -e "\n========================================================================"
echo -e "🎉 End-to-End Verification Complete!"
echo -e "📁 Look in the './$OUTPUT_DIR/' folder for all response files."
echo -e "========================================================================"