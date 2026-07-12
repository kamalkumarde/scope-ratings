create table public.submissions
(
    id                         integer generated always as identity
        primary key,
    filename                   varchar(255)  not null,
    final_status               varchar(255)  not null,
    current_status             varchar(255),
    current_status_time        timestamp with time zone default CURRENT_TIMESTAMP,
    submitted_at               timestamp with time zone default CURRENT_TIMESTAMP,
    execution_duration_seconds numeric(6, 3) not null,
    file_metadata              jsonb                    default '{}'::jsonb,
    parsed_data                jsonb                    default '{}'::jsonb,
    lineage_trace              jsonb                    default '{}'::jsonb
);

alter table public.submissions
    owner to rating_warehouse_user;

create table public.dim_entities
(
    entity_key            serial
        primary key,
    natural_key           text                 not null,
    sector                text,
    currency              text,
    accounting_principles text,
    year_end              text,
    entity_hash_key       char(32)             not null,
    entity_name           text                 not null,
    country_of_origin     text,
    is_current            boolean default true not null,
    valid_from            timestamp            not null,
    valid_to              timestamp,
    submission_id         integer              not null
);

alter table public.dim_entities
    owner to rating_warehouse_user;

create table public.dim_profiles
(
    profile_key                  serial
        primary key,
    entity_key                   integer              not null
        constraint fk_profiles_parent_entity
            references public.dim_entities
            on delete cascade,
    profile_hash_key             char(32)             not null,
    business_risk_profile        text,
    blended_industry_risk        text,
    competitive_positioning      text,
    market_share                 text,
    diversification              text,
    operating_profitability      text,
    financial_risk_profile       text,
    leverage                     text,
    interest_cover               text,
    cash_flow_cover              text,
    liquidity_notches            text,
    specific_factors_1           text,
    specific_factors_2           text,
    segmentation_criteria        text,
    rating_methodologies_applied text,
    is_current                   boolean default true not null,
    valid_from                   timestamp            not null,
    valid_to                     timestamp,
    submission_id                integer              not null,
    industry_aggregate_hash_key  char(32)
);

alter table public.dim_profiles
    owner to rating_warehouse_user;

create unique index uq_active_profile
    on public.dim_profiles (entity_key)
    where (is_current = true);

create index idx_dim_profiles_lookup
    on public.dim_profiles (entity_key, valid_from, valid_to);

create table public.dim_ind_profile
(
    industry_profile_key        serial
        primary key,
    profile_key                 integer              not null
        constraint fk_ind_profile_parent
            references public.dim_profiles
            on delete cascade,
    industry_hash_key           char(32)             not null,
    sector_name                 text                 not null,
    industry_weight_percentage  double precision     not null,
    industry_risk_score         varchar(10),
    is_current                  boolean default true not null,
    valid_from                  timestamp            not null,
    valid_to                    timestamp,
    submission_id               integer              not null,
    industry_aggregate_hash_key char(32)
);

alter table public.dim_ind_profile
    owner to rating_warehouse_user;

create unique index uq_active_ind_sector
    on public.dim_ind_profile (profile_key, sector_name)
    where (is_current = true);

create table public.fct_rating_metric
(
    fact_metric_key             bigserial
        primary key,
    entity_key                  integer     not null,
    profile_key                 integer     not null,
    industry_aggregate_hash_key varchar,
    submission_id               integer     not null,
    metric_name                 text        not null,
    year_label                  varchar(50) not null,
    calendar_year               integer     not null,
    is_forecast                 boolean                  default false,
    metric_value                numeric(18, 4),
    metric_value_formatted      varchar(100),
    processing_status           varchar(100),
    created_at                  timestamp with time zone default now(),
    updated_at                  timestamp with time zone default now(),
    constraint uq_fct_rating_metric_entity_grain
        unique (entity_key, metric_name, calendar_year)
);

alter table public.fct_rating_metric
    owner to rating_warehouse_user;

create index idx_fct_rating_entity
    on public.fct_rating_metric (entity_key);

create index idx_fct_rating_profile
    on public.fct_rating_metric (profile_key);

create index idx_fct_rating_ind_profile
    on public.fct_rating_metric (industry_aggregate_hash_key);

create index idx_fct_rating_metric_name
    on public.fct_rating_metric (metric_name);

CREATE TABLE IF NOT EXISTS public.pipeline_audit_logs (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    execution_status VARCHAR(50) NOT NULL, -- 'STARTED', 'SUCCESS', 'FAILURE'
    processed_records INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Index for faster analytical lookups
CREATE INDEX IF NOT EXISTS idx_pipeline_audit_filename ON public.pipeline_audit_logs(filename);    

