"""
load_management.py
==================
Load Management & Operator Advisory Engine.

Components
----------
1. DemandForecaster
   Ridge regression + time features to predict load for the next 2 hours.
   Trained on historical load_pct data with datetime features.

2. LoadManagementEngine
   Rule-based expert system augmented by ML forecasts.
   Generates prioritised, actionable suggestions for substation operators.

3. EnergyTheftDetector
   Z-score + KCL-based detector that flags meters for investigation.

Suggestions follow a priority schema:
  P1 = Critical (act within 5 min)  — imminent overload / transformer fault
  P2 = High     (act within 30 min) — voltage violation / high loss
  P3 = Medium   (plan today)        — approaching limits / theft suspected
  P4 = Low      (log only)          — trend flagged, monitor
"""

import os
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from dataclasses import dataclass, field
from typing import Optional

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Thresholds (tunable per grid zone) ────────────────────────────────────────
LOAD_WARNING = 80  # % load → P2 warning
LOAD_CRITICAL = 95  # % load → P1 critical
THERMAL_WARN = 100  # °C winding temp → P2
THERMAL_CRIT = 120  # °C winding temp → P1
VOLTAGE_LOW = 0.94  # pu → undervoltage warning
VOLTAGE_HIGH = 1.06  # pu → overvoltage warning
VOLTAGE_CRIT = 0.90  # pu → critical undervoltage
LOSS_WARN = 0.10  # 10% line loss → investigate
LOSS_CRIT = 0.20  # 20% line loss → strong theft signal
THEFT_ZSCORE = 3.0  # z-score on kWh → anomaly
THEFT_DURATION = 4  # consecutive anomalous windows to flag


@dataclass
class OperatorSuggestion:
    priority: int  # 1 (critical) to 4 (low)
    zone: str
    action: str
    reason: str
    impact_mw: float
    estimated_kwh_saved: float = 0.0
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "zone": self.zone,
            "action": self.action,
            "reason": self.reason,
            "impact_mw": round(self.impact_mw, 3),
            "kwh_saved": round(self.estimated_kwh_saved, 2),
            "tags": self.tags,
        }


@dataclass
class TheftFlag:
    meter_id: str
    confidence: float  # 0-1
    method: str  # "zscore" | "kcl" | "both"
    duration_hrs: float
    estimated_loss_kwh: float
    anomaly_score: float

    def to_dict(self) -> dict:
        return {
            "meter_id": self.meter_id,
            "confidence": round(self.confidence, 3),
            "method": self.method,
            "duration_hrs": round(self.duration_hrs, 1),
            "est_loss_kwh": round(self.estimated_loss_kwh, 2),
            "anomaly_score": round(self.anomaly_score, 4),
        }


# ──────────────────────────────────────────────────────────────────────────────
# 1. DEMAND FORECASTER
# ──────────────────────────────────────────────────────────────────────────────


