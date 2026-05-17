CREATE SCHEMA IF NOT EXISTS analytics;

DROP TABLE IF EXISTS analytics.housing_risk_features;

CREATE TABLE analytics.housing_risk_features AS
WITH base AS (
    SELECT
        a.geoid,
        a.acs_year,
        a.geo_name,
        a.total_population,
        a.median_household_income,
        a.poverty_rate,
        a.unemployment_rate,
        a.renter_occupied_rate,
        a.rent_burden_rate,
        a.no_vehicle_rate,
        a.single_mother_households,
        b.geom
    FROM raw.acs_demographics a
    JOIN raw.census_tract_boundaries b
        ON a.geoid = b.geoid
),

scored AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY poverty_rate) AS poverty_score,
        PERCENT_RANK() OVER (ORDER BY unemployment_rate) AS unemployment_score,
        PERCENT_RANK() OVER (ORDER BY rent_burden_rate) AS rent_burden_score,
        PERCENT_RANK() OVER (ORDER BY renter_occupied_rate) AS renter_score,
        PERCENT_RANK() OVER (ORDER BY no_vehicle_rate) AS no_vehicle_score,

        -- lower income = higher risk
        1 - PERCENT_RANK() OVER (ORDER BY median_household_income) AS income_stress_score
    FROM base
)

SELECT
    geoid,
    acs_year,
    geo_name,
    total_population,
    median_household_income,
    poverty_rate,
    unemployment_rate,
    renter_occupied_rate,
    rent_burden_rate,
    no_vehicle_rate,
    single_mother_households,

    poverty_score,
    unemployment_score,
    rent_burden_score,
    renter_score,
    no_vehicle_score,
    income_stress_score,

    (
        0.25 * poverty_score
      + 0.20 * rent_burden_score
      + 0.20 * income_stress_score
      + 0.15 * unemployment_score
      + 0.10 * renter_score
      + 0.10 * no_vehicle_score
    ) * 100 AS housing_instability_score,

    geom
FROM scored;

ALTER TABLE analytics.housing_risk_features
ADD PRIMARY KEY (geoid, acs_year);

CREATE INDEX IF NOT EXISTS idx_housing_risk_features_geom
ON analytics.housing_risk_features
USING GIST (geom);