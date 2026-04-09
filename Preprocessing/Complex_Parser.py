import numpy as np
import pandas as pd
import re
from Logger import log


_COMPLEX_RE = re.compile(
    r"([+-]?[\d.]+(?:[eE][+-]?\d+)?)"  # real part
    r"(?:([+-][\d.]+(?:[eE][+-]?\d+)?)j)?"  # imaginary part
)


def parse_complex_magnitude(value) -> float:
    """
    Parse a GridLAB-D complex string and return the magnitude.

    Handles all of these formats:
      "+2.30993e+02+9.27976e-01j"  →  230.996  (sqrt(real²+imag²))
      "+2.30993e+02"               →  230.993  (pure real — no imaginary part)
      "230.5"                      →  230.5
      "+4.95852e+00-6.88011e-01j"  →  5.006
      NaN / None / ""              →  NaN

    Returns
    -------
    float: magnitude, or np.nan if unparseable.
    """
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if not s:
        return np.nan

    # Strip trailing unit suffixes common in GridLAB-D: ' V', ' A', ' W', ' kW', ' VA' etc.
    s = re.sub(r"\s+[A-Za-z]+$", "", s).strip()

    m = _COMPLEX_RE.match(s)
    if not m:
        # Last-ditch: try direct float cast
        try:
            return float(s)
        except ValueError:
            return np.nan

    real_str, imag_str = m.group(1), m.group(2)
    try:
        real = float(real_str)
        imag = float(imag_str) if imag_str else 0.0
        return float(np.sqrt(real**2 + imag**2))
    except (ValueError, TypeError):
        return np.nan


def parse_complex_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Apply `parse_complex_magnitude` to each column in `cols`.
    Also tries every column that *looks* complex (contains 'j') if not in cols.
    Reports how many values were successfully parsed vs turned to NaN.
    """
    df = df.copy()

    # Auto-detect additional complex columns not in explicit list
    auto_complex = [
        c
        for c in df.columns
        if c not in cols
        and df[c].dtype == object
        and df[c].dropna().astype(str).str.contains("j", regex=False).any()
    ]
    all_cols = list(dict.fromkeys(cols + auto_complex))  # dedupe, preserve order

    for col in all_cols:
        if col not in df.columns:
            log.warn(f"Column '{col}' not found — skipping complex parse")
            continue

        original = df[col].copy()
        df[col] = df[col].apply(parse_complex_magnitude)
        n_total = len(df[col])
        n_nan = df[col].isna().sum()
        n_parsed = n_total - n_nan

        if n_nan > n_total * 0.10:
            log.warn(
                f"'{col}': {n_nan}/{n_total} values → NaN after complex parse "
                f"(>{10}% loss). Check format."
            )
        else:
            log.ok(f"'{col}': {n_parsed}/{n_total} values parsed as magnitudes")

    return df
