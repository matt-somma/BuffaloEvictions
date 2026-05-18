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

st.info(
    """
Think of this page as the neighborhood-dynamics view.
It is designed to help answer three questions:

1. How do tracts usually move between states from month to month?
2. Which transitions are common versus rare?
3. Does the system tend to reinforce stability, deterioration, or recovery?
"""
)

with st.expander("What this page is showing"):
    st.markdown(
        """
This page summarizes how tracts move between the platform's state labels over adjacent months:

- Stable
- Improving
- Emerging Risk
- Rapid Deterioration
- Chronic Distress

Rather than focusing on one tract, this page shows the **system-level movement patterns**
across the full tract set.

It helps answer questions about whether neighborhood conditions are sticky, whether recovery is common,
and how often tracts escalate into more severe distress.
"""
    )

with st.expander("How to interpret the Sankey diagram"):
    st.markdown(
        """
- Each node is a tract state.

- Each band shows movement from one state to the next between monthly observations.

- Thicker bands represent more transitions.

- The slider removes very small transition probabilities so you can focus on the more meaningful flows.

- Large self-to-self flows, such as **Stable -> Stable**, indicate persistence.
"""
    )

with st.expander("How to read the transition probabilities"):
    st.markdown(
        """
- **Transition probability** is conditional on the current state.
  For example, the probability of `Emerging Risk -> Rapid Deterioration`
  is measured out of all transitions starting from `Emerging Risk`.

- High self-transition probabilities indicate that a state tends to persist month to month.

- High transition probabilities into more severe states suggest deterioration pathways that may deserve monitoring.

- Higher probabilities into less severe states suggest more common recovery or stabilization pathways.
"""
    )

with st.expander("How to use this page for interpretation and planning"):
    st.markdown(
        """
Useful takeaways include:

- If **Stable -> Stable** dominates, most neighborhoods remain relatively steady month to month.

- If **Emerging Risk -> Rapid Deterioration** is meaningful, Emerging Risk should be treated as a serious early-warning state.

- If **Rapid Deterioration -> Chronic Distress** is common, short-term deterioration may often harden into entrenched distress.

- If **Improving -> Stable** is common, recovery may be plausible once a tract exits distress.

This page is especially useful for understanding the logic behind the forecasting problem:
the model is trying to anticipate movement into the most severe states before those transitions happen.
"""
    )

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
