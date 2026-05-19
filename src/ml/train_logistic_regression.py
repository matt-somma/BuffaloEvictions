from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import shap

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.exceptions import ConvergenceWarning

from src.database.db_connection import get_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "model_results"
LABELED_DATASET_QUERY = "SELECT * FROM analytics.tract_ml_features;"
LIVE_SCORING_DATASET_QUERY = "SELECT * FROM analytics.tract_ml_scoring_features;"
TRAIN_TEST_CUTOFF = pd.Timestamp("2023-01-01")
MODEL_VERSION = "v4_time_aware_live_scoring_assessment"


FEATURES = [
    "poverty_rate",
    "unemployment_rate",
    "renter_occupied_rate",
    "rent_burden_rate",
    "no_vehicle_rate",
    "median_household_income",
    "residential_parcel_share",
    "multifamily_share_of_residential",
    "residential_vacant_land_share",
    "owner_occupied_proxy_share",
    "poor_condition_share",
    "fair_or_worse_condition_share",
    "missing_condition_share",
    "avg_residential_total_value",
    "avg_land_value",
    "avg_residential_living_area",
    "pre_1940_residential_share",

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


C_VALUES = np.logspace(-3, 2, 8)
L1_RATIO_VALUES = [0.1, 0.3, 0.5, 0.7, 0.9]
TIME_AWARE_CV_SPLITS = 5
MIN_TRAIN_MONTHS = 48


class IdentityCalibrator:
    def fit(self, probabilities: np.ndarray, y_true: np.ndarray) -> "IdentityCalibrator":
        return self

    def predict(self, probabilities: np.ndarray) -> np.ndarray:
        return np.asarray(probabilities, dtype=float)


class SigmoidCalibrator:
    def __init__(self) -> None:
        self.model = LogisticRegression(
            solver="lbfgs",
            max_iter=1000,
            random_state=42,
        )

    def fit(self, probabilities: np.ndarray, y_true: np.ndarray) -> "SigmoidCalibrator":
        logits = probabilities_to_logits(probabilities)
        self.model.fit(logits.reshape(-1, 1), y_true)
        return self

    def predict(self, probabilities: np.ndarray) -> np.ndarray:
        logits = probabilities_to_logits(probabilities)
        return self.model.predict_proba(logits.reshape(-1, 1))[:, 1]


def build_model(C: float, l1_ratio: float) -> Pipeline:
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
                LogisticRegression(
                    solver="saga",
                    C=C,
                    l1_ratio=l1_ratio,
                    class_weight="balanced",
                    max_iter=10000,
                    tol=1e-3,
                    random_state=42,
                ),
            ),
        ]
    )


def load_modeling_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = get_engine()

    labeled_df = pd.read_sql(LABELED_DATASET_QUERY, engine)
    live_scoring_df = pd.read_sql(LIVE_SCORING_DATASET_QUERY, engine)

    for df in (labeled_df, live_scoring_df):
        df["month_date"] = pd.to_datetime(df["month_date"])

    return labeled_df, live_scoring_df


