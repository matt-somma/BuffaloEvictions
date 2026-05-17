from pathlib import Path

import pandas as pd

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "ml"
OUTPUT_PATH = OUTPUT_DIR / "tract_ml_features.csv"


QUERY = """
SELECT *
FROM analytics.tract_ml_features
WHERE future_distress_6m IS NOT NULL;
"""


def export_ml_dataset() -> None:
    engine = get_engine()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Reading ML features from PostgreSQL...")

    df = pd.read_sql(QUERY, engine)

    print(f"Rows exported: {len(df):,}")
    print(f"Writing CSV to: {OUTPUT_PATH}")

    df.to_csv(OUTPUT_PATH, index=False)

    print("Export complete.")


if __name__ == "__main__":
    export_ml_dataset()