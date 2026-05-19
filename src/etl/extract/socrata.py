import json
from typing import List

import pandas as pd
import requests


def fetch_socrata_dataset(
    *,
    base_url: str,
    dataset_id: str,
    page_size: int,
    order_by: str = ":id",
) -> pd.DataFrame:
    all_rows: List[dict] = []
    offset = 0

    while True:
        url = f"{base_url}/{dataset_id}.json"
        params = {
            "$limit": page_size,
            "$offset": offset,
            "$order": order_by,
        }

        print(f"Fetching rows {offset:,} to {offset + page_size:,} from {dataset_id}...")

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
    normalized = df.copy()

    normalized.columns = (
        normalized.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("/", "_", regex=False)
    )

    return normalized


def add_ingest_metadata(df: pd.DataFrame, *, dataset_id: str) -> pd.DataFrame:
    enriched = df.copy()
    enriched["source_dataset_id"] = dataset_id
    enriched["ingested_at"] = pd.Timestamp.utcnow()
    return enriched


def stringify_nested_values(df: pd.DataFrame) -> pd.DataFrame:
    sanitized = df.copy()

    for column in sanitized.columns:
        sanitized[column] = sanitized[column].map(
            lambda value: (
                json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else value
            )
        )

    return sanitized
