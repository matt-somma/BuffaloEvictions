# BuffaloEvictions

Volunteer work for Harvest House.

## Streamlit deployment

Use these settings when deploying to Streamlit Community Cloud:

- Repository root must contain `requirements.txt` and `packages.txt`.
- Main file path: `dashboards/streamlit/Home.py`
- Python version: use the app default unless you need to pin one explicitly.

Add database credentials in the Streamlit app secrets panel with this structure:

```toml
[database]
host = "..."
port = 5432
database = "..."
user = "..."
password = "..."
sslmode = "require"
connect_timeout = 10
```

If the secrets are missing or incomplete, the app now shows a setup message in the UI instead of failing with a raw traceback.

Important: Streamlit Community Cloud cannot connect to a database running on `localhost` on your own computer. Use a hosted PostgreSQL/PostGIS instance or another network-reachable database endpoint.
