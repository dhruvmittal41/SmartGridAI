import pandas as pd
import numpy as np
from Logger import log
from Complex_Parser import parse_complex_columns
from Handle_Missing import handle_missing
from Normalisation import normalise
from Class_balance_report import class_balance_report
from Windows import make_windows



WINDOW_CFG = {
    "substation":  dict(window_size=60,  stride=5,  out="windows_sub.npz"),
    "transformer": dict(window_size=120, stride=10, out="windows_trans.npz"),
    "meter":       dict(window_size=8,   stride=2,  out="windows_meter.npz"),
}



def process_substation(frames: list[pd.DataFrame],
                       all_scalers: dict,
                       dry_run: bool = False) -> dict | None:
    """
    Full pipeline for substation DataFrames.
    Complex cols: voltage_AN/BN/CN, current_A/B/C
    Returns dict with X, y, feature_cols, fault_types for downstream use.
    """
    if not frames:
        log.warn("No substation CSVs found — skipping.")
        return None

    df = pd.concat(frames, ignore_index=True)
    log.info(f"Merged {len(frames)} substation file(s) → {len(df)} rows")

    # ── Complex parse ────────────────────────────────────────────────────────
    complex_cols = [c for c in df.columns
                    if any(k in c.lower() for k in ['voltage','current'])]
    df = parse_complex_columns(df, complex_cols)

    # ── Timestamp index (helps interpolation) ───────────────────────────────
    if 'timestamp' in df.columns:
        try:
            df.index = pd.to_datetime(df['timestamp'])
            df = df.drop(columns=['timestamp'])
        except Exception:
            pass

    # ── Missing values ───────────────────────────────────────────────────────
    df = handle_missing(df)

    # ── Feature cols ─────────────────────────────────────────────────────────
    META = {'fault_label','fault_type','fault_class'}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c.lower() not in {m.lower() for m in META}]
    log.info(f"Feature columns ({len(feature_cols)}): {feature_cols}")

    # ── Normalise ────────────────────────────────────────────────────────────
    df = normalise(df, feature_cols, "substation", all_scalers, fit=True)

    if dry_run:
        log.info("[DRY RUN] Skipping window creation for substation.")
        return {"df": df, "feature_cols": feature_cols}

    # ── Windows ──────────────────────────────────────────────────────────────
    cfg = WINDOW_CFG["substation"]
    try:
        X, y = make_windows(df, cfg["window_size"], cfg["stride"], "fault_label", feature_cols)
    except ValueError as e:
        log.error(f"[Substation] make_windows failed: {e}", fatal=False)
        return None

    fault_types = None
    if 'fault_type' in df.columns:
        # Align fault_type with windows (take last-timestep value per window)
        n_windows  = X.shape[0]
        ft_arr     = df['fault_type'].values
        stride     = cfg['stride']
        ws         = cfg['window_size']
        fault_types = pd.Series([ft_arr[min(i*stride + ws - 1, len(ft_arr)-1)]
                                  for i in range(n_windows)])

    log.ok(f"Substation windows: X={X.shape}  y={y.shape}")
    return {"X": X, "y": y, "feature_cols": feature_cols,
            "fault_types": fault_types, "cfg": cfg}


def process_transformer(frames: list[pd.DataFrame],
                        all_scalers: dict,
                        dry_run: bool = False) -> dict | None:
    if not frames:
        log.warn("No transformer CSVs found — skipping.")
        return None

    df = pd.concat(frames, ignore_index=True)
    log.info(f"Merged {len(frames)} transformer file(s) → {len(df)} rows")

    complex_cols = [c for c in df.columns
                    if any(k in c.lower() for k in ['voltage','current'])]
    df = parse_complex_columns(df, complex_cols)

    if 'timestamp' in df.columns:
        try:
            df.index = pd.to_datetime(df['timestamp'])
            df = df.drop(columns=['timestamp'])
        except Exception:
            pass

    df = handle_missing(df)

    # ── Physics-derived features ─────────────────────────────────────────────
    if 'winding_temp_C' in df.columns and 'thermal_margin_C' in df.columns:
        df['thermal_margin_C'] = df['thermal_margin_C'].clip(lower=0.1)
    if 'winding_temp_C' in df.columns and 'load_pct' in df.columns:
        df['thermal_stress'] = (df['load_pct'] ** 2) / df['thermal_margin_C'].clip(lower=0.1)
        df['temp_grad_5']    = df['winding_temp_C'].diff(5).fillna(0)
        log.ok("Derived 'thermal_stress' and 'temp_grad_5' features")

    META = {'fault_label','fault_type','fault_class'}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c.lower() not in {m.lower() for m in META}]
    log.info(f"Feature columns ({len(feature_cols)}): {feature_cols}")

    df = normalise(df, feature_cols, "transformer", all_scalers, fit=True)

    if dry_run:
        return {"df": df, "feature_cols": feature_cols}

    cfg = WINDOW_CFG["transformer"]
    try:
        X, y = make_windows(df, cfg["window_size"], cfg["stride"], "fault_label", feature_cols)
    except ValueError as e:
        log.error(f"[Transformer] make_windows failed: {e}", fatal=False)
        return None

    fault_types = None
    if 'fault_type' in df.columns:
        ft_arr = df['fault_type'].values
        stride, ws = cfg['stride'], cfg['window_size']
        fault_types = pd.Series([ft_arr[min(i*stride + ws - 1, len(ft_arr)-1)]
                                  for i in range(X.shape[0])])

    log.ok(f"Transformer windows: X={X.shape}  y={y.shape}")
    return {"X": X, "y": y, "feature_cols": feature_cols,
            "fault_types": fault_types, "cfg": cfg}


