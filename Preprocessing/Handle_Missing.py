import pandas as pd
import numpy as np
from Logger import log


def _detect_col_category(col: str) -> str:
    """Returns 'voltage_current', 'temperature', or 'other'."""
    low = col.lower()
    if any(k in low for k in ["voltage", "current", "power", "freq"]):
        return "voltage_current"
    if any(k in low for k in ["temp", "thermal", "oil"]):
        return "temperature"
    return "other"


def handle_missing(
    df: pd.DataFrame, ffill_limit: int = 5, interp_limit: int = 20
) -> pd.DataFrame:
    """
    Per-column missing value strategy:

    voltage / current columns → forward-fill (max `ffill_limit` consecutive gaps).
        Rationale: short measurement dropouts; last valid reading is best estimate.

    temperature columns → time-based linear interpolation (max `interp_limit` gaps).
        Rationale: temperature changes slowly; linear fill preserves physical realism.

    other numeric columns → forward-fill then backward-fill as fallback.

    Any column with > 30% missing after imputation is flagged as an error.
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude_meta = {
        "fault_label",
        "fault_type",
        "meter",
        "theft_flag_raw",
        "undervoltage_flag",
        "tap_position",
    }

    report_rows = []
    for col in numeric_cols:
        if col in exclude_meta:
            continue

        n_before = df[col].isna().sum()
        if n_before == 0:
            continue

        cat = _detect_col_category(col)

        if cat == "voltage_current":
            df[col] = df[col].ffill(limit=ffill_limit)
            strategy = f"forward-fill (limit={ffill_limit})"
        elif cat == "temperature":
            if pd.api.types.is_datetime64_any_dtype(df.index):
                df[col] = df[col].interpolate(method="time", limit=interp_limit)
            else:
                df[col] = df[col].interpolate(method="linear", limit=interp_limit)
            strategy = f"linear-interpolate (limit={interp_limit})"
        else:
            df[col] = df[col].ffill().bfill()
            strategy = "ffill + bfill"

        n_after = df[col].isna().sum()
        pct_remaining = n_after / len(df) * 100
        report_rows.append((col, n_before, n_after, strategy))

        if pct_remaining > 30:
            log.error(
                f"'{col}': {pct_remaining:.1f}% NaN remaining after imputation. "
                f"Check your CSV for large data gaps."
            )
        elif n_after > 0:
            log.warn(
                f"'{col}': {n_after} NaN remain after {strategy} "
                f"(original had {n_before})"
            )
        else:
            log.ok(f"'{col}': {n_before} gaps filled via {strategy}")

    return df
