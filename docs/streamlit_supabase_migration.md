# Streamlit to Supabase Migration

This dashboard only needs a small analytics slice of the local database. You do not need to move the whole warehouse for Streamlit to work.

## Required objects

The Streamlit app reads these six tables:

- `analytics.housing_risk_features_v2`
- `analytics.neighborhood_transition_matrix`
- `analytics.tract_forecast_scores`
- `analytics.tract_neighborhood_labels`
- `analytics.tract_state_history`
- `analytics.tract_state_persistence`

## Current local row counts

- `analytics.tract_state_history`: `14,940`
- `analytics.housing_risk_features_v2`: `254`
- `analytics.tract_neighborhood_labels`: `90`
- `analytics.tract_state_persistence`: `90`
- `analytics.neighborhood_transition_matrix`: `25`
- `analytics.tract_forecast_scores`: `10,324`

## Why PostGIS matters

`analytics.housing_risk_features_v2` contains `geom public.geometry(Polygon,4326)`.

The Streamlit map pages call `ST_AsGeoJSON(r.geom)`, so the Supabase target must have PostGIS enabled before restoring the table.

Supabase docs:

- [Migrate from Postgres to Supabase](https://supabase.com/docs/guides/platform/migrating-to-supabase/postgres)
- [PostGIS: Geo queries](https://supabase.com/docs/guides/database/extensions/postgis)
- [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)

Notes from the docs:

- Use the **direct** Supabase Postgres connection string for `pg_dump` / `psql` style work, not the pooled one.
- Supabase supports PostGIS.
- PostGIS can be installed in a chosen schema. This project's dumped geometry type references `public.geometry`, so the migration script normalizes PostGIS into `public` before restore.

## One-command migration

From the repo root in PowerShell:

```powershell
$env:SUPABASE_DB_URL = "postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
.\scripts\migrate_streamlit_tables_to_supabase.ps1
```

The script will:

1. Read the local source database settings from `.env`
2. Enable or relocate `postgis` into `public` on Supabase
3. Create the `analytics` schema if needed
4. Drop and recreate just the six Streamlit dependency tables
5. Restore schema and data into Supabase

## Useful variants

Schema only:

```powershell
.\scripts\migrate_streamlit_tables_to_supabase.ps1 -SchemaOnly
```

Data only:

```powershell
.\scripts\migrate_streamlit_tables_to_supabase.ps1 -DataOnly
```

Explicit connection string instead of environment variable:

```powershell
.\scripts\migrate_streamlit_tables_to_supabase.ps1 -SupabaseDbUrl "postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres"
```

## After the restore

Point Streamlit at Supabase using Streamlit secrets:

```toml
[database]
host = "db.[project-ref].supabase.co"
port = 5432
database = "postgres"
user = "postgres"
password = "..."
sslmode = "require"
```

If you use the app locally and want to test against Supabase, update `.env` or temporarily override the database settings there too.
