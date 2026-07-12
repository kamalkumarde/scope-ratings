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

            
                 


    

    def load_entity(self, tcur: any , submission_id: int, natural_key:str) -> int:
        try:
            shared_cte = """
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
            """

            sql_update = shared_cte + """
                UPDATE dim_entities de
                SET is_current = FALSE,
                    valid_to = ph.now
                FROM processed_hash ph
                WHERE de.natural_key = ph.natural_key
                  AND de.is_current = TRUE
                  AND de.entity_hash_key != ph.entity_hash_key;
            """
            tcur.execute(sql_update, (submission_id,))

            status = 'DIM ENTITY UPDATED'

            sql_insert = shared_cte + """
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
                WHERE de.entity_key IS NULL OR de.entity_hash_key != ph.entity_hash_key
                RETURNING entity_key;
            """
            tcur.execute(sql_insert, (submission_id,))

            entity_key = self.get_entity_key(tcur=tcur,natural_key=natural_key)

            if entity_key:
                return entity_key        


           

            
            
        except Exception as e:
            self.logger.error("Failed dimensional entity pipeline load on submission %s: %s", submission_id, e)
            raise e

    def load_profile(self, tcur: any, submission_id: int, entity_key:int) -> int:
        """Populates analytical profile attributes into dim_profiles using split SCD2 commands."""
        try:
            
            #self.logger.info("************Inside Profile Load ****************")
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
                        s.submission_id, s.now, de.entity_key,
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
                    LEFT JOIN public.dim_entities de ON de.natural_key = (s.parsed_data->'metadata'->>'Rated entity') AND de.is_current = TRUE
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
                UPDATE public.dim_profiles dp
                SET is_current = FALSE,
                    valid_to = ph.now
                FROM processed_hash ph
                WHERE dp.entity_key = ph.entity_key
                AND dp.is_current = TRUE
                AND dp.profile_hash_key != ph.profile_hash_key
                RETURNING dp.profile_key;
            """
            #self.logger.info("************Befpr Profile update ****************")
            tcur.execute(sql_update, (submission_id,))
            #self.logger.info("************After Profile update ****************")
            #result = tcur.fetchone()

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
                        s.submission_id, s.now, de.entity_key,
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
                    LEFT JOIN public.dim_entities de ON de.natural_key = (s.parsed_data->'metadata'->>'Rated entity') AND de.is_current = TRUE
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
                    ph.entity_key, ph.profile_hash_key, ph.industry_aggregate_hash_key, ph.business_risk_profile, ph.blended_industry_risk,
                    ph.competitive_positioning, ph.market_share, ph.diversification, ph.operating_profitability,
                    ph.financial_risk_profile, ph.leverage, ph.interest_cover, ph.cash_flow_cover,
                    ph.liquidity_notches, ph.specific_factors_1, ph.specific_factors_2, ph.segmentation_criteria,
                    ph.rating_methodologies_applied, TRUE, ph.now, NULL, ph.submission_id
                FROM processed_hash ph
                LEFT JOIN public.dim_profiles dp ON ph.entity_key = dp.entity_key AND dp.is_current = TRUE -- Changed to LEFT JOIN
                WHERE dp.profile_key IS NULL OR dp.profile_hash_key != ph.profile_hash_key
                RETURNING profile_key;
                """
            #self.logger.info("************Before Profile Insert **************** %s",sql_insert)
            tcur.execute(sql_insert, (submission_id,))
            #self.logger.info("************After Profile insert ****************")
            profile_key = self.get_profile_key(tcur=tcur, entity_key=entity_key)

            if profile_key:
                return profile_key
            return 0
        
                

                
        except Exception as e:
            self.logger.error("Failed dimensional profile database load on submission %s: %s", submission_id, e)
            raise e
    

    def load_ind_profile(self, tcur: any, submission_id: int, profile_key:int)  -> List[int]:
        
        try:
            #self.logger.info("************Inside  Ind profile  **************** %s")
            sql_update_query = """

                        WITH raw_submission AS (
                SELECT id AS submission_id, parsed_data, NOW() AS now
                FROM public.submissions WHERE id = %s
            ),
            -- 1. Parse and extract the child JSON array elements
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
            -- 2. Fetch the newly active parent profile key that was generated/kept in the previous phase
            active_parent AS (
                SELECT dp.profile_key, de.natural_key
                FROM public.dim_profiles dp
                JOIN public.dim_entities de ON dp.entity_key = de.entity_key AND de.is_current = TRUE
                CROSS JOIN raw_submission s
                WHERE de.natural_key = (s.parsed_data->'metadata'->>'Rated entity')
                AND dp.is_current = TRUE
            ),
            -- 3. Hash the incoming staging metrics for each individual sector
            stg_child_hashes AS (
                SELECT
                    ui.submission_id, ui.now, ui.sector_name, ui.weight, ui.score, ap.profile_key,
                    md5(concat_ws('|', ui.sector_name, ui.weight::text, ui.score)) AS industry_hash_key
                FROM unnested_industries ui
                JOIN active_parent ap ON TRUE
            )
            -- 4. Expire records where the sector is active but the metric hashes don't match
            UPDATE public.dim_ind_profile dip
            SET is_current = FALSE,
                valid_to = sch.now
            FROM stg_child_hashes sch
            WHERE dip.profile_key = sch.profile_key
            AND dip.sector_name = sch.sector_name
            AND dip.is_current = TRUE
            AND dip.industry_hash_key != sch.industry_hash_key
            RETURNING dip.industry_profile_key;
               
            """
            #self.logger.info("************Before ind Profile update **************** %s")
            tcur.execute(sql_update_query, (submission_id,))
            #self.logger.info("***********After  ind Profile update **************** %s")
 
            sql_insert_query = """
                 
                        WITH raw_submission AS (
                        SELECT id AS submission_id, parsed_data, NOW() AS now
                        FROM public.submissions WHERE id = %s
                    ),
                    -- 1. Parse and extract individual child JSON array elements
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
                    -- 2. DYNAMICALLY GENERATE THE AGGREGATE SHIELD FINGERPRINT
                    stg_aggregate_hash AS (
                        SELECT
                            submission_id,
                            md5(string_agg(concat(sector_name, '|', weight, '|', score), ',' ORDER BY sector_name)) AS industry_aggregate_hash_key
                        FROM unnested_industries
                        GROUP BY submission_id
                    ),
                    -- 3. Fetch the newly active parent profile key
                    active_parent AS (
                        SELECT dp.profile_key, dp.valid_from
                        FROM public.dim_profiles dp
                        JOIN public.dim_entities de ON dp.entity_key = de.entity_key AND de.is_current = TRUE
                        CROSS JOIN raw_submission s
                        WHERE de.natural_key = (s.parsed_data->'metadata'->>'Rated entity')
                        AND dp.is_current = TRUE
                    ),
                    -- 4. Gather metrics and map individual row-level hashes alongside the parent aggregate tag
                    stg_child_hashes AS (
                        SELECT
                            ui.submission_id, ap.valid_from, ui.sector_name, ui.weight, ui.score, ap.profile_key,
                            ah.industry_aggregate_hash_key, -- The parent version grouping fingerprint
                            md5(concat_ws('|', ui.sector_name, ui.weight::text, ui.score)) AS industry_hash_key -- The row-level fingerprint
                        FROM unnested_industries ui
                        JOIN active_parent ap ON TRUE
                        JOIN stg_aggregate_hash ah ON ah.submission_id = ui.submission_id
                    )
                    -- 5. Safely insert rows with the aggregate version tag included
                    INSERT INTO public.dim_ind_profile (
                        profile_key, industry_hash_key, industry_aggregate_hash_key, -- Stored here safely now
                        sector_name, industry_weight_percentage, industry_risk_score,
                        is_current, valid_from, valid_to, submission_id
                    )
                    SELECT
                        sch.profile_key, sch.industry_hash_key, sch.industry_aggregate_hash_key,
                        sch.sector_name, sch.weight, sch.score,
                        TRUE, sch.valid_from, NULL, sch.submission_id
                    FROM stg_child_hashes sch
                    LEFT JOIN public.dim_ind_profile dip
                        ON sch.profile_key = dip.profile_key
                    AND sch.sector_name = dip.sector_name
                    AND dip.is_current = TRUE
                    WHERE dip.industry_profile_key IS NULL
                    OR dip.industry_hash_key != sch.industry_hash_key
                    RETURNING industry_profile_key;
  
            """
            #self.logger.info("************Before ind  Profile Insert **************** %s")
            tcur.execute(sql_insert_query, (submission_id,))
            #self.logger.info("************After ind Profile Insert **************** %s")

            ind_profiles = self.get_ind_profile_keys(tcur=tcur,profile_key=profile_key)
            if ind_profiles:
                return ind_profiles
            return []
        
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

              
        