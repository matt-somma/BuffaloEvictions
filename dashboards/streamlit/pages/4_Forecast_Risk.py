from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboards.streamlit.utils.db import run_query


TRACT_FORECAST_QUERY = """
SELECT
    f.geoid::text AS geoid,

    COALESCE(
        n.dominant_neighborhood || ' (' || f.geoid::text || ')',
        r.geo_name,
        f.geoid::text
    ) AS display_name,

    f.month_date,
    f.forecast_horizon,
    f.neighborhood_trajectory,
    f.actual_target,
    f.predicted_probability,
    f.predicted_class,
    f.risk_percentile,
    f.top_drivers,

    r.housing_instability_score_v2,
    r.poverty_rate,
    r.rent_burden_rate,
    r.no_vehicle_rate

FROM analytics.tract_forecast_scores f

LEFT JOIN analytics.housing_risk_features_v2 r
    ON f.geoid::text = r.geoid

LEFT JOIN analytics.tract_neighborhood_labels n
    ON f.geoid::text = n.geoid

WHERE f.geoid::text <> 'UNKNOWN';
"""


HORIZON_ORDER = ["1m", "3m", "6m", "12m"]


st.set_page_config(
    page_title="Tract Forecast Risk",
    layout="wide",
)

st.title("Tract-Level Forecast Risk")

st.markdown(
    """
This page shows model-predicted future distress risk at the census-tract level.
Use it to understand whether a tract appears to be at short-term, medium-term,
or longer-term risk of entering **Rapid Deterioration** or **Chronic Distress**.
"""
)

df = run_query(TRACT_FORECAST_QUERY)

if df.empty:
    st.warning("No tract forecast data found.")
    st.stop()

df["month_date"] = pd.to_datetime(df["month_date"])
df["month_str"] = df["month_date"].dt.strftime("%Y-%m")

tract_lookup = (
    df[["display_name", "geoid"]]
    .drop_duplicates()
    .sort_values("display_name")
)

selected_displays = st.multiselect(
    "Select tracts",
    tract_lookup["display_name"].tolist(),
    default=tract_lookup["display_name"].tolist()[:3],
)

st.caption(
    "Tip: compare nearby tracts to see how risk evolves differently across horizons."
)

if not selected_displays:
    st.info("Select at least one tract.")
    st.stop()

selected_geoids = tract_lookup.loc[
    tract_lookup["display_name"].isin(selected_displays),
    "geoid",
].tolist()

tract_df = df[df["geoid"].isin(selected_geoids)].copy()

latest_month = tract_df["month_date"].max()

selected_month = st.selectbox(
    "Forecast month",
    sorted(tract_df["month_str"].unique(), reverse=True),
    index=0,
)

month_df = tract_df[tract_df["month_str"] == selected_month].copy()

month_df["forecast_horizon"] = pd.Categorical(
    month_df["forecast_horizon"],
    categories=HORIZON_ORDER,
    ordered=True,
)

month_df = month_df.sort_values(
    ["display_name", "forecast_horizon"]
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Selected Tracts", len(selected_geoids))
col2.metric("Forecast Month", selected_month)

avg_6m = month_df.loc[
    month_df["forecast_horizon"] == "6m",
    "predicted_probability",
].mean()

max_6m = month_df.loc[
    month_df["forecast_horizon"] == "6m",
    "predicted_probability",
].max()

col3.metric("Avg 6M Risk", f"{avg_6m:.1%}")
col4.metric("Max 6M Risk", f"{max_6m:.1%}")

st.subheader("Forecast Risk by Horizon")

bar_fig = px.bar(
    month_df,
    x="forecast_horizon",
    y="predicted_probability",
    color="display_name",
    barmode="group",
    category_orders={
        "forecast_horizon": HORIZON_ORDER,
    },
    hover_data=[
        "neighborhood_trajectory",
        "risk_percentile",
        "top_drivers",
        "actual_target",
        "predicted_class",
    ],
    labels={
        "forecast_horizon": "Forecast Horizon",
        "predicted_probability": "Predicted Distress Probability",
        "display_name": "Tract",
    },
)

bar_fig.update_layout(
    yaxis_tickformat=".0%",
    height=550,
)

st.plotly_chart(bar_fig, use_container_width=True)

st.subheader("Risk Over Time")

selected_horizon = st.selectbox(
    "Risk history horizon",
    HORIZON_ORDER,
    index=2,
)

history_df = tract_df[
    tract_df["forecast_horizon"] == selected_horizon
].sort_values("month_date")

line_fig = px.line(
    history_df,
    x="month_date",
    y="predicted_probability",
    color="display_name",
    markers=True,
    hover_data=[
        "neighborhood_trajectory",
        "risk_percentile",
        "top_drivers",
        "actual_target",
    ],
    labels={
        "month_date": "Month",
        "predicted_probability": "Predicted Distress Probability",
        "display_name": "Tract",
    },
)

line_fig.update_layout(
    yaxis_tickformat=".0%",
    height=550,
)

st.plotly_chart(line_fig, use_container_width=True)

st.subheader("Forecast Explanation")

explanation_df = month_df[
    [
        "display_name",
        "forecast_horizon",
        "neighborhood_trajectory",
        "predicted_probability",
        "risk_percentile",
        "predicted_class",
        "actual_target",
        "top_drivers",
    ]
].copy()

explanation_df["predicted_probability"] = explanation_df[
    "predicted_probability"
].map(lambda x: f"{x:.1%}")

explanation_df["risk_percentile"] = explanation_df[
    "risk_percentile"
].map(lambda x: f"{x:.1f}")

st.dataframe(
    explanation_df,
    use_container_width=True,
    hide_index=True,
)

st.subheader("How to Interpret This Page")

st.markdown(
    """
- **1M risk** captures near-term warning signs.
- **3M risk** captures tactical intervention risk.
- **6M risk** captures medium-term deterioration risk.
- **12M risk** captures longer-term structural vulnerability.
- **Top drivers** show the main SHAP-based factors behind the model forecast.

Useful patterns:
- High 1M and high 12M risk may indicate entrenched distress.
- Low 1M but high 12M risk may indicate slower structural deterioration.
- High 1M but lower 12M risk may indicate a temporary acute shock.
"""
)