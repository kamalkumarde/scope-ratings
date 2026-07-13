# AI Usage Declaration

This document tracks the utilization of Artificial Intelligence (AI) tools across the components of the codebase.

## 📊 Summary Table

| Code Base | AI Used | Percentage (%) | Reason | Tool |
| :--- | :---: | :---: | :--- | :--- |
| **api** | **YES** | — | — | Gemini |
| ├── `__init__.py` | YES | 70% | Productivity and time constraints; embedded SQLs | Gemini |
| ├── `analytical.py` | YES | 70% | Productivity and time constraints; embedded SQLs | Gemini |
| ├── `dependencies.py` | YES | 70% | Productivity and time constraints; embedded SQLs | Gemini |
| ├── `main.py` | YES | 70% | Productivity and time constraints; embedded SQLs | Gemini |
| ├── `schemas.py` | NO | — | — | Gemini |
| └── `services.py` | YES | 70% | Productivity and time constraints; boilerplate code | Gemini |
| **audit.py** | NO | — | — | Gemini |
| **ConfigManager.py** | NO | — | — | Gemini |
| **DatabaseManager.py** | NO | — | — | Gemini |
| **ExcelLineageExtractor.py** | YES | 50% | For verifying validation and pandas functionality | Gemini |
| **ingestionpipeline.py** | NO | 10% | — | Gemini |
| **PipelineRunManager.py** | NO | — | — | Gemini |
| **SchemaValidator.py** | YES | 50% | For schema-based validation using YAML | Gemini |

## 🔍 Key Insights
* **Primary Tool**: Google Gemini was used exclusively for all AI-assisted tasks.
* **Core API Layer**: Heavily optimized using AI (70%) to handle boilerplate structures and accelerate the implementation of embedded SQL queries.
* **Data Processing**: AI assisted significantly (50%) in specific validation mechanics and data processing patterns (pandas).
* **Core Architecture**: Key orchestration and state management components (`ConfigManager`, `DatabaseManager`, `PipelineRunManager`) were developed completely without AI assistance.
