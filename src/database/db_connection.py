from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import os
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> dict:
    """
    Load project configuration from config.yaml.
    """
    path = config_path or CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_streamlit_secrets() -> dict | None:
    """
    Return Streamlit Cloud database secrets if running in Streamlit
    and secrets are configured.

    Expected secrets format:

    [database]
    host = "..."
    port = 5432
    database = "..."
    user = "..."
    password = "..."
    """
    try:
        import streamlit as st

        if "database" in st.secrets:
            return dict(st.secrets["database"])

    except Exception:
        return None

    return None


def get_database_settings() -> dict:
    """
    Load database settings from Streamlit secrets if available,
    otherwise fall back to local .env variables.
    """
    streamlit_secrets = get_streamlit_secrets()

    if streamlit_secrets:
        settings = {
            "host": streamlit_secrets.get("host"),
            "port": streamlit_secrets.get("port"),
            "database": streamlit_secrets.get("database"),
            "user": streamlit_secrets.get("user"),
            "password": streamlit_secrets.get("password"),
        }
    else:
        load_dotenv(ENV_PATH)

        settings = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
        }

    missing = [
        key
        for key, value in settings.items()
        if value is None or str(value).strip() == ""
    ]

    if missing:
        raise ValueError(
            "Missing required database settings: "
            f"{missing}. Configure .env locally or Streamlit secrets in deployment."
        )

    return settings


def get_database_url() -> str:
    """
    Build SQLAlchemy database URL from either Streamlit secrets or .env values.
    """
    settings = get_database_settings()

    user = quote_plus(str(settings["user"]))
    password = quote_plus(str(settings["password"]))
    host = settings["host"]
    port = settings["port"]
    database = settings["database"]

    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{host}:{port}/{database}"
    )


def get_engine() -> Engine:
    """
    Create SQLAlchemy engine for PostgreSQL/PostGIS.
    """
    database_url = get_database_url()

    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


def test_connection() -> None:
    """
    Test database connection and confirm PostGIS is available.
    """
    engine = get_engine()

    with engine.connect() as conn:
        db_version = conn.execute(text("SELECT version();")).scalar()
        postgis_version = conn.execute(text("SELECT PostGIS_Version();")).scalar()

    print("Database connection successful.")
    print(f"PostgreSQL: {db_version}")
    print(f"PostGIS: {postgis_version}")


if __name__ == "__main__":
    test_connection()