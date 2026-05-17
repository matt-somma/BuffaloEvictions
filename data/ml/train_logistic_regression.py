from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import shap

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "ml" / "tract_ml_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "model_results"


FEATURES = [
    "poverty_rate",
    "unemployment_rate",
    "renter_occupied_rate",
    "rent_burden_rate",
    "no_vehicle_rate",
    "median_household_income",

    "active_cases_per_1000_housing_units",
    "cases_last_12m_per_1000_housing_units",
    "cases_last_6m_per_1000_housing_units",
    "cases_last_3m_per_1000_housing_units",
    "properties_with_violations_per_1000_housing_units",

    "rolling_3m_active_cases",
    "rolling_6m_active_cases",
    "rolling_12m_active_cases",

    "acceleration_score",
    "medium_term_acceleration",
    "combined_trajectory_score",

    "distress_persistence_rate_to_date",
    "state_changes_to_date",

    "neighborhood_trajectory",
    "previous_trajectory",

    "neighbor_count",
    "neighbor_avg_trajectory_score",
    "neighbor_avg_acceleration_score",
    "neighbor_avg_rolling_3m",
    "neighbor_avg_rolling_12m",
    "distressed_neighbor_count",
    "rapid_neighbor_count",
    "chronic_neighbor_count",
    "reliable_distressed_neighbor_share",
    "reliable_rapid_neighbor_share",
    "reliable_chronic_neighbor_share",
    "border_weighted_neighbor_score",
    "border_weighted_neighbor_acceleration",
]


TARGETS = {
    "1m": "future_distress_1m",
    "3m": "future_distress_3m",
    "6m": "future_distress_6m",
    "12m": "future_distress_12m",
}


CATEGORICAL_FEATURES = [
    "neighborhood_trajectory",
    "previous_trajectory",
]


NUMERIC_FEATURES = [
    feature for feature in FEATURES
    if feature not in CATEGORICAL_FEATURES
]


def build_model() -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegressionCV(
                    Cs=10,
                    cv=5,
                    penalty="elasticnet",
                    solver="saga",
                    l1_ratios=[0.1, 0.3, 0.5, 0.7, 0.9],
                    scoring="roc_auc",
                    class_weight="balanced",
                    max_iter=5000,
                    n_jobs=-1,
                    random_state=42,
                ),
            ),
        ]
    )


def make_safe_feature_name(feature: str) -> str:
    return (
        feature
        .replace("num__", "")
        .replace("cat__", "")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )


def create_forecast_output(
    test_df: pd.DataFrame,
    target_col: str,
    horizon_label: str,
    probabilities: np.ndarray,
    predictions: np.ndarray,
    shap_values: np.ndarray,
    feature_names: np.ndarray,
    shap_importance_df: pd.DataFrame,
) -> pd.DataFrame:
    output_df = test_df.copy()

    output_df["predicted_probability"] = probabilities
    output_df["predicted_class"] = predictions

    output_df["risk_percentile"] = (
        output_df["predicted_probability"]
        .rank(pct=True)
        * 100
    )

    top_feature_names = shap_importance_df.head(15)["feature"].tolist()

    for idx, feature in enumerate(feature_names):
        if feature in top_feature_names:
            safe_feature = make_safe_feature_name(feature)
            output_df[f"shap__{safe_feature}"] = shap_values[:, idx]

    top_driver_rows = []

    for row in shap_values:
        top_idx = np.argsort(np.abs(row))[::-1][:3]

        top_driver_rows.append(
            ", ".join(
                make_safe_feature_name(feature_names[idx])
                for idx in top_idx
            )
        )

    output_df["top_drivers"] = top_driver_rows

    base_cols = [
        "geoid",
        "month_date",
        "neighborhood_trajectory",
        target_col,
        "predicted_probability",
        "predicted_class",
        "risk_percentile",
        "top_drivers",
    ]

    shap_cols = [
        col for col in output_df.columns
        if col.startswith("shap__")
    ]

    forecast_output = output_df[base_cols + shap_cols].copy()

    forecast_output = forecast_output.rename(
        columns={target_col: "actual_target"}
    )

    forecast_output["forecast_horizon"] = horizon_label
    forecast_output["target_column"] = target_col
    forecast_output["model_name"] = "elastic_net_logistic_regression"
    forecast_output["model_version"] = "v1"

    return forecast_output


