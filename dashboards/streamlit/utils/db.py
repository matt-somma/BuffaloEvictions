import pandas as pd
from sqlalchemy import text

from src.database.db_connection import get_engine


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    engine = get_engine()

    with engine.connect() as conn:
        return pd.read_sql(
            sql=text(query),
            con=conn,
            params=params or {},
        )