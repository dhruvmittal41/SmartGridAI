"""
model_ensemble.py
=================
Unified ModelEnsemble — loads all trained models and exposes a single
`predict(sample)` interface used by the FastAPI backend.

Pipeline for each prediction:
  1. Receive raw grid reading (dict or DataFrame row)
  2. Scale using saved scalers
  3. Build sliding-window sequences for each LSTM
  4. Compute LSTM reconstruction errors (anomaly scores)
  5. Run PINN constraint validation on raw features
  6. Assemble RF feature vector from LSTM scores + PINN scores + raw features
  7. Random Forest → fault_type + probabilities
  8. SHAP → top-3 contributing features
  9. Load management engine → operator suggestions
  10. Theft detector check
  Return: GridPrediction dataclass

Threading note:
  TensorFlow models are NOT thread-safe across sessions.
  Wrap model.predict() calls in a threading.Lock() inside FastAPI.
"""

import os
import json
import threading
import warnings

warnings.filterwarnings("ignore")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np
import pandas as pd
import joblib
from dataclasses import dataclass, field
from typing import Optional

from Training.lstm_models import SubstationLSTM, TransformerLSTM, MeterLSTM, MeterGridLabLSTM
from Training.pinn_validator import PINNValidator
from Training.fault_classifier_rf import FaultClassifierRF, FAULT_SEVERITY
from Training.load_management import LoadManagementEngine, EnergyTheftDetector, DemandForecaster

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")

# ── PINN weights for composite score ─────────────────────────────────────────
PINN_COLS = ["pinn_ohm", "pinn_power", "pinn_kcl", "pinn_thermal", "pinn_vdrop"]


