from pathlib import Path

import geopandas as gpd
from geoalchemy2 import Geometry
from sqlalchemy import text

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TRACT_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/"
    "tl_2023_36_tract.zip"
)


def load_erie_county_tracts() -> None:
    engine = get_engine()

    print("Reading New York census tract shapefile...")
    gdf = gpd.read_file(TRACT_URL)

    print("Filtering to Erie County...")
    gdf = gdf[gdf["COUNTYFP"] == "029"].copy()

    print(f"Rows after filter: {len(gdf)}")

    gdf = gdf.to_crs(epsg=4326)

    gdf = gdf.rename(
        columns={
            "GEOID": "geoid",
            "STATEFP": "statefp",
            "COUNTYFP": "countyfp",
            "TRACTCE": "tractce",
            "NAME": "name",
            "NAMELSAD": "namelsad",
            "geometry": "geom",
        }
    )

    keep_cols = [
        "geoid",
        "statefp",
        "countyfp",
        "tractce",
        "name",
        "namelsad",
        "geom",
    ]

    gdf = gdf[keep_cols]
    gdf = gdf.set_geometry("geom")

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.execute(text("DROP TABLE IF EXISTS raw.census_tract_boundaries;"))

    print("Loading tracts to PostGIS...")
    gdf.to_postgis(
        name="census_tract_boundaries",
        con=engine,
        schema="raw",
        if_exists="replace",
        index=False,
        dtype={"geom": Geometry("MULTIPOLYGON", srid=4326)},
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE raw.census_tract_boundaries
                ADD PRIMARY KEY (geoid);
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_census_tract_boundaries_geom
                ON raw.census_tract_boundaries
                USING GIST (geom);
                """
            )
        )

    print("Census tract boundaries loaded successfully.")


if __name__ == "__main__":
    load_erie_county_tracts()