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
    country_of_origin: Optional[str] = None  # Safe against database NULL fields
    is_current: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None
    submission_id: Optional[int] = None
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True

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
    upload_id: int
    filename: str
    uploaded_at: datetime
    status: str
    submission_id: Optional[int] = None
    execution_stage: Optional[str] = None
    error_message: Optional[str] = None

class SnapshotImpactReference(BaseModel):
    natural_id: str
    entity_name: str
    country_of_origin: Optional[str] = None
    is_current: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None

class UploadAuditDetailResponse(BaseModel):
    upload_id: int
    filename: str
    uploaded_at: datetime
    status: str
    submission_id: Optional[int] = None
    execution_stage: Optional[str] = None
    error_message: Optional[str] = None
    impacted_snapshots: List[SnapshotImpactReference] = []

class UploadStatsResponse(BaseModel):
    total_pipeline_runs: int
    total_files_evaluated: int
    success_count: int
    failure_count: int
    skipped_count: int
    
class CompanySnapshotListItem(BaseModel):
    natural_id: str
    entity_name: str
    country_of_origin: Optional[str] = None
    is_current: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None
    submission_id: Optional[int] = None
    sector: Optional[str] = None
    currency: Optional[str] = None

    class Config:
        from_attributes = True    
