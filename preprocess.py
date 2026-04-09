"""
preprocess.py
=============
Handles all four data sources:
  1. GridLAB-D substation CSV  (sparse: time features + fault labels)
  2. GridLAB-D transformer CSV (winding_temp, load_pct, thermal_margin)
  3. GridLAB-D meter/feeder CSV(feeder_power, loss_ratio, voltage, theft_flag)
  4. Kaggle Indian smart meter  (kWh, Voltage, Current, Frequency per meter)

Outputs:
  - Normalised NumPy arrays  (X_train, X_test, y_train, y_test)
  - Saved MinMaxScaler objects per model
  - Unified feature matrix for the Random-Forest classifier
"""

import os
import glob
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split

# ── paths ────────────────────────────────────────────────────────────────────
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")

for d in [PROCESSED_DIR, MODELS_DIR]:
    os.makedirs(d, exist_ok=True)

# ── constants ─────────────────────────────────────────────────────────────────
SEQ_LEN_METER = 60  # 60 rows × 3-min intervals = 3 hours of Kaggle meter data
SEQ_LEN_GRID = 48  # 48 rows of GridLAB-D data (minute-level, ~48 min window)
TEST_SPLIT = 0.2
RANDOM_STATE = 42

# ── helpers ───────────────────────────────────────────────────────────────────


def _read_gridlabd(path: str) -> pd.DataFrame:
    """
    GridLAB-D CSVs have coordinates as the first-row column names.
    E.g.:  +2.96796e+06,+1.64022e+06,minutes,hour_of_day,...
    We rename those first two coordinate columns to coord_x and coord_y.
    """
    df = pd.read_csv(path)
    cols = list(df.columns)
    # The first two columns are numeric strings (the node coordinates)
    try:
        float(cols[0])
        float(cols[1])
        cols[0] = "coord_x"
        cols[1] = "coord_y"
        df.columns = cols
    except ValueError:
        pass  # already named properly
    return df


def _make_sequences(arr: np.ndarray, seq_len: int):
    """Slide a window over arr to produce (N, seq_len, features) tensor."""
    xs = []
    for i in range(len(arr) - seq_len):
        xs.append(arr[i : i + seq_len])
    return np.array(xs, dtype=np.float32)


def _encode_fault_type(series: pd.Series) -> np.ndarray:
    """
    Map fault_type strings to integer class labels.
    Returns (encoded_array, fitted_LabelEncoder).
    """
    le = LabelEncoder()
    encoded = le.fit_transform(series.fillna("normal").astype(str))
    return encoded, le


# ──────────────────────────────────────────────────────────────────────────────
# 1. SUBSTATION
# ──────────────────────────────────────────────────────────────────────────────


def preprocess_substation(csv_path: str):
    """
    Features used: hour_of_day, day_of_week, minutes (normalised).
    The GridLAB-D substation file is sparse — only temporal features + labels.
    In a real deployment these would be augmented with live voltage/current.

    Returns
    -------
    X_train, X_test  : (N, SEQ_LEN_GRID, n_features)  float32
    y_train, y_test  : (N,)  int  — fault_label  (0=normal, 1=fault)
    ft_train, ft_test: (N,)  int  — fault_type class
    scaler           : fitted MinMaxScaler
    label_encoder    : fitted LabelEncoder for fault_type
    """
    df = _read_gridlabd(csv_path)

    # ── feature engineering ──────────────────────────────────────────────────
    # Cyclic encoding for hour and day avoids discontinuity at midnight / week-end
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    feature_cols = ["hour_sin", "hour_cos", "day_sin", "day_cos"]
    labels_bin = df["fault_label"].values.astype(int)
    fault_types, le = _encode_fault_type(df["fault_type"])

    # ── normalise ─────────────────────────────────────────────────────────────
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(df[feature_cols].values)

    # ── sequences ─────────────────────────────────────────────────────────────
    X_seq = _make_sequences(X_scaled, SEQ_LEN_GRID)
    y_seq = labels_bin[SEQ_LEN_GRID:]
    ft_seq = fault_types[SEQ_LEN_GRID:]

    X_tr, X_te, y_tr, y_te, ft_tr, ft_te = train_test_split(
        X_seq,
        y_seq,
        ft_seq,
        test_size=TEST_SPLIT,
        random_state=RANDOM_STATE,
        stratify=y_seq,
    )

    # ── persist ───────────────────────────────────────────────────────────────
    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler_substation.pkl"))
    joblib.dump(le, os.path.join(MODELS_DIR, "le_substation.pkl"))
    np.save(os.path.join(PROCESSED_DIR, "sub_X_train.npy"), X_tr)
    np.save(os.path.join(PROCESSED_DIR, "sub_X_test.npy"), X_te)
    np.save(os.path.join(PROCESSED_DIR, "sub_y_train.npy"), y_tr)
    np.save(os.path.join(PROCESSED_DIR, "sub_y_test.npy"), y_te)

    print(
        f"[Substation] train={X_tr.shape}  test={X_te.shape}  "
        f"fault_rate={y_seq.mean():.3f}  classes={list(le.classes_)}"
    )
    return X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le


