-- Payment Analytics Warehouse Schema
-- Star schema: dimension tables + fact table + aggregation materializations

begin;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

create table if not exists dim_customers (
    customer_id        varchar(10) primary key,
    customer_name      varchar(100) not null,
    email              varchar(100),
    phone              varchar(20),
    city               varchar(50),
    state              varchar(50),
    x_customer_id      double precision,
    y_customer_id      double precision,
    mean_amount        double precision,
    std_amount         double precision,
    mean_nb_tx_per_day double precision,
    registration_date  date,
    device_preference  varchar(20),
    created_at         timestamp default now()
);

create table if not exists dim_merchants (
    merchant_id          varchar(10) primary key,
    merchant_name        varchar(200) not null,
    category             varchar(50),
    city                 varchar(50),
    state                varchar(50),
    x_merchant_id        double precision,
    y_merchant_id        double precision,
    risk_score           integer check (risk_score between 0 and 100),
    registration_date    date,
    avg_transaction_value double precision,
    status               varchar(20),
    created_at           timestamp default now()
);

-- ============================================================================
-- FACT TABLE
-- ============================================================================

create table if not exists fact_transactions (
    transaction_id              varchar(15) primary key,
    customer_id                 varchar(10) references dim_customers(customer_id) on delete set null,
    merchant_id                 varchar(10) references dim_merchants(merchant_id) on delete set null,
    amount                      double precision not null,
    payment_method              varchar(20),
    category                    varchar(50),
    city                        varchar(50),
    state                       varchar(50),
    timestamp                   timestamp not null,
    status                      varchar(20),
    device_type                 varchar(20),
    is_fraud                    smallint default 0,
    fraud_score                 double precision,
    risk_level                  varchar(10),
    transaction_hour            integer check (transaction_hour between 0 and 23),
    weekend_flag                smallint default 0,
    customer_merchant_distance  double precision,
    created_at                  timestamp default now()
);

-- Indexes
create index if not exists idx_txn_customer      on fact_transactions(customer_id);
create index if not exists idx_txn_merchant      on fact_transactions(merchant_id);
create index if not exists idx_txn_timestamp     on fact_transactions(timestamp);
create index if not exists idx_txn_date          on fact_transactions((timestamp::date));
create index if not exists idx_txn_status        on fact_transactions(status);
create index if not exists idx_txn_is_fraud      on fact_transactions(is_fraud);
create index if not exists idx_txn_category      on fact_transactions(category);
create index if not exists idx_txn_city          on fact_transactions(city);
create index if not exists idx_txn_payment_method on fact_transactions(payment_method);
create index if not exists idx_txn_risk_level    on fact_transactions(risk_level);
create index if not exists idx_txn_amount        on fact_transactions(amount);
create index if not exists idx_txn_cust_date     on fact_transactions(customer_id, (timestamp::date));
create index if not exists idx_txn_merch_date    on fact_transactions(merchant_id, (timestamp::date));

-- ============================================================================
-- AGGREGATION TABLES
-- ============================================================================

create table if not exists agg_daily_revenue (
    txn_date              date primary key,
    total_revenue          double precision,
    total_transactions     integer,
    success_count          integer,
    failed_count           integer,
    refunded_count         integer,
    avg_transaction_value  double precision,
    fraud_count            integer,
    fraud_amount           double precision
);

create table if not exists agg_merchant_kpis (
    merchant_id        varchar(10) references dim_merchants(merchant_id) on delete cascade,
    metric_date        date default current_date,
    total_revenue       double precision,
    transaction_count   integer,
    unique_customers    integer,
    refund_rate         double precision,
    fraud_rate          double precision,
    merchant_score      double precision,
    primary key (merchant_id, metric_date)
);

create table if not exists agg_fraud_summary (
    txn_date            date primary key,
    total_transactions   integer,
    fraud_transactions   integer,
    fraud_rate           double precision,
    fraud_amount         double precision,
    total_amount         double precision,
    high_risk_count      integer,
    medium_risk_count    integer,
    low_risk_count       integer
);

create table if not exists agg_customer_segments (
    segment_id       serial primary key,
    segment_name     varchar(50),
    customer_count   integer,
    avg_spend        double precision,
    avg_transactions  double precision,
    total_revenue     double precision,
    updated_at       timestamp default now()
);

create table if not exists agg_payment_trends (
    payment_method    varchar(20),
    month             date,
    transaction_count integer,
    total_amount      double precision,
    primary key (payment_method, month)
);

create table if not exists agg_support_metrics (
    issue_type            varchar(30) primary key,
    ticket_count          integer,
    open_count            integer,
    resolved_count        integer,
    escalated_count       integer,
    high_priority_count   integer
);

-- ============================================================================
-- CONVENIENCE VIEWS
-- ============================================================================

create or replace view v_fraud_alerts as
    select
        t.transaction_id,
        t.timestamp,
        t.amount,
        t.payment_method,
        t.category,
        t.city,
        t.status,
        t.device_type,
        t.fraud_score,
        t.risk_level,
        t.customer_merchant_distance,
        t.transaction_hour,
        t.weekend_flag,
        c.customer_name,
        c.device_preference as customer_device,
        m.merchant_name,
        m.risk_score        as merchant_risk_score
    from fact_transactions t
    join dim_customers c on t.customer_id = c.customer_id
    join dim_merchants m  on t.merchant_id = m.merchant_id
    where t.is_fraud = 1
    order by t.timestamp desc;

create or replace view v_merchant_performance as
    select
        m.merchant_id,
        m.merchant_name,
        m.category,
        m.city,
        m.state,
        m.risk_score,
        m.status,
        count(t.transaction_id)                                    as total_txns,
        coalesce(sum(t.amount) filter (where t.status = 'Success'), 0) as revenue,
        coalesce(avg(t.amount) filter (where t.status = 'Success'), 0) as avg_txn_value,
        count(distinct t.customer_id)                              as unique_customers,
        coalesce(count(*) filter (where t.is_fraud = 1) * 100.0 / nullif(count(*), 0), 0) as fraud_pct,
        coalesce(count(*) filter (where t.status = 'Refunded') * 100.0 / nullif(count(*), 0), 0) as refund_pct
    from dim_merchants m
    left join fact_transactions t on m.merchant_id = t.merchant_id
    group by m.merchant_id, m.merchant_name, m.category, m.city, m.state, m.risk_score, m.status;

create or replace view v_customer_summary as
    select
        c.customer_id,
        c.customer_name,
        c.city,
        c.state,
        c.registration_date,
        c.device_preference,
        count(t.transaction_id)                                    as total_txns,
        coalesce(sum(t.amount) filter (where t.status = 'Success'), 0) as total_spend,
        coalesce(avg(t.amount) filter (where t.status = 'Success'), 0) as avg_txn_value,
        max(t.timestamp)                                           as last_txn,
        count(distinct t.merchant_id)                              as unique_merchants,
        coalesce(count(*) filter (where t.is_fraud = 1), 0)        as fraud_txn_count
    from dim_customers c
    left join fact_transactions t on c.customer_id = t.customer_id
    group by c.customer_id, c.customer_name, c.city, c.state, c.registration_date, c.device_preference;

commit;
