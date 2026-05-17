from pathlib import Path

import geopandas as gpd

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "housing_risk_features.geojson"


QUERY = """
SELECT
    geoid,
    geo_name,
    COALESCE(
        n.dominant_neighborhood || ' (' || r.geoid || ')',
        r.geo_name
    ) AS display_name,
    acs_year,
    total_population,
    median_household_income,
    poverty_rate,
    unemployment_rate,
    renter_occupied_rate,
    rent_burden_rate,
    no_vehicle_rate,
    housing_instability_score_v1 AS original_score,
    housing_instability_score_v2 AS enhanced_score,
    active_cases_per_1000_housing_units AS active_cases_per_1000,
    cases_last_12m_per_1000_housing_units AS recent_cases_per_1000,
    properties_with_violations_per_1000_housing_units AS properties_per_1000,
    geom
FROM analytics.housing_risk_features_v2
WHERE total_population > 500
  AND housing_instability_score_v2 IS NOT NULL;
"""


def export_housing_risk_geojson() -> None:
    engine = get_engine()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Reading housing risk features from PostGIS...")

    gdf = gpd.read_postgis(
        QUERY,
        con=engine,
        geom_col="geom",
    )

    gdf = gdf.to_crs(epsg=4326)

    print(f"Rows exported: {len(gdf)}")
    print(f"Writing GeoJSON to: {OUTPUT_PATH}")

    gdf.to_file(OUTPUT_PATH, driver="GeoJSON")

    print("GeoJSON export complete.")


if __name__ == "__main__":
    export_housing_risk_geojson()