# ──────────────────────────────────────────────────────────────────────────────
# 2. TRANSFORMER
# ──────────────────────────────────────────────────────────────────────────────


def preprocess_transformer(csv_path: str):
    """
    Features: winding_temp_C, load_pct, thermal_margin_C + cyclic time.
    Physics note: thermal_margin_C = rated_temp - winding_temp_C.
    We also derive a 'thermal_stress' feature = load_pct² / thermal_margin_C
    to capture non-linear heating under heavy load.
    """
    df = _read_gridlabd(csv_path)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    # Guard against division-by-zero in thermal_margin
    df["thermal_margin_C"] = df["thermal_margin_C"].replace(0, 0.1)
    df["thermal_stress"] = (df["load_pct"] ** 2) / df["thermal_margin_C"]
    # Rolling 5-step temp gradient — captures rising temperature trend
    df["temp_grad"] = df["winding_temp_C"].diff(5).fillna(0)

    feature_cols = [
        "winding_temp_C",
        "load_pct",
        "thermal_margin_C",
        "thermal_stress",
        "temp_grad",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
    ]
    labels_bin = df["fault_label"].values.astype(int)
    fault_types, le = _encode_fault_type(df["fault_type"])

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(df[feature_cols].values)

    X_seq = _make_sequences(X_scaled, SEQ_LEN_GRID)
    y_seq = labels_bin[SEQ_LEN_GRID:]
    ft_seq = fault_types[SEQ_LEN_GRID:]

    X_tr, X_te, y_tr, y_te, ft_tr, ft_te = train_test_split(
        X_seq,
        y_seq,
        ft_seq,
        test_size=TEST_SPLIT,
        random_state=RANDOM_STATE,
        stratify=y_seq,
    )

    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler_transformer.pkl"))
    joblib.dump(le, os.path.join(MODELS_DIR, "le_transformer.pkl"))
    np.save(os.path.join(PROCESSED_DIR, "xfmr_X_train.npy"), X_tr)
    np.save(os.path.join(PROCESSED_DIR, "xfmr_X_test.npy"), X_te)
    np.save(os.path.join(PROCESSED_DIR, "xfmr_y_train.npy"), y_tr)
    np.save(os.path.join(PROCESSED_DIR, "xfmr_y_test.npy"), y_te)

    print(
        f"[Transformer] train={X_tr.shape}  test={X_te.shape}  "
        f"fault_rate={y_seq.mean():.3f}  classes={list(le.classes_)}"
    )
    return X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le


# ──────────────────────────────────────────────────────────────────────────────
# 3. METER / FEEDER  (GridLAB-D theft & voltage data)
# ──────────────────────────────────────────────────────────────────────────────


