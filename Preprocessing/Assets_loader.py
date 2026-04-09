import pandas as pd
from pathlib import Path
from Logger import log


def detect_asset_type(df: pd.DataFrame, filename: str) -> str:
    """
    Heuristically determine whether a CSV is substation / transformer / meter.

    Priority order:
    1. Filename keywords (most reliable when naming convention is followed)
    2. Column set matching
    3. Return 'unknown' if neither matches
    """
    fname = filename.lower()

    # Filename-based detection (fast path)
    if any(k in fname for k in ["sub", "substation"]):
        return "substation"
    if any(k in fname for k in ["trans", "transformer", "xfmr"]):
        return "transformer"
    if any(
        k in fname
        for k in ["meter", "feeder", "smart", "kaggle", "bareilly", "mathura", "india"]
    ):
        return "meter"

    # Column-based detection (fallback)
    cols = set(c.lower() for c in df.columns)
    if any(c in cols for c in ["winding_temp_c", "winding_temp", "oil_temp_c"]):
        return "transformer"
    if any(
        c in cols
        for c in [
            "t_kwh",
            "feeder_power_w",
            "total_reported_w",
            "loss_ratio",
            "theft_flag_raw",
        ]
    ):
        return "meter"
    if any(
        c in cols
        for c in [
            "voltage_an",
            "voltage_bn",
            "voltage_cn",
            "current_a",
            "power_factor",
            "frequency_hz",
        ]
    ):
        return "substation"

    return "unknown"


def load_csv_safe(path: str) -> pd.DataFrame | None:
    """
    Load a CSV with useful error messages.
    Returns None if the file is empty or unparseable.
    """
    try:
        df = pd.read_csv(path, low_memory=False)
    except pd.errors.EmptyDataError:
        log.error(f"Empty file: {path}")
        return None
    except pd.errors.ParserError as e:
        log.error(f"CSV parse error in {Path(path).name}: {e}")
        return None
    except Exception as e:
        log.error(f"Cannot read {Path(path).name}: {e}")
        return None

    if df.empty:
        log.warn(f"{Path(path).name}: 0 rows after load")
        return None

    log.info(f"{Path(path).name}: {len(df)} rows × {len(df.columns)} cols")
    return df
