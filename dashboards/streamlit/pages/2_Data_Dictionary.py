from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from dashboards.streamlit.utils.data_dictionary import (
    METRIC_DEFINITIONS,
    SOURCE_OBJECTS,
)
from dashboards.streamlit.utils.view_options import render_label_mode_control


st.set_page_config(
    page_title="Data Dictionary",
    layout="wide",
)

render_label_mode_control()

st.title("Data Dictionary")

st.markdown(
    """
This page explains the key metrics, labels, and forecast outputs used throughout the platform.
Use it as a glossary when you need to understand what a field means, where it comes from,
and how it is calculated.
"""
)

st.caption(
    "The current public forecast layer is powered by the v4 assessment-enhanced live-scoring model."
)

metric_df = pd.DataFrame(METRIC_DEFINITIONS)
source_df = pd.DataFrame(SOURCE_OBJECTS)

st.subheader("How to Use This Page")
st.markdown(
    """
- Use the search box to find a metric name or phrase.
- Filter by category to narrow the glossary.
- Review the source object section to see which analytics tables power each page.
- Treat percentile-based metrics as relative comparisons across tracts, not absolute rates.
"""
)

left, right = st.columns([2, 1])

with left:
    search_text = st.text_input(
        "Search metrics or definitions",
        placeholder="Examples: trajectory score, threshold, rent burden, neighbor",
    ).strip().lower()

with right:
    selected_categories = st.multiselect(
        "Filter categories",
        options=sorted(metric_df["category"].unique()),
        default=sorted(metric_df["category"].unique()),
    )

filtered_df = metric_df[metric_df["category"].isin(selected_categories)].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df.apply(
            lambda row: search_text in " ".join(
                str(value).lower()
                for value in row
            ),
            axis=1,
        )
    ].copy()

st.subheader("Metric Glossary")
st.caption(f"{len(filtered_df)} metric definitions shown")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "metric": st.column_config.TextColumn("Metric"),
        "category": st.column_config.TextColumn("Category"),
        "source_object": st.column_config.TextColumn("Source Object"),
        "definition": st.column_config.TextColumn("Definition", width="large"),
        "business_interpretation": st.column_config.TextColumn("Business Interpretation", width="large"),
        "calculation": st.column_config.TextColumn("Calculation / Logic", width="large"),
    },
)

st.subheader("Important Interpretation Notes")

with st.expander("Trajectory labels and scores"):
    st.markdown(
        """
- `combined_trajectory_score` is a relative score based on percentile ranks within each month.
- `Rapid Deterioration` and `Chronic Distress` are rule-based labels, not model predictions.
- `Emerging Risk` means the tract scores high enough on the combined trajectory score to be flagged,
  even if it is not yet in the most severe states.
"""
    )

with st.expander("Structural vulnerability metrics"):
    st.markdown(
        """
- `housing_instability_score_v2` blends demographic vulnerability with code-violation burden.
- These structural metrics are slower-moving than the monthly trajectory metrics.
- A tract can have high structural vulnerability but still be temporarily stable in its monthly trajectory.
"""
    )

with st.expander("Forecast outputs"):
    st.markdown(
        """
- The public forecast layer currently uses the `v4_time_aware_live_scoring_assessment` model release.
- `predicted_probability` is the preferred risk field for dashboard interpretation.
- `predicted_class` depends on a tuned threshold and should be treated as a decision aid, not ground truth.
- `risk_percentile` is a relative rank, which makes it useful for prioritization across tracts.
- `top_drivers` summarizes the strongest SHAP contributors, which explains why the model scored a tract as risky.
"""
    )

st.subheader("Source Objects")
st.dataframe(
    source_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "object_name": st.column_config.TextColumn("Object"),
        "grain": st.column_config.TextColumn("Grain"),
        "used_for": st.column_config.TextColumn("Used For", width="large"),
    },
)

st.subheader("Quick FAQ")

faq_col1, faq_col2 = st.columns(2)

with faq_col1:
    st.markdown(
        """
**What does "per 1,000 housing units" mean?**

It standardizes counts by tract size so larger tracts do not automatically look riskier just because they contain more housing units.

**Why do some metrics use percentiles?**

Percentile ranks make cross-tract comparisons easier by showing where a tract sits relative to the rest of the city in that month.
"""
    )

with faq_col2:
    st.markdown(
        """
**What is the forecast target?**

The model predicts entry into `Rapid Deterioration` or `Chronic Distress` within a selected future horizon.

**What powers the current public forecast layer?**

The public forecast pages are currently driven by the `v4_time_aware_live_scoring_assessment` model, which adds assessment-derived structural features and live current-month scoring.

**Are the state labels predicted by the model?**

No. Current state labels are rule-based classifications from the trajectory pipeline. The model forecasts future entry into severe states.
"""
    )