def create_time_aware_folds(
    month_dates: pd.Series,
    n_splits: int = TIME_AWARE_CV_SPLITS,
    min_train_months: int = MIN_TRAIN_MONTHS,
) -> list[dict]:
    unique_months = np.array(sorted(pd.to_datetime(month_dates).dropna().unique()))
    n_months = len(unique_months)

    if n_months <= min_train_months + 1:
        raise ValueError(
            "Not enough monthly history for time-aware CV. "
            f"Months available: {n_months}, minimum required: {min_train_months + 2}."
        )

    remaining_months = n_months - min_train_months
    effective_splits = min(n_splits, remaining_months)
    base_val_months = max(1, remaining_months // effective_splits)
    remainder = remaining_months % effective_splits

    month_dates = pd.to_datetime(month_dates)
    folds = []
    train_end = min_train_months

    for fold_number in range(effective_splits):
        extra_month = 1 if fold_number < remainder else 0
        val_end = min(n_months, train_end + base_val_months + extra_month)

        train_months = unique_months[:train_end]
        val_months = unique_months[train_end:val_end]

        train_idx = np.flatnonzero(month_dates.isin(train_months).to_numpy())
        val_idx = np.flatnonzero(month_dates.isin(val_months).to_numpy())

        if len(train_idx) == 0 or len(val_idx) == 0:
            train_end = val_end
            continue

        folds.append(
            {
                "train_idx": train_idx,
                "val_idx": val_idx,
                "train_start": pd.Timestamp(train_months[0]),
                "train_end": pd.Timestamp(train_months[-1]),
                "val_start": pd.Timestamp(val_months[0]),
                "val_end": pd.Timestamp(val_months[-1]),
            }
        )

        train_end = val_end

    if not folds:
        raise ValueError("Failed to create any time-aware CV folds.")

    return folds


def probabilities_to_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def fit_model(model: Pipeline, X: pd.DataFrame, y: pd.Series) -> int:
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always", ConvergenceWarning)
        model.fit(X, y)

    return sum(
        issubclass(warning.category, ConvergenceWarning)
        for warning in caught_warnings
    )


def select_best_hyperparameters(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    month_dates: pd.Series,
) -> tuple[dict, pd.DataFrame, list[dict]]:
    folds = create_time_aware_folds(month_dates)
    results = []

    for C in C_VALUES:
        for l1_ratio in L1_RATIO_VALUES:
            fold_scores = []
            convergence_warnings = 0

            for fold in folds:
                fold_model = build_model(C=C, l1_ratio=l1_ratio)
                convergence_warnings += fit_model(
                    fold_model,
                    X_train.iloc[fold["train_idx"]],
                    y_train.iloc[fold["train_idx"]],
                )

                y_val = y_train.iloc[fold["val_idx"]]
                val_probabilities = fold_model.predict_proba(
                    X_train.iloc[fold["val_idx"]]
                )[:, 1]

                if y_val.nunique() < 2:
                    continue

                fold_scores.append(roc_auc_score(y_val, val_probabilities))

            if fold_scores:
                results.append(
                    {
                        "C": C,
                        "l1_ratio": l1_ratio,
                        "mean_cv_auc": float(np.mean(fold_scores)),
                        "min_cv_auc": float(np.min(fold_scores)),
                        "max_cv_auc": float(np.max(fold_scores)),
                        "num_folds": len(fold_scores),
                        "convergence_warnings": convergence_warnings,
                    }
                )

    if not results:
        raise ValueError("Time-aware CV did not produce any valid validation scores.")

    cv_results = pd.DataFrame(results).sort_values(
        ["mean_cv_auc", "min_cv_auc", "convergence_warnings", "l1_ratio", "C"],
        ascending=[False, False, True, False, True],
    )

    best = cv_results.iloc[0].to_dict()
    return best, cv_results, folds


def collect_validation_predictions(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    folds: list[dict],
    C: float,
    l1_ratio: float,
) -> tuple[np.ndarray, np.ndarray, int]:
    y_true_parts = []
    probability_parts = []
    convergence_warnings = 0

    for fold in folds:
        fold_model = build_model(C=C, l1_ratio=l1_ratio)
        convergence_warnings += fit_model(
            fold_model,
            X_train.iloc[fold["train_idx"]],
            y_train.iloc[fold["train_idx"]],
        )

        y_true_parts.append(y_train.iloc[fold["val_idx"]].to_numpy())
        probability_parts.append(
            fold_model.predict_proba(X_train.iloc[fold["val_idx"]])[:, 1]
        )

    return (
        np.concatenate(y_true_parts),
        np.concatenate(probability_parts),
        convergence_warnings,
    )


def fit_probability_calibrator(
    y_true: np.ndarray,
    raw_probabilities: np.ndarray,
) -> tuple[object, dict]:
    raw_brier = brier_score_loss(y_true, raw_probabilities)

    sigmoid_calibrator = SigmoidCalibrator().fit(raw_probabilities, y_true)
    calibrated_probabilities = sigmoid_calibrator.predict(raw_probabilities)
    calibrated_brier = brier_score_loss(y_true, calibrated_probabilities)

    if calibrated_brier + 1e-6 < raw_brier:
        return sigmoid_calibrator, {
            "method": "sigmoid",
            "raw_brier": float(raw_brier),
            "calibrated_brier": float(calibrated_brier),
        }

    return IdentityCalibrator(), {
        "method": "none",
        "raw_brier": float(raw_brier),
        "calibrated_brier": float(raw_brier),
    }


def tune_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> dict:
    candidate_thresholds = np.unique(
        np.clip(
            np.concatenate(
                [
                    np.linspace(0.05, 0.95, 91),
                    probabilities,
                ]
            ),
            0,
            1,
        )
    )

    best_result = None

    for threshold in candidate_thresholds:
        predictions = (probabilities >= threshold).astype(int)

        if predictions.sum() == 0:
            continue

        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        f1 = f1_score(y_true, predictions, zero_division=0)

        result = {
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "predicted_positive_rate": float(predictions.mean()),
        }

        if best_result is None:
            best_result = result
            continue

        if result["f1"] > best_result["f1"]:
            best_result = result
            continue

        if (
            result["f1"] == best_result["f1"]
            and result["precision"] > best_result["precision"]
        ):
            best_result = result
            continue

        if (
            result["f1"] == best_result["f1"]
            and result["precision"] == best_result["precision"]
            and result["threshold"] > best_result["threshold"]
        ):
            best_result = result

    if best_result is None:
        raise ValueError("Threshold tuning failed to find a valid threshold.")

    return best_result


def compute_shap_outputs(
    model: Pipeline,
    X: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    preprocessor = model.named_steps["preprocessor"]
    classifier = model.named_steps["classifier"]
    feature_names = preprocessor.get_feature_names_out()

    X_transformed = preprocessor.transform(X)

    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()

    explainer = shap.LinearExplainer(
        classifier,
        X_transformed,
        feature_names=feature_names,
    )

    shap_values = explainer.shap_values(X_transformed)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    shap_importance_df = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": mean_abs_shap,
        }
    ).sort_values("mean_abs_shap", ascending=False)

    return X_transformed, feature_names, shap_values, shap_importance_df


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
    scored_df: pd.DataFrame,
    target_col: str,
    horizon_label: str,
    score_set: str,
    decision_threshold: float,
    calibration_method: str,
    raw_probabilities: np.ndarray,
    probabilities: np.ndarray,
    predictions: np.ndarray,
    shap_values: np.ndarray,
    feature_names: np.ndarray,
    shap_importance_df: pd.DataFrame,
) -> pd.DataFrame:
    output_df = scored_df.copy()

    output_df["raw_predicted_probability"] = raw_probabilities
    output_df["predicted_probability"] = probabilities
    output_df["predicted_class"] = predictions
    output_df["decision_threshold"] = decision_threshold
    output_df["calibration_method"] = calibration_method

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
        "raw_predicted_probability",
        "predicted_probability",
        "predicted_class",
        "decision_threshold",
        "calibration_method",
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

    forecast_output["score_set"] = score_set
    forecast_output["label_available"] = forecast_output["actual_target"].notna()
    forecast_output["forecast_horizon"] = horizon_label
    forecast_output["target_column"] = target_col
    forecast_output["model_name"] = "elastic_net_logistic_regression"
    forecast_output["model_version"] = MODEL_VERSION

    return forecast_output


