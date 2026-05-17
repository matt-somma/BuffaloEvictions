import plotly.graph_objects as go
import streamlit as st

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from dashboards.streamlit.utils.db import run_query
from dashboards.streamlit.utils.queries import TRANSITION_MATRIX_QUERY


STATE_ORDER = [
    "Stable",
    "Improving",
    "Emerging Risk",
    "Rapid Deterioration",
    "Chronic Distress",
]

STATE_COLORS = {
    "Stable": "rgba(44, 160, 44, 0.8)",
    "Improving": "rgba(31, 119, 180, 0.8)",
    "Emerging Risk": "rgba(255, 127, 14, 0.8)",
    "Rapid Deterioration": "rgba(214, 39, 40, 0.8)",
    "Chronic Distress": "rgba(127, 0, 0, 0.8)",
}


st.set_page_config(
    page_title="State Transitions",
    layout="wide",
)

st.title("Neighborhood State Transitions")

df = run_query(TRANSITION_MATRIX_QUERY)

if df.empty:
    st.warning("No transition matrix data found.")
    st.stop()

min_probability = st.slider(
    "Minimum transition probability shown",
    min_value=0.0,
    max_value=1.0,
    value=0.02,
    step=0.01,
)

filtered = df[df["transition_probability"] >= min_probability].copy()

states = [state for state in STATE_ORDER if state in set(df["current_state"]).union(df["next_state"])]

state_to_idx = {state: idx for idx, state in enumerate(states)}

filtered["source"] = filtered["current_state"].map(state_to_idx)
filtered["target"] = filtered["next_state"].map(state_to_idx)

fig = go.Figure(
    data=[
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=22,
                line=dict(color="black", width=0.5),
                label=states,
                color=[STATE_COLORS.get(state, "gray") for state in states],
            ),
            link=dict(
                source=filtered["source"],
                target=filtered["target"],
                value=filtered["transition_count"],
                customdata=filtered["transition_probability"],
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>"
                    "Transitions: %{value}<br>"
                    "Probability: %{customdata:.1%}<extra></extra>"
                ),
            ),
        )
    ]
)

fig.update_layout(
    title="Month-to-Month Neighborhood State Transitions",
    font_size=12,
    height=700,
)

st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
### How to Read This Chart

This Sankey diagram shows how Buffalo census tracts transition between neighborhood risk states from one month to the next.

#### Reading the Flow

- Each box represents a neighborhood trajectory state.
- The connecting bands show how tracts move between states over time.
- Thicker bands represent more transitions.
- Hover over a band to see:
  - the number of tract-month transitions,
  - and the transition probability.

#### Example Interpretations

- **Stable → Stable**
  - Most neighborhoods remain stable month-to-month.
  - This is typically the largest flow.

- **Emerging Risk → Rapid Deterioration**
  - Indicates neighborhoods that are worsening quickly.

- **Rapid Deterioration → Chronic Distress**
  - Suggests short-term deterioration becoming long-term structural distress.

- **Improving → Stable**
  - Represents neighborhoods recovering toward stability.

#### Why This Matters

The chart helps identify:
- persistent distress,
- recovery patterns,
- emerging hotspots,
- and how neighborhood conditions evolve over time.

These transitions form the foundation for longer-term neighborhood risk forecasting.
"""
)

st.subheader("Transition Matrix")

display_df = df.copy()
display_df["transition_probability"] = display_df["transition_probability"].map(
    lambda x: f"{x:.1%}"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)