def process_meter(frames_gridlabd: list[pd.DataFrame],
                  frames_kaggle:   list[pd.DataFrame],
                  all_scalers: dict,
                  dry_run: bool = False) -> dict | None:
    """
    Handles both GridLAB-D feeder CSVs and Kaggle-style per-meter CSVs.
    Merges them into a single frame with a unified feature set.
    """
    frames = []

    # ── GridLAB-D feeder ─────────────────────────────────────────────────────
    for df in frames_gridlabd:
        complex_cols = [c for c in df.columns
                        if any(k in c.lower() for k in ['voltage','power','feeder'])]
        df = parse_complex_columns(df, complex_cols)
        if 'timestamp' in df.columns:
            try:
                df.index = pd.to_datetime(df['timestamp'])
                df = df.drop(columns=['timestamp'], errors='ignore')
            except Exception:
                pass
        # Derived features
        if 'feeder_power_W' in df.columns and 'total_reported_W' in df.columns:
            df['apparent_loss_W'] = df['feeder_power_W'] - df['total_reported_W']
            df['log_excess']      = np.log1p(df.get('excess_loss_pct', 0).clip(lower=0))
            df['loss_trend']      = df.get('loss_ratio', pd.Series(0, index=df.index)).diff(5).fillna(0)
        frames.append(df)

    # ── Kaggle smart meters ───────────────────────────────────────────────────
    for df in frames_kaggle:
        if 'x_Timestamp' in df.columns:
            try:
                df.index = pd.to_datetime(df['x_Timestamp'])
                df = df.drop(columns=['x_Timestamp'], errors='ignore')
            except Exception:
                pass
        if 't_kWh' in df.columns:
            df = df.rename(columns={'t_kWh': 'kWh'})
        if 'kWh' in df.columns and 'Voltage' in df.columns and 'Current' in df.columns:
            df['apparent_VA']  = df['Voltage'] * df['Current']
            df['active_W']     = df['kWh'] * 1e6 / 180     # 3-min intervals → W
            df['pf_est']       = (df['active_W'] / df['apparent_VA'].clip(lower=0.01)).clip(0, 1)
            df['voltage_dev']  = (df['Voltage'] - 230.0) / 230.0
            df['freq_dev']     = df.get('Frequency', 50.0) - 50.0
            # Per-meter rolling z-score (theft signal)
            if 'meter' in df.columns:
                df['kwh_zscore'] = df.groupby('meter')['kWh'].transform(
                    lambda x: ((x - x.rolling(20, min_periods=1).mean()) /
                               x.rolling(20, min_periods=1).std().fillna(0.01))
                )
            else:
                df['kwh_zscore'] = 0.0
            df = df.drop(columns=['meter'], errors='ignore')
            log.ok("Derived Kaggle features: apparent_VA, pf_est, voltage_dev, kwh_zscore")

        # Synthesise fault_label from kwh_zscore if not present
        if 'fault_label' not in df.columns:
            if 'kwh_zscore' in df.columns:
                df['fault_label'] = (df['kwh_zscore'].abs() > 3.0).astype(int)
                df['fault_type']  = np.where(df['fault_label'] == 1, 'theft_suspected', 'normal')
                log.warn("Kaggle CSV has no fault_label — synthesised from kwh_zscore > 3.0")
            else:
                df['fault_label'] = 0
                df['fault_type']  = 'normal'
                log.warn("Kaggle CSV has no fault_label — assuming all normal")
        frames.append(df)

    if not frames:
        log.warn("No meter CSVs found — skipping.")
        return None

    # Impute per-frame BEFORE concat so cross-source NaNs (cols absent in one
    # source but present in another) are not flagged as measurement gaps.
    frames = [handle_missing(f) for f in frames]

    df = pd.concat(frames, ignore_index=True)
    log.info(f"Merged {len(frames)} meter file(s) → {len(df)} rows")

    # Cross-source structural NaNs (col exists in GridLAB-D but not Kaggle) → 0
    cross_nan = [c for c in df.select_dtypes(include=["number"]).columns
                 if df[c].isna().mean() > 0.20]
    if cross_nan:
        df[cross_nan] = df[cross_nan].fillna(0)
        log.info(f"Cross-source NaN cols filled with 0: {cross_nan}")

    META = {'fault_label','fault_type','fault_class','meter'}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c.lower() not in {m.lower() for m in META}]
    log.info(f"Feature columns ({len(feature_cols)}): {feature_cols}")

    df = normalise(df, feature_cols, "meter", all_scalers, fit=True)

    if dry_run:
        return {"df": df, "feature_cols": feature_cols}

    cfg = WINDOW_CFG["meter"]
    try:
        X, y = make_windows(df, cfg["window_size"], cfg["stride"], "fault_label", feature_cols)
    except ValueError as e:
        log.error(f"[Meter] make_windows failed: {e}", fatal=False)
        return None

    fault_types = None
    if 'fault_type' in df.columns:
        ft_arr = df['fault_type'].values
        stride, ws = cfg['stride'], cfg['window_size']
        fault_types = pd.Series([ft_arr[min(i*stride + ws - 1, len(ft_arr)-1)]
                                  for i in range(X.shape[0])])

    log.ok(f"Meter windows: X={X.shape}  y={y.shape}")
    return {"X": X, "y": y, "feature_cols": feature_cols,
            "fault_types": fault_types, "cfg": cfg}