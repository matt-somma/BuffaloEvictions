DROP TABLE IF EXISTS analytics.tract_monthly_housing_metrics;

CREATE TABLE analytics.tract_monthly_housing_metrics AS

WITH monthly AS (
    SELECT
        geoid,

        date_trunc(
            'month',
            violation_date
        )::date AS month_date,

        COUNT(DISTINCT case_number) AS total_cases,

        COUNT(DISTINCT case_number)
            FILTER (WHERE status = 'ACTIVE')
            AS active_cases,

        COUNT(DISTINCT sbl)
            AS distinct_properties,

        COUNT(DISTINCT sbl)
            FILTER (WHERE status = 'ACTIVE')
            AS active_properties

    FROM staging.buffalo_code_violations_clean

    GROUP BY
        geoid,
        date_trunc('month', violation_date)
),

joined AS (
    SELECT
        m.*,

        a.total_population,
        a.occupied_housing_units,

        m.total_cases::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000
            AS total_cases_per_1000_units,

        m.active_cases::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000
            AS active_cases_per_1000_units

    FROM monthly m

    LEFT JOIN raw.acs_demographics a
        ON m.geoid = a.geoid
),

rolling AS (
    SELECT
        *,

        AVG(active_cases_per_1000_units)
            OVER (
                PARTITION BY geoid
                ORDER BY month_date
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ) AS rolling_3m_active_cases,

        AVG(active_cases_per_1000_units)
            OVER (
                PARTITION BY geoid
                ORDER BY month_date
                ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
            ) AS rolling_6m_active_cases,

        AVG(active_cases_per_1000_units)
            OVER (
                PARTITION BY geoid
                ORDER BY month_date
                ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
            ) AS rolling_12m_active_cases

    FROM joined
)

SELECT *
FROM rolling;