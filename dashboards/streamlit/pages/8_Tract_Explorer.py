import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dashboards.streamlit.utils.db import run_query
from dashboards.streamlit.utils.queries import (
    TRACT_LIST_QUERY,
    TRACT_TIME_SERIES_QUERY,
)


STATE_COLORS = {
    "Stable": "#2ca02c",
    "Improving": "#1f77b4",
    "Emerging Risk": "#ff7f0e",
    "Rapid Deterioration": "#d62728",
    "Chronic Distress": "#7f0000",
}


st.set_page_config(
    page_title="Tract Explorer",
    layout="wide",
)

st.title("Tract Explorer")

tracts = run_query(TRACT_LIST_QUERY)

tract_lookup = {
    row["display_name"]: row["geoid"]
    for _, row in tracts.iterrows()
}

selected_label = st.selectbox(
    "Select a census tract",
    list(tract_lookup.keys()),
)

selected_geoid = tract_lookup[selected_label]

history = run_query(
    TRACT_TIME_SERIES_QUERY,
    {"geoid": selected_geoid},
)

if history.empty:
    st.warning("No history found for this tract.")
    st.stop()

latest = history.sort_values("month_date").iloc[-1]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Current State", latest["neighborhood_trajectory"])
col2.metric("Trajectory Score", f"{latest['combined_trajectory_score']:.1f}")
col3.metric("3M Active Cases", f"{latest['rolling_3m_active_cases']:.1f}")
col4.metric("12M Active Cases", f"{latest['rolling_12m_active_cases']:.1f}")

st.subheader("Rolling Distress Trend")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=history["month_date"],
        y=history["rolling_3m_active_cases"],
        mode="lines",
        name="Rolling 3M",
    )
)

fig.add_trace(
    go.Scatter(
        x=history["month_date"],
        y=history["rolling_6m_active_cases"],
        mode="lines",
        name="Rolling 6M",
    )
)

fig.add_trace(
    go.Scatter(
        x=history["month_date"],
        y=history["rolling_12m_active_cases"],
        mode="lines",
        name="Rolling 12M",
    )
)

fig.update_layout(
    xaxis_title="Month",
    yaxis_title="Active Cases per 1,000 Housing Units",
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Trajectory Score Over Time")

score_fig = px.line(
    history,
    x="month_date",
    y="combined_trajectory_score",
    markers=True,
    labels={
        "month_date": "Month",
        "combined_trajectory_score": "Trajectory Score",
    },
)

score_fig.update_layout(hovermode="x unified")

st.plotly_chart(score_fig, use_container_width=True)

st.subheader("State History")

state_fig = px.scatter(
    history,
    x="month_date",
    y="neighborhood_trajectory",
    color="neighborhood_trajectory",
    color_discrete_map=STATE_COLORS,
    labels={
        "month_date": "Month",
        "neighborhood_trajectory": "Trajectory State",
    },
)

state_fig.update_traces(marker=dict(size=9))
state_fig.update_layout(showlegend=True)

st.plotly_chart(state_fig, use_container_width=True)

with st.expander("View monthly data"):
    st.dataframe(history, use_container_width=True, hide_index=True)