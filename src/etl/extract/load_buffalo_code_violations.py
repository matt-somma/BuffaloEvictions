from pathlib import Path
from typing import List

import pandas as pd
import requests
from sqlalchemy import text

from src.database.db_connection import get_engine, load_config


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def fetch_socrata_dataset(base_url: str, dataset_id: str, page_size: int) -> pd.DataFrame:
    all_rows: List[dict] = []
    offset = 0

    while True:
        url = f"{base_url}/{dataset_id}.json"
        params = {
            "$limit": page_size,
            "$offset": offset,
            "$order": ":id",
        }

        print(f"Fetching rows {offset:,} to {offset + page_size:,}...")

        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()

        rows = response.json()

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    return pd.DataFrame(all_rows)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )

    return df


def load_buffalo_code_violations() -> None:
    config = load_config()
    source_cfg = config["sources"]["buffalo_open_data"]

    base_url = source_cfg["base_url"]
    dataset_id = source_cfg["code_violations_dataset_id"]
    page_size = int(source_cfg.get("page_size", 50000))

    print("Fetching Buffalo code violations...")
    df = fetch_socrata_dataset(base_url, dataset_id, page_size)

    print(f"Rows fetched: {len(df):,}")

    if df.empty:
        raise ValueError("No rows returned from Buffalo code violations dataset.")

    df = normalize_columns(df)

    df["source_dataset_id"] = dataset_id
    df["ingested_at"] = pd.Timestamp.utcnow()

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.execute(text("DROP TABLE IF EXISTS raw.buffalo_code_violations;"))

    print("Loading raw.buffalo_code_violations...")
    df.to_sql(
        name="buffalo_code_violations",
        con=engine,
        schema="raw",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5000,
    )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_buffalo_code_violations_source
                ON raw.buffalo_code_violations (source_dataset_id);
                """
            )
        )

    print("Loaded raw.buffalo_code_violations successfully.")


if __name__ == "__main__":
    load_buffalo_code_violations()