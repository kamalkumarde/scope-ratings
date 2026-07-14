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
| 1186 | Value violation | 2 |
| 1081 | Value violation | 2 |
| 998 | Value violation | 2 |
| 1178 | Value violation | 2 |
| 907 | Value violation | 2 |
| 1157 | Value violation | 2 |
| 1162 | Value violation | 2 |
| 975 | Value violation | 2 |
| 1168 | Value violation | 2 |
| 950 | Value violation | 2 |
| 1022 | Value violation | 2 |
| 1196 | Value violation | 2 |
| 1184 | Value violation | 2 |
| 1183 | Value violation | 2 |
| 1126 | Value violation | 2 |
| 986 | Value violation | 2 |
| 1114 | Value violation | 2 |
| 953 | Value violation | 2 |
| 909 | Value violation | 2 |
| 1087 | Value violation | 2 |
| 972 | Value violation | 2 |
| 1099 | Value violation | 2 |
| 1191 | Value violation | 2 |
| 1051 | Value violation | 2 |
| 1200 | Value violation | 2 |
| 976 | Value violation | 2 |
| 1054 | Value violation | 2 |
| 911 | Value violation | 2 |
| 1127 | Value violation | 1 |
| 1153 | Mathematical al | 1 |
| 1133 | Value violation | 1 |
| 986 | Mathematical al | 1 |
| 1046 | Value violation | 1 |
| 992 | Value violation | 1 |
| 1062 | Value violation | 1 |
| 971 | Value violation | 1 |
| 1166 | Value violation | 1 |
| 1039 | Missing mandato | 1 |
| 923 | Value violation | 1 |
| 1095 | Mathematical al | 1 |
| 1038 | Value violation | 1 |
| 994 | Value violation | 1 |
| 1187 | Value violation | 1 |
| 1009 | Value violation | 1 |
| 1034 | Value violation | 1 |
| 1067 | Value violation | 1 |
| 1138 | Mathematical al | 1 |
| 1075 | Value violation | 1 |
| 1017 | Mathematical al | 1 |
| 1074 | Value violation | 1 |
| 1013 | Missing mandato | 1 |
| 960 | Value violation | 1 |
| 1169 | Mathematical al | 1 |
| 1026 | Value violation | 1 |
| 1131 | Value violation | 1 |
| 984 | Mathematical al | 1 |
| 1193 | Value violation | 1 |
| 1100 | Value violation | 1 |
| 1192 | Mathematical al | 1 |
| 1179 | Mathematical al | 1 |
| 1197 | Value violation | 1 |
| 1012 | Value violation | 1 |
| 1176 | Value violation | 1 |
| 1092 | Value violation | 1 |
| 1002 | Mathematical al | 1 |
| 1174 | Value violation | 1 |
| 1138 | Missing mandato | 1 |
| 947 | Value violation | 1 |
| 1182 | Value violation | 1 |
| 981 | Value violation | 1 |
| 1072 | Value violation | 1 |
| 969 | Mathematical al | 1 |
| 916 | Missing mandato | 1 |
| 917 | Value violation | 1 |
| 1169 | Missing mandato | 1 |
| 1152 | Value violation | 1 |
| 1125 | Value violation | 1 |
| 942 | Value violation | 1 |
| 937 | Value violation | 1 |
| 1081 | Mathematical al | 1 |
| 967 | Value violation | 1 |
| 1132 | Value violation | 1 |
| 1042 | Value violation | 1 |
| 1116 | Mathematical al | 1 |
| 1071 | Value violation | 1 |
| 1144 | Mathematical al | 1 |
| 1058 | Value violation | 1 |
| 1078 | Value violation | 1 |
| 1119 | Value violation | 1 |
| 1028 | Value violation | 1 |
| 1024 | Value violation | 1 |
| 912 | Value violation | 1 |
| 1084 | Value violation | 1 |
| 1082 | Value violation | 1 |
| 1142 | Mathematical al | 1 |
| 999 | Value violation | 1 |
| 938 | Value violation | 1 |
| 1178 | Mathematical al | 1 |
| 987 | Value violation | 1 |
| 1035 | Mathematical al | 1 |
| 1055 | Value violation | 1 |
| 951 | Value violation | 1 |
| 1115 | Mathematical al | 1 |
| 980 | Value violation | 1 |
| 955 | Value violation | 1 |
| 1135 | Mathematical al | 1 |
| 900 | Value violation | 1 |
| 1190 | Mathematical al | 1 |
| 1015 | Value violation | 1 |
| 1052 | Value violation | 1 |
| 1023 | Value violation | 1 |
| 908 | Value violation | 1 |
| 939 | Mathematical al | 1 |
| 1097 | Mathematical al | 1 |
| 1025 | Value violation | 1 |
| 1019 | Value violation | 1 |
| 1098 | Value violation | 1 |
| 1004 | Mathematical al | 1 |
| 1171 | Value violation | 1 |
| 1117 | Value violation | 1 |
| 970 | Mathematical al | 1 |
| 944 | Value violation | 1 |
| 919 | Missing mandato | 1 |
| 902 | Missing mandato | 1 |
| 1123 | Missing mandato | 1 |
| 1149 | Value violation | 1 |
| 1137 | Value violation | 1 |
| 1070 | Missing mandato | 1 |
| 959 | Missing mandato | 1 |
| 915 | Value violation | 1 |
| 1136 | Value violation | 1 |
| 941 | Value violation | 1 |
| 1049 | Value violation | 1 |
| 946 | Value violation | 1 |
| 1167 | Value violation | 1 |
| 989 | Value violation | 1 |
| 935 | Value violation | 1 |
| 901 | Value violation | 1 |
| 1030 | Mathematical al | 1 |
| 1030 | Missing mandato | 1 |
| 916 | Mathematical al | 1 |
| 897 | Value violation | 1 |
| 928 | Mathematical al | 1 |
| 1013 | Mathematical al | 1 |
| 914 | Value violation | 1 |
| 904 | Value violation | 1 |
| 1180 | Value violation | 1 |
| 1144 | Missing mandato | 1 |
| 1173 | Value violation | 1 |
| 1050 | Value violation | 1 |
| 1011 | Value violation | 1 |
| 1195 | Value violation | 1 |
| 1134 | Value violation | 1 |
| 1113 | Value violation | 1 |
| 1163 | Value violation | 1 |
| 939 | Value violation | 1 |
| 1017 | Value violation | 1 |
| 964 | Value violation | 1 |
| 1020 | Mathematical al | 1 |
| 982 | Value violation | 1 |
| 959 | Mathematical al | 1 |
| 1124 | Value violation | 1 |
| 1039 | Mathematical al | 1 |
| 1070 | Mathematical al | 1 |
| 1203 | Mathematical al | 1 |
| 1007 | Value violation | 1 |
| 1027 | Missing mandato | 1 |
| 1155 | Value violation | 1 |
| 1125 | Mathematical al | 1 |
| 927 | Value violation | 1 |
| 1113 | Mathematical al | 1 |
| 924 | Mathematical al | 1 |
| 1189 | Value violation | 1 |
| 1091 | Value violation | 1 |
| 1160 | Value violation | 1 |
| 918 | Value violation | 1 |
| 1188 | Value violation | 1 |
| 1053 | Value violation | 1 |
| 909 | Mathematical al | 1 |
| 906 | Mathematical al | 1 |
| 1158 | Value violation | 1 |
| 1198 | Value violation | 1 |
| 1121 | Value violation | 1 |
| 1151 | Value violation | 1 |
| 1128 | Mathematical al | 1 |
| 1029 | Value violation | 1 |
| 1066 | Value violation | 1 |
| 1057 | Value violation | 1 |
| 919 | Mathematical al | 1 |
| 1123 | Mathematical al | 1 |
| 1110 | Value violation | 1 |
| 1118 | Value violation | 1 |
| 1201 | Value violation | 1 |
| 1143 | Value violation | 1 |
| 973 | Value violation | 1 |
| 894 | Mathematical al | 1 |
| 1205 | Mathematical al | 1 |
| 1050 | Mathematical al | 1 |
| 898 | Value violation | 1 |
| 902 | Mathematical al | 1 |
| 1080 | Mathematical al | 1 |
| 1093 | Value violation | 1 |
| 931 | Value violation | 1 |
| 1159 | Value violation | 1 |
| 1153 | Value violation | 1 |
| 906 | Value violation | 1 |
| 1005 | Mathematical al | 1 |
| 1122 | Value violation | 1 |
| 896 | Value violation | 1 |
| 1203 | Value violation | 1 |
| 1145 | Value violation | 1 |
| 1048 | Value violation | 1 |
| 1027 | Mathematical al | 1 |
| 1008 | Value violation | 1 |
| 1156 | Value violation | 1 |
| 1103 | Value violation | 1 |
| 1002 | Value violation | 1 |
| 961 | Value violation | 1 |
| 928 | Missing mandato | 1 |
| 1105 | Value violation | 1 |
| 1135 | Missing mandato | 1 |
| 1170 | Value violation | 1 |
| 963 | Value violation | 1 |
| 1141 | Value violation | 1 |
| 956 | Value violation | 1 |
| 913 | Value violation | 1 |

