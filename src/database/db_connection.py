from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import os


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


def get_database_url() -> str:
    """
    Build SQLAlchemy database URL from .env values.
    """
    load_dotenv(ENV_PATH)

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    missing = [
        key
        for key, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_NAME": db_name,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not value
    ]

    if missing:
        raise ValueError(f"Missing required .env variables: {missing}")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


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