from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import plotly.express as px
import streamlit as st

from dashboards.streamlit.utils.db import run_query


EARLY_INTERVENTION_QUERY = """
SELECT
    f.geoid,

    COALESCE(
        n.dominant_neighborhood || ' (' || f.geoid::text || ')',
        r.geo_name,
        f.geoid::text
    ) AS display_name,

    f.month_date,
    f.neighborhood_trajectory,
    f.predicted_probability,
    f.risk_percentile,
    f.top_drivers,
    f.forecast_horizon,
    f.actual_target,

    r.housing_instability_score_v2,
    r.poverty_rate,
    r.rent_burden_rate,
    r.no_vehicle_rate

FROM analytics.tract_forecast_scores f

LEFT JOIN analytics.housing_risk_features_v2 r
    ON f.geoid::text = r.geoid

LEFT JOIN analytics.tract_neighborhood_labels n
    ON f.geoid::text = n.geoid

WHERE f.neighborhood_trajectory IN (
    'Stable',
    'Improving',
    'Emerging Risk'
) AND f.forecast_horizon = :forecast_horizon

ORDER BY f.predicted_probability DESC;
"""


st.set_page_config(
    page_title="Early Intervention Candidates",
    layout="wide",
)

st.title("Early Intervention Candidates")

st.markdown(
    """
This map shows the model-predicted probability that each census tract will enter
**Rapid Deterioration** or **Chronic Distress** within the selected forecast horizon.

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
    EARLY_INTERVENTION_QUERY,
    {"forecast_horizon": selected_horizon},
)

if df.empty:
    st.warning("No early intervention forecast data found.")
    st.stop()

df["month_date"] = df["month_date"].astype(str)

latest_month = df["month_date"].max()

left, right = st.columns(2)

with left:
    month_filter = st.selectbox(
        "Forecast month",
        sorted(df["month_date"].unique(), reverse=True),
        index=0,
    )

with right:
    min_probability = st.slider(
        "Minimum predicted probability",
        min_value=0.0,
        max_value=1.0,
        value=0.70,
        step=0.05,
    )

filtered = df[
    (df["month_date"] == month_filter)
    & (df["predicted_probability"] >= min_probability)
].copy()

st.subheader(f"Candidates for {month_filter}")

display_df = filtered[
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
].copy()

display_df["predicted_probability"] = display_df["predicted_probability"].map(
    lambda x: f"{x:.1%}"
)

display_df["risk_percentile"] = display_df["risk_percentile"].map(
    lambda x: f"{x:.1f}"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

st.subheader("Predicted Risk by Candidate Tract")

if not filtered.empty:
    bar_fig = px.bar(
        filtered.sort_values("predicted_probability"),
        x="predicted_probability",
        y="display_name",
        color="neighborhood_trajectory",
        orientation="h",
        hover_data=[
            "risk_percentile",
            "top_drivers",
            "housing_instability_score_v2",
            "poverty_rate",
            "rent_burden_rate",
            "no_vehicle_rate",
        ],
        labels={
            "predicted_probability": "Predicted Probability",
            "display_name": "Tract / Neighborhood",
            "neighborhood_trajectory": "Current State",
        },
    )

    bar_fig.update_layout(
        height=650,
        xaxis_tickformat=".0%",
        yaxis_title=None,
    )

    st.plotly_chart(bar_fig, use_container_width=True)
else:
    st.info("No tracts meet the current filter settings.")

st.subheader("How to Interpret This Page")

st.markdown(
    """
- **Predicted probability** estimates the likelihood of future distress within the forecast horizon.
- **Current state** shows whether the tract is currently Stable, Improving, or Emerging Risk.
- **Top drivers** summarize the strongest SHAP contributors for the forecast.
- Tracts with high forecasted risk but non-severe current state may be good candidates for early intervention.

A particularly useful pattern is:

> Stable or Improving today, but high predicted future risk.

That often indicates a tract where conditions may be worsening beneath the surface or where nearby deterioration is creating spillover pressure.
"""
)