import logging
from psycopg2.extensions import connection
from typing import List
#from src.audit import AuditLogger

class WarehouseLoader:
    """Handles dimensional star-schema loading logic."""
    def __init__(self,auditor):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.auditor = auditor
        
    def load(self, tconn: connection, submission_id: int) ->bool:       

        with tconn.cursor() as trn_cursor:
            try:
                
                stage = "4.1 Entity Load"
                status = "START"
                self.auditor.log(status= stage,submission_id=submission_id,error=status)

                natural_key = self.get_natural_key(submission_id=submission_id, tcur=trn_cursor)

                self.logger.info("Natural Key for Submission %s is %s",submission_id,natural_key)
                
                entity_key = self.load_entity(submission_id=submission_id, tcur=trn_cursor, natural_key=natural_key)

                self.logger.info("Entity Key is : %s ", entity_key)

                status = 'LOAD DIM ENTITY'

                stage = "4.2 Profile Load"
                self.auditor.log(status= stage,submission_id=submission_id,error=status)


                profile_key = self.load_profile(submission_id=submission_id, tcur=trn_cursor, entity_key=entity_key)

                self.logger.info("Profile Key is : %s ", profile_key)            

                status = 'LOAD DIM PROFILE'
                self.auditor.log(status= stage,submission_id=submission_id,error=status)
                
                ind_prof_keys = self.load_ind_profile(submission_id=submission_id, tcur=trn_cursor, profile_key=profile_key)

                self.logger.info("No of Profile Key is : %s ", len(ind_prof_keys))  

                stage = "4.3 Industry Profile load"
                status = 'LOAD DIM IND PROFILE'
                self.auditor.log(status= stage,submission_id=submission_id,error=status)

                fact_keys = self.load_fct_metric(submission_id=submission_id, tcur=trn_cursor, profile_key=profile_key)
                
                status = 'LOAD FACT METRIC'
                stage = "4.4 Profile Metric load"
                self.auditor.log(status= stage,submission_id=submission_id,error=status)

                
                self.logger.info("No of  Facts for profile %s", len(fact_keys))

                if len(fact_keys) > 0 :
                    return True
                else:
                    return False
            except Exception as e:
                 self.logger.error("Failed no Entity key for natural key id %s : %s", natural_key, e)

        
                
            

    

    def get_natural_key(self, tcur: any, submission_id: int) -> str:
        try:
            
            nsql =  """
        WITH prestage AS (
                    SELECT id AS submission_id, NOW() AS now, parsed_data
                    FROM public.submissions WHERE id = %s 
                )
             select    COALESCE(parsed_data->'metadata'->>'Rated entity', parsed_data->'parsed_data'->>'Rated entity') AS natural_key
             from prestage;
                """
            
            tcur.execute(nsql, (submission_id,))
            result = tcur.fetchone()
            if result:
                return result[0]
            return []      
            
        
        except Exception as e:
            self.logger.error("Failed no natural key for submissio id %s : %s", submission_id, e)
            raise e
    def get_entity_key(self, tcur: any, natural_key: str) -> int:
        try:            
            nsql =  """ select entity_key from dim_entities where natural_key = %s and is_current = true  """            
            tcur.execute(nsql, (natural_key,))
            result = tcur.fetchone()
            if result:
                return result[0]
            return []
        except Exception as e:
            self.logger.error("Failed no Entity key for natural key id %s : %s", natural_key, e)
            raise e
    def get_profile_key(self, tcur: any, entity_key: int) -> int:
        try:            
            nsql =  """ select profile_key from dim_profiles where entity_key = %s and is_current = true  """            
            tcur.execute(nsql, (entity_key,))
            result = tcur.fetchone()
            if result:
                return result[0]
            return []
        except Exception as e:
            self.logger.error("Failed no Profile key for entity key id %s : %s", entity_key, e)
            raise e      

    def get_ind_profile_keys(self, tcur: any, profile_key: int) -> List[int]:
        try:            
            nsql =  """ select industry_profile_key from dim_ind_profile  where profile_key = %s and is_current = true  """            
            tcur.execute(nsql, (profile_key,))
            result = tcur.fetchall()
            if result:
                return result
            return []
        
        except Exception as e:
            self.logger.error("Failed no Ind Profile key for entity key id %s : %s", profile_key, e)
            raise e
              
    def get_fact_keys(self, tcur: any, profile_key: int) -> List[int]:
        try:            
            nsql =  """ select fact_metric_key from fct_rating_metric where profile_key = %s  """            
            tcur.execute(nsql, (profile_key,))
            result = tcur.fetchall()
            if result:
                return result
            return []
        
        except Exception as e:
            self.logger.error("Failed no Ind Profile key for entity key id %s : %s", profile_key, e)
            raise e

            
                 


    

    def load_entity(self, tcur: any, submission_id: int, natural_key: str) -> int:
        try:
            # 1. First isolated statement: Perform the historical SCD2 record expiration (UPDATE)
            sql_update = """
                WITH prestage AS (
                    SELECT id AS submission_id, NOW() AS now, parsed_data
                    FROM public.submissions WHERE id = %s 
                ),
                processed_staging AS ( 
                    SELECT  
                        submission_id, now,
                        COALESCE(parsed_data->'metadata'->>'Rated entity', parsed_data->'parsed_data'->>'Rated entity') AS natural_key,
                        COALESCE(parsed_data->'metadata'->>'Country of origin', parsed_data->'parsed_data'->>'Country of origin') AS country_of_origin,
                        COALESCE(parsed_data->'metadata'->>'CorporateSector', parsed_data->'parsed_data'->>'CorporateSector') AS sector,
                        COALESCE(parsed_data->'metadata'->>'Accounting principles', parsed_data->'parsed_data'->>'Accounting principles') AS accounting_principles,
                        COALESCE(parsed_data->'metadata'->>'Reporting Currency/Units', parsed_data->'parsed_data'->>'Reporting Currency/Units') AS currency,
                        COALESCE(parsed_data->'metadata'->>'End of business year', parsed_data->'parsed_data'->>'End of business year') AS year_end
                    FROM prestage 
                ),
                processed_hash AS (
                    SELECT 
                        submission_id, now, natural_key, country_of_origin, sector,
                        accounting_principles, currency, year_end,
                        md5(concat_ws('|', natural_key, country_of_origin, sector,
                            accounting_principles, currency, year_end)) AS entity_hash_key
                    FROM processed_staging    
                )
                UPDATE dim_entities de
                SET is_current = FALSE,
                    valid_to = ph.now
                FROM processed_hash ph
                WHERE de.natural_key = ph.natural_key
                  AND de.is_current = TRUE
                  AND de.entity_hash_key != ph.entity_hash_key;
            """
            tcur.execute(sql_update, (submission_id,))

            # 2. Second isolated statement: Handle the active record tracking entry (INSERT)
            sql_insert = """
                WITH prestage AS (
                    SELECT id AS submission_id, NOW() AS now, parsed_data
                    FROM public.submissions WHERE id = %s 
                ),
                processed_staging AS ( 
                    SELECT  
                        submission_id, now,
                        COALESCE(parsed_data->'metadata'->>'Rated entity', parsed_data->'parsed_data'->>'Rated entity') AS natural_key,
                        COALESCE(parsed_data->'metadata'->>'Country of origin', parsed_data->'parsed_data'->>'Country of origin') AS country_of_origin,
                        COALESCE(parsed_data->'metadata'->>'CorporateSector', parsed_data->'parsed_data'->>'CorporateSector') AS sector,
                        COALESCE(parsed_data->'metadata'->>'Accounting principles', parsed_data->'parsed_data'->>'Accounting principles') AS accounting_principles,
                        COALESCE(parsed_data->'metadata'->>'Reporting Currency/Units', parsed_data->'parsed_data'->>'Reporting Currency/Units') AS currency,
                        COALESCE(parsed_data->'metadata'->>'End of business year', parsed_data->'parsed_data'->>'End of business year') AS year_end
                    FROM prestage 
                ),
                processed_hash AS (
                    SELECT 
                        submission_id, now, natural_key, country_of_origin, sector,
                        accounting_principles, currency, year_end,
                        md5(concat_ws('|', natural_key, country_of_origin, sector,
                            accounting_principles, currency, year_end)) AS entity_hash_key
                    FROM processed_staging    
                )
                INSERT INTO dim_entities (
                    natural_key, entity_name, country_of_origin, sector, accounting_principles, 
                    currency, year_end, entity_hash_key, is_current, valid_from, valid_to, submission_id 
                )
                SELECT 
                    ph.natural_key, ph.natural_key, ph.country_of_origin, ph.sector, ph.accounting_principles, 
                    ph.currency, ph.year_end, ph.entity_hash_key, TRUE, ph.now, null, ph.submission_id
                FROM processed_hash ph
                LEFT JOIN dim_entities de 
                    ON ph.natural_key = de.natural_key AND de.is_current = TRUE
                WHERE de.entity_key IS NULL OR de.entity_hash_key != ph.entity_hash_key;
            """
            tcur.execute(sql_insert, (submission_id,))

            entity_key = self.get_entity_key(tcur=tcur, natural_key=natural_key)
            if entity_key:
                return entity_key
            raise ValueError(f"Entity matching natural key '{natural_key}' not discovered or loaded.")
            
        except Exception as e:
            self.logger.error("Failed dimensional entity pipeline load on submission %s: %s", submission_id, e)
            raise e

    def load_profile(self, tcur: any, submission_id: int, entity_key: int) -> int:
        """Populates analytical profile attributes into dim_profiles using split SCD2 commands."""
        try:
            # 1. First isolated statement: Expire the profile pointing to the PREVIOUS version of this entity
            sql_update = """
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested_industries AS (
                    SELECT
                        s.submission_id,
                        ind.sector,
                        CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                        ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk')
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                stg_child_industry_hash AS (
                    SELECT
                        submission_id,
                        md5(string_agg(concat(sector, '|', weight, '|', score), ',' ORDER BY sector)) AS industry_aggregate_hash_key
                    FROM unnested_industries
                    GROUP BY submission_id
                ),
                processed_staging AS (
                    SELECT
                        s.submission_id, s.now,
                        -- CRITICAL FIX: Find the profile linked to the historical entity via natural_key 
                        -- regardless of whether that entity row is currently active or recently expired.
                        dp_old.entity_key,
                        s.parsed_data->'metadata'->>'Business risk profile' AS business_risk_profile,
                        s.parsed_data->'metadata'->'Industry risk' AS industry_risk_raw,
                        s.parsed_data->'metadata'->>'(Blended) Industry risk profile' AS blended_industry_risk,
                        s.parsed_data->'metadata'->>'Competitive Positioning' AS competitive_positioning,
                        s.parsed_data->'metadata'->>'Market share' AS market_share,
                        s.parsed_data->'metadata'->>'Diversification' AS diversification,
                        s.parsed_data->'metadata'->>'Operating profitability' AS operating_profitability,
                        s.parsed_data->'metadata'->>'Financial risk profile' AS financial_risk_profile,
                        s.parsed_data->'metadata'->>'Leverage' AS leverage,
                        s.parsed_data->'metadata'->>'Interest cover' AS interest_cover,
                        s.parsed_data->'metadata'->>'Cash flow cover' AS cash_flow_cover,
                        s.parsed_data->'metadata'->>'Liquidity' AS liquidity_notches,
                        s.parsed_data->'metadata'->>'Sector/company-specific factors (1)' AS specific_factors_1,
                        s.parsed_data->'metadata'->>'Sector/company-specific factors (2)' AS specific_factors_2,
                        s.parsed_data->'metadata'->>'Segmentation criteria' AS segmentation_criteria,
                        s.parsed_data->'metadata'->>'Rating methodologies applied' AS rating_methodologies_applied,
                        h.industry_aggregate_hash_key
                    FROM raw_submission s
                    LEFT JOIN stg_child_industry_hash h ON s.submission_id = h.submission_id
                    -- Look up past active profiles linked to this natural key text string
                    LEFT JOIN public.dim_entities de_all ON de_all.natural_key = (s.parsed_data->'metadata'->>'Rated entity')
                    LEFT JOIN public.dim_profiles dp_old ON dp_old.entity_key = de_all.entity_key AND dp_old.is_current = TRUE
                ),
                processed_hash AS (
                    SELECT
                        *,
                        md5(concat_ws('|',
                            business_risk_profile, blended_industry_risk, competitive_positioning,
                            market_share, diversification, operating_profitability, financial_risk_profile,
                            leverage, interest_cover, cash_flow_cover, liquidity_notches,
                            specific_factors_1, specific_factors_2, segmentation_criteria,
                            rating_methodologies_applied, industry_aggregate_hash_key
                        )) AS profile_hash_key
                    FROM processed_staging
                    WHERE entity_key IS NOT NULL
                )
                UPDATE public.dim_profiles dp
                SET is_current = FALSE,
                    valid_to = ph.now
                FROM processed_hash ph
                WHERE dp.entity_key = ph.entity_key
                AND dp.is_current = TRUE
                AND dp.profile_hash_key != ph.profile_hash_key;
            """
            tcur.execute(sql_update, (submission_id,))

            # 2. Second isolated statement: Direct target INSERT bound strictly to the passed new entity_key
            sql_insert = """
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested_industries AS (
                    SELECT
                        s.submission_id,
                        ind.sector,
                        CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                        ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk')
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                stg_child_industry_hash AS (
                    SELECT
                        submission_id,
                        md5(string_agg(concat(sector, '|', weight, '|', score), ',' ORDER BY sector)) AS industry_aggregate_hash_key
                    FROM unnested_industries
                    GROUP BY submission_id
                ),
                processed_staging AS (
                    SELECT
                        s.submission_id, s.now,
                        s.parsed_data->'metadata'->>'Business risk profile' AS business_risk_profile,
                        s.parsed_data->'metadata'->>'(Blended) Industry risk profile' AS blended_industry_risk,
                        s.parsed_data->'metadata'->>'Competitive Positioning' AS competitive_positioning,
                        s.parsed_data->'metadata'->>'Market share' AS market_share,
                        s.parsed_data->'metadata'->>'Diversification' AS diversification,
                        s.parsed_data->'metadata'->>'Operating profitability' AS operating_profitability,
                        s.parsed_data->'metadata'->>'Financial risk profile' AS financial_risk_profile,
                        s.parsed_data->'metadata'->>'Leverage' AS leverage,
                        s.parsed_data->'metadata'->>'Interest cover' AS interest_cover,
                        s.parsed_data->'metadata'->>'Cash flow cover' AS cash_flow_cover,
                        s.parsed_data->'metadata'->>'Liquidity' AS liquidity_notches,
                        s.parsed_data->'metadata'->>'Sector/company-specific factors (1)' AS specific_factors_1,
                        s.parsed_data->'metadata'->>'Sector/company-specific factors (2)' AS specific_factors_2,
                        s.parsed_data->'metadata'->>'Segmentation criteria' AS segmentation_criteria,
                        s.parsed_data->'metadata'->>'Rating methodologies applied' AS rating_methodologies_applied,
                        h.industry_aggregate_hash_key
                    FROM raw_submission s
                    LEFT JOIN stg_child_industry_hash h ON s.submission_id = h.submission_id
                ),
                processed_hash AS (
                    SELECT
                        *,
                        md5(concat_ws('|',
                            business_risk_profile, blended_industry_risk, competitive_positioning,
                            market_share, diversification, operating_profitability, financial_risk_profile,
                            leverage, interest_cover, cash_flow_cover, liquidity_notches,
                            specific_factors_1, specific_factors_2, segmentation_criteria,
                            rating_methodologies_applied, industry_aggregate_hash_key
                        )) AS profile_hash_key
                    FROM processed_staging
                )
                INSERT INTO public.dim_profiles (
                    entity_key, profile_hash_key, industry_aggregate_hash_key, business_risk_profile, blended_industry_risk,
                    competitive_positioning, market_share, diversification, operating_profitability,
                    financial_risk_profile, leverage, interest_cover, cash_flow_cover,
                    liquidity_notches, specific_factors_1, specific_factors_2, segmentation_criteria,
                    rating_methodologies_applied, is_current, valid_from, valid_to, submission_id
                )
                SELECT
                    %s AS entity_key, ph.profile_hash_key, ph.industry_aggregate_hash_key, ph.business_risk_profile, ph.blended_industry_risk,
                    ph.competitive_positioning, ph.market_share, ph.diversification, ph.operating_profitability,
                    ph.financial_risk_profile, ph.leverage, ph.interest_cover, ph.cash_flow_cover,
                    ph.liquidity_notches, ph.specific_factors_1, ph.specific_factors_2, ph.segmentation_criteria,
                    ph.rating_methodologies_applied, TRUE, ph.now, NULL, ph.submission_id
                FROM processed_hash ph
                LEFT JOIN public.dim_profiles dp ON dp.entity_key = %s AND dp.is_current = TRUE
                WHERE dp.profile_key IS NULL OR dp.profile_hash_key != ph.profile_hash_key;
            """
            # Note the parameter passing mapping to bind the explicit new entity_key safely
            tcur.execute(sql_insert, (submission_id, entity_key, entity_key))
            
            profile_key = self.get_profile_key(tcur=tcur, entity_key=entity_key)
            return profile_key if profile_key else 0
                
        except Exception as e:
            self.logger.error("Failed dimensional profile database load on submission %s: %s", submission_id, e)
            raise e

                
        except Exception as e:
            self.logger.error("Failed dimensional profile database load on submission %s: %s", submission_id, e)
            raise e
    
    def load_ind_profile(self, tcur: any, submission_id: int, profile_key: int) -> List[int]:
        """Loads industry risk profile dimensions using parent-linked history tracking."""
        try:
            # 1. Isolated UPDATE: Sweep and expire any active child rows that belong to 
            # this submission's natural key but are NOT tied to the newly generated profile_key.
            sql_update_query = """
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested_industries AS (
                    SELECT
                        s.submission_id, s.now,
                        ind.sector AS sector_name,
                        CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                        ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk')
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                -- Find ALL profile keys (past and present) tied to this entity's natural key
                historical_parent_scope AS (
                    SELECT dp.profile_key
                    FROM public.dim_profiles dp
                    JOIN public.dim_entities de ON dp.entity_key = de.entity_key
                    CROSS JOIN raw_submission s
                    WHERE de.natural_key = (s.parsed_data->'metadata'->>'Rated entity')
                ),
                stg_child_hashes AS (
                    SELECT
                        ui.submission_id, ui.now, ui.sector_name, ui.weight, ui.score,
                        md5(concat_ws('|', ui.sector_name, ui.weight::text, ui.score)) AS industry_hash_key
                    FROM unnested_industries ui
                )
                UPDATE public.dim_ind_profile dip
                SET is_current = FALSE,
                    valid_to = sch.now
                FROM stg_child_hashes sch
                WHERE dip.profile_key IN (SELECT profile_key FROM historical_parent_scope)
                  AND dip.sector_name = sch.sector_name
                  AND dip.is_current = TRUE
                  -- CRITICAL TRAP FIX: Expire it if its hash changed OR if it belongs to an older profile version
                  AND (dip.industry_hash_key != sch.industry_hash_key OR dip.profile_key != %s);
            """
            # Pass submission_id for the CTE, and the new profile_key for the evaluation check
            tcur.execute(sql_update_query, (submission_id, profile_key))
 
            # 2. Isolated INSERT: Append the current record matrix tied strictly to the new profile_key
            sql_insert_query = """
                WITH raw_submission AS (
                    SELECT id AS submission_id, parsed_data, NOW() AS now
                    FROM public.submissions WHERE id = %s
                ),
                unnested_industries AS (
                    SELECT
                        s.submission_id,
                        ind.sector AS sector_name,
                        CAST(REGEXP_REPLACE(COALESCE(ind."Industry weight", '0'), '[^0-9.]', '', 'g') AS FLOAT) AS weight,
                        ind."Industry risk score" AS score
                    FROM raw_submission s
                    CROSS JOIN LATERAL jsonb_to_recordset(s.parsed_data->'metadata'->'Industry risk')
                        AS ind(sector TEXT, "Industry weight" TEXT, "Industry risk score" TEXT)
                ),
                stg_aggregate_hash AS (
                    SELECT
                        submission_id,
                        md5(string_agg(concat(sector_name, '|', weight, '|', score), ',' ORDER BY sector_name)) AS industry_aggregate_hash_key
                    FROM unnested_industries
                    GROUP BY submission_id
                ),
                stg_child_hashes AS (
                    SELECT
                        ui.submission_id, ui.sector_name, ui.weight, ui.score,
                        ah.industry_aggregate_hash_key,
                        md5(concat_ws('|', ui.sector_name, ui.weight::text, ui.score)) AS industry_hash_key
                    FROM unnested_industries ui
                    JOIN stg_aggregate_hash ah ON ah.submission_id = ui.submission_id
                )
                INSERT INTO public.dim_ind_profile (
                    profile_key, industry_hash_key, industry_aggregate_hash_key,
                    sector_name, industry_weight_percentage, industry_risk_score,
                    is_current, valid_from, valid_to, submission_id
                )
                SELECT
                    %s AS profile_key, sch.industry_hash_key, sch.industry_aggregate_hash_key,
                    sch.sector_name, sch.weight, sch.score,
                    TRUE, NOW(), NULL, sch.submission_id
                FROM stg_child_hashes sch
                LEFT JOIN public.dim_ind_profile dip
                    ON dip.profile_key = %s
                   AND sch.sector_name = dip.sector_name
                   AND dip.is_current = TRUE
                WHERE dip.industry_profile_key IS NULL;
            """
            tcur.execute(sql_insert_query, (submission_id, profile_key, profile_key))

            return self.get_ind_profile_keys(tcur=tcur, profile_key=profile_key)
        except Exception as err:
            self.logger.error("Failed executing Type-2 SCD split process for dim_ind_profile: %s", err)
            raise err

        
    def load_fct_metric(self, tcur: any, submission_id: int,profile_key:int)  -> List[int]:
        """Populates industrial sector segmentation metrics grids."""
        try:
            #self.logger.info("************Inside Fact Load  **************** %s")
            sql_insert =  """INSERT INTO fct_rating_metric (
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
                    RETURNING fact_metric_key;
              """
            tcur.execute(sql_insert, (submission_id,))
            result = self.get_fact_keys(tcur=tcur,profile_key=profile_key)
            if result:
                return result
            return []
        except Exception as err:
            self.logger.error("Failed executing Type-2 SCD split process for dim_ind_profile: %s", err)
            raise err

              
        