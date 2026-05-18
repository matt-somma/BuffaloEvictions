DROP TABLE IF EXISTS analytics.code_violation_features;

CREATE TABLE analytics.code_violation_features AS
WITH property_first_month AS (
    SELECT
        geoid,
        sbl,
        MIN(date_trunc('month', violation_date))::date AS first_violation_month
    FROM staging.buffalo_code_violations_clean
    WHERE geoid IS NOT NULL
      AND sbl IS NOT NULL
    GROUP BY
        geoid,
        sbl
),

property_counts AS (
    SELECT
        m.geoid,
        m.month_date,
        COUNT(p.sbl) AS distinct_properties_with_violations
    FROM analytics.tract_monthly_housing_metrics m
    LEFT JOIN property_first_month p
        ON m.geoid = p.geoid
       AND p.first_violation_month <= m.month_date
    GROUP BY
        m.geoid,
        m.month_date
),

base AS (
    SELECT
        m.geoid,
        m.month_date,

        SUM(m.total_cases) OVER (
            PARTITION BY m.geoid
            ORDER BY m.month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS total_cases,

        m.active_cases,
        m.cases_last_12m,
        m.cases_last_6m,
        m.cases_last_3m,

        p.distinct_properties_with_violations,

        MIN(
            CASE
                WHEN m.total_cases > 0 THEN m.month_date
            END
        ) OVER (
            PARTITION BY m.geoid
        ) AS first_violation_date,

        MAX(
            CASE
                WHEN m.total_cases > 0 THEN m.month_date
            END
        ) OVER (
            PARTITION BY m.geoid
            ORDER BY m.month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS latest_violation_date,

        m.total_population,
        m.occupied_housing_units,

        m.active_cases_per_1000_units
            AS active_cases_per_1000_housing_units,

        m.cases_last_12m_per_1000_units
            AS cases_last_12m_per_1000_housing_units,

        m.cases_last_6m_per_1000_units
            AS cases_last_6m_per_1000_housing_units,

        m.cases_last_3m_per_1000_units
            AS cases_last_3m_per_1000_housing_units,

        m.active_properties::numeric
            / NULLIF(m.occupied_housing_units, 0) * 1000
            AS active_properties_per_1000_housing_units
    FROM analytics.tract_monthly_housing_metrics m
    LEFT JOIN property_counts p
        ON m.geoid = p.geoid
       AND m.month_date = p.month_date
)

SELECT
    geoid,
    month_date,
    total_cases,
    active_cases,
    cases_last_12m,
    cases_last_6m,
    cases_last_3m,
    distinct_properties_with_violations,
    first_violation_date,
    latest_violation_date,
    total_population,
    occupied_housing_units,

    total_cases::numeric
        / NULLIF(occupied_housing_units, 0) * 1000
        AS total_cases_per_1000_housing_units,

    active_cases_per_1000_housing_units,
    cases_last_12m_per_1000_housing_units,
    cases_last_6m_per_1000_housing_units,
    cases_last_3m_per_1000_housing_units,

    distinct_properties_with_violations::numeric
        / NULLIF(occupied_housing_units, 0) * 1000
        AS properties_with_violations_per_1000_housing_units,

    active_properties_per_1000_housing_units
FROM base;

ALTER TABLE analytics.code_violation_features
ADD PRIMARY KEY (geoid, month_date);

CREATE INDEX IF NOT EXISTS idx_code_violation_features_geoid_month
ON analytics.code_violation_features (geoid, month_date);