def preprocess_meter_gridlabd(csv_path: str):
    """
    Rich feature set:
      feeder_power_W, total_reported_W, loss_ratio, excess_loss_pct,
      theft_flag_raw, end_feeder_voltage_V, voltage_deviation_pct,
      undervoltage_flag + cyclic time.

    Derives:
      - apparent_loss = feeder_power_W - total_reported_W
      - log_excess    = log1p(excess_loss_pct) for heavy-tail skew
    """
    df = _read_gridlabd(csv_path)

    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    df["apparent_loss"] = df["feeder_power_W"] - df["total_reported_W"]
    df["log_excess"] = np.log1p(df["excess_loss_pct"].clip(lower=0))
    # Rolling 5-step loss trend
    df["loss_trend"] = df["loss_ratio"].diff(5).fillna(0)

    feature_cols = [
        "feeder_power_W",
        "total_reported_W",
        "loss_ratio",
        "apparent_loss",
        "log_excess",
        "loss_trend",
        "end_feeder_voltage_V",
        "voltage_deviation_pct",
        "undervoltage_flag",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
    ]
    labels_bin = df["fault_label"].values.astype(int)
    theft_labels = df["theft_flag_raw"].values.astype(int)
    fault_types, le = _encode_fault_type(df["fault_type"])

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(df[feature_cols].values)

    X_seq = _make_sequences(X_scaled, SEQ_LEN_GRID)
    y_seq = labels_bin[SEQ_LEN_GRID:]
    th_seq = theft_labels[SEQ_LEN_GRID:]
    ft_seq = fault_types[SEQ_LEN_GRID:]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_seq, y_seq, test_size=TEST_SPLIT, random_state=RANDOM_STATE, stratify=y_seq
    )
    _, _, th_tr, th_te = train_test_split(
        X_seq, th_seq, test_size=TEST_SPLIT, random_state=RANDOM_STATE, stratify=y_seq
    )

    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler_meter_glab.pkl"))
    joblib.dump(le, os.path.join(MODELS_DIR, "le_meter_glab.pkl"))
    np.save(os.path.join(PROCESSED_DIR, "meter_glab_X_train.npy"), X_tr)
    np.save(os.path.join(PROCESSED_DIR, "meter_glab_X_test.npy"), X_te)
    np.save(os.path.join(PROCESSED_DIR, "meter_glab_y_train.npy"), y_tr)
    np.save(os.path.join(PROCESSED_DIR, "meter_glab_y_test.npy"), y_te)

    print(
        f"[Meter-GridLAB] train={X_tr.shape}  test={X_te.shape}  "
        f"fault_rate={y_seq.mean():.3f}  theft_rate={th_seq.mean():.3f}"
    )
    return X_tr, X_te, y_tr, y_te, th_tr, th_te, scaler, le


# ──────────────────────────────────────────────────────────────────────────────
# 4. KAGGLE INDIAN SMART METERS (Bareilly / Mathura)
# ──────────────────────────────────────────────────────────────────────────────


