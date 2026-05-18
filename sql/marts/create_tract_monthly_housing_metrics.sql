DROP TABLE IF EXISTS analytics.tract_monthly_housing_metrics;

CREATE TABLE analytics.tract_monthly_housing_metrics AS
WITH bounds AS (
    SELECT
        MIN(date_trunc('month', violation_date))::date AS min_month,
        MAX(date_trunc('month', violation_date))::date AS max_month
    FROM staging.buffalo_code_violations_clean
    WHERE geoid IS NOT NULL
),

calendar AS (
    SELECT
        generate_series(
            min_month,
            max_month,
            INTERVAL '1 month'
        )::date AS month_date
    FROM bounds
),

geoids AS (
    SELECT DISTINCT
        geoid
    FROM staging.buffalo_code_violations_clean
    WHERE geoid IS NOT NULL
),

tract_month_grid AS (
    SELECT
        g.geoid,
        c.month_date
    FROM geoids g
    CROSS JOIN calendar c
),

monthly AS (
    SELECT
        geoid,
        date_trunc('month', violation_date)::date AS month_date,
        COUNT(DISTINCT case_number) AS total_cases,
        COUNT(DISTINCT case_number)
            FILTER (WHERE status = 'ACTIVE')
            AS active_cases,
        COUNT(DISTINCT sbl) AS distinct_properties,
        COUNT(DISTINCT sbl)
            FILTER (WHERE status = 'ACTIVE')
            AS active_properties
    FROM staging.buffalo_code_violations_clean
    WHERE geoid IS NOT NULL
    GROUP BY
        geoid,
        date_trunc('month', violation_date)
),

joined AS (
    SELECT
        grid.geoid,
        grid.month_date,

        COALESCE(m.total_cases, 0) AS total_cases,
        COALESCE(m.active_cases, 0) AS active_cases,
        COALESCE(m.distinct_properties, 0) AS distinct_properties,
        COALESCE(m.active_properties, 0) AS active_properties,

        a.total_population,
        a.occupied_housing_units,

        COALESCE(m.total_cases, 0)::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000
            AS total_cases_per_1000_units,

        COALESCE(m.active_cases, 0)::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000
            AS active_cases_per_1000_units
    FROM tract_month_grid grid
    LEFT JOIN monthly m
        ON grid.geoid = m.geoid
       AND grid.month_date = m.month_date
    LEFT JOIN raw.acs_demographics a
        ON grid.geoid = a.geoid
),

rolling AS (
    SELECT
        *,

        AVG(active_cases_per_1000_units) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_active_cases,

        AVG(active_cases_per_1000_units) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS rolling_6m_active_cases,

        AVG(active_cases_per_1000_units) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS rolling_12m_active_cases,

        SUM(total_cases) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS cases_last_3m,

        SUM(total_cases) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS cases_last_6m,

        SUM(total_cases) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS cases_last_12m
    FROM joined
)

SELECT
    *,

    cases_last_3m::numeric
        / NULLIF(occupied_housing_units, 0) * 1000
        AS cases_last_3m_per_1000_units,

    cases_last_6m::numeric
        / NULLIF(occupied_housing_units, 0) * 1000
        AS cases_last_6m_per_1000_units,

    cases_last_12m::numeric
        / NULLIF(occupied_housing_units, 0) * 1000
        AS cases_last_12m_per_1000_units
FROM rolling;

ALTER TABLE analytics.tract_monthly_housing_metrics
ADD PRIMARY KEY (geoid, month_date);

CREATE INDEX IF NOT EXISTS idx_tract_monthly_housing_metrics_month
ON analytics.tract_monthly_housing_metrics (month_date);
