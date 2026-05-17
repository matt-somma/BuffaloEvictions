DROP TABLE IF EXISTS analytics.tract_state_history;

CREATE TABLE analytics.tract_state_history AS
WITH monthly_base AS (
    SELECT
        geoid,
        month_date,
        rolling_3m_active_cases,
        rolling_6m_active_cases,
        rolling_12m_active_cases,
        rolling_3m_active_cases - rolling_12m_active_cases AS acceleration_score,
        rolling_6m_active_cases - rolling_12m_active_cases AS medium_term_acceleration
    FROM analytics.tract_monthly_housing_metrics
),

ranked AS (
    SELECT
        *,
        PERCENT_RANK() OVER (
            PARTITION BY month_date
            ORDER BY acceleration_score
        ) AS acceleration_percentile,

        PERCENT_RANK() OVER (
            PARTITION BY month_date
            ORDER BY rolling_12m_active_cases
        ) AS chronic_distress_percentile,

        PERCENT_RANK() OVER (
            PARTITION BY month_date
            ORDER BY medium_term_acceleration
        ) AS medium_term_acceleration_percentile
    FROM monthly_base
),

scored AS (
    SELECT
        *,
        (
            0.50 * chronic_distress_percentile
          + 0.35 * acceleration_percentile
          + 0.15 * medium_term_acceleration_percentile
        ) * 100 AS combined_trajectory_score
    FROM ranked
)

SELECT
    *,
    CASE
        WHEN acceleration_percentile >= 0.90
             AND chronic_distress_percentile >= 0.80
        THEN 'Rapid Deterioration'

        WHEN chronic_distress_percentile >= 0.85
        THEN 'Chronic Distress'

        WHEN combined_trajectory_score >= 70
        THEN 'Emerging Risk'

        WHEN acceleration_percentile <= 0.20
             AND rolling_3m_active_cases < rolling_12m_active_cases
        THEN 'Improving'

        ELSE 'Stable'
    END AS neighborhood_trajectory
FROM scored;

ALTER TABLE analytics.tract_state_history
ADD PRIMARY KEY (geoid, month_date);