def train_one_horizon(
    labeled_df: pd.DataFrame,
    live_scoring_df: pd.DataFrame,
    horizon_label: str,
    target_col: str,
) -> pd.DataFrame:
    print()
    print("=" * 60)
    print(f"Training horizon: {horizon_label}")
    print(f"Target column: {target_col}")
    print("=" * 60)

    required_cols = FEATURES + [target_col, "month_date", "geoid"]

    model_df = labeled_df[required_cols].copy()
    model_df = model_df[model_df[target_col].notna()].copy()

    train_df = model_df[
        model_df["month_date"] < TRAIN_TEST_CUTOFF
    ].copy().sort_values(["month_date", "geoid"]).reset_index(drop=True)

    test_df = model_df[
        model_df["month_date"] >= TRAIN_TEST_CUTOFF
    ].copy().sort_values(["month_date", "geoid"]).reset_index(drop=True)

    scoring_df = live_scoring_df[required_cols].copy().sort_values(
        ["month_date", "geoid"]
    ).reset_index(drop=True)

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

    print()
    print("=== LIVE SCORING WINDOW ===")
    print(f"Live rows: {len(scoring_df):,}")
    if not scoring_df.empty:
        print(
            f"Live scoring period: "
            f"{scoring_df['month_date'].min().date()} "
            f"to "
            f"{scoring_df['month_date'].max().date()}"
        )

    X_train = train_df[FEATURES]
    y_train = train_df[target_col]

    X_test = test_df[FEATURES]
    y_test = test_df[target_col]

    print()
    print("Selecting hyperparameters with time-aware CV...")
    best_params, cv_results, folds = select_best_hyperparameters(
        X_train=X_train,
        y_train=y_train,
        month_dates=train_df["month_date"],
    )

    print()
    print("=== TIME-AWARE CV ===")
    print(f"Folds used: {len(folds)}")
    for fold_idx, fold in enumerate(folds, start=1):
        print(
            f"Fold {fold_idx}: "
            f"train {fold['train_start'].date()} to {fold['train_end'].date()}, "
            f"validate {fold['val_start'].date()} to {fold['val_end'].date()}"
        )

    print()
    print("=== REGULARIZATION SETTINGS ===")
    print(f"Best C: {best_params['C']}")
    print(f"Best L1 ratio: {best_params['l1_ratio']}")
    print(f"Mean CV ROC-AUC: {best_params['mean_cv_auc']:.4f}")

    print()
    print("Top CV results:")
    print(
        cv_results.head(5).to_string(
            index=False,
            formatters={
                "C": lambda x: f"{x:.6f}",
                "l1_ratio": lambda x: f"{x:.1f}",
                "mean_cv_auc": lambda x: f"{x:.4f}",
                "min_cv_auc": lambda x: f"{x:.4f}",
                "max_cv_auc": lambda x: f"{x:.4f}",
            },
        )
    )

    print()
    print("Collecting validation predictions for calibration and threshold tuning...")
    oof_y_true, oof_raw_probabilities, tuning_convergence_warnings = collect_validation_predictions(
        X_train=X_train,
        y_train=y_train,
        folds=folds,
        C=float(best_params["C"]),
        l1_ratio=float(best_params["l1_ratio"]),
    )
    calibrator, calibration_result = fit_probability_calibrator(
        y_true=oof_y_true,
        raw_probabilities=oof_raw_probabilities,
    )
    oof_probabilities = calibrator.predict(oof_raw_probabilities)
    threshold_result = tune_threshold(oof_y_true, oof_probabilities)

    print()
    print("=== CALIBRATION ===")
    print(f"Method: {calibration_result['method']}")
    print(f"Validation raw Brier: {calibration_result['raw_brier']:.4f}")
    print(
        "Validation calibrated Brier: "
        f"{calibration_result['calibrated_brier']:.4f}"
    )
    print(
        "Convergence warnings during threshold-tuning fits: "
        f"{tuning_convergence_warnings}"
    )

    print()
    print("=== THRESHOLD TUNING ===")
    print(f"Chosen threshold: {threshold_result['threshold']:.3f}")
    print(f"Validation F1: {threshold_result['f1']:.4f}")
    print(f"Validation precision: {threshold_result['precision']:.4f}")
    print(f"Validation recall: {threshold_result['recall']:.4f}")
    print(
        "Validation predicted positive rate: "
        f"{threshold_result['predicted_positive_rate']:.4f}"
    )

    model = build_model(
        C=float(best_params["C"]),
        l1_ratio=float(best_params["l1_ratio"]),
    )

    print()
    print("Training final logistic regression model...")
    final_fit_convergence_warnings = fit_model(model, X_train, y_train)

    classifier = model.named_steps["classifier"]

    raw_probabilities = model.predict_proba(X_test)[:, 1]
    probabilities = calibrator.predict(raw_probabilities)
    predictions = (
        probabilities >= threshold_result["threshold"]
    ).astype(int)

    auc = roc_auc_score(y_test, probabilities)
    average_precision = average_precision_score(y_test, probabilities)
    brier = brier_score_loss(y_test, probabilities)

    print()
    print("=== LOGISTIC REGRESSION PERFORMANCE ===")
    print(f"ROC-AUC: {auc:.4f}")
    print(f"Average Precision: {average_precision:.4f}")
    print(f"Brier Score: {brier:.4f}")
    print(f"Calibration method: {calibration_result['method']}")
    print(f"Final fit convergence warnings: {final_fit_convergence_warnings}")

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
    X_test_transformed, feature_names, shap_values, shap_importance_df = compute_shap_outputs(
        model,
        X_test,
    )

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

    backtest_output = create_forecast_output(
        scored_df=test_df,
        target_col=target_col,
        horizon_label=horizon_label,
        score_set="holdout_backtest",
        decision_threshold=threshold_result["threshold"],
        calibration_method=calibration_result["method"],
        raw_probabilities=raw_probabilities,
        probabilities=probabilities,
        predictions=predictions,
        shap_values=shap_values,
        feature_names=feature_names,
        shap_importance_df=shap_importance_df,
    )

    print()
    print("Training production model on all labeled rows for live scoring...")
    production_model = build_model(
        C=float(best_params["C"]),
        l1_ratio=float(best_params["l1_ratio"]),
    )
    production_fit_convergence_warnings = fit_model(
        production_model,
        model_df[FEATURES],
        model_df[target_col],
    )
    print(
        "Production fit convergence warnings: "
        f"{production_fit_convergence_warnings}"
    )

    live_output = pd.DataFrame()

    if not scoring_df.empty:
        X_live = scoring_df[FEATURES]
        live_raw_probabilities = production_model.predict_proba(X_live)[:, 1]
        live_probabilities = calibrator.predict(live_raw_probabilities)
        live_predictions = (
            live_probabilities >= threshold_result["threshold"]
        ).astype(int)

        _, live_feature_names, live_shap_values, live_shap_importance_df = compute_shap_outputs(
            production_model,
            X_live,
        )

        live_output = create_forecast_output(
            scored_df=scoring_df,
            target_col=target_col,
            horizon_label=horizon_label,
            score_set="live_scoring",
            decision_threshold=threshold_result["threshold"],
            calibration_method=calibration_result["method"],
            raw_probabilities=live_raw_probabilities,
            probabilities=live_probabilities,
            predictions=live_predictions,
            shap_values=live_shap_values,
            feature_names=live_feature_names,
            shap_importance_df=live_shap_importance_df,
        )

    return pd.concat(
        [backtest_output, live_output],
        ignore_index=True,
    )


def main() -> None:
    print("Loading labeled backtest and live scoring datasets...")
    labeled_df, live_scoring_df = load_modeling_datasets()

    print(f"Labeled rows loaded: {len(labeled_df):,}")
    print(f"Live scoring rows loaded: {len(live_scoring_df):,}")

    all_forecast_outputs = []

    for horizon_label, target_col in TARGETS.items():
        forecast_output = train_one_horizon(
            labeled_df=labeled_df,
            live_scoring_df=live_scoring_df,
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

    print()
    print("Forecast rows by score set:")
    print(
        final_output
        .groupby("score_set")
        .size()
        .to_string()
    )


if __name__ == "__main__":
    main()
