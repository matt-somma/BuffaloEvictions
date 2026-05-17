DROP TABLE IF EXISTS analytics.housing_risk_features_v2;

CREATE TABLE analytics.housing_risk_features_v2 AS

WITH base AS (
    SELECT
        h.geoid,
        h.acs_year,
        h.geo_name,

        h.total_population,
        h.median_household_income,

        h.poverty_rate,
        h.unemployment_rate,
        h.renter_occupied_rate,
        h.rent_burden_rate,
        h.no_vehicle_rate,

        h.poverty_score,
        h.unemployment_score,
        h.rent_burden_score,
        h.renter_score,
        h.no_vehicle_score,
        h.income_stress_score,
        h.housing_instability_score AS housing_instability_score_v1,

        cv.active_cases_per_1000_housing_units,
        cv.cases_last_12m_per_1000_housing_units,
        cv.properties_with_violations_per_1000_housing_units,

        h.geom


    FROM analytics.housing_risk_features h

    LEFT JOIN analytics.code_violation_features cv
        ON h.geoid = cv.geoid
),

scored AS (
    SELECT
        *,

        PERCENT_RANK() OVER (
            ORDER BY active_cases_per_1000_housing_units
        ) AS active_cases_score,

        PERCENT_RANK() OVER (
            ORDER BY cases_last_12m_per_1000_housing_units
        ) AS recent_cases_score,

        PERCENT_RANK() OVER (
            ORDER BY properties_with_violations_per_1000_housing_units
        ) AS distressed_properties_score

    FROM base
)

SELECT
    *,

    (
        0.18 * poverty_score
      + 0.15 * rent_burden_score
      + 0.15 * income_stress_score
      + 0.10 * unemployment_score
      + 0.07 * renter_score
      + 0.05 * no_vehicle_score

      + 0.15 * active_cases_score
      + 0.10 * recent_cases_score
      + 0.05 * distressed_properties_score

    ) * 100 AS housing_instability_score_v2

FROM scored;