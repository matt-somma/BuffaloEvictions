from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import streamlit as st


st.set_page_config(
    page_title="Buffalo Housing Instability Intelligence Platform",
    layout="wide",
)


st.title("Buffalo Housing Instability Intelligence Platform")

st.markdown(
    """
A spatial-temporal analytics platform for understanding, forecasting,
and visualizing neighborhood housing instability across Buffalo census tracts.
"""
)


st.divider()


left, right = st.columns([2, 1])

with left:
    st.subheader("Purpose of the Dashboard")

    st.markdown(
        """
This platform was built to help identify and monitor patterns of housing instability,
neighborhood distress, and emerging risk across Buffalo communities.

The dashboard combines:

- temporal analytics,
- spatial spillover modeling,
- machine learning forecasting,
- tract-level risk scoring,
- transition analysis,
- explainable AI,
- and interactive geographic visualization.

The goal is to support:

- proactive intervention,
- neighborhood stabilization,
- policy analysis,
- resource prioritization,
- and longitudinal urban risk monitoring.

Rather than only identifying neighborhoods already in crisis,
the platform is designed to surface early-warning indicators and forecast
future deterioration risk before severe distress becomes entrenched.
"""
    )

with right:
    st.subheader("Created By")

    st.markdown(
        """
### Matt Somma

Senior Analytics & Product Automation Professional

Specializing in:
- spatial analytics
- machine learning
- forecasting
- data engineering
- decision intelligence systems
- urban risk analytics

Built using:
- Python
- PostgreSQL/PostGIS
- Streamlit
- Plotly
- scikit-learn
- SHAP
"""
    )


st.divider()


st.subheader("Platform Capabilities")

cap1, cap2, cap3 = st.columns(3)

with cap1:
    st.markdown(
        """
### Spatial Analytics

- tract-level hotspot detection
- neighborhood spillover modeling
- border-weighted distress analysis
- temporal mapping
- geographic clustering
"""
    )

with cap2:
    st.markdown(
        """
### Forecasting & ML

- multi-horizon forecasting
- temporal logistic regression
- explainable AI (SHAP)
- trajectory classification
- persistence modeling
"""
    )

with cap3:
    st.markdown(
        """
### Decision Support

- early intervention targeting
- tract comparison tools
- forecast monitoring
- transition visualization
- neighborhood trajectory analysis
"""
    )


st.divider()


st.subheader("How to Use the Dashboard")

st.markdown(
    """
### Recommended Workflow

1. Explore current neighborhood conditions using the hotspot and tract explorer pages.
2. Review transition dynamics and persistence patterns using the Sankey and transition tools.
3. Analyze forecast probabilities across multiple horizons.
4. Identify early-intervention candidates before severe distress emerges.
5. Compare tracts longitudinally to understand how neighborhood risk evolves over time.
"""
)


st.divider()


st.caption(
    "Buffalo Housing Instability Intelligence Platform • Spatial-Temporal Urban Risk Analytics"
)
