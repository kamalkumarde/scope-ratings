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
                SELECT de.natural_key, de.entity_name, de.country_of_origin, 
                       de.is_current, de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE de.is_current = TRUE
                ORDER BY de.entity_name LIMIT %s OFFSET %s;
            """, (limit, offset))
            return [self._map_company(r) for r in cursor.fetchall()]

    def get_company_by_id(self, company_id: str) -> schemas.CompanyDetailResponse:
        with self.db.cursor() as cursor:
            try:
                # If identifier is purely numeric (e.g., '43'), match against entity_key
                target_key = int(company_id)
                cursor.execute("""
                    SELECT de.natural_key, de.entity_name, de.country_of_origin, 
                           de.is_current, de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                    FROM dim_entities de
                    LEFT JOIN public.submissions s ON de.submission_id = s.id
                    WHERE de.entity_key = %s AND de.is_current = TRUE;
                """, (target_key,))
            except (ValueError, TypeError):
                # Fallback to searching against natural_key if it's an alphanumeric string
                cursor.execute("""
                    SELECT de.natural_key, de.entity_name, de.country_of_origin, 
                           de.is_current, de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                    FROM dim_entities de
                    LEFT JOIN public.submissions s ON de.submission_id = s.id
                    WHERE de.natural_key = %s AND de.is_current = TRUE;
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
                WHERE natural_key = %s ORDER BY valid_from DESC;
            """, (natural_id,))
            return [schemas.CompanyVersion(submission_id=r[0], valid_from=r[1], valid_to=r[2], is_current=r[3]) for r in cursor.fetchall()]
        


    def get_pit_comparison(self, company_ids: List[str], as_of_date: date) -> List[schemas.CompanyDetailResponse]:
    # Clean up leading/trailing whitespaces from every input element in the array
        cleaned_keys = [k.strip() for k in company_ids if k]
        
        with self.db.cursor() as cursor:

            cursor.execute("""
                SELECT de.natural_key, de.entity_name, de.country_of_origin, de.is_current, 
                    de.valid_from, de.valid_to, de.submission_id, s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE TRIM(de.natural_key) = ANY(%s) 
                AND de.valid_from::date <= %s 
                AND (de.valid_to::date >= %s OR de.valid_to IS NULL);
            """, (cleaned_keys, as_of_date, as_of_date))
            
            raw_rows = cursor.fetchall()  # Fetch everything into memory immediately

    # 2. Map data to your Pydantic schemas outside the cursor's context boundary
        return [self._map_company(row) for row in raw_rows]
        

    def get_historical_metrics(self, company_id: str, metrics: Optional[List[str]]) -> List[schemas.TimeSeriesAnalysisResponse]:
            
        cleaned_key = company_id.strip() if company_id else ""
        print(f"--- DEBUG: Incoming company_id original: '{company_id}', cleaned: '{cleaned_key}' ---", flush=True)
        
        with self.db.cursor() as cursor:
            query = """
                SELECT de.natural_key, f.metric_name, f.calendar_year, f.year_label, 
                    f.metric_value, f.metric_value_formatted, f.is_forecast, f.processing_status
                FROM fct_rating_metric f
                JOIN dim_entities de ON f.entity_key = de.entity_key
                WHERE TRIM(de.natural_key) ILIKE %s
            """
            params = [cleaned_key]
            if metrics:
                query += " AND f.metric_name = ANY(%s)"
                params.append(metrics)
                
            query += " ORDER BY f.metric_name ASC, f.calendar_year ASC;"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            print(f"--- DEBUG: DB Query returned {len(rows)} raw rows ---", flush=True)
            if len(rows) > 0:
                print(f"--- DEBUG: First raw row look: {rows[0]} ---", flush=True)
            
            if not rows:
                print("--- DEBUG: No rows found, throwing 404 ---", flush=True)
                raise HTTPException(status_code=404, detail=f"No historical observations found.")

            grouped = {}
            for r in rows:
                metric_name = r[1]
                year = r[2]
                
                if metric_name not in grouped:
                    grouped[metric_name] = {}
                    
                if year in grouped[metric_name]:
                    continue
                    
                grouped[metric_name][year] = schemas.MetricDataPoint(
                    calendar_year=year,
                    year_label=r[3],
                    metric_value=float(r[4]) if r[4] is not None else None,
                    metric_value_formatted=r[5],
                    is_forecast=r[6],
                    processing_status=r[7]
                )

            print(f"--- DEBUG: Formed {len(grouped)} distinct metric categories ---", flush=True)
            
            output = [
                schemas.TimeSeriesAnalysisResponse(
                    natural_id=company_id, 
                    metric_name=m_name, 
                    history=list(m_years.values())
                ) for m_name, m_years in grouped.items()
            ]
            
            print(f"--- DEBUG: Returning final output list containing {len(output)} records ---", flush=True)
            return output
    # ==========================================
    # SNAPSHOT ENGINE
    # ==========================================
    def list_snapshots(
                    self, 
                    company_id: Optional[str], 
                    from_date: Optional[date], 
                    to_date: Optional[date], 
                    sector: Optional[str], 
                    country: Optional[str], 
                    currency: Optional[str]
                ) -> List[schemas.CompanySnapshotListItem]:            
        
        with self.db.cursor() as cursor:
            # Base query joining dimensions with submission document tables
            query = """
                SELECT de.natural_key, de.entity_name, de.country_of_origin, de.is_current, 
                    de.valid_from, de.valid_to, de.submission_id,
                    s.parsed_data->'company_info'->>'sector' as sector,
                    s.parsed_data->'company_info'->>'currency' as currency
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE 1=1
            """
            params = []
            
            # Resilient spacing filter for Company Natural Key
            if company_id:
                query += " AND TRIM(de.natural_key) ILIKE %s"
                params.append(company_id.strip())
                
            # Date boundaries
            if from_date:
                query += " AND de.valid_from::date >= %s"
                params.append(from_date)
            if to_date:
                query += " AND (de.valid_to::date <= %s OR de.valid_to IS NULL)"
                params.append(to_date)
                
            # Dimension metadata attributes
            if country:
                query += " AND de.country_of_origin ILIKE %s"
                params.append(country.strip())
            if sector:
                query += " AND s.parsed_data->'company_info'->>'sector' ILIKE %s"
                params.append(f"%{sector.strip()}%")
            if currency:
                query += " AND s.parsed_data->'company_info'->>'currency' ILIKE %s"
                params.append(currency.strip())
                
            query += " ORDER BY de.natural_key ASC, de.valid_from DESC;"
            
            cursor.execute(query, params)
            raw_rows = cursor.fetchall()

        # Safely convert to target response schema outside the cursor block
        return [
            schemas.CompanySnapshotListItem(
                natural_id=r[0],
                entity_name=r[1],
                country_of_origin=r[2],
                is_current=r[3],
                valid_from=r[4],
                valid_to=r[5],
                submission_id=r[6],
                sector=r[7],
                currency=r[8]
            ) for r in raw_rows
        ]

    def get_snapshots(self, company_id: Optional[str], from_date: Optional[date], to_date: Optional[date],
                      sector: Optional[str], country: Optional[str], currency: Optional[str]) -> List[schemas.SnapshotResponse]:
        with self.db.cursor() as cursor:
            query = """
                SELECT de.entity_key, de.natural_key, COALESCE(de.valid_from::date, CURRENT_DATE), s.parsed_data
                FROM dim_entities de
                LEFT JOIN public.submissions s ON de.submission_id = s.id
                WHERE 1=1
            """
            params = []
            if company_id:
                query += " AND de.natural_key = %s"; params.append(company_id)
            if from_date:
                query += " AND de.valid_from >= %s"; params.append(from_date)
            if to_date:
                query += " AND de.valid_from <= %s"; params.append(to_date)
            if country:
                query += " AND de.country_of_origin = %s"; params.append(country)
            
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
                SELECT de.entity_key, de.natural_key, COALESCE(de.valid_from::date, CURRENT_DATE), s.parsed_data
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
                SELECT de.entity_key, de.natural_key, CURRENT_DATE, s.parsed_data 
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
    

    def get_upload_audits(self, limit: int = 100) -> List[schemas.UploadAuditResponse]:
        """
        GET /uploads
        Lists all processed files from the pipeline details log (Requirement #1).
        """
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, file_name, processed_at, outcome, submission_id, execution_stage, error_message
                FROM pipeline_file_details
                ORDER BY processed_at DESC
                LIMIT %s;
            """, (limit,))
            raw_rows = cursor.fetchall()

        return [
            schemas.UploadAuditResponse(
                upload_id=row[0],
                filename=row[1],
                uploaded_at=row[2],
                status=row[3],  # 'outcome' maps to status
                submission_id=row[4],
                execution_stage=row[5],
                error_message=row[6]
            ) for row in raw_rows
        ]


    def get_upload_details(self, upload_id: int) -> schemas.UploadAuditDetailResponse:
        """
        GET /uploads/{upload_id}/details
        Retrieves full processing log details for a file, plus any generated dimension rows.
        """
        with self.db.cursor() as cursor:
            # 1. Fetch the file processing record
            cursor.execute("""
                SELECT id, file_name, processed_at, outcome, submission_id, execution_stage, error_message
                FROM pipeline_file_details
                WHERE id = %s;
            """, (upload_id,))
            file_row = cursor.fetchone()
            
            if not file_row:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Upload transaction tracking record '{upload_id}' not found."
                )
                
            # 2. Pull snapshots generated by this run using the associated submission_id
            submission_id = file_row[4]
            generated_snapshots = []
            
            if submission_id:
                cursor.execute("""
                    SELECT de.natural_key, de.entity_name, de.country_of_origin, de.is_current, 
                        de.valid_from, de.valid_to
                    FROM dim_entities de
                    WHERE de.submission_id = %s
                    ORDER BY de.natural_key ASC;
                """, (submission_id,))
                affected_entities = cursor.fetchall()
                
                generated_snapshots = [
                    {
                        "natural_id": row[0],
                        "entity_name": row[1],
                        "country_of_origin": row[2],
                        "is_current": row[3],
                        "valid_from": row[4],
                        "valid_to": row[5]
                    } for row in affected_entities
                ]

        return schemas.UploadAuditDetailResponse(
            upload_id=file_row[0],
            filename=file_row[1],
            uploaded_at=file_row[2],
            status=file_row[3],
            submission_id=file_row[4],
            execution_stage=file_row[5],
            error_message=file_row[6],
            impacted_snapshots=generated_snapshots
        )


    def get_upload_stats(self) -> schemas.UploadStatsResponse:
        """
        GET /uploads/stats
        Aggregates metrics from the master pipeline runs table.
        """
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(run_id) as total_runs,
                    SUM(total_files) as total_files_processed,
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failures,
                    SUM(skipped_count) as total_skipped
                FROM pipeline_runs;
            """)
            row = cursor.fetchone()

        return schemas.UploadStatsResponse(
            total_pipeline_runs=row[0] or 0,
            total_files_evaluated=row[1] or 0,
            success_count=row[2] or 0,
            failure_count=row[3] or 0,
            skipped_count=row[4] or 0
        )


    def get_binary_file_content(self, upload_id: int):
        """
        GET /uploads/{upload_id}/file
        Fetches the raw binary BYTEA content directly from the database table.
        """
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT file_name, file_content 
                FROM pipeline_file_details 
                WHERE id = %s;
            """, (upload_id,))
            row = cursor.fetchone()
            
        if not row or not row[1]:
            raise HTTPException(status_code=404, detail="File asset binary content missing from warehouse log record.")
        return row[0], row[1]
    # ==========================================
    # HELPERS
    # ==========================================
    def _map_company(self, row) -> schemas.CompanyDetailResponse:
        meta_payload = row[7] if isinstance(row[7], dict) else json.loads(row[7] or '{}')
        
        inner_metadata = meta_payload.get("metadata") if isinstance(meta_payload, dict) else None
        if not isinstance(inner_metadata, dict):
            inner_metadata = meta_payload if isinstance(meta_payload, dict) else {}

        return schemas.CompanyDetailResponse(
            natural_id=str(row[0]), 
            entity_name=row[1], 
            country_of_origin=row[2],
            is_current=row[3], 
            valid_from=row[4], 
            valid_to=row[5], 
            submission_id=row[6],
            metadata=inner_metadata
        )