from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "scratch" / "presentation_assets"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.database.db_connection import get_engine

plt.rcParams.update(
    {
        "figure.dpi": 200,
        "font.size": 12,
        "axes.titlesize": 18,
        "axes.labelsize": 13,
    }
)

COLORS = {
    "paper": "#F6F3EE",
    "ink": "#13293D",
    "teal": "#2A7F8C",
    "teal_soft": "#86B3BF",
    "gold": "#D0902F",
    "rust": "#C8544C",
    "orange": "#E07E00",
    "blue": "#3367D6",
    "green": "#3A8C5A",
    "red": "#C91F1F",
}


def get_label_map(engine) -> dict[str, str]:
    labels = pd.read_sql(
        "SELECT geoid::text AS geoid, dominant_neighborhood FROM analytics.tract_neighborhood_labels",
        engine,
    )
    return dict(zip(labels["geoid"], labels["dominant_neighborhood"]))


def tract_label(geoid: str, label_map: dict[str, str]) -> str:
    neighborhood = label_map.get(str(geoid), str(geoid))
    return f"{neighborhood} ({geoid})"


def build_hotspots_chart(engine, label_map: dict[str, str]) -> None:
    query = """
    SELECT
        geoid::text AS geoid,
        neighborhood_trajectory,
        combined_trajectory_score
    FROM analytics.tract_state_history
    WHERE month_date = DATE '2026-05-01'
      AND geoid::text <> 'UNKNOWN'
    ORDER BY combined_trajectory_score DESC
    LIMIT 8;
    """
    df = pd.read_sql(query, engine)
    df["label"] = df["geoid"].map(lambda geoid: tract_label(geoid, label_map))
    df = df.iloc[::-1].reset_index(drop=True)

    color_map = {
        "Rapid Deterioration": COLORS["red"],
        "Chronic Distress": COLORS["rust"],
        "Emerging Risk": COLORS["orange"],
        "Improving": COLORS["green"],
        "Stable": COLORS["teal_soft"],
    }
    bar_colors = [color_map.get(state, COLORS["teal"]) for state in df["neighborhood_trajectory"]]

    fig, ax = plt.subplots(figsize=(12, 7), facecolor=COLORS["paper"])
    ax.set_facecolor(COLORS["paper"])
    bars = ax.barh(df["label"], df["combined_trajectory_score"], color=bar_colors)

    for bar, value in zip(bars, df["combined_trajectory_score"]):
        ax.text(
            min(value + 0.8, 100.5),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}",
            va="center",
            ha="left",
            fontsize=12,
            color=COLORS["ink"],
            fontweight="bold",
        )

    ax.set_title(
        "Top current hotspot tracts by trajectory score\nLatest state snapshot: May 1, 2026",
        loc="left",
        fontweight="bold",
    )
    ax.set_xlabel("Combined trajectory score")
    ax.set_xlim(0, 102)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "hotspots_top8.png", bbox_inches="tight")
    plt.close(fig)


def build_early_intervention_chart(engine, label_map: dict[str, str]) -> None:
    query = """
    SELECT
        geoid::text AS geoid,
        neighborhood_trajectory,
        predicted_probability
    FROM analytics.tract_forecast_scores
    WHERE month_date = DATE '2026-05-01'
      AND forecast_horizon = '6m'
      AND score_set = 'live_scoring'
      AND neighborhood_trajectory IN ('Stable', 'Improving', 'Emerging Risk')
    ORDER BY predicted_probability DESC
    LIMIT 8;
    """
    df = pd.read_sql(query, engine)
    df["label"] = df["geoid"].map(lambda geoid: tract_label(geoid, label_map))
    df = df.iloc[::-1].reset_index(drop=True)

    state_colors = {
        "Emerging Risk": COLORS["orange"],
        "Improving": COLORS["green"],
        "Stable": COLORS["blue"],
    }
    bar_colors = [state_colors.get(state, COLORS["teal"]) for state in df["neighborhood_trajectory"]]

    fig, ax = plt.subplots(figsize=(12, 7), facecolor=COLORS["paper"])
    ax.set_facecolor(COLORS["paper"])
    bars = ax.barh(df["label"], df["predicted_probability"], color=bar_colors)

    for bar, value in zip(bars, df["predicted_probability"]):
        ax.text(
            value + 0.005,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0%}",
            va="center",
            ha="left",
            fontsize=12,
            color="#111111",
        )

    ax.set_title(
        "Top early-intervention candidates\n6-month forecast, latest live-scored month: May 1, 2026",
        loc="left",
        fontweight="bold",
    )
    ax.set_xlabel("Predicted probability of entering severe distress")
    ax.set_xlim(0, max(df["predicted_probability"].max() + 0.03, 0.48))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.1%}")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "early_intervention_top8.png", bbox_inches="tight")
    plt.close(fig)


