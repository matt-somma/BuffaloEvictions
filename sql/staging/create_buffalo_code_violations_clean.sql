CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.buffalo_code_violations_clean;

CREATE TABLE staging.buffalo_code_violations_clean AS
SELECT
    uniquekey::bigint AS violation_id,
    case_number,
    date::timestamp AS violation_date,
    date_trunc('month', date::timestamp)::date AS violation_month,

    case_type,
    upper(status) AS status,
    code,
    code_section,
    description,
    comments,
    inspector,
    propclass,
    sbl,

    address,
    city,
    state,
    zip,
    neighborhood,
    council_district,
    police_district,

    latitude::double precision AS latitude,
    longitude::double precision AS longitude,

    geoid20_tract AS geoid,
    geoid20_blockgroup,
    geoid20_block,

    ST_SetSRID(
        ST_MakePoint(longitude::double precision, latitude::double precision),
        4326
    ) AS geom,

    source_dataset_id,
    ingested_at

FROM raw.buffalo_code_violations
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude <> ''
  AND longitude <> ''
  AND geoid20_tract IS NOT NULL
  AND geoid20_tract <> '';

ALTER TABLE staging.buffalo_code_violations_clean
ADD PRIMARY KEY (violation_id);

CREATE INDEX IF NOT EXISTS idx_code_violations_clean_geoid
ON staging.buffalo_code_violations_clean (geoid);

CREATE INDEX IF NOT EXISTS idx_code_violations_clean_date
ON staging.buffalo_code_violations_clean (violation_date);

CREATE INDEX IF NOT EXISTS idx_code_violations_clean_geom
ON staging.buffalo_code_violations_clean
USING GIST (geom);