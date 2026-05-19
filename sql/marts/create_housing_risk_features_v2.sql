DROP TABLE IF EXISTS analytics.housing_risk_features_v2;

CREATE TABLE analytics.housing_risk_features_v2 AS

WITH latest_code_features AS (
    SELECT DISTINCT ON (geoid)
        geoid,
        active_cases_per_1000_housing_units,
        cases_last_12m_per_1000_housing_units,
        properties_with_violations_per_1000_housing_units
    FROM analytics.code_violation_features
    ORDER BY
        geoid,
        month_date DESC
),

base AS (
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

        af.parcel_count,
        af.residential_parcel_count,
        af.multifamily_parcel_count,
        af.residential_vacant_land_count,
        af.residential_parcel_share,
        af.multifamily_share_of_residential,
        af.residential_vacant_land_share,
        af.owner_occupied_proxy_share,
        af.non_owner_occupied_proxy_share,
        af.poor_condition_share,
        af.fair_or_worse_condition_share,
        af.missing_condition_share,
        af.avg_total_value,
        af.avg_residential_total_value,
        af.avg_land_value,
        af.avg_residential_living_area,
        af.avg_residential_units,
        af.pre_1940_residential_share,

        h.geom


    FROM analytics.housing_risk_features h

    LEFT JOIN latest_code_features cv
        ON h.geoid = cv.geoid

    LEFT JOIN analytics.tract_assessment_features_current af
        ON h.geoid = af.geoid
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
