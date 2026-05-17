from pathlib import Path
from typing import Dict

import pandas as pd
import requests
from sqlalchemy import text

from src.database.db_connection import get_engine, load_config

import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]


ACS_VARIABLES: Dict[str, str] = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B17001_001E": "poverty_universe",
    "B17001_002E": "poverty_count",
    "B23025_003E": "labor_force_count",
    "B23025_005E": "unemployed_count",
    "B25003_001E": "occupied_housing_units",
    "B25003_003E": "renter_occupied_units",
    "B25070_001E": "gross_rent_universe",
    "B25070_007E": "rent_30_34_9_pct_income",
    "B25070_008E": "rent_35_39_9_pct_income",
    "B25070_009E": "rent_40_49_9_pct_income",
    "B25070_010E": "rent_50_plus_pct_income",
    "B08201_001E": "households_vehicle_universe",
    "B08201_002E": "households_no_vehicle",
    "B11003_016E": "single_parent_family_households",
}


def build_acs_url(config: dict) -> str:
    load_dotenv(PROJECT_ROOT / ".env")

    census_cfg = config["sources"]["census"]

    year = census_cfg["year"]
    dataset = census_cfg["dataset"]
    state_fips = census_cfg["state_fips"]
    county_fips = census_cfg["county_fips"]
    base_url = census_cfg["base_url"]

    api_key = os.getenv("CENSUS_API_KEY")

    variables = ["NAME"] + list(ACS_VARIABLES.keys())
    get_vars = ",".join(variables)

    url = (
        f"{base_url}/{year}/{dataset}"
        f"?get={get_vars}"
        f"&for=tract:*"
        f"&in=state:{state_fips}%20county:{county_fips}"
    )

    if api_key:
        url += f"&key={api_key}"

    return url


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def transform_acs_response(data: list, acs_year: int) -> pd.DataFrame:
    header = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=header)

    rename_map = {
        **ACS_VARIABLES,
        "NAME": "geo_name",
        "state": "statefp",
        "county": "countyfp",
        "tract": "tractce",
    }

    df = df.rename(columns=rename_map)

    df["geoid"] = df["statefp"] + df["countyfp"] + df["tractce"]
    df["acs_year"] = acs_year

    numeric_cols = list(ACS_VARIABLES.values())

    for col in numeric_cols:
        df[col] = safe_numeric(df[col])

    df["poverty_rate"] = df["poverty_count"] / df["poverty_universe"]
    df["unemployment_rate"] = df["unemployed_count"] / df["labor_force_count"]
    df["renter_occupied_rate"] = (
        df["renter_occupied_units"] / df["occupied_housing_units"]
    )

    df["rent_burdened_units"] = (
        df["rent_30_34_9_pct_income"]
        + df["rent_35_39_9_pct_income"]
        + df["rent_40_49_9_pct_income"]
        + df["rent_50_plus_pct_income"]
    )

    df["rent_burden_rate"] = (
        df["rent_burdened_units"] / df["gross_rent_universe"]
    )

    df["no_vehicle_rate"] = (
        df["households_no_vehicle"] / df["households_vehicle_universe"]
    )

    rate_cols = [
        "poverty_rate",
        "unemployment_rate",
        "renter_occupied_rate",
        "rent_burden_rate",
        "no_vehicle_rate",
    ]

    for col in rate_cols:
        df[col] = df[col].replace([float("inf"), -float("inf")], pd.NA)

    keep_cols = [
        "geoid",
        "acs_year",
        "geo_name",
        "statefp",
        "countyfp",
        "tractce",
        "total_population",
        "median_household_income",
        "poverty_universe",
        "poverty_count",
        "poverty_rate",
        "labor_force_count",
        "unemployed_count",
        "unemployment_rate",
        "occupied_housing_units",
        "renter_occupied_units",
        "renter_occupied_rate",
        "gross_rent_universe",
        "rent_burdened_units",
        "rent_burden_rate",
        "households_vehicle_universe",
        "households_no_vehicle",
        "no_vehicle_rate",
        "single_parent_family_households",
    ]

    return df[keep_cols]


def load_acs_demographics() -> None:
    config = load_config()
    census_cfg = config["sources"]["census"]
    acs_year = int(census_cfg["year"])

    url = build_acs_url(config)

    print("Requesting ACS demographics...")
    response = requests.get(url, timeout=60)

    print(f"Request URL: {url}")
    print(f"Status code: {response.status_code}")
    print(f"Response preview: {response.text[:1000]}")

    response.raise_for_status()

    if "Invalid Key" in response.text:
        raise ValueError(
            "Census API rejected your key as invalid. "
            "Remove CENSUS_API_KEY from .env or generate a new key."
        )

    if "Missing Key" in response.text:
        raise ValueError(
            "Census API says a key is required. "
            "Add a valid CENSUS_API_KEY to .env."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError(
            "Census API did not return JSON. "
            "Check the response preview above for the exact API error."
        ) from exc

    print("Transforming ACS response...")
    df = transform_acs_response(data, acs_year)

    print(f"Rows returned: {len(df)}")

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.execute(text("DROP TABLE IF EXISTS raw.acs_demographics;"))

    print("Loading ACS demographics to Postgres...")
    df.to_sql(
        name="acs_demographics",
        con=engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE raw.acs_demographics
                ADD PRIMARY KEY (geoid, acs_year);
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_acs_demographics_geoid
                ON raw.acs_demographics (geoid);
                """
            )
        )

    print("ACS demographics loaded successfully.")
    print(f"Request URL: {url}")
    print(f"Status code: {response.status_code}")
    print("Response preview:")
    print(response.text[:2000])


if __name__ == "__main__":
    load_acs_demographics()