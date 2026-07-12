import json
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from . import schemas

class WarehouseAnalyticalService:
    def __init__(self, db_connection):
        self.db = db_connection

    # ==========================================
    # COMPANY ENGINE
    # ==========================================
    def get_active_companies(self, limit: int, offset: int) -> List[schemas.CompanyDetailResponse]:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT de.natural_id, de.entity_name, de.country_of_origin, 
                       de.is_current, de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE de.is_current = TRUE
                ORDER BY de.entity_name LIMIT %s OFFSET %s;
            """, (limit, offset))
            return [self._map_company(r) for r in cursor.fetchall()]

    def get_company_by_id(self, company_id: str) -> schemas.CompanyDetailResponse:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT de.natural_id, de.entity_name, de.country_of_origin, 
                       de.is_current, de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE de.natural_id = %s AND de.is_current = TRUE;
            """, (company_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")
            return self._map_company(row)

    def get_entity_versions(self, natural_id: str) -> List[schemas.CompanyVersion]:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT submission_id, valid_from, valid_to, is_current 
                FROM dim_entities 
                WHERE natural_id = %s ORDER BY valid_from DESC;
            """, (natural_id,))
            return [schemas.CompanyVersion(submission_id=r[0], valid_from=r[1], valid_to=r[2], is_current=r[3]) for r in cursor.fetchall()]

    def get_pit_comparison(self, company_ids: List[str], as_of_date: date) -> List[schemas.CompanyDetailResponse]:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT de.natural_id, de.entity_name, de.country_of_origin, de.is_current, 
                       de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE de.natural_id = ANY(%s) 
                  AND de.valid_from <= %s 
                  AND (de.valid_to > %s OR de.valid_to IS NULL);
            """, (company_ids, as_of_date, as_of_date))
            return [self._map_company(r) for r in cursor.fetchall()]

    def get_historical_metrics(self, company_id: str, metrics: Optional[List[str]]) -> List[schemas.TimeSeriesAnalysisResponse]:
        with self.db.cursor() as cursor:
            query = """
                SELECT de.natural_id, f.metric_name, f.calendar_year, f.year_label, 
                       f.metric_value, f.metric_value_formatted, f.is_forecast, f.processing_status
                FROM fct_rating_metric f
                JOIN dim_entities de ON f.entity_key = de.entity_key
                WHERE de.natural_id = %s
            """
            params = [company_id]
            if metrics:
                query += " AND f.metric_name = ANY(%s)"
                params.append(metrics)
            query += " ORDER BY f.metric_name, f.calendar_year ASC;"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                raise HTTPException(status_code=404, detail="No historical observations found.")

            grouped = {}
            for r in rows:
                grouped.setdefault(r[1], []).append(schemas.MetricDataPoint(
                    calendar_year=r[2], year_label=r[3], metric_value=r[4],
                    metric_value_formatted=r[5], is_forecast=r[6], processing_status=r[7]
                ))
            return [schemas.TimeSeriesAnalysisResponse(natural_id=company_id, metric_name=k, history=v) for k, v in grouped.items()]

    # ==========================================
    # SNAPSHOT ENGINE
    # ==========================================
    def get_snapshots(self, company_id: Optional[str], from_date: Optional[date], to_date: Optional[date],
                      sector: Optional[str], country: Optional[str], currency: Optional[str]) -> List[schemas.SnapshotResponse]:
        with self.db.cursor() as cursor:
            # We filter dynamically against our SCD2 timeline
            query = """
                SELECT de.entity_key, de.natural_id, COALESCE(de.valid_from::date, CURRENT_DATE), s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE 1=1
            """
            params = []
            if company_id:
                query += " AND de.natural_id = %s"; params.append(company_id)
            if from_date:
                query += " AND de.valid_from >= %s"; params.append(from_date)
            if to_date:
                query += " AND de.valid_from <= %s"; params.append(to_date)
            if country:
                query += " AND de.country_of_origin = %s"; params.append(country)
            
            # If your custom metadata object carries inner system keys like sector/currency:
            if sector:
                query += " AND (s.parsed_data->'metadata'->>'sector') = %s"; params.append(sector)
            if currency:
                query += " AND (s.parsed_data->'metadata'->>'currency') = %s"; params.append(currency)

            cursor.execute(query, params)
            return [
                schemas.SnapshotResponse(
                    snapshot_id=r[0], company_id=r[1], as_of_date=r[2],
                    data=(r[3] if isinstance(r[3], dict) else json.loads(r[3] or '{}'))
                ) for r in cursor.fetchall()
            ]

    def get_snapshot_by_id(self, snapshot_id: int) -> schemas.SnapshotResponse:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT de.entity_key, de.natural_id, COALESCE(de.valid_from::date, CURRENT_DATE), s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE de.entity_key = %s;
            """, (snapshot_id,))
            r = cursor.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail=f"Snapshot mapping '{snapshot_id}' not found.")
            return schemas.SnapshotResponse(snapshot_id=r[0], company_id=r[1], as_of_date=r[2], data=(r[3] or {}))

    def get_latest_all_entities(self) -> List[schemas.SnapshotResponse]:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT de.entity_key, de.natural_id, CURRENT_DATE, s.parsed_data 
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id 
                WHERE de.is_current = TRUE;
            """)
            return [
                schemas.SnapshotResponse(snapshot_id=r[0], company_id=r[1], as_of_date=r[2], data=(r[3] or {})) 
                for r in cursor.fetchall()
            ]

    # ==========================================
    # AUDIT TRACKING ENGINE
    # ==========================================
    def get_upload_audits(self, limit: int) -> List[schemas.UploadAuditResponse]:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, final_status, submitted_at, execution_duration_seconds
                FROM public.submissions
                ORDER BY submitted_at DESC LIMIT %s;
            """, (limit,))
            return [
                schemas.UploadAuditResponse(
                    id=r[0], filename=r[1], status=r[2], submitted_at=r[3], execution_duration=float(r[4] or 0.0)
                ) for r in cursor.fetchall()
            ]

    def get_upload_details(self, upload_id: int) -> schemas.UploadAuditDetailResponse:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, final_status, current_status, submitted_at, execution_duration_seconds, file_metadata, parsed_data
                FROM public.submissions WHERE id = %s;
            """, (upload_id,))
            r = cursor.fetchone()
            if not r:
                raise HTTPException(status_code=404, detail=f"Upload transaction tracking record '{upload_id}' not found.")
            return schemas.UploadAuditDetailResponse(
                id=r[0], filename=r[1], final_status=r[2], current_status=r[3], submitted_at=r[4],
                execution_duration_seconds=float(r[5] or 0.0),
                file_metadata=(r[6] if isinstance(r[6], dict) else json.loads(r[6] or '{}')),
                parsed_data=(r[7] if isinstance(r[7], dict) else json.loads(r[7] or '{}'))
            )

    def get_binary_storage_path(self, upload_id: int) -> str:
        with self.db.cursor() as cursor:
            cursor.execute("SELECT (file_metadata->>'absolute_path') FROM public.submissions WHERE id = %s;", (upload_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                raise HTTPException(status_code=404, detail="Spreadsheet path binding missing from vault payload.")
            return result[0]

    def get_upload_stats(self) -> schemas.UploadStatsResponse:
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*),
                    COUNT(*) FILTER (WHERE final_status = 'SUCCESS'),
                    COUNT(*) FILTER (WHERE final_status = 'FAILURE'),
                    COUNT(*) FILTER (WHERE final_status = 'PROCESSING')
                FROM public.submissions;
            """)
            r = cursor.fetchone()
            return schemas.UploadStatsResponse(
                total_uploads=r[0], successful_uploads=r[1], failed_uploads=r[2], processing_uploads=r[3]
            )

    # ==========================================
    # HELPERS
    # ==========================================
    def _map_company(self, row) -> schemas.CompanyDetailResponse:
        meta_payload = row[7] if isinstance(row[7], dict) else json.loads(row[7] or '{}')
        return schemas.CompanyDetailResponse(
            natural_id=row[0], entity_name=row[1], country_of_origin=row[2],
            is_current=row[3], valid_from=row[4], valid_to=row[5], submission_id=row[6],
            metadata=meta_payload.get("metadata", {})
        )