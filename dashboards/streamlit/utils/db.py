import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database.db_connection import get_engine
from src.utils.public_labels import (
    mask_dataframe_public_labels,
    public_label_cache_key,
)


def _render_database_error(message: str, exc: Exception, *, show_secrets_example: bool) -> None:
    st.error(message)

    if show_secrets_example:
        st.markdown(
            """
Add the app's database credentials in Streamlit Cloud under
`App settings` -> `Secrets` using this structure:
"""
        )
        st.code(
            """[database]
host = "..."
port = 5432
database = "..."
user = "..."
password = "..."
""",
            language="toml",
        )

    with st.expander("Technical details"):
        st.code(f"{type(exc).__name__}: {exc}")

    st.stop()


@st.cache_resource(show_spinner=False)
def _get_cached_engine():
    return get_engine()


@st.cache_data(ttl=600, show_spinner=False)
def _run_query_cached(
    query: str,
    params_items: tuple[tuple[str, object], ...],
    cache_salt: str,
) -> pd.DataFrame:
    engine = _get_cached_engine()
    params = dict(params_items)

    with engine.connect() as conn:
        return pd.read_sql(
            sql=text(query),
            con=conn,
            params=params,
        )


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    try:
        normalized_params = tuple(sorted((params or {}).items()))
        cache_salt = public_label_cache_key(st.secrets)
        df = _run_query_cached(query, normalized_params, cache_salt)
        return mask_dataframe_public_labels(df, secrets=st.secrets)
    except ValueError as exc:
        _render_database_error(
            "Database credentials are missing or incomplete for this deployment.",
            exc,
            show_secrets_example=True,
        )
    except SQLAlchemyError as exc:
        _render_database_error(
            "The app could not connect to PostgreSQL/PostGIS. Confirm the Streamlit secrets are correct and that the database accepts incoming connections from Streamlit Cloud.",
            exc,
            show_secrets_example=False,
        )
