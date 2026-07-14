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

### Data Quality Report Upload Level

| run\_id | outcome | execution\_stage | substr | file\_count |
| :--- | :--- | :--- | :--- | :--- |
| 12 | FAILURE | 3.Validation | Mathematic | 3 |
| 11 | SUCCESS | 5.Transform | null | 24 |
| 13 | SKIPPED | 1.Initial | Duplicate  | 29 |
| 13 | FAILURE | 3.Validation | Mathematic | 3 |
| 12 | FAILURE | 3.Validation | Value viol | 78 |
| 12 | SKIPPED | 1.Initial | Duplicate  | 8 |
| 12 | FAILURE | 5.Transform | Warehouse  | 4 |
| 11 | FAILURE | 2.Extraction | sequence i | 1 |
| 11 | FAILURE | 3.Validation | Missing ma | 5 |
| 11 | FAILURE | 3.Validation | Mathematic | 3 |
| 13 | FAILURE | 3.Validation | Missing ma | 5 |
| 11 | SKIPPED | 1.Initial | Duplicate  | 8 |
| 11 | FAILURE | 3.Validation | Value viol | 78 |
| 12 | FAILURE | 2.Extraction | sequence i | 1 |
| 12 | FAILURE | 3.Validation | Missing ma | 5 |
| 13 | FAILURE | 3.Validation | Value viol | 78 |
| 13 | FAILURE | 5.Transform | Warehouse  | 4 |
| 12 | SUCCESS | 5.Transform | null | 20 |

 



### Data Quality Report File  Level


| submission\_id | error\_type | error\_per\_file |
| :--- | :--- | :--- |
| 1044 | Value violation | 3 |
| 921 | Value violation | 3 |
| 1177 | Value violation | 3 |
| 1079 | Value violation | 3 |
| 1032 | Value violation | 3 |
| 968 | Value violation | 3 |
| 1140 | Value violation | 3 |
| 933 | Value violation | 3 |
| 1147 | Value violation | 3 |
| 1204 | Value violation | 2 |
| 1064 | Value violation | 2 |
| 943 | Value violation | 2 |
| 1185 | Value violation | 2 |
| 1179 | Value violation | 2 |
| 995 | Value violation | 2 |
| 1080 | Value violation | 2 |
| 1175 | Value violation | 2 |
| 1063 | Value violation | 2 |
| 899 | Value violation | 2 |
| 1097 | Value violation | 2 |
| 1120 | Value violation | 2 |
| 1043 | Value violation | 2 |
| 1199 | Value violation | 2 |
| 1086 | Value violation | 2 |
| 1077 | Value violation | 2 |
| 1164 | Value violation | 2 |
| 957 | Value violation | 2 |
| 991 | Value violation | 2 |
| 1129 | Value violation | 2 |
| 1130 | Value violation | 2 |
| 936 | Value violation | 2 |
| 1205 | Value violation | 2 |
| 1109 | Value violation | 2 |
| 1047 | Value violation | 2 |
| 1068 | Value violation | 2 |
| 1192 | Value violation | 2 |
| 1194 | Value violation | 2 |
| 932 | Value violation | 2 |
| 1128 | Value violation | 2 |
| 1165 | Value violation | 2 |
| 1000 | Value violation | 2 |
| 970 | Value violation | 2 |
| 1018 | Value violation | 2 |
| 966 | Value violation | 2 |
| 969 | Value violation | 2 |
| 1088 | Value violation | 2 |
| 1146 | Value violation | 2 |
| 1021 | Value violation | 2 |
| 1003 | Value violation | 2 |
| 940 | Value violation | 2 |
| 1004 | Value violation | 2 |
| 910 | Value violation | 2 |
| 1083 | Value violation | 2 |
| 988 | Value violation | 2 |
| 979 | Value violation | 2 |
| 1096 | Value violation | 2 |
| 1020 | Value violation | 2 |
| 1154 | Value violation | 2 |
| 985 | Value violation | 2 |
| 1115 | Value violation | 2 |
| 977 | Value violation | 2 |
| 1202 | Value violation | 2 |
| 1111 | Value violation | 2 |
| 952 | Value violation | 2 |
| 1106 | Value violation | 2 |
| 1061 | Value violation | 2 |
| 1150 | Value violation | 2 |
| 1181 | Value violation | 2 |
| 1090 | Value violation | 2 |
| 1010 | Value violation | 2 |
| 1102 | Value violation | 2 |
| 1141 | Value violation | 1 |
| 956 | Value violation | 1 |
| 913 | Value violation | 1 |

