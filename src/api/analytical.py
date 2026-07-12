import os
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import date

from .dependencies import get_analytical_service
from .services import WarehouseAnalyticalService
from . import schemas

router = APIRouter(tags=["Credit Risk Warehouse Services Engine"])

# ==========================================
# COMPANY ROUTING BOUNDARIES
# ==========================================
@router.get("/companies", response_model=List[schemas.CompanyDetailResponse])
def list_companies(limit: int = 100, offset: int = 0, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_active_companies(limit=limit, offset=offset)

@router.get("/companies/compare", response_model=List[schemas.CompanyDetailResponse])
def compare_companies_point_in_time(
    company_ids: List[str] = Query(..., description="Target list of natural_ids"),
    as_of_date: date = Query(..., description="Target Point-in-Time benchmark target execution slice"),
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    return service.get_pit_comparison(company_ids=company_ids, as_of_date=as_of_date)

@router.get("/companies/{company_id}", response_model=schemas.CompanyDetailResponse)
def get_company_details(company_id: str, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_company_by_id(company_id)

@router.get("/companies/{company_id}/versions", response_model=List[schemas.CompanyVersion])
def get_company_versions(company_id: str, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_entity_versions(company_id)

@router.get("/companies/{company_id}/history", response_model=List[schemas.TimeSeriesAnalysisResponse])
def get_company_time_series_history(
    company_id: str, 
    metrics: Optional[List[str]] = Query(None, description="Target execution filter labels"),
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    return service.get_historical_metrics(company_id=company_id, metrics=metrics)

# ==========================================
# SNAPSHOT ROUTING BOUNDARIES
# ==========================================
@router.get("/snapshots", response_model=List[schemas.SnapshotResponse])
def list_snapshots(
    company_id: Optional[str] = None, from_date: Optional[date] = None, to_date: Optional[date] = None,
    sector: Optional[str] = None, country: Optional[str] = None, currency: Optional[str] = None,
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    return service.get_snapshots(company_id, from_date, to_date, sector, country, currency)

@router.get("/snapshots/latest", response_model=List[schemas.SnapshotResponse])
def get_latest_snapshots(service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_latest_all_entities()

@router.get("/snapshots/{snapshot_id}", response_model=schemas.SnapshotResponse)
def get_snapshot_details(snapshot_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_snapshot_by_id(snapshot_id)

# ==========================================
# AUDITING & BINARY DOWNLOADS
# ==========================================
@router.get("/uploads", response_model=List[schemas.UploadAuditResponse])
def list_upload_history(limit: int = 100, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_audits(limit=limit)

@router.get("/uploads/stats", response_model=schemas.UploadStatsResponse)
def get_upload_statistics(service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_stats()

@router.get("/uploads/{upload_id}/details", response_model=schemas.UploadAuditDetailResponse)
def get_specific_upload_details(upload_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_details(upload_id)

@router.get("/uploads/{upload_id}/file")
def download_original_excel_file(upload_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    file_path = service.get_binary_storage_path(upload_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Spreadsheet asset missing from disk storage volume.")
    
    friendly_name = os.path.basename(file_path)
    return FileResponse(
        path=file_path, 
        filename=friendly_name, 
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12"
    )