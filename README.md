# Scope Ratings Pipeline

This project is an automated data ingestion and transformation pipeline designed to process rating-related metadata from Excel sheets and load them into a relational warehouse using SCD Type 2 (Slowly Changing Dimension) tracking.

## 📌 Project Overview
The pipeline automates the extraction, validation, and loading of credit rating data, ensuring structural integrity and historical traceability.

## 🚀 Key Features
* **Automated Validation**: Ensures data compliance with predefined schema rules.
* **Data Transformation**: Handles complex logic such as dynamic matrix padding and JSON restructuring.
* **SCD Type 2 Warehouse**: Maintains historical records using hash-based change detection.
* **Atomic Transactions**: Processes submissions using robust SQL transactions to prevent data inconsistency.

## 📂 Project Structure
```plaintext
scope-ratings/
├── api/                    # FastAPI endpoints and business logic layers
│   ├── __init__.py
│   ├── analytical.py
│   ├── dependencies.py
│   ├── main.py
│   ├── schemas.py
│   └── services.py
├── audit.py                # Logging and lineage tracking
├── ConfigManager.py        # Configuration and environment handling
├── DatabaseManager.py      # Core database connection and transaction handling
├── ExcelLineageExtractor.py# Parsing logic for Excel metadata
├── ingestionpipeline.py    # Orchestrates the flow from extraction to storage
├── PipelineRunManager.py   # Manages state and execution of pipeline runs
├── SchemaValidator.py      # Structural and value compliance logic
├── WarehouseLoader.py      # Handles data persistence into SCD tables
└── WarehouseManager.py     # High-level management of warehouse interactions
```

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/kamalkumarde/scope-ratings.git
cd scope-ratings
mkdir data dlq archive log
```

### 2. Build and Deploy
```bash
docker compose up -d --build
# veify API health
curl -X GET http://localhost:8000/health

docker compose run pipeline
```

### 3. Database Initialization
Ensure the PostgreSQL container is running and execute your DDL migration scripts to initialize the required schema tables.

## 🔌 API Documentation
The project includes a RESTful API built with FastAPI.  
**Base URL**: `http://localhost:8000/api/v1`

### Company Endpoints
* **List Companies**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/companies?limit=10&offset=0' -H 'accept: application/json' | jq
  ```
* **Get Company**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/companies/43' -H 'accept: application/json' | jq
  ```
* **List Versions**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/companies/Company%20A/versions' -H 'accept: application/json' | jq
  ```
* **Get History**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/companies/Company%20A/history' -H 'accept: application/json' | jq
  ```
* **Compare Companies**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/companies/compare?company_ids=Company%20A&company_ids=Company%20B&as_of_date=2026-07-13' -H 'accept: application/json' | jq
  ```

### Snapshot Endpoints
* **Filter by Company**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/snapshots?company_id=Company%20A' -H 'accept: application/json' | jq
  ```
* **Latest Snapshot**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/snapshots/latest' -H 'accept: application/json' | jq
  ```

### Upload & Submission Endpoints
* **List Uploads**:
  ```bash
  curl -s -X 'GET' 'http://localhost:8000/api/v1/uploads?limit=10' -H 'accept: application/json' | jq
  ```
* **Download File**:
  ```bash
  curl -X 'GET' 'http://localhost:8000/api/v1/uploads/568/file' -H 'accept: application/json' -o submission_013_valid.xlsm
  ```

## ⚙️ Usage

### Run Tests
```bash
docker compose run --rm -v "$(pwd):/app" pipeline pytest tests/test_pipeline/ tests/test_integration.py -v
docker compose run --rm -v "$(pwd):/app" --workdir /app api pytest tests/test_api/ tests/test_integration.py::test_api_upload_file_streaming_lifecycle -v
```


### Run the Pipeline move the data files to the data folder in the project root
```bash
docker compose run pipeline 
```
 
### Curls to run all the apis or run test/api_verifier.sh to get the seperate json files per api call

```bash
curl -s -X 'GET' \
  'http://localhost:8000/api/v1/companies?limit=10&offset=0' \
  -H 'accept: application/json' | jq


  curl -s -X 'GET' \
  'http://localhost:8000/api/v1/companies/43 \
  -H 'accept: application/json' | jq

   curl -s -X 'GET' \
  'http://localhost:8000/api/v1/companies/Company%20A/versions' \
  -H 'accept: application/json' | jq

 curl -s -X 'GET' 'http://localhost:8000/api/v1/companies/Company%20A/history' \
 -H 'accept: application/json' | jq

 curl -s -X 'GET' \
  'http://localhost:8000/api/v1/companies/compare?company_ids=Company%20A&company_ids=Company%20B&as_of_date=2026-07-13' \
  -H 'accept: application/json' | jq


  curl -s -X 'GET' \
  'http://localhost:8000/api/v1/snapshots?company_id=Company%20A' \
  -H 'accept: application/json' | jq


   curl -s -X 'GET' \
  'http://localhost:8000/api/v1/snapshots/25' \
  -H 'accept: application/json' | jq

  curl -s -X 'GET' \
  'http://localhost:8000/api/v1/snapshots/latest' \
  -H 'accept: application/json' | jq


  curl -s -X 'GET' \
  'http://localhost:8000/api/v1/uploads?limit=10' \
  -H 'accept: application/json' | jq

  curl -s -X 'GET' 'http://localhost:8000/api/v1/uploads/stats' -H 'accept: application/json' | jq
{

curl -s -X 'GET' 'http://localhost:8000/api/v1/uploads?limit=5' -H 'accept: application/json' | jq

curl -X 'GET' \
  'http://localhost:8000/api/v1/uploads/568/file' \
  -H 'accept: application/json' \
  -o submission_013_valid.xlsm


```
 

