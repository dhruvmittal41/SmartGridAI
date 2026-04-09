"""
train_all.py
============
Master training script — runs the complete SmartGrid AI training pipeline.

Usage:
    python train_all.py \
        --substation  data/raw/substation_*.csv \
        --transformer data/raw/transformer_*.csv \
        --meter_glab  data/raw/meter_feeder_*.csv \
        --kaggle      data/raw/smart_meter_india.csv \
        --epochs      50 \
        --threshold   95

All arguments are optional. If a file pattern yields no matches the
corresponding model is skipped (printed as a warning).

Output:
    models/saved/  — all .keras and .pkl files
    data/processed/ — numpy arrays and RF feature matrix

Expected runtime:
    ~8–15 min on CPU with typical hackathon dataset sizes.
    Use --epochs 20 for a quick 3-min run to verify the pipeline.
"""

import os
import sys
import glob
import argparse
import warnings

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import pandas as pd

# ── Allow running from project root ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from preprocess import (
    preprocess_substation,
    preprocess_transformer,
    preprocess_meter_gridlabd,
    preprocess_kaggle_meters,
    build_rf_feature_matrix,
    load_all_csvs,
)
from Training.lstm_models import (
    SubstationLSTM,
    TransformerLSTM,
    MeterLSTM,
    MeterGridLabLSTM,
    train_model_on_normals,
    evaluate_model,
)
from Training.pinn_validator import PINNValidator
from Training.fault_classifier_rf import FaultClassifierRF
from Training.load_management import DemandForecaster

MODELS_DIR = "models/saved"
PROCESSED_DIR = "data/processed"
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def resolve_paths(pattern: str) -> list:
    """Glob pattern or single file path. Returns list of existing paths."""
    if "*" in pattern or "?" in pattern:
        paths = sorted(glob.glob(pattern))
    else:
        paths = [pattern] if os.path.exists(pattern) else []
    return paths


def concat_csvs_gridlabd(pattern: str) -> str | None:
    """
    If multiple CSVs match, concatenate and write a temp file.
    Returns path to the (possibly temp) CSV, or None if no files.
    """
    paths = resolve_paths(pattern)
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]
    # Multiple files — concatenate
    df = load_all_csvs(pattern)
    out = os.path.join(PROCESSED_DIR, "_concat_tmp.csv")
    df.to_csv(out, index=False)
    return out