def build_horizon_summary_chart(engine) -> None:
    query = """
    SELECT
        forecast_horizon,
        AVG(predicted_probability) AS avg_probability,
        COUNT(*) FILTER (WHERE predicted_probability >= 0.20) AS tracts_above_20pct
    FROM analytics.tract_forecast_scores
    WHERE month_date = DATE '2026-05-01'
      AND score_set = 'live_scoring'
    GROUP BY forecast_horizon
    ORDER BY CASE forecast_horizon
        WHEN '1m' THEN 1
        WHEN '3m' THEN 2
        WHEN '6m' THEN 3
        WHEN '12m' THEN 4
        ELSE 99
    END;
    """
    df = pd.read_sql(query, engine)

    fig, ax1 = plt.subplots(figsize=(10, 6), facecolor=COLORS["paper"])
    ax1.set_facecolor(COLORS["paper"])

    bar_colors = [COLORS["teal_soft"], "#6698A3", COLORS["teal"], COLORS["gold"]]
    bars = ax1.bar(df["forecast_horizon"], df["tracts_above_20pct"], color=bar_colors, width=0.6)
    ax1.set_ylabel("Tracts with risk >= 20%", color=COLORS["ink"])
    ax1.tick_params(axis="y", colors=COLORS["ink"])
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    for bar, count in zip(bars, df["tracts_above_20pct"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            count + 0.6,
            f"{int(count)}",
            ha="center",
            va="bottom",
            color=COLORS["ink"],
            fontweight="bold",
            fontsize=14,
        )

    ax2 = ax1.twinx()
    ax2.plot(
        df["forecast_horizon"],
        df["avg_probability"],
        color=COLORS["rust"],
        marker="o",
        linewidth=2.5,
    )
    ax2.set_ylabel("Average predicted probability", color=COLORS["rust"])
    ax2.tick_params(axis="y", colors=COLORS["rust"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color(COLORS["rust"])

    for horizon, value in zip(df["forecast_horizon"], df["avg_probability"]):
        ax2.text(horizon, value + 0.008, f"{value:.3f}", color=COLORS["rust"], ha="center", va="bottom")

    ax1.set_title(
        "Forecast signal grows with longer horizons\nLatest live-scored month: May 1, 2026",
        loc="left",
        fontweight="bold",
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "horizon_summary.png", bbox_inches="tight")
    plt.close(fig)


def build_hamlin_case_chart(engine) -> None:
    query = """
    SELECT
        month_date,
        combined_trajectory_score,
        rolling_3m_active_cases,
        rolling_12m_active_cases
    FROM analytics.tract_state_history
    WHERE geoid::text = '36029005202'
      AND month_date BETWEEN DATE '2025-05-01' AND DATE '2026-05-01'
    ORDER BY month_date;
    """
    df = pd.read_sql(query, engine)
    df["month_date"] = pd.to_datetime(df["month_date"])

    fig, ax1 = plt.subplots(figsize=(12, 6), facecolor=COLORS["paper"])
    ax1.set_facecolor(COLORS["paper"])

    ax1.plot(
        df["month_date"],
        df["combined_trajectory_score"],
        color=COLORS["red"],
        linewidth=2.8,
        label="Trajectory score",
    )
    ax1.axvline(pd.Timestamp("2025-05-01"), color="#4F5D75", linestyle="--", linewidth=1.6, label="Historical backtest month")
    ax1.set_ylabel("Trajectory score")
    ax1.set_ylim(0, 100)
    ax1.spines["top"].set_visible(False)

    ax2 = ax1.twinx()
    ax2.plot(
        df["month_date"],
        df["rolling_3m_active_cases"],
        color=COLORS["orange"],
        linewidth=2.0,
        label="Rolling 3M active cases",
    )
    ax2.plot(
        df["month_date"],
        df["rolling_12m_active_cases"],
        color=COLORS["blue"],
        linewidth=2.0,
        label="Rolling 12M active cases",
    )
    ax2.set_ylabel("Active cases per 1,000 units")
    ax2.spines["top"].set_visible(False)

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left", frameon=False)

    ax1.set_title(
        "Hamlin Park case study: from elevated risk to rapid deterioration",
        loc="left",
        fontweight="bold",
    )
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "hamlin_case_study_v2.png", bbox_inches="tight")
    plt.close(fig)


def build_transition_chart(engine) -> None:
    query = """
    SELECT
        current_state,
        next_state,
        transition_probability
    FROM analytics.neighborhood_transition_matrix
    WHERE current_state IN ('Stable', 'Emerging Risk', 'Rapid Deterioration')
      AND next_state IN ('Stable', 'Emerging Risk', 'Rapid Deterioration', 'Chronic Distress')
    ORDER BY current_state, transition_probability DESC;
    """
    df = pd.read_sql(query, engine)
    focus_pairs = [
        ("Stable", "Stable"),
        ("Emerging Risk", "Emerging Risk"),
        ("Emerging Risk", "Stable"),
        ("Emerging Risk", "Rapid Deterioration"),
        ("Rapid Deterioration", "Rapid Deterioration"),
        ("Rapid Deterioration", "Chronic Distress"),
    ]
    focus_df = pd.DataFrame(focus_pairs, columns=["current_state", "next_state"]).merge(
        df,
        on=["current_state", "next_state"],
        how="left",
    )
    focus_df["label"] = focus_df["current_state"] + " -> " + focus_df["next_state"]

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=COLORS["paper"])
    ax.set_facecolor(COLORS["paper"])
    bars = ax.barh(
        focus_df["label"][::-1],
        focus_df["transition_probability"][::-1],
        color=[COLORS["teal"], COLORS["teal_soft"], COLORS["green"], COLORS["orange"], COLORS["rust"], COLORS["red"]],
    )

    for bar, value in zip(bars, focus_df["transition_probability"][::-1]):
        ax.text(value + 0.01, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center")

    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Transition probability")
    ax.set_title("Selected state transition probabilities", loc="left", fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "transition_probs.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    label_map = get_label_map(engine)

    build_hotspots_chart(engine, label_map)
    build_early_intervention_chart(engine, label_map)
    build_horizon_summary_chart(engine)
    build_hamlin_case_chart(engine)
    build_transition_chart(engine)

    print(f"Saved refreshed presentation assets to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