def train_one_horizon(
    df: pd.DataFrame,
    horizon_label: str,
    target_col: str,
) -> pd.DataFrame:
    print()
    print("=" * 60)
    print(f"Training horizon: {horizon_label}")
    print(f"Target column: {target_col}")
    print("=" * 60)

    required_cols = FEATURES + [target_col, "month_date", "geoid"]

    model_df = df[required_cols].copy()
    model_df = model_df[model_df[target_col].notna()].copy()

    train_df = model_df[
        model_df["month_date"] < "2023-01-01"
    ].copy()

    test_df = model_df[
        model_df["month_date"] >= "2023-01-01"
    ].copy()

    print()
    print("=== TEMPORAL SPLIT ===")
    print(f"Train rows: {len(train_df):,}")
    print(f"Test rows: {len(test_df):,}")

    print()
    print(
        f"Train period: "
        f"{train_df['month_date'].min().date()} "
        f"to "
        f"{train_df['month_date'].max().date()}"
    )

    print(
        f"Test period: "
        f"{test_df['month_date'].min().date()} "
        f"to "
        f"{test_df['month_date'].max().date()}"
    )

    X_train = train_df[FEATURES]
    y_train = train_df[target_col]

    X_test = test_df[FEATURES]
    y_test = test_df[target_col]

    model = build_model()

    print()
    print("Training logistic regression model...")
    model.fit(X_train, y_train)

    classifier = model.named_steps["classifier"]

    print()
    print("=== REGULARIZATION SETTINGS ===")
    print(f"Best C: {classifier.C_[0]}")
    print(f"Best L1 ratio: {classifier.l1_ratio_[0]}")

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = model.predict(X_test)

    auc = roc_auc_score(y_test, probabilities)

    print()
    print("=== LOGISTIC REGRESSION PERFORMANCE ===")
    print(f"ROC-AUC: {auc:.4f}")

    print()
    print("=== CLASSIFICATION REPORT ===")
    print(classification_report(y_test, predictions))

    print()
    print("=== CONFUSION MATRIX ===")
    print(confusion_matrix(y_test, predictions))

    baseline_auc = roc_auc_score(
        y_test,
        X_test["combined_trajectory_score"],
    )

    print()
    print("=== CURRENT TRAJECTORY SCORE PERFORMANCE ===")
    print(f"Trajectory Score ROC-AUC: {baseline_auc:.4f}")

    print()
    print("=== MODEL IMPROVEMENT ===")
    print(f"Delta ROC-AUC: {auc - baseline_auc:.4f}")

    preprocessor = model.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_[0]

    importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "abs_coefficient": np.abs(coefficients),
        }
    ).sort_values("abs_coefficient", ascending=False)

    print()
    print("=== FEATURE IMPORTANCE ===")
    print(importance_df.head(25).to_string(index=False))

    print()
    print("=== SHAP EXPLAINABILITY ===")

    X_test_transformed = preprocessor.transform(X_test)

    if hasattr(X_test_transformed, "toarray"):
        X_test_transformed = X_test_transformed.toarray()

    explainer = shap.LinearExplainer(
        classifier,
        X_test_transformed,
        feature_names=feature_names,
    )

    shap_values = explainer.shap_values(X_test_transformed)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    shap_importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": mean_abs_shap,
        }
    ).sort_values("mean_abs_shap", ascending=False)

    print()
    print(shap_importance_df.head(25).to_string(index=False))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    shap_importance_path = OUTPUT_DIR / f"shap_importance_{horizon_label}.csv"
    shap_importance_df.to_csv(shap_importance_path, index=False)

    shap_plot_path = OUTPUT_DIR / f"shap_summary_logistic_regression_{horizon_label}.png"

    shap.summary_plot(
        shap_values,
        X_test_transformed,
        feature_names=feature_names,
        show=False,
    )

    plt.tight_layout()
    plt.savefig(
        shap_plot_path,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    print(f"Saved SHAP importance to {shap_importance_path}")
    print(f"Saved SHAP summary plot to {shap_plot_path}")

    forecast_output = create_forecast_output(
        test_df=test_df,
        target_col=target_col,
        horizon_label=horizon_label,
        probabilities=probabilities,
        predictions=predictions,
        shap_values=shap_values,
        feature_names=feature_names,
        shap_importance_df=shap_importance_df,
    )

    return forecast_output


def main() -> None:
    print("Loading modeling dataset...")

    df = pd.read_csv(DATA_PATH)
    df["month_date"] = pd.to_datetime(df["month_date"])

    print(f"Rows loaded: {len(df):,}")

    all_forecast_outputs = []

    for horizon_label, target_col in TARGETS.items():
        forecast_output = train_one_horizon(
            df=df,
            horizon_label=horizon_label,
            target_col=target_col,
        )

        all_forecast_outputs.append(forecast_output)

    final_output = pd.concat(
        all_forecast_outputs,
        ignore_index=True,
    )

    engine = get_engine()

    final_output.to_sql(
        name="tract_forecast_scores",
        con=engine,
        schema="analytics",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    print()
    print("Saved all forecast horizons to analytics.tract_forecast_scores")

    print()
    print("Forecast rows by horizon:")
    print(
        final_output
        .groupby("forecast_horizon")
        .size()
        .to_string()
    )


if __name__ == "__main__":
    main()