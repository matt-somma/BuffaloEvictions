DROP TABLE IF EXISTS analytics.tract_adjacency;

CREATE TABLE analytics.tract_adjacency AS
SELECT
    a.geoid AS geoid,
    b.geoid AS neighbor_geoid,
    ST_Length(
        ST_Intersection(a.geom, b.geom)::geography
    ) AS shared_border_meters
FROM raw.census_tract_boundaries a
JOIN raw.census_tract_boundaries b
    ON a.geoid <> b.geoid
   AND ST_Touches(a.geom, b.geom)
JOIN raw.acs_demographics aa
    ON a.geoid = aa.geoid
JOIN raw.acs_demographics bb
    ON b.geoid = bb.geoid
WHERE ST_Length(
    ST_Intersection(a.geom, b.geom)::geography
) > 0
  AND aa.total_population > 500
  AND aa.occupied_housing_units > 100
  AND bb.total_population > 500
  AND bb.occupied_housing_units > 100;

ALTER TABLE analytics.tract_adjacency
ADD PRIMARY KEY (geoid, neighbor_geoid);