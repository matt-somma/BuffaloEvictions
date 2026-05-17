DROP TABLE IF EXISTS analytics.tract_trajectory_features;

CREATE TABLE analytics.tract_trajectory_features AS

WITH latest AS (
    SELECT
        *,

        rolling_3m_active_cases
            - rolling_12m_active_cases
            AS acceleration_score,

        rolling_6m_active_cases
            - rolling_12m_active_cases
            AS medium_term_acceleration

    FROM analytics.tract_monthly_housing_metrics

    WHERE month_date = (
        SELECT MAX(month_date)
        FROM analytics.tract_monthly_housing_metrics
    )
),

classified AS (
    SELECT
        *,

        CASE

            WHEN rolling_12m_active_cases >= 15
                 AND acceleration_score >= 5
            THEN 'Rapid Deterioration'

            WHEN rolling_12m_active_cases >= 15
            THEN 'Chronic Distress'

            WHEN acceleration_score >= 5
            THEN 'Emerging Risk'

            WHEN acceleration_score <= -3
            THEN 'Improving'

            ELSE 'Stable'

        END AS neighborhood_trajectory

    FROM latest
)

SELECT *
FROM classified;