@dataclass
class GridPrediction:
    """Full prediction output for one grid node at one timestamp."""

    node_id: str
    timestamp: str
    fault_type: str
    fault_detected: bool
    confidence: float
    severity: int  # 0–5
    anomaly_scores: dict = field(default_factory=dict)  # per LSTM
    pinn_violations: dict = field(default_factory=dict)  # per law
    explanation: list = field(default_factory=list)  # SHAP top-3
    suggestions: list = field(default_factory=list)  # operator actions
    theft_flags: list = field(default_factory=list)  # energy theft
    raw_summary: dict = field(default_factory=dict)  # key readings

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "fault_type": self.fault_type,
            "fault_detected": self.fault_detected,
            "confidence": self.confidence,
            "severity": self.severity,
            "anomaly_scores": self.anomaly_scores,
            "pinn_violations": self.pinn_violations,
            "explanation": self.explanation,
            "suggestions": [
                s.to_dict() if hasattr(s, "to_dict") else s for s in self.suggestions
            ],
            "theft_flags": [
                t.to_dict() if hasattr(t, "to_dict") else t for t in self.theft_flags
            ],
            "raw_summary": self.raw_summary,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class ModelEnsemble:
    """
    Orchestrates all SmartGrid AI models.

    Usage (after training):
        ensemble = ModelEnsemble()
        ensemble.load_all()
        pred = ensemble.predict_from_dict(raw_reading)
    """

    def __init__(self):
        self.sub_lstm: Optional[SubstationLSTM] = None
        self.xfmr_lstm: Optional[TransformerLSTM] = None
        self.meter_lstm: Optional[MeterLSTM] = None
        self.mglab_lstm: Optional[MeterGridLabLSTM] = None
        self.rf_clf: Optional[FaultClassifierRF] = None
        self.pinn: Optional[PINNValidator] = None
        self.load_engine: Optional[LoadManagementEngine] = None
        self.theft_det: Optional[EnergyTheftDetector] = None

        # Scalers (loaded from disk)
        self.scalers = {}
        self._lock = threading.Lock()
        self._loaded = False

        # In-memory sliding windows (node_id → deque of readings)
        self._buffers: dict = {}
        self._buffer_size = 60  # max history per node

    # ── Load all persisted models ─────────────────────────────────────────────
    def load_all(self) -> "ModelEnsemble":
        print("[Ensemble] Loading all models...")

        # LSTM models
        for attr, cls, name in [
            ("sub_lstm", SubstationLSTM, "substation_lstm"),
            ("xfmr_lstm", TransformerLSTM, "transformer_lstm"),
            ("meter_lstm", MeterLSTM, "meter_lstm"),
            ("mglab_lstm", MeterGridLabLSTM, "meter_gridlab_lstm"),
        ]:
            path = os.path.join(MODELS_DIR, f"{name}.keras")
            if os.path.exists(path):
                m = cls()
                m.load(path)
                setattr(self, attr, m)
            else:
                print(f"  WARNING: {name} not found at {path} — skipping")

        # RF classifier
        rf_path = os.path.join(MODELS_DIR, "rf_classifier.pkl")
        if os.path.exists(rf_path):
            self.rf_clf = FaultClassifierRF()
            self.rf_clf.load()
        else:
            print("  WARNING: RF classifier not found — skipping")

        # Scalers
        for key in ["substation", "transformer", "meter_glab", "kaggle_meter"]:
            p = os.path.join(MODELS_DIR, f"scaler_{key}.pkl")
            if os.path.exists(p):
                self.scalers[key] = joblib.load(p)

        # Support models
        self.pinn = PINNValidator()
        self.theft_det = EnergyTheftDetector()

        forecaster = DemandForecaster()
        fc_path = os.path.join(MODELS_DIR, "demand_forecaster.pkl")
        if os.path.exists(fc_path):
            forecaster.load()
        self.load_engine = LoadManagementEngine(forecaster=forecaster)

        self._loaded = True
        print("[Ensemble] All models loaded ✓")
        return self

    # ── Main prediction entry point ───────────────────────────────────────────
    def predict_from_dict(
        self,
        raw: dict,
        node_id: str = "node_001",
        node_type: str = "meter",  # "meter"|"substation"|"transformer"
    ) -> GridPrediction:
        """
        Accepts a raw reading dict, returns a full GridPrediction.
        Thread-safe (acquires lock around TF inference).

        raw dict keys (any combination):
          Kaggle meter:  Voltage, Current, kWh, Frequency
          GridLAB sub:   hour_of_day, day_of_week, minutes
          GridLAB xfmr:  winding_temp_C, load_pct, thermal_margin_C
          GridLAB meter: feeder_power_W, total_reported_W, loss_ratio,
                         end_feeder_voltage_V, voltage_deviation_pct
        """
        import datetime

        # ── Buffer management (sliding window) ───────────────────────────────
        if node_id not in self._buffers:
            self._buffers[node_id] = []
        buf = self._buffers[node_id]
        buf.append(raw)
        if len(buf) > self._buffer_size:
            buf.pop(0)

        df_raw = pd.DataFrame(buf)
        ts_str = raw.get("timestamp", str(datetime.datetime.utcnow()))

        # ── PINN validation ───────────────────────────────────────────────────
        pinn_scores = self.pinn.validate_batch(df_raw).iloc[-1]
        pinn_violation = self.pinn.validate_single(raw)

        # ── LSTM anomaly scores ────────────────────────────────────────────────
        anomaly_scores = {}
        with self._lock:
            anomaly_scores = self._run_lstm_inference(df_raw, node_type)

        # ── Assemble RF feature vector ─────────────────────────────────────────
        rf_features = self._build_rf_vector(anomaly_scores, pinn_scores, raw)
        X_rf = np.array([rf_features["values"]], dtype=np.float32)

        # ── RF fault classification ────────────────────────────────────────────
        fault_type = "normal"
        confidence = 1.0
        explanation = []
        if self.rf_clf and self.rf_clf._trained:
            results = self.rf_clf.predict_with_explanation(X_rf, top_k=3)
            r = results[0]
            fault_type = r["fault_type"]
            confidence = r["confidence"]
            explanation = r["explanation"]

        fault_detected = fault_type != "normal"
        severity = FAULT_SEVERITY.get(fault_type, 0)

        # ── Load management suggestions ────────────────────────────────────────
        suggestions = self.load_engine.generate_suggestions(
            zone=node_id,
            load_pct=float(raw.get("load_pct", 50.0)),
            voltage_pu=float(raw.get("voltage_pu", 1.0)),
            winding_temp=float(raw.get("winding_temp_C", 50.0)),
            loss_ratio=float(raw.get("loss_ratio", 0.02)),
        )

        # ── Theft check ────────────────────────────────────────────────────────
        theft_flags = []
        if len(buf) >= 8 and node_type == "meter":
            df_buf = pd.DataFrame(buf)
            if "kWh" in df_buf.columns:
                flags = self.theft_det.detect_from_kaggle(
                    df_buf.assign(meter=node_id, ts=pd.RangeIndex(len(df_buf))),
                    ts_col="ts",
                )
                theft_flags = flags
            elif "feeder_power_W" in df_buf.columns:
                flags = self.theft_det.detect_from_gridlabd(df_buf)
                theft_flags = flags

        # ── Raw summary (for dashboard display) ───────────────────────────────
        raw_summary = {k: v for k, v in raw.items() if isinstance(v, (int, float, str))}

        return GridPrediction(
            node_id=node_id,
            timestamp=ts_str,
            fault_type=fault_type,
            fault_detected=fault_detected,
            confidence=confidence,
            severity=severity,
            anomaly_scores=anomaly_scores,
            pinn_violations=pinn_violation.to_dict(),
            explanation=explanation,
            suggestions=suggestions,
            theft_flags=theft_flags,
            raw_summary=raw_summary,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_lstm_inference(self, df: pd.DataFrame, node_type: str) -> dict:
        """
        Builds sequences and runs LSTM inference for the appropriate model.
        Returns dict of anomaly score floats.
        """
        scores = {}
        try:
            # Substation LSTM
            if self.sub_lstm and {"hour_of_day", "day_of_week"}.issubset(df.columns):
                X = self._build_sequence_sub(df)
                if X is not None:
                    scores["substation"] = float(
                        self.sub_lstm.predict_anomaly_scores(X)[0]
                    )

            # Transformer LSTM
            if self.xfmr_lstm and "winding_temp_C" in df.columns:
                X = self._build_sequence_xfmr(df)
                if X is not None:
                    scores["transformer"] = float(
                        self.xfmr_lstm.predict_anomaly_scores(X)[0]
                    )

            # Meter LSTM (Kaggle)
            if self.meter_lstm and "kWh" in df.columns:
                X = self._build_sequence_meter(df)
                if X is not None:
                    scores["meter"] = float(
                        self.meter_lstm.predict_anomaly_scores(X)[0]
                    )

            # Meter GridLAB LSTM
            if self.mglab_lstm and "feeder_power_W" in df.columns:
                X = self._build_sequence_mglab(df)
                if X is not None:
                    scores["meter_gridlab"] = float(
                        self.mglab_lstm.predict_anomaly_scores(X)[0]
                    )
        except Exception as e:
            print(f"[Ensemble] LSTM inference error: {e}")
        return scores

    def _build_sequence_sub(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        cols = ["hour_of_day", "day_of_week"]
        needed = self.sub_lstm.seq_len
        if len(df) < needed:
            return None
        df2 = df[cols].copy().fillna(0)
        df2["hs"] = np.sin(2 * np.pi * df2["hour_of_day"] / 24)
        df2["hc"] = np.cos(2 * np.pi * df2["hour_of_day"] / 24)
        df2["ds"] = np.sin(2 * np.pi * df2["day_of_week"] / 7)
        df2["dc"] = np.cos(2 * np.pi * df2["day_of_week"] / 7)
        scaler = self.scalers.get("substation")
        vals = df2[["hs", "hc", "ds", "dc"]].values[-needed:]
        if scaler:
            vals = scaler.transform(vals)
        return vals[np.newaxis, :, :]  # (1, seq, features)

    def _build_sequence_xfmr(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        needed = self.xfmr_lstm.seq_len
        if len(df) < needed:
            return None
        df2 = df.copy().fillna(0)
        df2["thermal_margin_C"] = df2.get(
            "thermal_margin_C", 140 - df2.get("winding_temp_C", 50)
        )
        df2["thermal_stress"] = df2.get("load_pct", 50) ** 2 / (
            df2["thermal_margin_C"].clip(lower=0.1)
        )
        df2["temp_grad"] = df2.get("winding_temp_C", 50).diff(5).fillna(0)
        hour = df2.get("hour_of_day", pd.Series(np.zeros(len(df2))))
        dow = df2.get("day_of_week", pd.Series(np.zeros(len(df2))))
        df2["hs"] = np.sin(2 * np.pi * hour / 24)
        df2["hc"] = np.cos(2 * np.pi * hour / 24)
        df2["ds"] = np.sin(2 * np.pi * dow / 7)
        df2["dc"] = np.cos(2 * np.pi * dow / 7)
        cols = [
            "winding_temp_C",
            "load_pct",
            "thermal_margin_C",
            "thermal_stress",
            "temp_grad",
            "hs",
            "hc",
            "ds",
            "dc",
        ]
        avail = [c for c in cols if c in df2.columns]
        vals = df2[avail].values[-needed:]
        # Pad features if needed
        if vals.shape[1] < 9:
            pad = np.zeros((vals.shape[0], 9 - vals.shape[1]))
            vals = np.concatenate([vals, pad], axis=1)
        scaler = self.scalers.get("transformer")
        if scaler:
            vals = scaler.transform(vals)
        return vals[np.newaxis, :, :]

    def _build_sequence_meter(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        needed = self.meter_lstm.seq_len
        if len(df) < needed:
            return None
        df2 = df.copy().fillna(0)
        df2["apparent_VA"] = df2.get("Voltage", 230) * df2.get("Current", 1)
        df2["active_W"] = df2.get("kWh", 0.001) * 3_600_000 / 180
        df2["pf_est"] = (df2["active_W"] / df2["apparent_VA"].clip(lower=0.01)).clip(
            0, 1
        )
        df2["voltage_dev"] = (df2.get("Voltage", 230) - 230.0) / 230.0
        df2["freq_dev"] = df2.get("Frequency", 50) - 50.0
        df2["kwh_zscore"] = 0.0  # default for real-time
        vals = df2[
            [
                "kWh",
                "Voltage",
                "Current",
                "Frequency",
                "apparent_VA",
                "pf_est",
                "voltage_dev",
                "freq_dev",
                "kwh_zscore",
            ]
        ].values[-needed:]
        n_feat = self.meter_lstm.n_features
        if vals.shape[1] < n_feat:
            pad = np.zeros((vals.shape[0], n_feat - vals.shape[1]))
            vals = np.concatenate([vals, pad], axis=1)
        scaler = self.scalers.get("kaggle_meter")
        if scaler:
            vals = scaler.transform(vals)
        return vals[np.newaxis, :, :]

    def _build_sequence_mglab(self, df: pd.DataFrame) -> Optional[np.ndarray]:
        needed = self.mglab_lstm.seq_len
        if len(df) < needed:
            return None
        df2 = df.copy().fillna(0)
        df2["apparent_loss"] = df2.get("feeder_power_W", 0) - df2.get(
            "total_reported_W", 0
        )
        df2["log_excess"] = np.log1p(df2.get("excess_loss_pct", 0).clip(lower=0))
        df2["loss_trend"] = df2.get("loss_ratio", 0).diff(5).fillna(0)
        vals = df2[
            [
                "feeder_power_W",
                "total_reported_W",
                "loss_ratio",
                "apparent_loss",
                "log_excess",
                "loss_trend",
                "end_feeder_voltage_V",
                "voltage_deviation_pct",
                "undervoltage_flag",
            ]
        ].values[-needed:]
        n_feat = self.mglab_lstm.n_features
        if vals.shape[1] < n_feat:
            pad = np.zeros((vals.shape[0], n_feat - vals.shape[1]))
            vals = np.concatenate([vals, pad], axis=1)
        scaler = self.scalers.get("meter_glab")
        if scaler:
            vals = scaler.transform(vals)
        return vals[np.newaxis, :, :]

    def _build_rf_vector(self, anomaly_scores: dict, pinn_scores, raw: dict) -> dict:
        """Assembles the RF feature vector from all sub-model outputs."""
        names = []
        values = []

        for k in ["substation", "transformer", "meter", "meter_gridlab"]:
            names.append(f"{k}_recon_err")
            values.append(anomaly_scores.get(k, 0.0))

        for col in PINN_COLS:
            names.append(col)
            values.append(float(pinn_scores.get(col, 0.0)))
        names.append("pinn_composite")
        values.append(float(pinn_scores.get("pinn_composite", 0.0)))

        # Add key raw features
        for rk in [
            "load_pct",
            "voltage_pu",
            "winding_temp_C",
            "loss_ratio",
            "voltage_deviation_pct",
        ]:
            names.append(rk)
            values.append(float(raw.get(rk, 0.0)))

        return {"names": names, "values": values}


# ── Standalone smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    print("=" * 60)
    print("MODEL ENSEMBLE SMOKE TEST (no trained models required)")
    print("=" * 60)

    # Build ensemble without loading (graceful degradation)
    ensemble = ModelEnsemble()
    ensemble.pinn = PINNValidator()
    ensemble.theft_det = EnergyTheftDetector()
    ensemble.load_engine = LoadManagementEngine(DemandForecaster())

    # Simulate a faulty reading
    faulty_reading = {
        "Voltage": 195.0,
        "Current": 22.5,
        "kWh": 0.0001,
        "Frequency": 49.2,
        "feeder_power_W": 6000.0,
        "total_reported_W": 3800.0,
        "loss_ratio": 0.37,
        "excess_loss_pct": 37.0,
        "theft_flag_raw": 1,
        "end_feeder_voltage_V": 210.0,
        "voltage_deviation_pct": -8.3,
        "undervoltage_flag": 1,
        "winding_temp_C": 125.0,
        "load_pct": 98.0,
        "thermal_margin_C": 15.0,
        "hour_of_day": 14.0,
        "day_of_week": 2,
        "voltage_pu": 0.85,
    }

    # Feed 70 identical readings to fill buffers
    for i in range(70):
        pred = ensemble.predict_from_dict(
            raw=faulty_reading, node_id="Sub-Bareilly-01", node_type="meter"
        )

    print(f"\nFinal prediction (after 70 readings):")
    print(f"  Fault detected : {pred.fault_detected}")
    print(f"  Fault type     : {pred.fault_type}")
    print(f"  Severity       : {pred.severity}/5")
    print(f"  Anomaly scores : {pred.anomaly_scores}")
    print(f"  PINN composite : {pred.pinn_violations.get('total', 'N/A')}")
    print(f"  Suggestions    : {len(pred.suggestions)} generated")
    if pred.suggestions:
        print(
            f"    → [P{pred.suggestions[0].priority}] {pred.suggestions[0].action[:60]}"
        )
    print(f"  Theft flags    : {len(pred.theft_flags)}")

    print("\nEnsemble smoke test passed ✓")
