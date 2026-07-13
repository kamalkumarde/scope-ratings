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
    lineage_trace              jsonb                    default '{}'::jsonb,
    run_id                     integer                  default 0
);

alter table public.submissions
    owner to rating_warehouse_user;

create table public.pipeline_audit_logs
(
    id                serial
        primary key,
    filename          varchar(255) not null,
    submission_id     integer,
    execution_status  varchar(50)  not null,
    processed_records integer                  default 0,
    error_message     text,
    started_at        timestamp with time zone default CURRENT_TIMESTAMP,
    completed_at      timestamp with time zone
);

alter table public.pipeline_audit_logs
    owner to rating_warehouse_user;

create index idx_pipeline_audit_filename
    on public.pipeline_audit_logs (filename);

create table public.submission_errors
(
    id              serial
        primary key,
    submission_id integer,
    filename      text,
    error_message text
);

alter table public.submission_errors
    owner to rating_warehouse_user;

create table public.dim_entities
(
    entity_key            serial
        primary key,
    natural_key           text                 not null,
    entity_name           text                 not null,
    country_of_origin     text,
    sector                text,
    accounting_principles text,
    currency              text,
    year_end              text,
    entity_hash_key       char(32)             not null,
    is_current            boolean default true not null,
    valid_from            timestamp            not null,
    valid_to              timestamp,
    submission_id         integer              not null
);

alter table public.dim_entities
    owner to rating_warehouse_user;

create unique index uq_active_entity
    on public.dim_entities (natural_key)
    where (is_current = true);

create index idx_entities_natural
    on public.dim_entities (natural_key);

create table public.dim_profiles
(
    profile_key                  serial
        primary key,
    entity_key                   integer              not null
        constraint fk_profiles_entity
            references public.dim_entities
            on delete cascade,
    entity_hash_key              char(32)             not null,
    profile_hash_key             char(32)             not null,
    industry_aggregate_hash_key  char(32),
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
    submission_id                integer              not null
);

alter table public.dim_profiles
    owner to rating_warehouse_user;

create unique index uq_active_profile
    on public.dim_profiles (entity_key)
    where (is_current = true);

create index idx_profiles_entity
    on public.dim_profiles (entity_key);

create index idx_profiles_entity_hash
    on public.dim_profiles (entity_hash_key);

create table public.dim_ind_profile
(
    industry_profile_key        serial
        primary key,
    profile_key                 integer              not null
        constraint fk_ind_profile
            references public.dim_profiles
            on delete cascade,
    profile_hash_key            char(32),
    industry_hash_key           char(32)             not null,
    industry_aggregate_hash_key char(32),
    sector_name                 text                 not null,
    industry_weight_percentage  double precision     not null,
    industry_risk_score         varchar(10),
    is_current                  boolean default true not null,
    valid_from                  timestamp            not null,
    valid_to                    timestamp,
    submission_id               integer              not null,
    constraint uq_profile_sector_hash
        unique (profile_key, sector_name, industry_hash_key)
);

alter table public.dim_ind_profile
    owner to rating_warehouse_user;

create unique index uq_active_industry
    on public.dim_ind_profile (profile_key, sector_name, industry_hash_key)
    where (is_current = true);

create index idx_ind_profile_parent
    on public.dim_ind_profile (profile_key);

create table public.fct_rating_metric
(
    fact_metric_key             serial
        primary key,
    entity_key                  integer not null,
    profile_key                 integer not null,
    industry_aggregate_hash_key char(32),
    submission_id               integer not null,
    metric_name                 text    not null,
    year_label                  text    not null,
    calendar_year               integer,
    is_forecast                 boolean,
    metric_value                numeric(18, 4),
    metric_value_formatted      text,
    processing_status           text,
    updated_at                  timestamp default now()
);

alter table public.fct_rating_metric
    owner to rating_warehouse_user;

create unique index uq_fact_metric
    on public.fct_rating_metric (entity_key, profile_key, metric_name, calendar_year);

create table public.pipeline_runs
(
    run_id        serial
        primary key,
    started_at    timestamp default CURRENT_TIMESTAMP,
    status        varchar(20),
    total_files   integer   default 0,
    success_count integer   default 0,
    failure_count integer   default 0,
    skipped_count integer   default 0
);

alter table public.pipeline_runs
    owner to rating_warehouse_user;

create table public.pipeline_file_details
(
    id              serial
        primary key,
    run_id          bigint
        references public.pipeline_runs
            on delete cascade,
    file_name       varchar(255)                                                        not null,
    processed_at    timestamp default CURRENT_TIMESTAMP,
    outcome         varchar(20),
    submission_id   integer,
    execution_stage varchar(50),
    error_message   text,
    file_content    bytea
);

alter table public.pipeline_file_details
    owner to rating_warehouse_user;

