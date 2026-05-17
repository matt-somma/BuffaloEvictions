DROP TABLE IF EXISTS analytics.tract_state_persistence;

CREATE TABLE analytics.tract_state_persistence AS
WITH monthly_base AS (
    SELECT
        geoid,
        month_date,
        rolling_3m_active_cases,
        rolling_6m_active_cases,
        rolling_12m_active_cases,

        rolling_3m_active_cases - rolling_12m_active_cases
            AS acceleration_score,

        rolling_6m_active_cases - rolling_12m_active_cases
            AS medium_term_acceleration
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
),

classified AS (
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
    FROM scored
),

state_changes AS (
    SELECT
        *,
        LAG(neighborhood_trajectory) OVER (
            PARTITION BY geoid
            ORDER BY month_date
        ) AS previous_trajectory,

        CASE
            WHEN LAG(neighborhood_trajectory) OVER (
                PARTITION BY geoid
                ORDER BY month_date
            ) IS NULL
            THEN 0

            WHEN neighborhood_trajectory <>
                 LAG(neighborhood_trajectory) OVER (
                    PARTITION BY geoid
                    ORDER BY month_date
                 )
            THEN 1

            ELSE 0
        END AS state_change_flag
    FROM classified
),

state_groups AS (
    SELECT
        *,
        SUM(state_change_flag) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS state_group_id
    FROM state_changes
),

with_streaks AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY geoid, state_group_id
            ORDER BY month_date
        ) AS months_in_current_state
    FROM state_groups
),

summary_features AS (
    SELECT
        geoid,

        COUNT(*) AS total_months_observed,

        SUM(state_change_flag) AS total_state_changes,

        COUNT(*) FILTER (
            WHERE neighborhood_trajectory = 'Rapid Deterioration'
        ) AS months_rapid_deterioration,

        COUNT(*) FILTER (
            WHERE neighborhood_trajectory = 'Chronic Distress'
        ) AS months_chronic_distress,

        COUNT(*) FILTER (
            WHERE neighborhood_trajectory = 'Emerging Risk'
        ) AS months_emerging_risk,

        COUNT(*) FILTER (
            WHERE neighborhood_trajectory = 'Improving'
        ) AS months_improving,

        COUNT(*) FILTER (
            WHERE neighborhood_trajectory = 'Stable'
        ) AS months_stable,

        MAX(months_in_current_state) AS longest_state_streak
    FROM with_streaks
    GROUP BY geoid
),

latest AS (
    SELECT DISTINCT ON (geoid)
        geoid,
        month_date AS latest_month,
        neighborhood_trajectory AS current_trajectory,
        previous_trajectory,
        months_in_current_state,
        rolling_3m_active_cases,
        rolling_6m_active_cases,
        rolling_12m_active_cases,
        acceleration_score,
        combined_trajectory_score
    FROM with_streaks
    ORDER BY geoid, month_date DESC
)

SELECT
    l.*,
    s.total_months_observed,
    s.total_state_changes,
    s.months_rapid_deterioration,
    s.months_chronic_distress,
    s.months_emerging_risk,
    s.months_improving,
    s.months_stable,
    s.longest_state_streak,

    (
        s.months_rapid_deterioration
      + s.months_chronic_distress
      + s.months_emerging_risk
    ) AS months_any_distress,

    (
        s.months_rapid_deterioration
      + s.months_chronic_distress
      + s.months_emerging_risk
    )::numeric / NULLIF(s.total_months_observed, 0)
        AS distress_persistence_rate

FROM latest l
JOIN summary_features s
    ON l.geoid = s.geoid;

ALTER TABLE analytics.tract_state_persistence
ADD PRIMARY KEY (geoid);