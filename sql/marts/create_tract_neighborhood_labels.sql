DROP TABLE IF EXISTS analytics.tract_neighborhood_labels;

CREATE TABLE analytics.tract_neighborhood_labels AS

WITH counts AS (
    SELECT
        geoid20_tract AS geoid,
        neighborhood,
        COUNT(*) AS violation_count
    FROM raw.buffalo_code_violations
    WHERE geoid20_tract IS NOT NULL
      AND neighborhood IS NOT NULL
      AND neighborhood <> ''
    GROUP BY
        geoid20_tract,
        neighborhood
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY geoid
            ORDER BY violation_count DESC
        ) AS rn,

        SUM(violation_count) OVER (
            PARTITION BY geoid
        ) AS total_count
    FROM counts
)

SELECT
    geoid,
    neighborhood AS dominant_neighborhood,
    violation_count,
    total_count,

    ROUND(
        violation_count::numeric
        / NULLIF(total_count, 0),
        3
    ) AS neighborhood_share

FROM ranked
WHERE rn = 1;