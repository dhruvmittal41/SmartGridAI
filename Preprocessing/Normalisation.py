import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from Logger import log


def normalise(
    df: pd.DataFrame,
    feature_cols: list[str],
    scaler_key: str,
    all_scalers: dict,
    fit: bool = True,
) -> pd.DataFrame:
    """
    MinMaxScaler per feature column.

    Parameters
    ----------
    df           : input DataFrame
    feature_cols : columns to normalise (must all be numeric)
    scaler_key   : identifier stored in all_scalers dict (e.g. "substation")
    all_scalers  : shared dict accumulating all scalers — saved at the end
    fit          : True = fit+transform (training), False = transform only (inference)

    Returns DataFrame with feature_cols replaced by [0,1] values.
    Notes:
      - Columns with zero variance are skipped (constant feature — useless).
      - Original dtypes are preserved on non-feature columns.
    """
    df = df.copy()

    # Drop constant columns
    zero_var = [c for c in feature_cols if c in df.columns and df[c].nunique() <= 1]
    if zero_var:
        log.warn(f"[{scaler_key}] Constant columns removed: {zero_var}")
        feature_cols = [c for c in feature_cols if c not in zero_var]

    valid_cols = [c for c in feature_cols if c in df.columns]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        log.warn(f"[{scaler_key}] Columns not in DataFrame: {missing}")

    if not valid_cols:
        log.error(f"[{scaler_key}] No valid feature columns to normalise.")
        return df

    X = df[valid_cols].values.astype(np.float32)

    if fit:
        scaler = MinMaxScaler(feature_range=(0, 1))
        X_scaled = scaler.fit_transform(X)
        all_scalers[scaler_key] = {
            "scaler": scaler,
            "columns": valid_cols,
            "data_min": scaler.data_min_.tolist(),
            "data_max": scaler.data_max_.tolist(),
        }
    else:
        if scaler_key not in all_scalers:
            log.error(
                f"[{scaler_key}] Scaler not found. Run in fit=True mode first.",
                fatal=True,
            )
        info = all_scalers[scaler_key]
        scaler = info["scaler"]
        # Align columns with what was fitted
        X_aligned = np.zeros((len(df), len(info["columns"])), dtype=np.float32)
        for i, col in enumerate(info["columns"]):
            if col in df.columns:
                X_aligned[:, i] = df[col].values
        X_scaled = scaler.transform(X_aligned)
        valid_cols = info["columns"]

    df[valid_cols] = X_scaled
    log.ok(
        f"[{scaler_key}] Normalised {len(valid_cols)} features "
        f"{'(fitted)' if fit else '(transform-only)'}"
    )
    return df
