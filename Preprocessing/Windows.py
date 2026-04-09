import pandas as pd
import numpy as np
from pathlib import Path
from Logger import log


def make_windows(
    df: pd.DataFrame,
    window_size: int,
    stride: int,
    label_col: str,
    feature_cols: list[str] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create overlapping sliding windows over a time-series DataFrame.

    Parameters
    ----------
    df           : normalised DataFrame (rows = timesteps)
    window_size  : number of consecutive rows per window  (e.g. 60)
    stride       : step between windows                   (e.g. 5 for augmentation)
    label_col    : column name of binary or multi-class label
    feature_cols : which columns to include as features (None = all numeric
                   except label columns and meta columns)

    Returns
    -------
    X : np.ndarray  shape (N_windows, window_size, n_features)  float32
    y : np.ndarray  shape (N_windows,)                          int32

    Label assignment: the label of the LAST timestep in each window.
    This is the standard convention — the model predicts what happens
    at the end of the observed window.

    Raises
    ------
    ValueError  if df is shorter than window_size (cannot make even one window).
    """
    EXCLUDE_ALWAYS = {
        "fault_label",
        "fault_type",
        "fault_label_type",
        "fault_class",
        "theft_flag_raw",
        "undervoltage_flag",
        "meter",
        "timestamp",
        "x_Timestamp",
        "t_kWh",  # Kaggle ts/label cols
    }

    if label_col not in df.columns:
        raise ValueError(
            f"make_windows: label_col='{label_col}' not found in DataFrame.\n"
            f"  Available columns: {list(df.columns)}"
        )

    if len(df) < window_size:
        raise ValueError(
            f"make_windows: DataFrame has {len(df)} rows but window_size={window_size}.\n"
            f"  Need at least {window_size} rows. "
            f"Merge more CSV files or reduce window_size."
        )

    if feature_cols is None:
        feature_cols = [
            c
            for c in df.select_dtypes(include=[np.number]).columns
            if c.lower() not in {x.lower() for x in EXCLUDE_ALWAYS} and c != label_col
        ]

    if not feature_cols:
        raise ValueError(
            "make_windows: No feature columns found after exclusions.\n"
            f"  All numeric columns: {list(df.select_dtypes(include=[np.number]).columns)}"
        )

    X_arr = df[feature_cols].values.astype(np.float32)
    y_arr = df[label_col].values.astype(np.int32)

    n_windows = max(0, (len(df) - window_size) // stride + 1)
    if n_windows == 0:
        raise ValueError(
            f"make_windows: stride={stride} + window_size={window_size} "
            f"yields 0 windows from {len(df)} rows."
        )

    X_out = np.empty((n_windows, window_size, len(feature_cols)), dtype=np.float32)
    y_out = np.empty(n_windows, dtype=np.int32)

    for i in range(n_windows):
        start = i * stride
        end = start + window_size
        X_out[i] = X_arr[start:end]
        y_out[i] = y_arr[end - 1]  # label = last timestep

    return X_out, y_out





def save_windows(result: dict, out_path: Path, asset_name: str):
    """Save X, y and metadata to .npz. Verifies file after write."""
    if result is None or "X" not in result:
        log.warn(f"No window data to save for {asset_name}")
        return

    X, y = result["X"], result["y"]

    np.savez_compressed(
        str(out_path),
        X             = X,
        y             = y,
        feature_cols  = np.array(result.get("feature_cols", []), dtype=object),
        window_size   = np.array([result["cfg"]["window_size"]]),
        stride        = np.array([result["cfg"]["stride"]]),
    )

    # Verify round-trip
    check = np.load(str(out_path), allow_pickle=True)
    assert check["X"].shape == X.shape, "Save verification failed: shape mismatch"
    assert check["y"].shape == y.shape

    kb = out_path.stat().st_size // 1024
    log.ok(f"Saved {out_path.name}  ({kb:,} KB)  X={X.shape}  y={y.shape}")