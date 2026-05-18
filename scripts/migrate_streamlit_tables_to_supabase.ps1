param(
    [string]$SupabaseDbUrl = $env:SUPABASE_DB_URL,
    [switch]$SchemaOnly,
    [switch]$DataOnly
)

$ErrorActionPreference = "Stop"

if ($SchemaOnly -and $DataOnly) {
    throw "Use either -SchemaOnly or -DataOnly, not both together."
}

function Get-ProjectRoot {
    return Split-Path -Parent $PSScriptRoot
}

function Read-DotEnv {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing .env file at $Path"
    }

    $values = @{}

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()

        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        $values[$key] = $value
    }

    return $values
}

function Require-Command {
    param(
        [string]$Name
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not on PATH."
    }
}

function Run-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [hashtable]$EnvironmentOverrides = @{}
    )

    $previousValues = @{}

    try {
        foreach ($entry in $EnvironmentOverrides.GetEnumerator()) {
            $previousValues[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, "Process")
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
        }

        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        foreach ($entry in $EnvironmentOverrides.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $previousValues[$entry.Key], "Process")
        }
    }
}

$projectRoot = Get-ProjectRoot
$envPath = Join-Path $projectRoot ".env"
$dotenv = Read-DotEnv -Path $envPath

if (-not $SupabaseDbUrl) {
    throw "Set SUPABASE_DB_URL to your Supabase direct Postgres connection string, or pass -SupabaseDbUrl explicitly."
}

Require-Command -Name "pg_dump"
Require-Command -Name "psql"

$sourceHost = $dotenv["DB_HOST"]
$sourcePort = $dotenv["DB_PORT"]
$sourceDatabase = $dotenv["DB_NAME"]
$sourceUser = $dotenv["DB_USER"]
$sourcePassword = $dotenv["DB_PASSWORD"]

foreach ($requiredKey in @("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")) {
    if (-not $dotenv.ContainsKey($requiredKey) -or -not $dotenv[$requiredKey]) {
        throw "Missing required source setting $requiredKey in $envPath"
    }
}

$tableList = @(
    "analytics.housing_risk_features_v2",
    "analytics.neighborhood_transition_matrix",
    "analytics.tract_forecast_scores",
    "analytics.tract_neighborhood_labels",
    "analytics.tract_state_history",
    "analytics.tract_state_persistence"
)

$tempDir = Join-Path $projectRoot "tmp\supabase_streamlit_migration"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$bootstrapSqlPath = Join-Path $tempDir "bootstrap_supabase.sql"
$schemaDumpPath = Join-Path $tempDir "streamlit_schema.sql"
$dataDumpPath = Join-Path $tempDir "streamlit_data.sql"

$quotedTables = $tableList | ForEach-Object { "'$_'" }

$bootstrapSql = @'
CREATE SCHEMA IF NOT EXISTS analytics;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'postgis'
    ) THEN
        EXECUTE 'ALTER EXTENSION postgis SET SCHEMA public';
    ELSE
        EXECUTE 'CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public';
    END IF;
END $$;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[__TABLE_LIST__]
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS %s CASCADE', table_name);
    END LOOP;
END $$;
'@

$bootstrapSql = $bootstrapSql.Replace("__TABLE_LIST__", ($quotedTables -join ", "))

Set-Content -LiteralPath $bootstrapSqlPath -Value $bootstrapSql -Encoding UTF8

$sourceDumpArgs = @(
    "--host=$sourceHost",
    "--port=$sourcePort",
    "--username=$sourceUser",
    "--dbname=$sourceDatabase",
    "--no-owner",
    "--no-privileges",
    "--verbose"
)

foreach ($tableName in $tableList) {
    $sourceDumpArgs += "--table=$tableName"
}

if (-not $DataOnly) {
    $schemaArgs = @("--schema-only") + $sourceDumpArgs
    Run-ExternalCommand `
        -FilePath "pg_dump" `
        -Arguments $schemaArgs `
        -EnvironmentOverrides @{ PGPASSWORD = $sourcePassword } `
        | Set-Content -LiteralPath $schemaDumpPath -Encoding UTF8
}

if (-not $SchemaOnly) {
    $dataArgs = @("--data-only") + $sourceDumpArgs
    Run-ExternalCommand `
        -FilePath "pg_dump" `
        -Arguments $dataArgs `
        -EnvironmentOverrides @{ PGPASSWORD = $sourcePassword } `
        | Set-Content -LiteralPath $dataDumpPath -Encoding UTF8
}

Run-ExternalCommand `
    -FilePath "psql" `
    -Arguments @($SupabaseDbUrl, "-v", "ON_ERROR_STOP=1", "-f", $bootstrapSqlPath)

if (-not $DataOnly) {
    Run-ExternalCommand `
        -FilePath "psql" `
        -Arguments @($SupabaseDbUrl, "-v", "ON_ERROR_STOP=1", "-f", $schemaDumpPath)
}

if (-not $SchemaOnly) {
    Run-ExternalCommand `
        -FilePath "psql" `
        -Arguments @($SupabaseDbUrl, "-v", "ON_ERROR_STOP=1", "-f", $dataDumpPath)
}

Write-Host ""
Write-Host "Migrated Streamlit dependencies to Supabase:"
$tableList | ForEach-Object { Write-Host " - $_" }
Write-Host ""
Write-Host "Bootstrap SQL: $bootstrapSqlPath"
if (-not $DataOnly) {
    Write-Host "Schema dump:   $schemaDumpPath"
}
if (-not $SchemaOnly) {
    Write-Host "Data dump:     $dataDumpPath"
}
