-- Unlabeled live scoring feature set.
-- This table covers the newest months that are excluded from analytics.tract_ml_features
-- because future outcome labels are not yet fully observed.
DROP TABLE IF EXISTS analytics.tract_ml_scoring_features;

CREATE TABLE analytics.tract_ml_scoring_features AS
WITH state_history AS (
    SELECT
        geoid,
        month_date,
        neighborhood_trajectory,
        rolling_3m_active_cases,
        rolling_6m_active_cases,
        rolling_12m_active_cases,
        acceleration_score,
        medium_term_acceleration,
        acceleration_percentile,
        chronic_distress_percentile,
        medium_term_acceleration_percentile,
        combined_trajectory_score,

        LAG(neighborhood_trajectory, 1) OVER (
            PARTITION BY geoid ORDER BY month_date
        ) AS previous_trajectory,

        LAG(combined_trajectory_score, 1) OVER (
            PARTITION BY geoid ORDER BY month_date
        ) AS trajectory_score_lag_1m,

        LAG(acceleration_score, 1) OVER (
            PARTITION BY geoid ORDER BY month_date
        ) AS acceleration_score_lag_1m
    FROM analytics.tract_state_history
    WHERE geoid <> 'UNKNOWN'
),

persistence_flags AS (
    SELECT
        geoid,
        month_date,
        neighborhood_trajectory,

        CASE
            WHEN neighborhood_trajectory <>
                 LAG(neighborhood_trajectory) OVER (
                    PARTITION BY geoid ORDER BY month_date
                 )
            THEN 1
            ELSE 0
        END AS state_change_flag,

        CASE
            WHEN neighborhood_trajectory IN (
                'Emerging Risk',
                'Rapid Deterioration',
                'Chronic Distress'
            )
            THEN 1
            ELSE 0
        END AS distress_flag

    FROM analytics.tract_state_history
    WHERE geoid <> 'UNKNOWN'
),

persistence_asof AS (
    SELECT
        geoid,
        month_date,
        neighborhood_trajectory,

        COUNT(*) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS months_observed_to_date,

        SUM(distress_flag) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS distress_months_to_date,

        SUM(state_change_flag) OVER (
            PARTITION BY geoid
            ORDER BY month_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS state_changes_to_date

    FROM persistence_flags
),

acs AS (
    SELECT
        geoid,
        total_population,
        median_household_income,
        poverty_rate,
        unemployment_rate,
        renter_occupied_rate,
        rent_burden_rate,
        no_vehicle_rate,
        poverty_score,
        unemployment_score,
        rent_burden_score,
        renter_score,
        no_vehicle_score,
        income_stress_score,
        housing_instability_score_v1,
        housing_instability_score_v2
    FROM analytics.housing_risk_features_v2
),

code_features AS (
    SELECT
        geoid,
        month_date,
        total_cases,
        active_cases,
        cases_last_12m,
        cases_last_6m,
        cases_last_3m,
        active_cases_per_1000_housing_units,
        cases_last_12m_per_1000_housing_units,
        cases_last_6m_per_1000_housing_units,
        cases_last_3m_per_1000_housing_units,
        properties_with_violations_per_1000_housing_units,
        active_properties_per_1000_housing_units
    FROM analytics.code_violation_features
)

SELECT
    s.geoid,
    s.month_date,

    s.neighborhood_trajectory,
    s.previous_trajectory,

    s.rolling_3m_active_cases,
    s.rolling_6m_active_cases,
    s.rolling_12m_active_cases,
    s.acceleration_score,
    s.medium_term_acceleration,
    s.acceleration_percentile,
    s.chronic_distress_percentile,
    s.medium_term_acceleration_percentile,
    s.combined_trajectory_score,
    s.trajectory_score_lag_1m,
    s.acceleration_score_lag_1m,

    p.months_observed_to_date,
    p.distress_months_to_date,
    p.distress_months_to_date::numeric
        / NULLIF(p.months_observed_to_date, 0)
        AS distress_persistence_rate_to_date,
    p.state_changes_to_date,

    a.total_population,
    a.median_household_income,
    a.poverty_rate,
    a.unemployment_rate,
    a.renter_occupied_rate,
    a.rent_burden_rate,
    a.no_vehicle_rate,
    a.poverty_score,
    a.unemployment_score,
    a.rent_burden_score,
    a.renter_score,
    a.no_vehicle_score,
    a.income_stress_score,
    a.housing_instability_score_v1,
    a.housing_instability_score_v2,

    c.total_cases,
    c.active_cases,
    c.cases_last_12m,
    c.active_cases_per_1000_housing_units,
    c.cases_last_12m_per_1000_housing_units,
    c.cases_last_6m_per_1000_housing_units,
    c.cases_last_3m_per_1000_housing_units,
    c.properties_with_violations_per_1000_housing_units,
    c.active_properties_per_1000_housing_units,

    NULL::int AS future_distress_1m,
    NULL::int AS future_distress_3m,
    NULL::int AS future_distress_6m,
    NULL::int AS future_distress_12m,
    NULL::date AS first_future_distress_month,
    NULL::int AS months_until_future_distress,

    sp.neighbor_count,
    sp.neighbor_avg_trajectory_score,
    sp.neighbor_avg_acceleration_score,
    sp.neighbor_avg_rolling_3m,
    sp.neighbor_avg_rolling_12m,

    sp.distressed_neighbor_count,
    sp.rapid_neighbor_count,
    sp.chronic_neighbor_count,

    sp.reliable_distressed_neighbor_share,
    sp.reliable_rapid_neighbor_share,
    sp.reliable_chronic_neighbor_share,

    sp.border_weighted_neighbor_score,
    sp.border_weighted_neighbor_acceleration

FROM state_history s

LEFT JOIN persistence_asof p
    ON s.geoid = p.geoid
   AND s.month_date = p.month_date

LEFT JOIN acs a
    ON s.geoid = a.geoid

LEFT JOIN code_features c
    ON s.geoid = c.geoid
   AND s.month_date = c.month_date

LEFT JOIN analytics.tract_spillover_features sp
    ON s.geoid = sp.geoid
   AND s.month_date = sp.month_date

WHERE s.month_date > (
    SELECT MAX(month_date) - INTERVAL '12 months'
    FROM analytics.tract_state_history
);

ALTER TABLE analytics.tract_ml_scoring_features
ADD PRIMARY KEY (geoid, month_date);
