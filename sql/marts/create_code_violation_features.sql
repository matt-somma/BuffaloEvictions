DROP TABLE IF EXISTS analytics.code_violation_features;

CREATE TABLE analytics.code_violation_features AS
WITH base AS (
    SELECT
        geoid,
        COUNT(*) AS total_violations,
        COUNT(*) FILTER (WHERE status = 'ACTIVE') AS active_violations,
        COUNT(*) FILTER (WHERE violation_date >= CURRENT_DATE - INTERVAL '12 months') AS violations_last_12m,
        COUNT(*) FILTER (WHERE violation_date >= CURRENT_DATE - INTERVAL '6 months') AS violations_last_6m,
        COUNT(*) FILTER (WHERE violation_date >= CURRENT_DATE - INTERVAL '3 months') AS violations_last_3m,
        COUNT(DISTINCT sbl) AS distinct_properties_with_violations,
        MIN(violation_date) AS first_violation_date,
        MAX(violation_date) AS latest_violation_date
    FROM staging.buffalo_code_violations_clean
    GROUP BY geoid
),

joined AS (
    SELECT
        b.*,
        a.total_population,
        a.occupied_housing_units,

        b.total_violations::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000 AS violations_per_1000_housing_units,

        b.active_violations::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000 AS active_violations_per_1000_housing_units,

        b.violations_last_12m::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000 AS violations_last_12m_per_1000_housing_units,

        b.distinct_properties_with_violations::numeric
            / NULLIF(a.occupied_housing_units, 0) * 1000 AS properties_with_violations_per_1000_housing_units

    FROM base b
    LEFT JOIN raw.acs_demographics a
        ON b.geoid = a.geoid
)

SELECT *
FROM joined;

ALTER TABLE analytics.code_violation_features
ADD PRIMARY KEY (geoid);

CREATE INDEX IF NOT EXISTS idx_code_violation_features_geoid
ON analytics.code_violation_features (geoid);