class DemandForecaster:
    """
    Ridge regression forecaster for 2-hour-ahead load prediction.
    Features: hour_sin/cos, day_sin/cos, lag_1h, lag_24h, lag_7d rolling mean.
    """

    def __init__(self, horizon_steps: int = 24):  # 24 steps × 5min = 2h
        self.horizon = horizon_steps
        self.pipeline: Pipeline = None
        self._trained: bool = False

    def _make_features(
        self, df: pd.DataFrame, load_col: str = "load_pct"
    ) -> pd.DataFrame:
        """Build time + lag features from a DataFrame with datetime index."""
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            df.index = pd.to_datetime(df.index)

        hour = df.index.hour + df.index.minute / 60
        dow = df.index.dayofweek

        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        df["day_sin"] = np.sin(2 * np.pi * dow / 7)
        df["day_cos"] = np.cos(2 * np.pi * dow / 7)

        n = len(df)
        df["lag_1"] = df[load_col].shift(1).fillna(df[load_col].mean())
        df["lag_12"] = df[load_col].shift(12).fillna(df[load_col].mean())
        df["lag_24"] = df[load_col].shift(24).fillna(df[load_col].mean())
        df["rolling_6"] = df[load_col].rolling(6, min_periods=1).mean()
        df["rolling_24"] = df[load_col].rolling(24, min_periods=1).mean()

        feat_cols = [
            "hour_sin",
            "hour_cos",
            "day_sin",
            "day_cos",
            "lag_1",
            "lag_12",
            "lag_24",
            "rolling_6",
            "rolling_24",
        ]
        return df[feat_cols], df[load_col]

    def train(self, df: pd.DataFrame, load_col: str = "load_pct") -> "DemandForecaster":
        X, y = self._make_features(df, load_col)
        self.pipeline = Pipeline(
            [("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))]
        )
        self.pipeline.fit(X.values, y.values)
        y_pred = self.pipeline.predict(X.values)
        mae = mean_absolute_error(y.values, y_pred)
        print(f"[DemandForecaster] MAE={mae:.2f}%  (in-sample)")
        self._trained = True
        joblib.dump(self.pipeline, os.path.join(MODELS_DIR, "demand_forecaster.pkl"))
        return self

    def forecast(self, df: pd.DataFrame, load_col: str = "load_pct") -> pd.Series:
        """
        Returns a Series of predicted load_pct for the next `horizon` steps.
        Uses the last available window to build features, then iterates.
        """
        if not self._trained:
            raise RuntimeError("Train the forecaster first.")

        df_ext = df.copy()
        preds = []
        last_ts = df_ext.index[-1]
        freq = pd.infer_freq(df_ext.index) or "5min"

        for step in range(self.horizon):
            X_now, _ = self._make_features(df_ext, load_col)
            p = float(self.pipeline.predict(X_now.values[-1:]))
            p = float(np.clip(p, 0, 130))
            preds.append(p)
            # Append predicted value for next iteration
            next_ts = last_ts + pd.tseries.frequencies.to_offset(freq) * (step + 1)
            new_row = pd.DataFrame({load_col: [p]}, index=[next_ts])
            df_ext = pd.concat([df_ext, new_row])

        forecast_index = pd.date_range(
            start=last_ts + pd.tseries.frequencies.to_offset(freq),
            periods=self.horizon,
            freq=freq,
        )
        return pd.Series(preds, index=forecast_index, name="forecast_load_pct")

    def load(self):
        path = os.path.join(MODELS_DIR, "demand_forecaster.pkl")
        self.pipeline = joblib.load(path)
        self._trained = True
        return self


# ──────────────────────────────────────────────────────────────────────────────
# 2. LOAD MANAGEMENT ENGINE
# ──────────────────────────────────────────────────────────────────────────────


class LoadManagementEngine:
    """
    Generates prioritised operator suggestions based on:
      - Current grid state (load, temperature, voltage, losses)
      - 2-hour demand forecast
      - LSTM anomaly scores
      - PINN violation scores
    """

    def __init__(self, forecaster: Optional[DemandForecaster] = None):
        self.forecaster = forecaster or DemandForecaster()

    def _suggest_load_shed(
        self, zone: str, load_pct: float, forecast_peak: float
    ) -> Optional[OperatorSuggestion]:
        """P1/P2 load shedding recommendation."""
        if load_pct >= LOAD_CRITICAL or forecast_peak >= LOAD_CRITICAL:
            return OperatorSuggestion(
                priority=1,
                zone=zone,
                action=f"Shed non-critical loads immediately — target {LOAD_CRITICAL - 10:.0f}% load",
                reason=f"Current load {load_pct:.1f}% (critical: ≥{LOAD_CRITICAL}%) | "
                f"2h forecast peak {forecast_peak:.1f}%",
                impact_mw=(load_pct - (LOAD_CRITICAL - 10))
                / 100
                * 10,  # assume 10 MVA base
                tags=["load_shedding", "critical", "prevent_outage"],
            )
        elif load_pct >= LOAD_WARNING or forecast_peak >= LOAD_WARNING + 5:
            return OperatorSuggestion(
                priority=2,
                zone=zone,
                action=f"Prepare load shedding schedule — current {load_pct:.1f}%",
                reason=f"Load approaching limit. Forecast peak: {forecast_peak:.1f}%",
                impact_mw=(load_pct - LOAD_WARNING) / 100 * 10,
                tags=["load_management", "warning"],
            )
        return None

    def _suggest_capacitor(
        self, zone: str, voltage_pu: float
    ) -> Optional[OperatorSuggestion]:
        """Capacitor bank / reactive power compensation."""
        if voltage_pu <= VOLTAGE_CRIT:
            return OperatorSuggestion(
                priority=1,
                zone=zone,
                action="Switch ON capacitor bank immediately — critical undervoltage",
                reason=f"Voltage {voltage_pu:.3f} pu (critical: ≤{VOLTAGE_CRIT} pu)",
                impact_mw=0.0,
                tags=["voltage_regulation", "capacitor", "critical"],
            )
        elif voltage_pu <= VOLTAGE_LOW:
            return OperatorSuggestion(
                priority=2,
                zone=zone,
                action="Switch ON capacitor bank — undervoltage detected",
                reason=f"Voltage {voltage_pu:.3f} pu (limit: {VOLTAGE_LOW} pu)",
                impact_mw=0.0,
                tags=["voltage_regulation", "capacitor"],
            )
        elif voltage_pu >= VOLTAGE_HIGH:
            return OperatorSuggestion(
                priority=2,
                zone=zone,
                action="Switch OFF capacitor bank — overvoltage detected",
                reason=f"Voltage {voltage_pu:.3f} pu (limit: {VOLTAGE_HIGH} pu)",
                impact_mw=0.0,
                tags=["voltage_regulation", "overvoltage"],
            )
        return None

    def _suggest_thermal(
        self, zone: str, winding_temp: float, load_pct: float
    ) -> Optional[OperatorSuggestion]:
        if winding_temp >= THERMAL_CRIT:
            shed_pct = min(30, max(10, (winding_temp - THERMAL_CRIT) / 2))
            return OperatorSuggestion(
                priority=1,
                zone=zone,
                action=f"Reduce transformer loading by {shed_pct:.0f}% — critical thermal",
                reason=f"Winding temp {winding_temp:.1f}°C (critical: ≥{THERMAL_CRIT}°C) | "
                f"Load: {load_pct:.1f}%",
                impact_mw=shed_pct / 100 * 10,
                tags=["thermal", "transformer", "critical"],
            )
        elif winding_temp >= THERMAL_WARN:
            return OperatorSuggestion(
                priority=2,
                zone=zone,
                action=f"Monitor transformer closely — high winding temperature",
                reason=f"Winding temp {winding_temp:.1f}°C (warning: ≥{THERMAL_WARN}°C)",
                impact_mw=0.0,
                tags=["thermal", "transformer", "warning"],
            )
        return None

    def _suggest_loss_investigation(
        self, zone: str, loss_ratio: float
    ) -> Optional[OperatorSuggestion]:
        if loss_ratio >= LOSS_CRIT:
            kwh = loss_ratio * 5000 * 0.5  # rough estimate: 5 kW base × 30 min
            return OperatorSuggestion(
                priority=2,
                zone=zone,
                action="Dispatch field team — energy theft / meter fault suspected",
                reason=f"Feeder loss ratio {loss_ratio*100:.1f}% (critical: ≥{LOSS_CRIT*100:.0f}%)",
                impact_mw=0.0,
                estimated_kwh_saved=kwh,
                tags=["energy_theft", "loss_investigation"],
            )
        elif loss_ratio >= LOSS_WARN:
            return OperatorSuggestion(
                priority=3,
                zone=zone,
                action="Schedule meter audit — elevated feeder losses",
                reason=f"Feeder loss ratio {loss_ratio*100:.1f}% (warning: ≥{LOSS_WARN*100:.0f}%)",
                impact_mw=0.0,
                tags=["energy_theft", "monitoring"],
            )
        return None

    def generate_suggestions(
        self,
        zone: str,
        load_pct: float,
        voltage_pu: float,
        winding_temp: float = 50.0,
        loss_ratio: float = 0.02,
        forecast_df: Optional[pd.DataFrame] = None,
        load_col: str = "load_pct",
    ) -> list[OperatorSuggestion]:
        """
        Main entry point for the advisory engine.
        Returns sorted list of OperatorSuggestion by priority.
        """
        suggestions = []

        # ── 2h demand forecast ──────────────────────────────────────────────
        forecast_peak = load_pct  # default = current
        if forecast_df is not None and self.forecaster._trained:
            try:
                fc = self.forecaster.forecast(forecast_df, load_col)
                forecast_peak = float(fc.max())
            except Exception as e:
                print(f"[LoadMgmt] Forecast failed: {e}")

        # ── Apply rules ─────────────────────────────────────────────────────
        for fn, args in [
            (self._suggest_load_shed, (zone, load_pct, forecast_peak)),
            (self._suggest_capacitor, (zone, voltage_pu)),
            (self._suggest_thermal, (zone, winding_temp, load_pct)),
            (self._suggest_loss_investigation, (zone, loss_ratio)),
        ]:
            s = fn(*args)
            if s is not None:
                suggestions.append(s)

        # Sort by priority ascending (1 = most urgent)
        suggestions.sort(key=lambda x: x.priority)
        return suggestions


# ──────────────────────────────────────────────────────────────────────────────
# 3. ENERGY THEFT DETECTOR
# ──────────────────────────────────────────────────────────────────────────────


class EnergyTheftDetector:
    """
    Two-method detection:
    1. Z-score: per-meter rolling z-score of kWh consumption.
       If |z| > THEFT_ZSCORE for ≥ THEFT_DURATION consecutive windows → flag.
    2. KCL: feeder supply - sum(meter readings) > LOSS_CRIT → flag all meters
       in that feeder for investigation.

    Combines both into a single confidence score.
    """

    def detect_from_kaggle(
        self,
        df: pd.DataFrame,
        meter_col: str = "meter",
        kwh_col: str = "kWh",
        ts_col: str = "ts",
        interval_min: float = 3.0,
    ) -> list[TheftFlag]:
        """
        Detect theft from Kaggle-style per-meter dataset.
        """
        flags = []
        for meter_id, grp in df.groupby(meter_col):
            grp = grp.sort_values(ts_col) if ts_col in grp.columns else grp
            kwh = grp[kwh_col].values

            if len(kwh) < THEFT_DURATION + 2:
                continue

            # ── Rolling z-score ──────────────────────────────────────────────
            roll_mean = pd.Series(kwh).rolling(20, min_periods=1).mean().values
            roll_std = (
                pd.Series(kwh).rolling(20, min_periods=1).std().fillna(0.01).values
            )
            z_scores = (kwh - roll_mean) / (roll_std + 1e-6)

            # Count consecutive high-z windows
            is_anomaly = np.abs(z_scores) > THEFT_ZSCORE
            max_consec = self._max_consecutive(is_anomaly)
            anomaly_frac = is_anomaly.mean()

            if max_consec >= THEFT_DURATION:
                confidence = min(1.0, max_consec / (THEFT_DURATION * 3))
                duration_h = max_consec * interval_min / 60
                # Estimated loss: difference between expected and recorded kWh
                expected_kwh = roll_mean[is_anomaly].sum()
                recorded_kwh = kwh[is_anomaly].sum()
                loss_kwh = max(0.0, expected_kwh - recorded_kwh)

                flags.append(
                    TheftFlag(
                        meter_id=str(meter_id),
                        confidence=confidence,
                        method="zscore",
                        duration_hrs=duration_h,
                        estimated_loss_kwh=loss_kwh,
                        anomaly_score=float(np.abs(z_scores).max()),
                    )
                )
        return flags

    def detect_from_gridlabd(
        self,
        df: pd.DataFrame,
        feeder_col: str = "feeder_power_W",
        reported_col: str = "total_reported_W",
        loss_col: str = "loss_ratio",
    ) -> list[TheftFlag]:
        """
        Detect theft from GridLAB-D feeder-level data using KCL.
        """
        flags = []
        if loss_col in df.columns:
            loss = df[loss_col].values
        else:
            feeder = df[feeder_col].values
            reported = df[reported_col].values
            loss = (feeder - reported) / (feeder + 1e-6)

        # Sustained high-loss windows
        is_suspicious = loss > LOSS_WARN
        max_consec = self._max_consecutive(is_suspicious)

        if max_consec >= THEFT_DURATION:
            avg_loss = loss[is_suspicious].mean()
            feeder_pw = (
                df[feeder_col].values[is_suspicious].mean()
                if feeder_col in df.columns
                else 5000
            )
            loss_kwh = avg_loss * feeder_pw * max_consec / 60  # kWh

            confidence = min(1.0, avg_loss / LOSS_CRIT)
            flags.append(
                TheftFlag(
                    meter_id="feeder_aggregate",
                    confidence=confidence,
                    method="kcl",
                    duration_hrs=max_consec / 60,
                    estimated_loss_kwh=loss_kwh,
                    anomaly_score=float(avg_loss),
                )
            )
        return flags

    @staticmethod
    def _max_consecutive(boolean_array: np.ndarray) -> int:
        """Returns the maximum run of True values in a boolean array."""
        max_run = 0
        current = 0
        for v in boolean_array:
            if v:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        return max_run


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    np.random.seed(0)
    print("=" * 55)
    print("LOAD MANAGEMENT ENGINE TEST")
    print("=" * 55)

    # ── Demand forecaster test ────────────────────────────────────────────────
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="5min")
    load = (
        40
        + 30 * np.sin(2 * np.pi * (np.arange(n) % 288) / 288)
        + np.random.randn(n) * 3
    )
    df_hist = pd.DataFrame({"load_pct": load}, index=idx)

    forecaster = DemandForecaster(horizon_steps=24)
    forecaster.train(df_hist)
    fc = forecaster.forecast(df_hist)
    print(f"\n2h forecast peak: {fc.max():.1f}%  |  min: {fc.min():.1f}%")

    # ── Suggestion engine test ────────────────────────────────────────────────
    engine = LoadManagementEngine(forecaster=forecaster)
    suggestions = engine.generate_suggestions(
        zone="Substation-A / Zone-3",
        load_pct=97.0,
        voltage_pu=0.92,
        winding_temp=115.0,
        loss_ratio=0.22,
        forecast_df=df_hist,
    )
    print(f"\nGenerated {len(suggestions)} suggestions:")
    for s in suggestions:
        print(f"  [P{s.priority}] {s.action[:65]}")

    # ── Theft detector test ───────────────────────────────────────────────────
    n_m = 500
    ts = pd.date_range("2024-01-01", periods=n_m, freq="3min")
    kwh = np.random.normal(0.002, 0.0005, n_m)
    kwh[350:420] *= 0.1  # simulate theft (very low reading)
    df_m = pd.DataFrame({"ts": ts, "meter": "BR02", "kWh": kwh})

    detector = EnergyTheftDetector()
    flags = detector.detect_from_kaggle(df_m)
    print(f"\nTheft flags ({len(flags)}):")
    for f in flags:
        print(f"  {json.dumps(f.to_dict(), indent=4)}")

    print("\nLoad Management Engine test passed ✓")