def preprocess_kaggle_meters(csv_path: str):
    """
    Per-meter time-series: kWh, Voltage, Current, Frequency.
    Strategy:
      - Parse timestamp, extract cyclic time features
      - Compute per-meter rolling z-scores  (energy theft proxy)
      - Normalise per meter then concatenate

    For the LSTM autoencoder we train on all meters jointly.
    Reconstruction error on unseen data → anomaly score.

    Also derives PINN-ready columns:
      apparent_power_VA = Voltage × Current
      power_factor_est  = (kWh_per_interval × 3600 / interval_s) / apparent_power_VA
    """
    df = pd.read_csv(csv_path, parse_dates=["x_Timestamp"])
    df = df.rename(columns={"x_Timestamp": "ts", "t_kWh": "kWh"})
    df = df.sort_values(["meter", "ts"]).reset_index(drop=True)

    # ── interval in seconds ───────────────────────────────────────────────────
    df["interval_s"] = (
        df.groupby("meter")["ts"]
        .diff()
        .dt.total_seconds()
        .fillna(180)  # default 3-min intervals (Bareilly dataset)
    )

    # ── time features ─────────────────────────────────────────────────────────
    df["hour"] = df["ts"].dt.hour + df["ts"].dt.minute / 60
    df["dow"] = df["ts"].dt.dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["day_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["day_cos"] = np.cos(2 * np.pi * df["dow"] / 7)

    # ── physics-derived features ──────────────────────────────────────────────
    df["apparent_VA"] = df["Voltage"] * df["Current"]
    df["active_W"] = (df["kWh"] * 3_600_000) / df["interval_s"].clip(lower=1)
    df["pf_est"] = (df["active_W"] / df["apparent_VA"].clip(lower=0.01)).clip(0, 1)
    df["voltage_dev"] = (
        df["Voltage"] - 230.0
    ) / 230.0  # pu deviation from 230V nominal

    # ── per-meter rolling z-score of kWh  (theft proxy) ─────────────────────
    df["kwh_roll_mean"] = df.groupby("meter")["kWh"].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean()
    )
    df["kwh_roll_std"] = df.groupby("meter")["kWh"].transform(
        lambda x: x.rolling(window=20, min_periods=1).std().fillna(0.01)
    )
    df["kwh_zscore"] = (df["kWh"] - df["kwh_roll_mean"]) / df["kwh_roll_std"]

    # ── frequency deviation ───────────────────────────────────────────────────
    df["freq_dev"] = df["Frequency"] - 50.0  # nominal 50 Hz (India)

    feature_cols = [
        "kWh",
        "Voltage",
        "Current",
        "Frequency",
        "apparent_VA",
        "pf_est",
        "voltage_dev",
        "freq_dev",
        "kwh_zscore",
        "hour_sin",
        "hour_cos",
        "day_sin",
        "day_cos",
    ]

    # ── normalise globally (across all meters) ────────────────────────────────
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(df[feature_cols].fillna(0).values)

    # ── sequences ─────────────────────────────────────────────────────────────
    # IMPORTANT: sequences must NOT cross meter boundaries
    all_seqs = []
    meters = df["meter"].unique()
    for m in meters:
        idx = df[df["meter"] == m].index
        data = X_scaled[idx]
        if len(data) > SEQ_LEN_METER:
            seqs = _make_sequences(data, SEQ_LEN_METER)
            all_seqs.append(seqs)

    X_seq = (
        np.concatenate(all_seqs, axis=0)
        if all_seqs
        else np.empty((0, SEQ_LEN_METER, len(feature_cols)))
    )

    # Autoencoder trains on ALL data (no y needed for unsupervised)
    X_tr, X_te = train_test_split(
        X_seq, test_size=TEST_SPLIT, random_state=RANDOM_STATE
    )

    # ── also return flat feature df for RF ────────────────────────────────────
    df_for_rf = df[feature_cols + ["meter"]].copy()

    joblib.dump(scaler, os.path.join(MODELS_DIR, "scaler_kaggle_meter.pkl"))
    np.save(os.path.join(PROCESSED_DIR, "kaggle_X_train.npy"), X_tr)
    np.save(os.path.join(PROCESSED_DIR, "kaggle_X_test.npy"), X_te)

    print(
        f"[Kaggle Meters] train={X_tr.shape}  test={X_te.shape}  "
        f"meters={len(meters)}  features={len(feature_cols)}"
    )
    return X_tr, X_te, scaler, df_for_rf, feature_cols


# ──────────────────────────────────────────────────────────────────────────────
# 5. BUILD UNIFIED RF FEATURE MATRIX
#    Call this AFTER all LSTM models are trained and predictions are available
# ──────────────────────────────────────────────────────────────────────────────


def build_rf_feature_matrix(
    sub_scores: np.ndarray,  # (N,) LSTM reconstruction error — substation
    xfmr_scores: np.ndarray,  # (N,) LSTM reconstruction error — transformer
    meter_scores: np.ndarray,  # (N,) LSTM reconstruction error — meter
    pinn_scores: dict,  # {"ohm": (N,), "power": (N,), "kcl": (N,)}
    raw_features: np.ndarray,  # (N, k) — raw grid readings at prediction time
    fault_labels: np.ndarray,  # (N,) — ground truth binary
    fault_types: np.ndarray,  # (N,) — encoded fault class
    feature_names: list = None,
):
    """
    Assembles the complete feature matrix for the Random Forest classifier.

    Input columns:
      [sub_recon_err, xfmr_recon_err, meter_recon_err,
       pinn_ohm_viol, pinn_power_viol, pinn_kcl_viol,
       pinn_total_viol,
       ...raw_features]

    Returns pd.DataFrame (easy to pass to RF and SHAP).
    """
    N = len(fault_labels)
    assert sub_scores.shape[0] == N, "substation score length mismatch"
    assert xfmr_scores.shape[0] == N, "transformer score length mismatch"
    assert meter_scores.shape[0] == N, "meter score length mismatch"

    df = pd.DataFrame(
        {
            "sub_recon_err": sub_scores,
            "xfmr_recon_err": xfmr_scores,
            "meter_recon_err": meter_scores,
            "pinn_ohm_viol": pinn_scores.get("ohm", np.zeros(N)),
            "pinn_power_viol": pinn_scores.get("power", np.zeros(N)),
            "pinn_kcl_viol": pinn_scores.get("kcl", np.zeros(N)),
            "pinn_total_viol": (
                pinn_scores.get("ohm", np.zeros(N))
                + pinn_scores.get("power", np.zeros(N))
                + pinn_scores.get("kcl", np.zeros(N))
            ),
        }
    )

    if raw_features is not None and raw_features.shape[1] > 0:
        raw_cols = feature_names or [f"raw_{i}" for i in range(raw_features.shape[1])]
        for i, col in enumerate(raw_cols):
            df[col] = raw_features[:, i]

    df["fault_label"] = fault_labels
    df["fault_type"] = fault_types

    out_path = os.path.join(PROCESSED_DIR, "rf_features.csv")
    df.to_csv(out_path, index=False)
    print(f"[RF Matrix] shape={df.shape}  saved to {out_path}")
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 6. CONVENIENCE: load multiple GridLAB-D CSVs of the same type and concatenate
# ──────────────────────────────────────────────────────────────────────────────


