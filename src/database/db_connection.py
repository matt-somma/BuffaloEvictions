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
    sslmode = "require"  # optional
    connect_timeout = 10  # optional
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
            "sslmode": streamlit_secrets.get("sslmode"),
            "connect_timeout": streamlit_secrets.get("connect_timeout"),
        }
    else:
        load_dotenv(ENV_PATH)

        settings = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "sslmode": os.getenv("DB_SSLMODE"),
            "connect_timeout": os.getenv("DB_CONNECT_TIMEOUT"),
        }

    required_keys = [
        "host",
        "port",
        "database",
        "user",
        "password",
    ]

    missing = [
        key
        for key in required_keys
        for value in [settings.get(key)]
        if value is None or str(value).strip() == ""
    ]

    if missing:
        raise ValueError(
            "Missing required database settings: "
            f"{missing}. Configure .env locally or Streamlit secrets in deployment."
        )

    return settings


def _build_connect_args(settings: dict) -> dict:
    """
    Build optional psycopg2 connect arguments for cloud-hosted databases.
    """
    connect_args = {}

    sslmode = settings.get("sslmode")
    if sslmode and str(sslmode).strip():
        connect_args["sslmode"] = str(sslmode).strip()

    connect_timeout = settings.get("connect_timeout")
    if connect_timeout not in (None, ""):
        connect_args["connect_timeout"] = int(connect_timeout)

    return connect_args


def get_database_url(settings: dict | None = None) -> str:
    """
    Build SQLAlchemy database URL from either Streamlit secrets or .env values.
    """
    settings = settings or get_database_settings()

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
    settings = get_database_settings()
    database_url = get_database_url(settings)
    connect_args = _build_connect_args(settings)

    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=1800,
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
