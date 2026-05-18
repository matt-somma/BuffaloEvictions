from pathlib import Path

import pandas as pd

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "ml"
BACKTEST_OUTPUT_PATH = OUTPUT_DIR / "tract_ml_features.csv"
LIVE_SCORING_OUTPUT_PATH = OUTPUT_DIR / "tract_ml_scoring_features.csv"


BACKTEST_QUERY = """
SELECT *
FROM analytics.tract_ml_features
WHERE future_distress_6m IS NOT NULL;
"""

LIVE_SCORING_QUERY = """
SELECT *
FROM analytics.tract_ml_scoring_features;
"""


def export_ml_dataset() -> None:
    engine = get_engine()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Reading labeled ML features from PostgreSQL...")

    backtest_df = pd.read_sql(BACKTEST_QUERY, engine)
    live_scoring_df = pd.read_sql(LIVE_SCORING_QUERY, engine)

    print(f"Labeled rows exported: {len(backtest_df):,}")
    print(f"Live scoring rows exported: {len(live_scoring_df):,}")
    print(f"Writing labeled CSV to: {BACKTEST_OUTPUT_PATH}")
    print(f"Writing live scoring CSV to: {LIVE_SCORING_OUTPUT_PATH}")

    backtest_df.to_csv(BACKTEST_OUTPUT_PATH, index=False)
    live_scoring_df.to_csv(LIVE_SCORING_OUTPUT_PATH, index=False)

    print("Export complete.")


if __name__ == "__main__":
    export_ml_dataset()
