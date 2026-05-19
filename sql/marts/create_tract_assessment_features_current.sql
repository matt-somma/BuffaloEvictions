DROP TABLE IF EXISTS analytics.tract_assessment_features_current;

CREATE TABLE analytics.tract_assessment_features_current AS
WITH tract_universe AS (
    SELECT DISTINCT geoid::text AS geoid
    FROM analytics.tract_state_history
    WHERE geoid::text <> 'UNKNOWN'
),
cleaned_assessment AS (
    SELECT DISTINCT ON (r.print_key)
        r.print_key AS parcel_id,
        r.sbl,
        r.geoid20_tract AS geoid,
        r.property_class_code,
        r.prop_class_description,
        r.homestead_code,
        r.overall_condition,
        r.overall_condition_description,
        CASE
            WHEN r.total_value ~ '^[0-9]+(\.[0-9]+)?$'
            THEN r.total_value::numeric
        END AS total_value_num,
        CASE
            WHEN r.land_value ~ '^[0-9]+(\.[0-9]+)?$'
            THEN r.land_value::numeric
        END AS land_value_num,
        CASE
            WHEN r.total_living_area ~ '^[0-9]+(\.[0-9]+)?$'
            THEN r.total_living_area::numeric
        END AS living_area_num,
        CASE
            WHEN r.units ~ '^[0-9]+(\.[0-9]+)?$'
            THEN r.units::numeric
        END AS units_num,
        CASE
            WHEN r.year_built ~ '^[0-9]{4}$'
            THEN r.year_built::integer
        END AS year_built_num,
        LEFT(r.property_class_code, 1) AS property_class_group,
        CASE
            WHEN LEFT(r.property_class_code, 1) = '2' THEN 1
            ELSE 0
        END AS is_residential,
        CASE
            WHEN r.property_class_code IN ('311', '312') THEN 1
            ELSE 0
        END AS is_residential_vacant_land,
        CASE
            WHEN r.property_class_code IN ('220', '230', '281', '411') THEN 1
            WHEN LEFT(r.property_class_code, 1) = '2'
             AND r.units ~ '^[0-9]+(\.[0-9]+)?$'
             AND r.units::numeric >= 2 THEN 1
            ELSE 0
        END AS is_multifamily,
        CASE
            WHEN r.homestead_code = 'H' THEN 1
            ELSE 0
        END AS is_owner_occupied_proxy,
        CASE
            WHEN r.homestead_code = 'N' THEN 1
            ELSE 0
        END AS is_non_owner_occupied_proxy,
        CASE
            WHEN r.overall_condition = '1' THEN 1
            ELSE 0
        END AS is_poor_condition,
        CASE
            WHEN r.overall_condition IN ('1', '2') THEN 1
            ELSE 0
        END AS is_fair_or_worse_condition,
        CASE
            WHEN r.overall_condition IS NULL OR r.overall_condition = '' THEN 1
            ELSE 0
        END AS has_missing_condition,
        CASE
            WHEN LEFT(r.property_class_code, 1) = '2'
             AND r.year_built ~ '^[0-9]{4}$'
             AND r.year_built::integer < 1940 THEN 1
            ELSE 0
        END AS is_pre_1940_residential
    FROM raw.buffalo_assessment_roll r
    JOIN tract_universe tu
        ON r.geoid20_tract = tu.geoid
    WHERE r.print_key IS NOT NULL
      AND r.print_key <> ''
      AND r.geoid20_tract ~ '^[0-9]{11}$'
    ORDER BY r.print_key
)
SELECT
    geoid,
    COUNT(*) AS parcel_count,
    COUNT(*) FILTER (WHERE is_residential = 1) AS residential_parcel_count,
    COUNT(*) FILTER (WHERE is_multifamily = 1) AS multifamily_parcel_count,
    COUNT(*) FILTER (WHERE is_residential_vacant_land = 1) AS residential_vacant_land_count,

    AVG(is_residential::numeric) AS residential_parcel_share,
    CASE
        WHEN COUNT(*) FILTER (WHERE is_residential = 1) > 0
        THEN COUNT(*) FILTER (WHERE is_multifamily = 1)::numeric
            / COUNT(*) FILTER (WHERE is_residential = 1)
    END AS multifamily_share_of_residential,
    CASE
        WHEN COUNT(*) FILTER (WHERE is_residential = 1) > 0
        THEN COUNT(*) FILTER (WHERE is_residential_vacant_land = 1)::numeric
            / COUNT(*) FILTER (WHERE is_residential = 1)
    END AS residential_vacant_land_share,

    AVG(is_owner_occupied_proxy::numeric) AS owner_occupied_proxy_share,
    AVG(is_non_owner_occupied_proxy::numeric) AS non_owner_occupied_proxy_share,
    AVG(is_poor_condition::numeric) AS poor_condition_share,
    AVG(is_fair_or_worse_condition::numeric) AS fair_or_worse_condition_share,
    AVG(has_missing_condition::numeric) AS missing_condition_share,

    AVG(total_value_num) AS avg_total_value,
    AVG(total_value_num) FILTER (WHERE is_residential = 1) AS avg_residential_total_value,
    AVG(land_value_num) AS avg_land_value,
    AVG(living_area_num) FILTER (WHERE is_residential = 1) AS avg_residential_living_area,
    AVG(units_num) FILTER (WHERE is_residential = 1) AS avg_residential_units,

    CASE
        WHEN COUNT(*) FILTER (WHERE is_residential = 1) > 0
        THEN COUNT(*) FILTER (WHERE is_pre_1940_residential = 1)::numeric
            / COUNT(*) FILTER (WHERE is_residential = 1)
    END AS pre_1940_residential_share

FROM cleaned_assessment
GROUP BY geoid;

ALTER TABLE analytics.tract_assessment_features_current
ADD PRIMARY KEY (geoid);
