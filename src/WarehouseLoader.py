import logging
from psycopg2.extensions import connection
from typing import List

class WarehouseLoader:
    """Handles dimensional star-schema loading logic with robust SCD2 cascading."""

    def __init__(self, auditor):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auditor = auditor

    def load(self, tconn: connection, submission_id: int) -> bool:
        """Main loading entry point."""
        with tconn.cursor() as trn_cursor:
            try:
                stage = "4.1 Entity Load"
                status = "START"
                self.auditor.log(status=stage, submission_id=submission_id, error=status)

                natural_key = self.get_natural_key(submission_id=submission_id, tcur=trn_cursor)
                self.logger.info("Natural Key for Submission %s is %s", submission_id, natural_key)

                # Full cascade starts here
                entity_key = self.load_entity(submission_id=submission_id, tcur=trn_cursor, natural_key=natural_key)

                self.logger.info("Entity Key is : %s ", entity_key)

                status = 'LOAD DIM ENTITY'
                stage = "4.2 Profile Load"
                self.auditor.log(status=stage, submission_id=submission_id, error=status)

                # Profile and Industry are triggered inside load_entity -> load_profile
                profile_key = self.load_profile(submission_id=submission_id, tcur=trn_cursor, entity_key=entity_key)

                self.logger.info("Profile Key is : %s ", profile_key)

                status = 'LOAD DIM PROFILE'
                stage = "4.3 Industry Profile load"
                self.auditor.log(status=stage, submission_id=submission_id, error=status)

                fact_keys = self.load_fct_metric(submission_id=submission_id, tcur=trn_cursor, profile_key=profile_key)

                status = 'LOAD FACT METRIC'
                stage = "4.4 Profile Metric load"
                self.auditor.log(status=stage, submission_id=submission_id, error=status)

                #self.logger.info("No of Facts for profile %s", len(fact_keys))

                if fact_keys:
                    return True
                return False
            

            except Exception as e:
                self.logger.error("Failed loading submission %s: %s", submission_id, e, exc_info=True)
                raise

    # ====================== GETTERS ======================
    def get_natural_key(self, tcur: any, submission_id: int) -> str:
        try:
            nsql = """
                WITH prestage AS (
                    SELECT id AS submission_id, parsed_data
                    FROM public.submissions WHERE id = %s 
                )
                SELECT COALESCE(parsed_data->'metadata'->>'Rated entity', 
                       parsed_data->'parsed_data'->>'Rated entity') AS natural_key
                FROM prestage;
            """
            tcur.execute(nsql, (submission_id,))
            result = tcur.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error("Failed to get natural key: %s", e)
            raise

    def get_entity_key(self, tcur: any, natural_key: str) -> int:
        try:
            tcur.execute("SELECT entity_key FROM dim_entities WHERE natural_key = %s AND is_current = true", 
                        (natural_key,))
            result = tcur.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error("Failed to get entity key: %s", e)
            raise

    def get_profile_key(self, tcur: any, entity_key: int) -> int:
        try:
            tcur.execute("SELECT profile_key FROM dim_profiles WHERE entity_key = %s AND is_current = true", 
                        (entity_key,))
            result = tcur.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.error("Failed to get profile key: %s", e)
            raise

    def get_ind_profile_keys(self, tcur: any, profile_key: int) -> List[int]:
        try:
            tcur.execute("""
                SELECT industry_profile_key 
                FROM dim_ind_profile 
                WHERE profile_key = %s AND is_current = true
            """, (profile_key,))
            return [r[0] for r in tcur.fetchall()]
        except Exception as e:
            self.logger.error("Failed to get ind profile keys: %s", e)
            raise

    # ====================== CORE SCD2 LOADERS ======================

    def _get_or_create_entity(self, tcur: any, submission_id: int, natural_key: str) -> int:
        """Detect change and return correct entity_key."""
        try:
            tcur.execute("""
                SELECT entity_key, entity_hash_key 
                FROM dim_entities 
                WHERE natural_key = %s AND is_current = TRUE
            """, (natural_key,))
            current = tcur.fetchone()
            old_entity_key = current[0] if current else None
            old_hash = current[1] if current else None

            tcur.execute("""
                WITH prestage AS (SELECT parsed_data FROM public.submissions WHERE id = %s)
                SELECT md5(concat_ws('|',
                    COALESCE(parsed_data->'metadata'->>'Rated entity', parsed_data->'parsed_data'->>'Rated entity'),
                    COALESCE(parsed_data->'metadata'->>'Country of origin', parsed_data->'parsed_data'->>'Country of origin'),
                    COALESCE(parsed_data->'metadata'->>'CorporateSector', parsed_data->'parsed_data'->>'CorporateSector'),
                    COALESCE(parsed_data->'metadata'->>'Accounting principles', parsed_data->'parsed_data'->>'Accounting principles'),
                    COALESCE(parsed_data->'metadata'->>'Reporting Currency/Units', parsed_data->'parsed_data'->>'Reporting Currency/Units'),
                    COALESCE(parsed_data->'metadata'->>'End of business year', parsed_data->'parsed_data'->>'End of business year')
                )) AS new_hash FROM prestage;
            """, (submission_id,))
            new_hash = tcur.fetchone()[0]

            if old_entity_key is None or old_hash != new_hash:
                self.logger.info("Entity changed → creating new version")
                if old_entity_key:
                    tcur.execute("UPDATE dim_entities SET is_current=FALSE, valid_to=NOW() WHERE entity_key=%s", 
                               (old_entity_key,))

                sql_insert = """
                    WITH prestage AS (SELECT id AS submission_id, NOW() AS now, parsed_data FROM public.submissions WHERE id = %s),
                    pre_processed AS (
                        SELECT submission_id, now,
                               COALESCE(parsed_data->'metadata'->>'Rated entity', parsed_data->'parsed_data'->>'Rated entity') AS natural_key,
                               COALESCE(parsed_data->'metadata'->>'Country of origin', parsed_data->'parsed_data'->>'Country of origin') AS country_of_origin,
                               COALESCE(parsed_data->'metadata'->>'CorporateSector', parsed_data->'parsed_data'->>'CorporateSector') AS sector,
                               COALESCE(parsed_data->'metadata'->>'Accounting principles', parsed_data->'parsed_data'->>'Accounting principles') AS accounting_principles,
                               COALESCE(parsed_data->'metadata'->>'Reporting Currency/Units', parsed_data->'parsed_data'->>'Reporting Currency/Units') AS currency,
                               COALESCE(parsed_data->'metadata'->>'End of business year', parsed_data->'parsed_data'->>'End of business year') AS year_end
                        FROM prestage
                    ) ,
                       processed as (
                        select  submission_id, now,natural_key, country_of_origin, sector, accounting_principles, currency, year_end,
                                md5(concat_ws('|', natural_key, country_of_origin, sector, accounting_principles, currency, year_end)) AS entity_hash_key
                            from pre_processed )
                    INSERT INTO dim_entities (
                        natural_key, entity_name, country_of_origin, sector, accounting_principles,
                        currency, year_end, entity_hash_key, is_current, valid_from, valid_to, submission_id
                    )
                    SELECT natural_key, natural_key, country_of_origin, sector, accounting_principles,
                           currency, year_end, entity_hash_key, TRUE, now, NULL, submission_id
                    FROM processed
                    RETURNING entity_key;
                """
                tcur.execute(sql_insert, (submission_id,))
                return tcur.fetchone()[0]
            else:
                return old_entity_key

        except Exception as e:
            self.logger.error("_get_or_create_entity failed: %s", e)
            raise

    def load_entity(self, tcur: any, submission_id: int, natural_key: str) -> int:
        """Public wrapper."""
        return self._get_or_create_entity(tcur, submission_id, natural_key)

    def load_profile(self, tcur: any, submission_id: int, entity_key: int) -> int:
        """Load profile and trigger industry profiles on any change."""
        try:
            self.logger.info("load_profile | entity_key=%s", entity_key)

            if entity_key <= 0:
                raise ValueError(f"Invalid entity_key: {entity_key}")

            # Get entity hash
            tcur.execute("SELECT entity_hash_key FROM dim_entities WHERE entity_key = %s AND is_current = TRUE", 
                        (entity_key,))
            eh = tcur.fetchone()
            entity_hash = eh[0] if eh else None

            # Prepare data
            sql_prepare = """
               WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested AS (
                    SELECT s.submission_id, ind.sector,
                           CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                           ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk') 
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                agg AS (
                    SELECT submission_id,
                           md5(string_agg(concat(sector,'|',weight,'|',score), ',') OVER (PARTITION BY submission_id )) AS industry_aggregate_hash_key
                    FROM unnested 
                    
                )
                SELECT r.submission_id,
                    r.now, %s AS entity_key, %s AS entity_hash_key,
                    r.parsed_data->'metadata'->>'Business risk profile' AS business_risk_profile,
                    r.parsed_data->'metadata'->>'(Blended) Industry risk profile' AS blended_industry_risk,
                    r.parsed_data->'metadata'->>'Competitive Positioning' AS competitive_positioning,
                    r.parsed_data->'metadata'->>'Market share' AS market_share,
                    r.parsed_data->'metadata'->>'Diversification' AS diversification,
                    r.parsed_data->'metadata'->>'Operating profitability' AS operating_profitability,
                    r.parsed_data->'metadata'->>'Financial risk profile' AS financial_risk_profile,
                    r.parsed_data->'metadata'->>'Leverage' AS leverage,
                    r.parsed_data->'metadata'->>'Interest cover' AS interest_cover,
                    r.parsed_data->'metadata'->>'Cash flow cover' AS cash_flow_cover,
                    r.parsed_data->'metadata'->>'Liquidity' AS liquidity_notches,
                    r.parsed_data->'metadata'->>'Sector/company-specific factors (1)' AS specific_factors_1,
                    r.parsed_data->'metadata'->>'Sector/company-specific factors (2)' AS specific_factors_2,
                    r.parsed_data->'metadata'->>'Segmentation criteria' AS segmentation_criteria,
                    r.parsed_data->'metadata'->>'Rating methodologies applied' AS rating_methodologies_applied,
                    a.industry_aggregate_hash_key,
                    md5(concat_ws('|', 
                        r.parsed_data->'metadata'->>'Business risk profile',
                        r.parsed_data->'metadata'->>'(Blended) Industry risk profile',
                        r.parsed_data->'metadata'->>'Competitive Positioning',
                        r.parsed_data->'metadata'->>'Market share',
                        r.parsed_data->'metadata'->>'Diversification',
                        r.parsed_data->'metadata'->>'Operating profitability',
                        r.parsed_data->'metadata'->>'Financial risk profile',
                        r.parsed_data->'metadata'->>'Leverage',
                        r.parsed_data->'metadata'->>'Interest cover',
                        r.parsed_data->'metadata'->>'Cash flow cover',
                        r.parsed_data->'metadata'->>'Liquidity',
                        r.parsed_data->'metadata'->>'Sector/company-specific factors (1)',
                        r.parsed_data->'metadata'->>'Sector/company-specific factors (2)',
                        r.parsed_data->'metadata'->>'Segmentation criteria',
                        r.parsed_data->'metadata'->>'Rating methodologies applied',
                        a.industry_aggregate_hash_key
                    )) AS profile_hash_key
                FROM raw_submission r
                LEFT JOIN agg a ON a.submission_id = r.submission_id;


            """
            self.logger.info("load_profile |************************* ")
            tcur.execute(sql_prepare, (submission_id, entity_key, entity_hash))
            self.logger.info("load_profile |**********11111111*************** ")
            
            row = tcur.fetchone()
            if not row:
                return 0

            new_profile_hash = row[-1]
            self.logger.info("load_profile |**********2222222222222221*************** ")

            # Check for change
            tcur.execute("""
                SELECT profile_key, profile_hash_key 
                FROM dim_profiles 
                WHERE entity_key = %s AND is_current = TRUE
            """, (entity_key,))
            current = tcur.fetchone()
            self.logger.info("load_profile |**********333333333333333333*************** ")

            if current and current[1] == new_profile_hash:
                self.logger.info("No change in profile")
                self.load_ind_profile(tcur, submission_id, current[0])
                return current[0]
 
            # Expire old profile
            tcur.execute("UPDATE dim_profiles SET is_current=FALSE, valid_to=NOW() WHERE entity_key=%s AND is_current=TRUE", 
                        (entity_key,))

            # Insert new profile
            self.logger.info("load_profile |**********44444444*************** %s", )
            sql_insert = """
                INSERT INTO dim_profiles (
                    entity_key, entity_hash_key, profile_hash_key, industry_aggregate_hash_key,
                    business_risk_profile, blended_industry_risk, competitive_positioning, market_share,
                    diversification, operating_profitability, financial_risk_profile, leverage,
                    interest_cover, cash_flow_cover, liquidity_notches, specific_factors_1,
                    specific_factors_2, segmentation_criteria, rating_methodologies_applied,
                    is_current, valid_from, valid_to, submission_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, TRUE, %s, NULL, %s)
                RETURNING profile_key;
            """

            tcur.execute(sql_insert, (
                row[2], row[3], new_profile_hash, row[20],
                row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11],
                row[12], row[13], row[14], row[15], row[16], row[17], row[18],
                row[1], row[0]
            ))

            new_profile_key = tcur.fetchone()[0]

            # Trigger industry profiles
            self.load_ind_profile(tcur, submission_id, new_profile_key)

            return new_profile_key

        except Exception as e:
            self.logger.error("load_profile failed: %s", e, exc_info=True)
            raise

    def load_ind_profile(self, tcur: any, submission_id: int, profile_key: int) -> List[int]:   

        try:

            if profile_key <= 0:
                self.logger.warning("Invalid profile_key: %s", profile_key)
                return []

            self.logger.info("load_ind_profile started for profile_key=%s", profile_key)

            # 1. Expire ALL current records for this profile_key
            tcur.execute("""
                UPDATE dim_ind_profile 
                SET is_current = FALSE, 
                    valid_to = NOW()
                WHERE profile_key = %s 
                AND is_current = TRUE;
            """, (profile_key,))
            
            expired_count = tcur.rowcount
            self.logger.debug("Expired %d old industry records for profile_key=%s", expired_count, profile_key)

            # 2. Insert new records (safe from duplicates)
            sql_insert = """
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested AS (
                    SELECT 
                        s.submission_id,
                        ind.sector AS sector_name,
                        CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                        ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk') 
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                hashed_aggregation AS (
                    SELECT 
                        submission_id,
                        sector_name,
                        weight,
                        score,
                        md5(string_agg(concat(sector_name,'|',weight,'|',score), ',') OVER (PARTITION BY submission_id )) AS industry_aggregate_hash_key
                    FROM unnested
                )
                INSERT INTO dim_ind_profile (
                    profile_key, 
                    profile_hash_key,
                    industry_hash_key, 
                    industry_aggregate_hash_key,
                    sector_name, 
                    industry_weight_percentage, 
                    industry_risk_score,
                    is_current, 
                    valid_from, 
                    submission_id
                )
                SELECT 
                    %s,
                    (SELECT profile_hash_key FROM dim_profiles WHERE profile_key = %s),
                    md5(concat_ws('|', sector_name, weight, score)),
                    industry_aggregate_hash_key,
                    sector_name, 
                    weight, 
                    score,
                    TRUE, 
                    NOW(), 
                    submission_id
                FROM hashed_aggregation
                ON CONFLICT (profile_key, sector_name, industry_hash_key) 
                DO NOTHING;
            """

            tcur.execute(sql_insert, (submission_id, profile_key, profile_key))

            inserted = tcur.rowcount
            self.logger.info("load_ind_profile completed | profile_key=%s | inserted=%d", profile_key, inserted)

            return self.get_ind_profile_keys(tcur, profile_key)

        except Exception as e:
            self.logger.error("load_ind_profile failed for profile_key=%s: %s", profile_key, e, exc_info=True)
            raise

    def load_fct_metric(self, tcur: any, submission_id: int, profile_key: int) -> List[int]:
        """Fact table loader (unchanged from original with minor safety)."""
        try:
            sql_insert = """INSERT INTO fct_rating_metric (
                    entity_key,
                    profile_key,
                    industry_aggregate_hash_key,
                    submission_id,
                    metric_name,
                    year_label,
                    calendar_year,
                    is_forecast,
                    metric_value,
                    metric_value_formatted,
                    processing_status
                )
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data
                    FROM public.submissions
                    WHERE id = %s
                ),
                stg_dimensions AS (
                    SELECT DISTINCT
                        s.submission_id,
                        de.entity_key,
                        dp.profile_key,
                        dip.industry_aggregate_hash_key, -- Fixed: Must be the integer primary key, not the hash key string
                        s.parsed_data
                    FROM raw_submission s
                    JOIN public.dim_entities de ON de.natural_key = s.parsed_data->'metadata'->>'Rated entity' AND de.is_current = TRUE
                    JOIN public.dim_profiles dp ON dp.entity_key = de.entity_key AND dp.is_current = TRUE
                    -- Maps metrics to every active industry slice under the current parent profile
                    JOIN public.dim_ind_profile dip ON dip.profile_key = dp.profile_key AND dip.is_current = TRUE
                ),
                stg_timeline_metrics AS (
                    SELECT
                        d.entity_key,
                        d.profile_key,
                        d.industry_aggregate_hash_key,
                        d.submission_id,
                        metric.key AS metric_name,
                        year_data.key AS year_label,
                        CAST(REGEXP_REPLACE(year_data.key, '[^0-9]', '', 'g') AS INTEGER) AS calendar_year,
                        CASE WHEN year_data.key LIKE '%%E' THEN TRUE ELSE FALSE END AS is_forecast,

                        -- Safe numeric data extraction condition rule (Mapped directly to target naming)
                        CASE
                            WHEN REPLACE(year_data.value::text, '"', '') ~ '^-?[0-9]+(\.[0-9]+)?$'
                            THEN CAST(REPLACE(year_data.value::text, '"', '') AS NUMERIC(18,4))
                            ELSE NULL
                        END AS metric_value,

                        -- Exact text layout formatting condition rule (Mapped directly to target naming)
                        CASE
                            WHEN REPLACE(year_data.value::text, '"', '') ~ '^-?[0-9]+(\.[0-9]+)?$'
                            THEN TO_CHAR(CAST(REPLACE(year_data.value::text, '"', '') AS NUMERIC), 'FM999,999,990.00')
                            ELSE NULL
                        END AS metric_value_formatted,

                        metric.value->>'status' AS processing_status
                    FROM stg_dimensions d
                    CROSS JOIN LATERAL jsonb_each(d.parsed_data->'scopeCreditMetrics'->'metrics') AS metric
                    CROSS JOIN LATERAL jsonb_each(metric.value) AS year_data
                    WHERE year_data.key != 'status'
                )
                SELECT
                    entity_key, profile_key, industry_aggregate_hash_key, submission_id,
                    metric_name, year_label, calendar_year, is_forecast,
                    metric_value, metric_value_formatted, processing_status
                FROM stg_timeline_metrics
                ON CONFLICT (entity_key,profile_key, metric_name, calendar_year)
                DO UPDATE SET
                    metric_value                = EXCLUDED.metric_value,
                    metric_value_formatted      = EXCLUDED.metric_value_formatted,
                    processing_status           = EXCLUDED.processing_status,
                    submission_id               = EXCLUDED.submission_id,               
                    profile_key                 = EXCLUDED.profile_key,                 
                    industry_aggregate_hash_key = EXCLUDED.industry_aggregate_hash_key, 
                    year_label                  = EXCLUDED.year_label,
                    is_forecast                 = EXCLUDED.is_forecast,
                    updated_at                  = NOW()
                    RETURNING fact_metric_key;"""
            tcur.execute(sql_insert, (submission_id,))

            return len(tcur.fetchall())
        except Exception as err:
            self.logger.error("load_fct_metric failed: %s", err)
            raise