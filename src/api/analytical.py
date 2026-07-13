# src/api/analytical.py
import os
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from typing import List, Optional
from datetime import date
import io

from .dependencies import get_analytical_service
from .services import WarehouseAnalyticalService
from . import schemas

router = APIRouter(tags=["Credit Risk Warehouse Services Engine"])

# ==========================================
# 1. STATIC/EXPLICIT & COLLECTION ENDPOINTS (NO PATH PARAMS)
# ==========================================

@router.get("/snapshots", response_model=List[schemas.CompanySnapshotListItem])
def list_company_snapshots(
    company_id: Optional[str] = Query(None, description="Filter by company natural key (handles spaces)"),
    from_date: Optional[date] = Query(None, description="Start date of historical window (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date of historical window (YYYY-MM-DD)"),
    sector: Optional[str] = Query(None, description="Filter by corporate industrial sector"),
    country: Optional[str] = Query(None, description="Filter by country of origin"),
    currency: Optional[str] = Query(None, description="Filter by reporting base currency"),
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    """
    List historical company snapshots with advanced multi-criteria filters.
    """
    return service.list_snapshots(
        company_id=company_id, from_date=from_date, to_date=to_date,
        sector=sector, country=country, currency=currency
    )

@router.get("/snapshots/latest", response_model=List[schemas.SnapshotResponse])
def get_latest_snapshots(service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_latest_all_entities()

@router.get("/companies/search", response_model=schemas.CompanyDetailResponse)
def search_company_by_query(
    company_id: str = Query(..., description="The query identifier key of the entity"),
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    """Fetches company details via query parameters (?company_id=43)"""
    return service.get_company_by_id(company_id)

@router.get("/companies", response_model=List[schemas.CompanyDetailResponse])
def list_companies(
    limit: int = 100, 
    offset: int = 0, 
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    return service.get_active_companies(limit=limit, offset=offset)

@router.get("/companies/compare", response_model=List[schemas.CompanyDetailResponse])
def compare_companies_at_point_in_time(
    company_ids: List[str] = Query(..., description="List of company natural keys to compare"),
    as_of_date: date = Query(..., description="Target historical slice date (YYYY-MM-DD)"),
    service: WarehouseAnalyticalService = Depends(get_analytical_service)
):
    """
    Compares multiple companies at a specific point in time (Requirement #2).
    Resolves historical versions active on the provided slice date.
    """
    return service.get_pit_comparison(company_ids=company_ids, as_of_date=as_of_date)

@router.get("/uploads", response_model=List[schemas.UploadAuditResponse])
def list_upload_history(limit: int = 100, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_audits(limit=limit)

@router.get("/uploads/stats", response_model=schemas.UploadStatsResponse)
def get_upload_statistics(service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_stats()


# ==========================================
# 2. DYNAMIC PATH PARAMETER ROUTES (EVALUATED LAST)
# ==========================================

@router.get("/snapshots/{snapshot_id}", response_model=schemas.SnapshotResponse)
def get_snapshot_details(snapshot_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_snapshot_by_id(snapshot_id)

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

@router.get("/uploads/{upload_id}/details", response_model=schemas.UploadAuditDetailResponse)
def get_specific_upload_details(upload_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    return service.get_upload_details(upload_id)

@router.get("/uploads/{upload_id}/file")
def download_original_excel_file(upload_id: int, service: WarehouseAnalyticalService = Depends(get_analytical_service)):
    """
    Streams the original file asset directly from database bytea storage (Requirement #1).
    """
    filename, file_bytes = service.get_binary_file_content(upload_id)
    
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