def train_pipeline(args: argparse.Namespace):
    print("=" * 65)
    print("  SmartGrid AI — Full Training Pipeline")
    print("=" * 65)

    all_anomaly_scores = {}
    all_pinn_scores = {}
    all_labels = []
    all_fault_types = []
    rf_raw_features = []

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: SUBSTATION LSTM
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 1 — Substation LSTM")
    sub_path = concat_csvs_gridlabd(args.substation)
    if sub_path:
        X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le = preprocess_substation(
            sub_path
        )
        sub_model = train_model_on_normals(
            SubstationLSTM, X_tr, y_tr, threshold_percentile=args.threshold
        )
        # Override with actual n_features from data
        sub_model.build(X_tr.shape[1], X_tr.shape[2])
        sub_model.train(X_tr[y_tr == 0], verbose=0)
        sub_model.compute_threshold(X_tr[y_tr == 0])
        sub_model.save()
        eval_sub = evaluate_model(sub_model, X_te, y_te)

        sub_scores_tr = sub_model.predict_anomaly_scores(X_tr)
        sub_scores_te = sub_model.predict_anomaly_scores(X_te)
        all_anomaly_scores["sub"] = {"train": sub_scores_tr, "test": sub_scores_te}
    else:
        print(f"  SKIP: No substation CSV found at '{args.substation}'")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: TRANSFORMER LSTM
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 2 — Transformer LSTM")
    xfmr_path = concat_csvs_gridlabd(args.transformer)
    if xfmr_path:
        X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le = preprocess_transformer(
            xfmr_path
        )
        xfmr_model = TransformerLSTM()
        xfmr_model.build(X_tr.shape[1], X_tr.shape[2])
        xfmr_model.train(X_tr[y_tr == 0], verbose=0)
        xfmr_model.compute_threshold(X_tr[y_tr == 0])
        xfmr_model.save()
        eval_xfmr = evaluate_model(xfmr_model, X_te, y_te)

        xfmr_scores_tr = xfmr_model.predict_anomaly_scores(X_tr)
        xfmr_scores_te = xfmr_model.predict_anomaly_scores(X_te)
        all_anomaly_scores["xfmr"] = {"train": xfmr_scores_tr, "test": xfmr_scores_te}
    else:
        print(f"  SKIP: No transformer CSV found at '{args.transformer}'")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: METER GRIDLAB LSTM
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 3 — Meter GridLAB LSTM")
    mglab_path = concat_csvs_gridlabd(args.meter_glab)
    if mglab_path:
        X_tr, X_te, y_tr, y_te, th_tr, th_te, scaler, le = preprocess_meter_gridlabd(
            mglab_path
        )
        mglab_model = MeterGridLabLSTM()
        mglab_model.build(X_tr.shape[1], X_tr.shape[2])
        mglab_model.train(X_tr[y_tr == 0], verbose=0)
        mglab_model.compute_threshold(X_tr[y_tr == 0])
        mglab_model.save()
        eval_mglab = evaluate_model(mglab_model, X_te, y_te)

        mglab_scores_tr = mglab_model.predict_anomaly_scores(X_tr)
        mglab_scores_te = mglab_model.predict_anomaly_scores(X_te)
        all_anomaly_scores["mglab"] = {
            "train": mglab_scores_tr,
            "test": mglab_scores_te,
        }
    else:
        print(f"  SKIP: No meter GridLAB CSV found at '{args.meter_glab}'")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: KAGGLE METER LSTM
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 4 — Kaggle Smart Meter LSTM")
    kaggle_paths = resolve_paths(args.kaggle)
    if kaggle_paths:
        X_tr, X_te, scaler, df_rf, feat_cols = preprocess_kaggle_meters(kaggle_paths[0])
        meter_model = MeterLSTM()
        meter_model.build(X_tr.shape[1], X_tr.shape[2])
        meter_model.train(X_tr, verbose=0)  # all Kaggle data treated as normal
        meter_model.compute_threshold(X_tr)
        meter_model.save()
        # No labelled test set for unsupervised Kaggle data
        print(f"[MeterLSTM] Kaggle model trained (unsupervised)")

        meter_scores_tr = meter_model.predict_anomaly_scores(X_tr)
        all_anomaly_scores["meter"] = {"train": meter_scores_tr}
    else:
        print(f"  SKIP: No Kaggle CSV found at '{args.kaggle}'")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: PINN VALIDATION + RF FEATURE MATRIX
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 5 — PINN Validation + RF Feature Assembly")

    # Use transformer data as the main RF training dataset (richest features)
    xfmr_raw_path = concat_csvs_gridlabd(args.transformer)
    mglab_raw_path = concat_csvs_gridlabd(args.meter_glab)

    if xfmr_raw_path and mglab_raw_path:
        # Load both raw CSVs
        from preprocess import _read_gridlabd

        df_xfmr = _read_gridlabd(xfmr_raw_path)
        df_mglab = _read_gridlabd(mglab_raw_path)

        # Align length
        n = min(len(df_xfmr), len(df_mglab))
        df_xfmr = df_xfmr.iloc[:n].reset_index(drop=True)
        df_mglab = df_mglab.iloc[:n].reset_index(drop=True)

        # PINN on merged features
        df_merged = pd.concat(
            [
                df_xfmr[["winding_temp_C", "load_pct", "thermal_margin_C"]],
                df_mglab[
                    [
                        "feeder_power_W",
                        "total_reported_W",
                        "loss_ratio",
                        "end_feeder_voltage_V",
                        "voltage_deviation_pct",
                        "undervoltage_flag",
                        "theft_flag_raw",
                    ]
                ],
            ],
            axis=1,
        )

        validator = PINNValidator()
        pinn_df = validator.validate_batch(df_merged)

        # LSTM scores on aligned data (use last N of each)
        seq_len = 48
        offset = seq_len  # first seq_len rows are consumed by sliding window

        def _safe_scores(key, length):
            s = all_anomaly_scores.get(key, {}).get("train")
            if s is None:
                return np.zeros(length)
            # Resample to match length by repeating/truncating
            if len(s) >= length:
                return s[:length]
            return np.concatenate([s, np.zeros(length - len(s))])

        target_n = n - offset
        sub_sc = _safe_scores("sub", target_n)
        xfmr_sc = _safe_scores("xfmr", target_n)
        mglab_sc = _safe_scores("mglab", target_n)
        pinn_sub = {
            "ohm": pinn_df["pinn_ohm"].values[offset:],
            "power": pinn_df["pinn_power"].values[offset:],
            "kcl": pinn_df["pinn_kcl"].values[offset:],
        }

        raw_feats = (
            df_merged[
                [
                    "winding_temp_C",
                    "load_pct",
                    "thermal_margin_C",
                    "loss_ratio",
                    "voltage_deviation_pct",
                    "undervoltage_flag",
                ]
            ]
            .iloc[offset:]
            .values
        )

        fault_labels = df_mglab["fault_label"].values[offset:]
        fault_types = df_mglab["fault_type"].values[offset:]
        # Merge fault types: theft from mglab, thermal from xfmr
        xfmr_types = df_xfmr["fault_type"].values[offset:]
        combined_type = np.where(fault_types == "normal", xfmr_types, fault_types)

        rf_df = build_rf_feature_matrix(
            sub_scores=sub_sc,
            xfmr_scores=xfmr_sc,
            meter_scores=mglab_sc,
            pinn_scores=pinn_sub,
            raw_features=raw_feats,
            fault_labels=fault_labels,
            fault_types=combined_type,
            feature_names=[
                "winding_temp",
                "load_pct",
                "thermal_margin",
                "loss_ratio",
                "voltage_dev",
                "undervoltage",
            ],
        )

        # ─────────────────────────────────────────────────────────────────────
        # STEP 6: RANDOM FOREST + SHAP
        # ─────────────────────────────────────────────────────────────────────
        print("\n▶ Step 6 — Random Forest Classifier + SHAP")
        clf = FaultClassifierRF(n_estimators=args.rf_trees, max_depth=12)
        clf.build()

        split = int(len(rf_df) * 0.8)
        df_tr_rf = rf_df.iloc[:split]
        df_te_rf = rf_df.iloc[split:]

        clf.train(df_tr_rf, target_col="fault_type")
        X_te_rf = df_te_rf.drop(
            columns=["fault_type", "fault_label"], errors="ignore"
        ).values
        y_te_raw = df_te_rf["fault_type"].values
        metrics = clf.evaluate(X_te_rf, y_te_raw)
        clf.save()

        # Feature importance
        imp = clf.get_feature_importance().head(8)
        print(f"\nTop features:\n{imp.to_string(index=False)}")

    else:
        print("  SKIP: Need both transformer and meter CSVs for RF training.")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: DEMAND FORECASTER
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶ Step 7 — Demand Forecaster")
    if xfmr_raw_path:
        df_xfmr = _read_gridlabd(xfmr_raw_path)
        # Build datetime index from minutes column
        df_xfmr.index = pd.to_datetime("2024-01-01") + pd.to_timedelta(
            df_xfmr["minutes"], unit="m"
        )
        forecaster = DemandForecaster(horizon_steps=24)
        forecaster.train(df_xfmr, load_col="load_pct")
    else:
        print("  SKIP: No transformer CSV for demand forecaster.")

    # ─────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  TRAINING COMPLETE")
    print("=" * 65)
    trained = [
        f for f in os.listdir(MODELS_DIR) if f.endswith(".keras") or f.endswith(".pkl")
    ]
    print(f"\nSaved {len(trained)} model files:")
    for f in sorted(trained):
        size = os.path.getsize(os.path.join(MODELS_DIR, f)) // 1024
        print(f"  {f:45s} {size:>6} KB")

    print(
        "\n✓ All models trained and saved.\n"
        "  Next step: run 'uvicorn api.main:app --reload' to start the API.\n"
    )


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="SmartGrid AI — Training Pipeline")
    parser.add_argument(
        "--substation",
        default="data/raw/substation*.csv",
        help="Glob for substation GridLAB-D CSVs",
    )
    parser.add_argument(
        "--transformer",
        default="data/raw/transformer*.csv",
        help="Glob for transformer GridLAB-D CSVs",
    )
    parser.add_argument(
        "--meter_glab",
        default="data/raw/meter*.csv",
        help="Glob for meter/feeder GridLAB-D CSVs",
    )
    parser.add_argument(
        "--kaggle",
        default="data/raw/smart_meter_india.csv",
        help="Path to Kaggle Indian smart meter CSV",
    )
    parser.add_argument(
        "--epochs", type=int, default=50, help="Max epochs per LSTM model"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=95.0,
        help="Anomaly threshold percentile (default 95)",
    )
    parser.add_argument(
        "--rf_trees", type=int, default=300, help="Number of RF estimators"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Patch epoch count into model defaults
    import Training.lstm_models as lstm_module

    for cls_name in [
        "SubstationLSTM",
        "TransformerLSTM",
        "MeterLSTM",
        "MeterGridLabLSTM",
    ]:
        getattr(lstm_module, cls_name).epochs = args.epochs

    train_pipeline(args)
