from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from dashboards.streamlit.utils.db import run_query


HOTSPOT_QUERY = """
SELECT
    p.geoid,
    COALESCE(
        n.dominant_neighborhood || ' (' || p.geoid || ')',
        r.geo_name,
        p.geoid
    ) AS display_name,
    p.current_trajectory,
    p.previous_trajectory,
    p.months_in_current_state,
    p.total_state_changes,
    p.months_any_distress,
    p.distress_persistence_rate,
    p.combined_trajectory_score,
    p.acceleration_score,
    p.rolling_3m_active_cases,
    p.rolling_6m_active_cases,
    p.rolling_12m_active_cases
FROM analytics.tract_state_persistence p
LEFT JOIN analytics.housing_risk_features_v2 r
    ON p.geoid = r.geoid
LEFT JOIN analytics.tract_neighborhood_labels n
    ON p.geoid = n.geoid
WHERE p.geoid <> 'UNKNOWN'
ORDER BY p.combined_trajectory_score DESC;
"""


STATE_COLORS = {
    "Stable": "#2ca02c",
    "Improving": "#1f77b4",
    "Emerging Risk": "#ff7f0e",
    "Rapid Deterioration": "#d62728",
    "Chronic Distress": "#7f0000",
}


st.set_page_config(
    page_title="Hotspot Analysis",
    layout="wide",
)

st.title("Hotspot Analysis")

st.markdown(
    """
This page identifies census tracts with the strongest signs of housing instability,
including rapid deterioration, chronic distress, emerging risk, and recovery patterns.
"""
)

st.info(
    """
Think of this page as a current-condition triage view.
It is designed to help answer three questions:

1. Which tracts appear most stressed right now?
2. Which tracts have persistent or entrenched distress?
3. Which tracts may be recovering, but still deserve monitoring?
"""
)

with st.expander("What this page means by a hotspot"):
    st.markdown(
        """
A **hotspot** is not just a tract with a high raw case count.
In this dashboard, hotspots are tracts that score highly on the platform's
trajectory and persistence metrics, which means they may be:

- carrying a high sustained burden of active housing distress,
- worsening faster than their own recent baseline,
- remaining stuck in distress for long periods,
- or repeatedly cycling through unstable states.

The page combines:

- **current trajectory state**,
- **trajectory score**,
- **acceleration score**,
- **distress persistence**, and
- **state history**

to help distinguish between chronic structural distress, new deterioration,
and possible improvement.
"""
    )

with st.expander("How to interpret the core metrics"):
    st.markdown(
        """
- **Current trajectory**
  describes the tract's present rule-based condition: Stable, Improving,
  Emerging Risk, Rapid Deterioration, or Chronic Distress.

- **Combined trajectory score**
  is the main composite hotspot metric on this page. Higher scores indicate
  a tract that looks more burdened and/or more unstable relative to other tracts.

- **Acceleration score**
  compares recent active-case pressure to the tract's longer-run baseline.
  Positive values suggest worsening momentum.

- **Distress persistence rate**
  shows how much of the tract's observed history has been spent in
  Emerging Risk, Rapid Deterioration, or Chronic Distress.

- **Months in current state**
  helps distinguish a newly changed tract from one that has been stuck in the
  same condition for a long time.

- **Total state changes**
  indicates how volatile or unstable a tract's history has been over time.
"""
    )

with st.expander("How to use this page for decision-making"):
    st.markdown(
        """
Useful reading patterns include:

- **High trajectory score + high persistence**
  can indicate entrenched distress that may need sustained intervention.

- **High trajectory score + high acceleration + low persistence**
  can indicate a tract that is deteriorating quickly right now.

- **Improving state + still-high persistence**
  can indicate recovery from a long period of strain, where support may still matter.

- **Frequent state changes**
  can indicate instability or fragility, even if the tract is not currently in the most severe state.

This page is best used as a prioritization tool alongside the forecast,
temporal map, and tract explorer pages.
"""
    )

df = run_query(HOTSPOT_QUERY)

if df.empty:
    st.warning("No hotspot data found.")
    st.stop()

left, right = st.columns(2)

with left:
    selected_states = st.multiselect(
        "Filter by trajectory state",
        options=sorted(df["current_trajectory"].dropna().unique()),
        default=sorted(df["current_trajectory"].dropna().unique()),
    )

with right:
    top_n = st.slider(
        "Number of tracts to show",
        min_value=5,
        max_value=50,
        value=15,
        step=5,
    )

filtered = df[df["current_trajectory"].isin(selected_states)].copy()

st.subheader("Top Current Hotspots")

top_hotspots = (
    filtered.sort_values("combined_trajectory_score", ascending=False)
    .head(top_n)
)

display_cols = [
    "geoid",
    "display_name",
    "current_trajectory",
    "previous_trajectory",
    "combined_trajectory_score",
    "acceleration_score",
    "distress_persistence_rate",
    "months_in_current_state",
    "months_any_distress",
    "total_state_changes",
]

st.dataframe(
    top_hotspots[display_cols],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Trajectory Score by Tract")

bar_fig = px.bar(
    top_hotspots.sort_values("combined_trajectory_score"),
    x="combined_trajectory_score",
    y="display_name",
    color="current_trajectory",
    color_discrete_map=STATE_COLORS,
    orientation="h",
    labels={
        "combined_trajectory_score": "Trajectory Score",
        "display_name": "Census Tract",
        "current_trajectory": "Current State",
    },
)

bar_fig.update_layout(
    height=600,
    yaxis_title=None,
    xaxis_title="Trajectory Score",
)

st.plotly_chart(bar_fig, use_container_width=True)

st.subheader("Persistence vs Current Trajectory Risk")

scatter_fig = px.scatter(
    filtered,
    x="distress_persistence_rate",
    y="combined_trajectory_score",
    color="current_trajectory",
    size="months_any_distress",
    hover_data=[
        "geoid",
        "display_name",
        "previous_trajectory",
        "months_in_current_state",
        "total_state_changes",
        "rolling_3m_active_cases",
        "rolling_12m_active_cases",
    ],
    color_discrete_map=STATE_COLORS,
    labels={
        "distress_persistence_rate": "Distress Persistence Rate",
        "combined_trajectory_score": "Current Trajectory Score",
        "current_trajectory": "Current State",
        "months_any_distress": "Months in Any Distress",
    },
)

scatter_fig.update_layout(
    height=650,
)

st.plotly_chart(scatter_fig, use_container_width=True)

st.subheader("Segmented Lists")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Rapid Deterioration")
    st.dataframe(
        df[df["current_trajectory"] == "Rapid Deterioration"]
        .sort_values("combined_trajectory_score", ascending=False)
        .head(10)[
            [
                "geoid",
                "display_name",
                "combined_trajectory_score",
                "months_in_current_state",
                "distress_persistence_rate",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with col2:
    st.markdown("### Chronic Distress")
    st.dataframe(
        df[df["current_trajectory"] == "Chronic Distress"]
        .sort_values("distress_persistence_rate", ascending=False)
        .head(10)[
            [
                "geoid",
                "display_name",
                "combined_trajectory_score",
                "months_in_current_state",
                "distress_persistence_rate",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with col3:
    st.markdown("### Improving")
    st.dataframe(
        df[df["current_trajectory"] == "Improving"]
        .sort_values("acceleration_score", ascending=True)
        .head(10)[
            [
                "geoid",
                "display_name",
                "combined_trajectory_score",
                "months_in_current_state",
                "distress_persistence_rate",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
