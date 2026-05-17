DROP TABLE IF EXISTS analytics.tract_spillover_features;

CREATE TABLE analytics.tract_spillover_features AS
WITH neighbor_months AS (
    SELECT
        a.geoid,
        h.month_date,
        a.neighbor_geoid,
        h.neighborhood_trajectory,
        h.combined_trajectory_score,
        h.acceleration_score,
        h.rolling_3m_active_cases,
        h.rolling_12m_active_cases,
        a.shared_border_meters
    FROM analytics.tract_adjacency a
    JOIN analytics.tract_state_history h
        ON a.neighbor_geoid = h.geoid
),

aggregated AS (
    SELECT
        geoid,
        month_date,

        COUNT(*) AS neighbor_count,

        AVG(combined_trajectory_score) AS neighbor_avg_trajectory_score,
        AVG(acceleration_score) AS neighbor_avg_acceleration_score,
        AVG(rolling_3m_active_cases) AS neighbor_avg_rolling_3m,
        AVG(rolling_12m_active_cases) AS neighbor_avg_rolling_12m,

        SUM(
            CASE
                WHEN neighborhood_trajectory IN (
                    'Emerging Risk',
                    'Rapid Deterioration',
                    'Chronic Distress'
                )
                THEN 1 ELSE 0
            END
        ) AS distressed_neighbor_count,

        SUM(
            CASE
                WHEN neighborhood_trajectory = 'Rapid Deterioration'
                THEN 1 ELSE 0
            END
        ) AS rapid_neighbor_count,

        SUM(
            CASE
                WHEN neighborhood_trajectory = 'Chronic Distress'
                THEN 1 ELSE 0
            END
        ) AS chronic_neighbor_count,

        SUM(
            combined_trajectory_score * shared_border_meters
        ) / NULLIF(SUM(shared_border_meters), 0)
            AS border_weighted_neighbor_score,

        SUM(
            acceleration_score * shared_border_meters
        ) / NULLIF(SUM(shared_border_meters), 0)
            AS border_weighted_neighbor_acceleration

    FROM neighbor_months
    GROUP BY
        geoid,
        month_date
)

SELECT
    *,
    distressed_neighbor_count::numeric
        / NULLIF(neighbor_count, 0) AS distressed_neighbor_share,

    rapid_neighbor_count::numeric
        / NULLIF(neighbor_count, 0) AS rapid_neighbor_share,

    chronic_neighbor_count::numeric
        / NULLIF(neighbor_count, 0) AS chronic_neighbor_share,

    CASE
        WHEN neighbor_count >= 3
        THEN distressed_neighbor_count::numeric / NULLIF(neighbor_count, 0)
        ELSE NULL
    END AS reliable_distressed_neighbor_share,

    CASE
        WHEN neighbor_count >= 3
        THEN rapid_neighbor_count::numeric / NULLIF(neighbor_count, 0)
        ELSE NULL
    END AS reliable_rapid_neighbor_share,

    CASE
        WHEN neighbor_count >= 3
        THEN chronic_neighbor_count::numeric / NULLIF(neighbor_count, 0)
        ELSE NULL
    END AS reliable_chronic_neighbor_share
FROM aggregated;

ALTER TABLE analytics.tract_spillover_features
ADD PRIMARY KEY (geoid, month_date);