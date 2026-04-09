import argparse
import sys
import traceback
from pathlib import Path
import joblib
import pandas as pd
from Logger import StepLogger
from Assets_loader import detect_asset_type, load_csv_safe
from Handle_Missing import handle_missing
from Windows import make_windows, save_windows
from Class_balance_report import class_balance_report
from Preprocess import process_substation
from Preprocess import process_transformer
from Preprocess import process_meter


HERE         = Path(__file__).resolve().parent        
PROJECT_ROOT = HERE.parent                           
DEFAULT_DATA = PROJECT_ROOT / "dataset"
SCALERS_OUT  = HERE / "scalers.pkl"


_R = "\033[91m";  _G = "\033[92m";  _Y = "\033[93m"
_B = "\033[94m";  _W = "\033[0m";   _BOLD = "\033[1m"

def _c(color, text): return f"{color}{text}{W}" if sys.stdout.isatty() else text
W = _W  # reset


WINDOW_CFG = {
    "substation":  dict(window_size=60,  stride=5,  out="windows_sub.npz"),
    "transformer": dict(window_size=120, stride=10, out="windows_trans.npz"),
    "meter":       dict(window_size=8,   stride=2,  out="windows_meter.npz"),
}



def run(data_dir: str = None, dry_run: bool = False):
    """
    Full pipeline. Call this from CLI or import and call from training script.
    """
    global log
    log = StepLogger(total_steps=6)

    data_path = Path(data_dir) if data_dir else DEFAULT_DATA

    print(f"\n{'═'*60}")
    print(f"  {_BOLD}SmartGrid AI — Preprocessing Pipeline{W}")
    print(f"{'═'*60}")
    print(f"  Data dir  : {data_path}")
    print(f"  Scalers   : {SCALERS_OUT}")
    print(f"  Dry run   : {dry_run}")

    # ── STEP 1: Discover CSVs ───────────────────────────────────────────────
    log.step("Discovering CSVs in dataset/")

    csv_files = sorted(data_path.glob("*.csv"))
    if not csv_files:
        log.error(f"No CSV files found in {data_path}.\n"
                  f"  Put your GridLAB-D and Kaggle CSVs into {data_path}/\n"
                  f"  Or run: python dataset/generate_test_data.py",
                  fatal=True)

    routed = {"substation": [], "transformer": [], "meter_glab": [],
              "meter_kaggle": [], "unknown": []}

    for path in csv_files:
        df = load_csv_safe(str(path))
        if df is None:
            continue
        atype = detect_asset_type(df, path.name)
        # Separate GridLAB-D meter (has feeder_power_W) from Kaggle meter (has t_kWh)
        if atype == "meter":
            if 't_kWh' in df.columns or 'x_Timestamp' in df.columns:
                routed["meter_kaggle"].append(df)
                log.info(f"  {path.name} → {_G}meter (Kaggle){W}")
            else:
                routed["meter_glab"].append(df)
                log.info(f"  {path.name} → {_G}meter (GridLAB-D){W}")
        elif atype in routed:
            routed[atype].append(df)
            log.info(f"  {path.name} → {_G}{atype}{W}")
        else:
            routed["unknown"].append((path.name, df))
            log.warn(f"  {path.name} → {_Y}unknown type — skipped{W}")

    for k in ["substation", "transformer"]:
        if not routed[k]:
            log.warn(f"No {k} CSVs detected. "
                     f"Rename files to include '{k}' or add expected columns.")

    # ── STEP 2: Parse complex columns ────────────────────────────────────────
    log.step("Parsing GridLAB-D complex-number columns")
    # (Done inside per-asset processors — logged there)
    log.info("Complex parsing delegated to per-asset processors (Step 3)")

    # ── STEP 3: Process each asset type ────────────────────────────────────
    log.step("Per-asset processing (complex parse + missing values + features)")
    all_scalers = {}

    sub_result   = process_substation(routed["substation"],  all_scalers, dry_run)
    xfmr_result  = process_transformer(routed["transformer"], all_scalers, dry_run)
    meter_result = process_meter(routed["meter_glab"], routed["meter_kaggle"],
                                  all_scalers, dry_run)

    # ── STEP 4: Save scalers ────────────────────────────────────────────────
    log.step("Saving normalisation scalers → preprocessing/scalers.pkl")

    if not all_scalers:
        log.warn("No scalers were fitted (no data was processed).")
    else:
        HERE.mkdir(parents=True, exist_ok=True)
        joblib.dump(all_scalers, SCALERS_OUT)
        kb = SCALERS_OUT.stat().st_size // 1024
        log.ok(f"Saved scalers.pkl  ({kb} KB)  keys={list(all_scalers.keys())}")

        # Print scaler summary
        for key, info in all_scalers.items():
            log.info(f"  [{key}] {len(info['columns'])} features  "
                     f"min_range=[{min(info['data_min']):.3f}..{max(info['data_min']):.3f}]  "
                     f"max_range=[{min(info['data_max']):.3f}..{max(info['data_max']):.3f}]")

    # ── STEP 5: Save windows ────────────────────────────────────────────────
    log.step("Creating and saving sliding windows (.npz files)")

    if not dry_run:
        for result, name in [
            (sub_result,   "substation"),
            (xfmr_result,  "transformer"),
            (meter_result, "meter"),
        ]:
            if result and "X" in result:
                out_path = data_path / WINDOW_CFG[name]["out"]
                save_windows(result, out_path, name)
    else:
        log.info("[DRY RUN] No .npz files written.")

    # ── STEP 6: Class balance report ─────────────────────────────────────────
    log.step("Class balance report")

    label_map = {0: "normal", 1: "fault"}

    for result, name in [
        (sub_result,   "substation"),
        (xfmr_result,  "transformer"),
        (meter_result, "meter"),
    ]:
        if result and "y" in result:
            class_balance_report(
                y            = result["y"],
                label_names  = label_map,
                dataset_name = name,
                fault_type_series = result.get("fault_types")
            )


    log.summary()


    if not log.errors:
        msg = ("✅ Preprocessing complete — windows ready in dataset/\n"
               f"   windows_sub.npz   : {sub_result['X'].shape   if sub_result  and 'X' in sub_result  else 'SKIPPED'}\n"
               f"   windows_trans.npz : {xfmr_result['X'].shape  if xfmr_result and 'X' in xfmr_result else 'SKIPPED'}\n"
               f"   windows_meter.npz : {meter_result['X'].shape if meter_result and 'X' in meter_result else 'SKIPPED'}\n"
               f"   scalers.pkl       : {list(all_scalers.keys())}\n\n"
               "   📢 @Dhruv   — sub and transformer windows are ready.\n"
               "   📢 @Ruchit  — meter windows + scalers are ready.\n")
        print(f"\n{_G}{_BOLD}{msg}{W}")
    else:
        print(f"\n{_R}Preprocessing finished with {len(log.errors)} error(s). "
              f"Fix above before running model training.{W}")

    return {
        "substation":  sub_result,
        "transformer": xfmr_result,
        "meter":       meter_result,
        "scalers":     all_scalers,
    }




def parse_args():
    p = argparse.ArgumentParser(
        description="SmartGrid AI Preprocessing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python preprocessing/preprocess.py
  python preprocessing/preprocess.py --data_dir data/raw/
  python preprocessing/preprocess.py --dry_run
  python preprocessing/preprocess.py --data_dir dataset/ --dry_run
        """
    )
    p.add_argument("--data_dir", type=str, default=None,
                   help=f"Directory containing CSV files (default: {DEFAULT_DATA})")
    p.add_argument("--dry_run", action="store_true",
                   help="Validate + normalise only — do NOT write .npz files")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        run(data_dir=args.data_dir, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print(f"\n{_Y}Interrupted by user.{W}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{_R}FATAL: Unhandled exception:{W}")
        traceback.print_exc()
        sys.exit(1)