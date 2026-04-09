import pandas as pd
import numpy as np
from Logger import log
import sys

MIN_CLASS_SAMPLES = 50

_R = "\033[91m"
_G = "\033[92m"
_Y = "\033[93m"
_W = "\033[0m"


def _c(color, text):
    return f"{color}{text}{W}" if sys.stdout.isatty() else text


W = _W


def class_balance_report(
    y: np.ndarray,
    label_names: dict,
    dataset_name: str,
    fault_type_series: pd.Series = None,
):
    """
    Prints class counts with visual bar chart.
    Flags any class with < MIN_CLASS_SAMPLES samples.
    Also prints fault type breakdown if available.
    """
    log.section(f"Class Balance — {dataset_name}")
    unique, counts = np.unique(y, return_counts=True)
    total = len(y)

    max_count = counts.max()
    bar_width = 30

    print(f"  {'Class':<20} {'Count':>7}  {'%':>5}  Bar")
    print(f"  {'─'*20} {'─'*7}  {'─'*5}  {'─'*bar_width}")

    for u, c in zip(unique, counts):
        name = label_names.get(int(u), f"class_{u}")
        pct = c / total * 100
        bar_len = int(c / max_count * bar_width)
        bar = ("█" * bar_len).ljust(bar_width)
        color = _G if name == "normal" else _Y if c >= MIN_CLASS_SAMPLES else _R
        flag = (
            ""
            if c >= MIN_CLASS_SAMPLES
            else f"  ← {_R}⚠ BELOW {MIN_CLASS_SAMPLES} SAMPLES{W}"
        )
        print(f"  {name:<20} {c:>7,}  {pct:>4.1f}%  {color}{bar}{W}{flag}")

        if c < MIN_CLASS_SAMPLES:
            log.warn(
                f"{dataset_name} — '{name}' has only {c} windows (min: {MIN_CLASS_SAMPLES}). "
                "Consider: reduce stride to augment, or merge more CSV files."
            )

    print(f"  {'─'*20} {'─'*7}")
    print(f"  {'TOTAL':<20} {total:>7,}\n")

    if fault_type_series is not None:
        breakdown = fault_type_series.value_counts()
        log.section(f"Fault type breakdown — {dataset_name}")
        for ft, cnt in breakdown.items():
            print(f"    {ft:<28} {cnt:>5,}")
