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
from dashboards.streamlit.utils.view_options import render_label_mode_control


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

render_label_mode_control()

st.title("Tract Explorer")

st.info(
    """
Think of this page as the tract-level case review view.
It is designed to help answer three questions:

1. How has one tract changed over time?
2. Is current risk part of a long pattern or a more recent shift?
3. Does the tract look stable, improving, volatile, or deteriorating?
"""
)

with st.expander("What this page is for"):
    st.markdown(
        """
This page lets you inspect one tract's monthly history in detail.
It is especially useful when a tract has already been flagged elsewhere in the dashboard
and you want to understand the story behind that flag.

Use it to move from:

- **citywide comparison**
  to
- **single-tract historical diagnosis**

so you can see whether a tract's current condition reflects chronic burden,
recent worsening, recovery, or repeated instability.
"""
    )

with st.expander("How to interpret the key metrics at the top"):
    st.markdown(
        """
- **Current State**
  is the tract's latest rule-based trajectory label.

- **Trajectory Score**
  summarizes how burdened and/or unstable the tract currently looks relative to peers.

- **3M Active Cases**
  highlights near-term pressure.

- **12M Active Cases**
  shows the longer-run burden and helps distinguish temporary spikes from sustained stress.
"""
    )

with st.expander("How to read the charts"):
    st.markdown(
        """
- **Rolling Distress Trend**
  shows short-, medium-, and longer-term active-case pressure.
  If the 3M line rises above the 12M line, the tract may be worsening faster than its baseline.

- **Trajectory Score Over Time**
  shows how the tract's relative risk status changes month to month.
  Rising values generally indicate growing concern.

- **State History**
  shows when the tract moved between Stable, Improving, Emerging Risk,
  Rapid Deterioration, and Chronic Distress.
  Repeated transitions can indicate volatility, while long runs in severe states
  can indicate entrenchment.
"""
    )

with st.expander("How to use this page for tract review"):
    st.markdown(
        """
Useful review patterns include:

- **Sustained high 12M burden**
  suggests chronic pressure.

- **Sharp increase in 3M burden**
  can indicate a newer deterioration signal.

- **State bouncing between categories**
  can indicate instability even if the tract is not always severe.

- **Improving current state after a long severe run**
  can indicate recovery, but often with continued vulnerability.

This page is often the best final check before treating a tract as a priority case.
"""
    )

tracts = run_query(TRACT_LIST_QUERY)

tract_lookup = {
    row["display_name"]: row["geoid"]
    for _, row in tracts.sort_values("display_name").iterrows()
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
