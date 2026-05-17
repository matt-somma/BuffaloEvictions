TRACT_LIST_QUERY = """
SELECT DISTINCT
    h.geoid,
    COALESCE(
        n.dominant_neighborhood || ' (' || h.geoid || ')',
        r.geo_name,
        h.geoid
    ) AS display_name
FROM analytics.tract_state_history h
LEFT JOIN analytics.housing_risk_features_v2 r
    ON h.geoid = r.geoid
LEFT JOIN analytics.tract_neighborhood_labels n
    ON h.geoid = n.geoid
WHERE h.geoid <> 'UNKNOWN'
ORDER BY display_name;
"""

TRACT_TIME_SERIES_QUERY = """
SELECT
    month_date,
    rolling_3m_active_cases,
    rolling_6m_active_cases,
    rolling_12m_active_cases,
    acceleration_score,
    combined_trajectory_score,
    neighborhood_trajectory
FROM analytics.tract_state_history
WHERE geoid = :geoid
ORDER BY month_date;
"""

TRANSITION_MATRIX_QUERY = """
SELECT
    current_state,
    next_state,
    transition_count,
    transition_probability
FROM analytics.neighborhood_transition_matrix
ORDER BY current_state, next_state;
"""

TEMPORAL_MAP_QUERY = """
SELECT
    h.geoid,
    h.month_date,

    COALESCE(
        n.dominant_neighborhood || ' (' || h.geoid || ')',
        r.geo_name,
        h.geoid
    ) AS display_name,

    h.neighborhood_trajectory,
    h.combined_trajectory_score,
    h.acceleration_score,
    h.rolling_3m_active_cases,
    h.rolling_12m_active_cases,

    ST_AsGeoJSON(r.geom)::json AS geometry

FROM analytics.tract_state_history h

LEFT JOIN analytics.housing_risk_features_v2 r
    ON h.geoid = r.geoid

LEFT JOIN analytics.tract_neighborhood_labels n
    ON h.geoid = n.geoid

WHERE h.geoid <> 'UNKNOWN'
  AND r.geom IS NOT NULL

ORDER BY
    h.month_date,
    h.geoid;
"""