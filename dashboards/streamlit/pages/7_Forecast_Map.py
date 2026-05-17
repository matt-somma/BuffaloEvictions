from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import json

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from shapely.geometry import shape

from dashboards.streamlit.utils.db import run_query


FORECAST_MAP_QUERY = """
SELECT
    f.geoid::text AS geoid,

    COALESCE(
        n.dominant_neighborhood || ' (' || f.geoid::text || ')',
        r.geo_name,
        f.geoid::text
    ) AS display_name,

    f.month_date,
    f.neighborhood_trajectory,
    f.actual_target,
    f.predicted_probability,
    f.predicted_class,
    f.risk_percentile,
    f.top_drivers,
    f.forecast_horizon,

    r.housing_instability_score_v2,
    r.poverty_rate,
    r.rent_burden_rate,
    r.no_vehicle_rate,

    ST_AsGeoJSON(r.geom)::json AS geometry

FROM analytics.tract_forecast_scores f

LEFT JOIN analytics.housing_risk_features_v2 r
    ON f.geoid::text = r.geoid

LEFT JOIN analytics.tract_neighborhood_labels n
    ON f.geoid::text = n.geoid

WHERE r.geom IS NOT NULL
  AND f.geoid::text <> 'UNKNOWN';
"""


STATE_ORDER = [
    "Stable",
    "Improving",
    "Emerging Risk",
    "Rapid Deterioration",
    "Chronic Distress",
]


st.set_page_config(
    page_title="Forecast Risk Map",
    layout="wide",
)

st.title("Forecast Risk Map")

st.markdown(
    """
This map shows the model-predicted probability that each census tract will enter
**Rapid Deterioration** or **Chronic Distress** within the six-month forecast horizon.

Use it as an early-warning layer: areas with high forecast risk but non-severe current states
may be good candidates for proactive monitoring or intervention.
"""
)

HORIZON_ORDER = ["1m", "3m", "6m", "12m"]

selected_horizon = st.selectbox(
    "Forecast horizon",
    HORIZON_ORDER,
    index=2,
)

df = run_query(
    FORECAST_MAP_QUERY,
    {"forecast_horizon": selected_horizon},
)

if df.empty:
    st.warning("No forecast map data found.")
    st.stop()

df["month_date"] = pd.to_datetime(df["month_date"])
df["month_str"] = df["month_date"].dt.strftime("%Y-%m")

left, middle, right = st.columns(3)

with left:
    selected_month = st.selectbox(
        "Forecast month",
        sorted(df["month_str"].unique(), reverse=True),
        index=0,
    )

with middle:
    selected_states = st.multiselect(
        "Current trajectory states",
        options=[state for state in STATE_ORDER if state in df["neighborhood_trajectory"].unique()],
        default=[
            state
            for state in ["Stable", "Improving", "Emerging Risk"]
            if state in df["neighborhood_trajectory"].unique()
        ],
    )

with right:
    min_probability = st.slider(
        "Minimum predicted probability",
        min_value=0.0,
        max_value=1.0,
        value=0.50,
        step=0.05,
    )

early_only = st.toggle(
    "Early-intervention candidates only",
    value=True,
    help="Shows tracts that are not currently Rapid Deterioration or Chronic Distress.",
)

filtered = df[
    (df["month_str"] == selected_month)
    & (df["predicted_probability"] >= min_probability)
    & (df["neighborhood_trajectory"].isin(selected_states))
].copy()

if early_only:
    filtered = filtered[
        filtered["neighborhood_trajectory"].isin(
            ["Stable", "Improving", "Emerging Risk"]
        )
    ].copy()

if filtered.empty:
    st.info("No tracts match the selected filters.")
    st.stop()

geojson = {
    "type": "FeatureCollection",
    "features": [],
}

for _, row in filtered.iterrows():
    geojson["features"].append(
        {
            "type": "Feature",
            "id": row["geoid"],
            "properties": {
                "geoid": row["geoid"],
            },
            "geometry": row["geometry"],
        }
    )

fig = px.choropleth_mapbox(
    filtered,
    geojson=geojson,
    locations="geoid",
    featureidkey="properties.geoid",
    color="predicted_probability",
    hover_name="display_name",
    hover_data={
        "neighborhood_trajectory": True,
        "predicted_probability": ":.1%",
        "risk_percentile": ":.1f",
        "top_drivers": True,
        "housing_instability_score_v2": ":.1f",
        "poverty_rate": ":.1%",
        "rent_burden_rate": ":.1%",
        "no_vehicle_rate": ":.1%",
        "month_str": False,
        "geoid": False,
    },
    color_continuous_scale="YlOrRd",
    range_color=(0, 1),
    mapbox_style="carto-positron",
    center={
        "lat": 42.8864,
        "lon": -78.8784,
    },
    zoom=10,
    opacity=0.78,
)

fig.update_layout(
    height=800,
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(
        title="Predicted Horizon Distress Risk",
        tickformat=".0%",
    ),
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Forecasted High-Risk Tracts")

table_df = filtered[
    [
        "display_name",
        "neighborhood_trajectory",
        "predicted_probability",
        "risk_percentile",
        "top_drivers",
        "housing_instability_score_v2",
        "poverty_rate",
        "rent_burden_rate",
        "no_vehicle_rate",
    ]
].sort_values("predicted_probability", ascending=False).copy()

table_df["predicted_probability"] = table_df["predicted_probability"].map(
    lambda x: f"{x:.1%}"
)

table_df["risk_percentile"] = table_df["risk_percentile"].map(
    lambda x: f"{x:.1f}"
)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
)

st.markdown(
    """
### How to Interpret This Map

- Darker tracts have higher predicted probability of future distress.
- The forecast target is entering **Rapid Deterioration** or **Chronic Distress** within a targeted horizon.
- The **top drivers** field gives the main SHAP-based explanation for each tract's forecast.
- Early-intervention candidates are tracts that are not currently severe, but show elevated future risk.
"""
)