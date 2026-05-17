from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboards.streamlit.utils.db import run_query
from dashboards.streamlit.utils.queries import TEMPORAL_MAP_QUERY


MAP_LAYERS = {
    "Trajectory Score": {
        "column": "combined_trajectory_score",
        "label": "Trajectory Score",
        "scale": "YlOrRd",
    },
    "Acceleration Score": {
        "column": "acceleration_score",
        "label": "Acceleration Score",
        "scale": "RdYlGn_r",
    },
    "Rolling 3M Active Cases": {
        "column": "rolling_3m_active_cases",
        "label": "Rolling 3M Active Cases",
        "scale": "OrRd",
    },
    "Rolling 12M Active Cases": {
        "column": "rolling_12m_active_cases",
        "label": "Rolling 12M Active Cases",
        "scale": "OrRd",
    },
}


st.set_page_config(
    page_title="Temporal Neighborhood Map",
    layout="wide",
)

st.title("Temporal Neighborhood Risk Map")

st.markdown(
    """
This map shows how tract-level housing instability changes over time.
Use the controls below to switch between risk layers, animate month-by-month change,
or focus only on the latest available month.
"""
)

df = run_query(TEMPORAL_MAP_QUERY)

if df.empty:
    st.warning("No temporal map data found.")
    st.stop()

df["month_date"] = pd.to_datetime(df["month_date"])
df["month_str"] = df["month_date"].dt.strftime("%Y-%m")

left, middle, right = st.columns(3)

with left:
    selected_layer = st.selectbox(
        "Map layer",
        list(MAP_LAYERS.keys()),
    )

with middle:
    latest_only = st.toggle(
        "Latest month only",
        value=False,
    )

with right:
    animation_speed = st.slider(
        "Animation speed, milliseconds per month",
        min_value=250,
        max_value=3000,
        value=900,
        step=250,
    )

layer_config = MAP_LAYERS[selected_layer]
color_col = layer_config["column"]

if latest_only:
    latest_month = df["month_date"].max()
    map_df = df[df["month_date"] == latest_month].copy()
    st.info(f"Showing latest available month: {latest_month.strftime('%Y-%m')}")
else:
    map_df = df.copy()

geojson = {
    "type": "FeatureCollection",
    "features": [],
}

seen_geoids = set()

for _, row in df.iterrows():
    if row["geoid"] in seen_geoids:
        continue

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

    seen_geoids.add(row["geoid"])

common_args = dict(
    data_frame=map_df,
    geojson=geojson,
    locations="geoid",
    featureidkey="properties.geoid",
    color=color_col,
    hover_name="display_name",
    hover_data={
        "neighborhood_trajectory": True,
        "combined_trajectory_score": ":.1f",
        "acceleration_score": ":.1f",
        "rolling_3m_active_cases": ":.1f",
        "rolling_12m_active_cases": ":.1f",
        "month_str": True,
        "geoid": False,
    },
    color_continuous_scale=layer_config["scale"],
    mapbox_style="carto-positron",
    center={
        "lat": 42.8864,
        "lon": -78.8784,
    },
    zoom=10,
    opacity=0.75,
)

if latest_only:
    fig = px.choropleth_mapbox(**common_args)
else:
    fig = px.choropleth_mapbox(
        **common_args,
        animation_frame="month_str",
    )

    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = animation_speed
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 200

fig.update_layout(
    height=850,
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(
        title=layer_config["label"],
    ),
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
### How to Interpret This Map

- **Trajectory Score** shows overall deterioration risk based on recent trend, chronic burden, and acceleration.
- **Acceleration Score** highlights tracts worsening faster than their longer-term baseline.
- **Rolling 3M Active Cases** emphasizes short-term operational pressure.
- **Rolling 12M Active Cases** emphasizes sustained longer-term burden.
- **Latest month only** removes the animation and shows the most recent available snapshot.
"""
)