def load_all_csvs(pattern: str) -> pd.DataFrame:
    """
    Glob a directory for all CSVs matching pattern and concatenate.
    Example: load_all_csvs("data/raw/substation_*.csv")
    """
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files found matching: {pattern}")
    frames = [_read_gridlabd(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    print(f"Loaded {len(files)} file(s) → {len(df)} rows from pattern '{pattern}'")
    return df


if __name__ == "__main__":
    # ── Quick smoke test ─────────────────────────────────────────────────────
    # Generates tiny synthetic CSVs matching each format and runs preprocessing
    import tempfile, os

    # Synthetic substation
    sub_data = (
        "2967960.0,1640220.0,minutes,hour_of_day,day_of_week,fault_label,fault_type\n"
    )
    for i in range(200):
        sub_data += f"2967960.0,1640220.0,{i}.0,{(i%24)/24:.4f},{i%7},{'1' if i>180 else '0'},{'overload' if i>180 else 'normal'}\n"

    # Synthetic transformer
    xfmr_data = "40057.5,100745,minutes,hour_of_day,day_of_week,winding_temp_C,load_pct,thermal_margin_C,fault_label,fault_type\n"
    for i in range(200):
        temp = 35 + (i / 200) * 80
        load = 10 + (i / 200) * 100
        margin = 140 - temp
        xfmr_data += f"34813.9,100736,{i}.0,{(i%24)/24:.4f},{i%7},{temp:.1f},{load:.1f},{margin:.1f},{'1' if temp>100 else '0'},{'thermal_fault' if temp>100 else 'normal'}\n"

    # Synthetic meter
    meter_data = "6446,11224.8,minutes,hour_of_day,day_of_week,feeder_power_W,total_reported_W,loss_ratio,excess_loss_pct,theft_flag_raw,end_feeder_voltage_V,voltage_deviation_pct,undervoltage_flag,fault_label,fault_type\n"
    for i in range(200):
        theft = 1 if i > 170 else 0
        meter_data += f"5985.22,11223.4,{i*15}.0,{(i%96)/96:.4f},{i%7},5000.0,{4000 if theft else 4900}.0,{0.2 if theft else 0.02:.2f},{20.0 if theft else 0.0:.1f},{theft},239.6,0.0,0,{theft},{'theft' if theft else 'normal'}\n"

    with tempfile.TemporaryDirectory() as tmp:
        sub_path = os.path.join(tmp, "substation.csv")
        xfmr_path = os.path.join(tmp, "transformer.csv")
        mtr_path = os.path.join(tmp, "meter.csv")

        open(sub_path, "w").write(sub_data)
        open(xfmr_path, "w").write(xfmr_data)
        open(mtr_path, "w").write(meter_data)

        print("=" * 60)
        print("PREPROCESSING SMOKE TEST")
        print("=" * 60)
        preprocess_substation(sub_path)
        preprocess_transformer(xfmr_path)
        preprocess_meter_gridlabd(mtr_path)
        print("\nAll preprocessing passed ✓")
