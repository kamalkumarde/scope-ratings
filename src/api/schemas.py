from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

# --- Company & Versioning ---
class CompanyVersion(BaseModel):
    submission_id: int
    valid_from: datetime
    valid_to: Optional[datetime] = None
    is_current: bool

class CompanyDetailResponse(BaseModel):
    natural_id: str
    entity_name: str
    country_of_origin: str
    is_current: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None
    submission_id: Optional[int] = None
    metadata: Dict[str, Any]

# --- Snapshots ---
class SnapshotResponse(BaseModel):
    snapshot_id: int
    company_id: str
    as_of_date: date
    data: Dict[str, Any]

# --- Financial Metrics ---
class MetricDataPoint(BaseModel):
    calendar_year: int
    year_label: str
    metric_value: Optional[Decimal] = None
    metric_value_formatted: Optional[str] = None
    is_forecast: bool
    processing_status: str

class TimeSeriesAnalysisResponse(BaseModel):
    natural_id: str
    metric_name: str
    history: List[MetricDataPoint]

# --- Audits & Telemetry ---
class UploadAuditResponse(BaseModel):
    id: int
    filename: str
    status: str
    submitted_at: datetime
    execution_duration: float

class UploadAuditDetailResponse(BaseModel):
    id: int
    filename: str
    final_status: str
    current_status: str
    submitted_at: datetime
    execution_duration_seconds: float
    file_metadata: Dict[str, Any]
    parsed_data: Dict[str, Any]

class UploadStatsResponse(BaseModel):
    total_uploads: int
    successful_uploads: int
    failed_uploads: int
    processing_uploads: int