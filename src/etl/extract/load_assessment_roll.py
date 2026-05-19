from pathlib import Path

from sqlalchemy import text

from src.database.db_connection import get_engine, load_config
from src.etl.extract.socrata import (
    add_ingest_metadata,
    fetch_socrata_dataset,
    normalize_columns,
    stringify_nested_values,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_assessment_roll() -> None:
    config = load_config()
    source_cfg = config["sources"]["buffalo_open_data"]

    base_url = source_cfg["base_url"]
    dataset_id = source_cfg["assessment_roll_dataset_id"]
    page_size = int(source_cfg.get("page_size", 50000))

    print("Fetching Buffalo assessment roll...")
    df = fetch_socrata_dataset(
        base_url=base_url,
        dataset_id=dataset_id,
        page_size=page_size,
    )

    print(f"Rows fetched: {len(df):,}")

    if df.empty:
        raise ValueError("No rows returned from the Buffalo assessment roll dataset.")

    df = normalize_columns(df)
    df = stringify_nested_values(df)
    df = add_ingest_metadata(df, dataset_id=dataset_id)

    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.execute(text("DROP TABLE IF EXISTS raw.buffalo_assessment_roll;"))

    print("Loading raw.buffalo_assessment_roll...")
    df.to_sql(
        name="buffalo_assessment_roll",
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
                CREATE INDEX IF NOT EXISTS idx_buffalo_assessment_roll_source
                ON raw.buffalo_assessment_roll (source_dataset_id);
                """
            )
        )

    print("Loaded raw.buffalo_assessment_roll successfully.")


if __name__ == "__main__":
    load_assessment_roll()
