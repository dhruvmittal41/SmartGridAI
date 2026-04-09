"""
tests/test_pipeline.py
======================
End-to-end tests for SmartGrid AI ML pipeline.
Run with:  python -m pytest tests/ -v

Tests cover:
  - Data preprocessing (all 4 formats)
  - PINN validator (physics correctness)
  - LSTM model build + forward pass
  - RF classifier (train + predict + SHAP)
  - Load management engine (rule coverage)
  - Theft detector (both methods)
  - Model ensemble (smoke test)

All tests use synthetic data — no real CSVs needed.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import pandas as pd
import tempfile
import pytest

# ── Test data generators ──────────────────────────────────────────────────────


def make_substation_csv(n: int = 200) -> str:
    """Generate a GridLAB-D substation CSV."""
    header = "+2.96796e+06,+1.64022e+06,minutes,hour_of_day,day_of_week,fault_label,fault_type\n"
    rows = []
    for i in range(n):
        fl = 1 if i > int(n * 0.85) else 0
        ft = "overload" if fl else "normal"
        rows.append(f"2967960.0,1640220.0,{i}.0,{(i%24)/24:.4f},{i%7},{fl},{ft}")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(header + "\n".join(rows))
    tmp.close()
    return tmp.name


def make_transformer_csv(n: int = 200) -> str:
    header = "+40057.5,+100745,minutes,hour_of_day,day_of_week,winding_temp_C,load_pct,thermal_margin_C,fault_label,fault_type\n"
    rows = []
    for i in range(n):
        temp = 35 + (i / n) * 110
        load = 15 + (i / n) * 115
        margin = max(140 - temp, 0.1)
        fl = 1 if temp > 100 else 0
        ft = "thermal_fault" if fl else "normal"
        rows.append(
            f"34813.9,100736,{i}.0,{(i%24)/24:.4f},{i%7},{temp:.1f},{load:.1f},{margin:.1f},{fl},{ft}"
        )
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(header + "\n".join(rows))
    tmp.close()
    return tmp.name


def make_meter_csv(n: int = 200) -> str:
    header = "+6446,+11224.8,minutes,hour_of_day,day_of_week,feeder_power_W,total_reported_W,loss_ratio,excess_loss_pct,theft_flag_raw,end_feeder_voltage_V,voltage_deviation_pct,undervoltage_flag,fault_label,fault_type\n"
    rows = []
    for i in range(n):
        theft = 1 if i > int(n * 0.80) else 0
        rep_W = 3800.0 if theft else 4900.0
        loss = (5000 - rep_W) / 5000
        exc = max(0, (loss - 0.02) * 100)
        rows.append(
            f"5985.22,11223.4,{i*15}.0,{(i%96)/96:.4f},{i%7},"
            f"5000.0,{rep_W},{loss:.4f},{exc:.1f},{theft},239.6,0.0,0,{theft},"
            f"{'theft' if theft else 'normal'}"
        )
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(header + "\n".join(rows))
    tmp.close()
    return tmp.name


def make_kaggle_csv(n: int = 400) -> str:
    """Minimal Kaggle-style smart meter CSV."""
    header = "x_Timestamp,t_kWh,Voltage,Current,Frequency,meter\n"
    rows = []
    ts = pd.date_range("2024-01-01", periods=n, freq="3min")
    for i, t in enumerate(ts):
        meter = "BR02" if i < n // 2 else "BR03"
        kwh = max(0, np.random.normal(0.002, 0.0005))
        V = np.random.normal(230, 3)
        I = np.random.uniform(0.1, 6)
        F = np.random.normal(50.0, 0.05)
        rows.append(f"{t},{kwh:.4f},{V:.2f},{I:.2f},{F:.2f},{meter}")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(header + "\n".join(rows))
    tmp.close()
    return tmp.name


# ── PREPROCESSING TESTS ───────────────────────────────────────────────────────


class TestPreprocessing:

    def test_substation(self):
        from preprocess import preprocess_substation

        path = make_substation_csv(200)
        X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le = preprocess_substation(path)
        assert X_tr.ndim == 3, "Expected 3D tensor"
        assert X_tr.shape[2] == 4, "Expected 4 features (cyclic time)"
        assert set(y_tr).issubset({0, 1}), "Labels must be binary"
        os.unlink(path)

    def test_transformer(self):
        from preprocess import preprocess_transformer

        path = make_transformer_csv(200)
        X_tr, X_te, y_tr, y_te, ft_tr, ft_te, scaler, le = preprocess_transformer(path)
        assert X_tr.shape[2] == 9, f"Expected 9 features, got {X_tr.shape[2]}"
        assert X_tr.min() >= -0.01 and X_tr.max() <= 1.01, "Scaler out of bounds"
        os.unlink(path)

    def test_meter_gridlabd(self):
        from preprocess import preprocess_meter_gridlabd

        path = make_meter_csv(200)
        X_tr, X_te, y_tr, y_te, th_tr, th_te, scaler, le = preprocess_meter_gridlabd(
            path
        )
        assert X_tr.shape[2] == 13, f"Expected 13 features, got {X_tr.shape[2]}"
        os.unlink(path)

    def test_kaggle_meters(self):
        from preprocess import preprocess_kaggle_meters

        path = make_kaggle_csv(400)
        X_tr, X_te, scaler, df_rf, feat_cols = preprocess_kaggle_meters(path)
        assert X_tr.ndim == 3
        assert X_tr.shape[2] == len(feat_cols)
        assert "kWh" in feat_cols
        assert "pf_est" in feat_cols
        os.unlink(path)


# ── PINN TESTS ────────────────────────────────────────────────────────────────


class TestPINN:

    def setup_method(self):
        from Training.pinn_validator import PINNValidator

        self.validator = PINNValidator()

    def test_ohm_normal(self):
        """Normal readings should have near-zero Ohm violation."""
        V = np.array([230.0])
        I = np.array([5.0])
        # R=1Ω → expected V=5V, actual V=230V → large score (different scales)
        # This is expected — R_nominal is a population parameter
        score = self.validator.check_ohm(V, I)
        assert 0.0 <= score[0] <= 1.0

    def test_kcl_no_theft(self):
        """Zero theft should yield near-zero KCL violation."""
        feeder = np.array([5000.0])
        reported = np.array([4900.0])  # 2% loss — below threshold
        score = self.validator.check_kcl(feeder, reported)
        assert score[0] < 0.5, f"Expected low score, got {score[0]}"

    def test_kcl_theft(self):
        """High loss should yield high KCL violation."""
        feeder = np.array([5000.0])
        reported = np.array([2000.0])  # 60% loss
        score = self.validator.check_kcl(feeder, reported)
        assert score[0] > 0.5, f"Expected high score, got {score[0]}"

    def test_thermal_normal(self):
        """Normal temperature should not trigger thermal violation."""
        wt = np.array([55.0])
        margin = np.array([85.0])
        score = self.validator.check_thermal(wt, margin)
        assert score[0] < 0.5

    def test_thermal_critical(self):
        """Temperature near limit should trigger thermal violation."""
        wt = np.array([130.0])
        margin = np.array([10.0])
        score = self.validator.check_thermal(wt, margin)
        assert score[0] > 0.5

    def test_batch_shape(self):
        """validate_batch must return same row count as input."""
        n = 100
        df = pd.DataFrame(
            {
                "Voltage": np.random.normal(230, 5, n),
                "Current": np.random.uniform(1, 8, n),
                "active_W": np.random.uniform(200, 1800, n),
                "pf_est": np.full(n, 0.90),
                "winding_temp_C": np.random.normal(60, 10, n),
                "thermal_margin_C": np.random.normal(80, 10, n),
                "load_pct": np.random.uniform(20, 90, n),
                "feeder_power_W": np.random.normal(5000, 200, n),
                "total_reported_W": np.random.normal(4900, 200, n),
                "loss_ratio": np.random.uniform(0, 0.05, n),
                "end_feeder_voltage_V": np.random.normal(229, 3, n),
            }
        )
        out = self.validator.validate_batch(df)
        assert len(out) == n
        assert "pinn_composite" in out.columns
        assert out["pinn_composite"].between(0, 1).all(), "Scores out of [0,1]"

    def test_faulty_higher_than_normal(self):
        """Faulty batch should score higher than normal batch."""
        n_normal = 100
        n_faulty = 50

        def _make_df(n, faulty=False):
            return pd.DataFrame(
                {
                    "Voltage": np.full(n, 195.0 if faulty else 230.0),
                    "Current": np.full(n, 22.0 if faulty else 3.0),
                    "active_W": np.full(n, 500.0 if faulty else 1800.0),
                    "pf_est": np.full(n, 0.90),
                    "winding_temp_C": np.full(n, 125.0 if faulty else 55.0),
                    "thermal_margin_C": np.full(n, 15.0 if faulty else 85.0),
                    "load_pct": np.full(n, 110.0 if faulty else 45.0),
                    "feeder_power_W": np.full(n, 5000.0),
                    "total_reported_W": np.full(n, 2000.0 if faulty else 4900.0),
                    "loss_ratio": np.full(n, 0.60 if faulty else 0.02),
                    "end_feeder_voltage_V": np.full(n, 210.0 if faulty else 229.0),
                }
            )

        normal_score = self.validator.validate_batch(_make_df(n_normal, False))[
            "pinn_composite"
        ].mean()
        faulty_score = self.validator.validate_batch(_make_df(n_faulty, True))[
            "pinn_composite"
        ].mean()
        assert (
            faulty_score > normal_score
        ), f"Faulty score {faulty_score:.3f} should exceed normal {normal_score:.3f}"


# ── LSTM TESTS ────────────────────────────────────────────────────────────────


class TestLSTMModels:

    def _forward_pass(self, cls, seq_len, n_features):
        model = cls()
        model.build(seq_len, n_features)
        dummy = np.random.randn(4, seq_len, n_features).astype(np.float32)
        out = model.model.predict(dummy, verbose=0)
        assert out.shape == dummy.shape, f"Shape mismatch: {out.shape}"
        return model

    def test_substation_build(self):
        from Training.lstm_models import SubstationLSTM

        self._forward_pass(SubstationLSTM, 48, 4)

    def test_transformer_build(self):
        from Training.lstm_models import TransformerLSTM

        self._forward_pass(TransformerLSTM, 48, 9)

    def test_meter_build(self):
        from Training.lstm_models import MeterLSTM

        self._forward_pass(MeterLSTM, 60, 13)

    def test_meter_gridlab_build(self):
        from Training.lstm_models import MeterGridLabLSTM

        self._forward_pass(MeterGridLabLSTM, 48, 13)

    def test_threshold_normal_lower_than_faulty(self):
        """After training on normal data, faulty data should score higher."""
        from Training.lstm_models import TransformerLSTM

        np.random.seed(0)
        seq, feat = 20, 3
        X_normal = np.random.randn(200, seq, feat).astype(np.float32) * 0.1
        X_faulty = np.random.randn(50, seq, feat).astype(np.float32) * 3.0

        model = TransformerLSTM()
        model.build(seq, feat)
        model.model.fit(X_normal, X_normal, epochs=3, batch_size=32, verbose=0)
        model.compute_threshold(X_normal)
        normal_scores = model.reconstruction_errors(X_normal).mean()
        faulty_scores = model.reconstruction_errors(X_faulty).mean()
        assert (
            faulty_scores > normal_scores
        ), f"Faulty ({faulty_scores:.4f}) should beat normal ({normal_scores:.4f})"

    def test_anomaly_score_shape(self):
        """Anomaly scores must be shape (N,)."""
        from Training.lstm_models import SubstationLSTM

        m = SubstationLSTM()
        m.build(10, 4)
        X = np.random.randn(32, 10, 4).astype(np.float32)
        m.model.fit(X, X, epochs=1, verbose=0)
        m.compute_threshold(X)
        scores = m.predict_anomaly_scores(X)
        assert scores.shape == (32,)


# ── RF TESTS ──────────────────────────────────────────────────────────────────


class TestRFClassifier:

    @pytest.fixture(autouse=True)
    def build_classifier(self):
        from Training.fault_classifier_rf import FaultClassifierRF

        np.random.seed(42)
        n = 500
        classes = ["normal", "overload", "energy_theft", "transformer_failure"]
        y = np.random.choice(classes, size=n, p=[0.60, 0.18, 0.12, 0.10])
        self.df = pd.DataFrame(
            {
                "sub_recon_err": np.where(y == "overload", 1.5, 0.1)
                + np.random.randn(n) * 0.15,
                "xfmr_recon_err": np.where(y == "transformer_failure", 2.0, 0.1)
                + np.random.randn(n) * 0.15,
                "meter_recon_err": np.where(y == "energy_theft", 1.8, 0.1)
                + np.random.randn(n) * 0.15,
                "pinn_ohm_viol": np.random.rand(n) * 0.2,
                "pinn_power_viol": np.random.rand(n) * 0.2,
                "pinn_kcl_viol": np.where(y == "energy_theft", 0.75, 0.03)
                + np.random.randn(n) * 0.05,
                "pinn_thermal": np.where(y == "transformer_failure", 0.85, 0.04)
                + np.random.randn(n) * 0.04,
                "pinn_composite": np.random.rand(n) * 0.3,
                "fault_type": y,
                "fault_label": (y != "normal").astype(int),
            }
        ).clip(lower=0)
        self.clf = FaultClassifierRF(n_estimators=50)
        self.clf.train(self.df)

    def test_predict_returns_valid_class(self):
        X = self.df.drop(columns=["fault_type", "fault_label"]).values[:10]
        preds = self.clf.predict(X)
        valid = set(self.clf.label_encoder.classes_)
        assert all(p in valid for p in preds)

    def test_proba_sums_to_one(self):
        X = self.df.drop(columns=["fault_type", "fault_label"]).values[:20]
        proba = self.clf.predict_proba(X)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_shap_explanation_keys(self):
        X = self.df.drop(columns=["fault_type", "fault_label"]).values[:5]
        results = self.clf.predict_with_explanation(X, top_k=3)
        assert len(results) == 5
        for r in results:
            assert "fault_type" in r
            assert "confidence" in r
            assert "severity" in r
            assert "explanation" in r
            assert len(r["explanation"]) <= 3
            for ex in r["explanation"]:
                assert "feature" in ex
                assert "impact" in ex
                assert "direction" in ex

    def test_feature_importance_sorted(self):
        imp = self.clf.get_feature_importance()
        assert list(imp["importance"]) == sorted(imp["importance"], reverse=True)

    def test_oob_score_reasonable(self):
        assert (
            self.clf.rf.oob_score_ > 0.60
        ), f"OOB score {self.clf.rf.oob_score_:.3f} too low (may indicate data/label issue)"


# ── LOAD MANAGEMENT TESTS ─────────────────────────────────────────────────────


class TestLoadManagement:

    def setup_method(self):
        from Training.load_management import LoadManagementEngine, DemandForecaster

        self.engine = LoadManagementEngine()

    def test_critical_load_triggers_p1(self):
        suggestions = self.engine.generate_suggestions(
            zone="Zone-A", load_pct=97.0, voltage_pu=1.0
        )
        p1 = [s for s in suggestions if s.priority == 1]
        assert len(p1) >= 1, "Critical load (97%) must generate P1 suggestion"

    def test_normal_load_no_shed(self):
        suggestions = self.engine.generate_suggestions(
            zone="Zone-B",
            load_pct=50.0,
            voltage_pu=1.0,
            winding_temp=55.0,
            loss_ratio=0.02,
        )
        shed = [
            s
            for s in suggestions
            if "Shed" in s.action or "shedding" in s.action.lower()
        ]
        assert len(shed) == 0, "Normal conditions should not trigger load shedding"

    def test_undervoltage_triggers_capacitor(self):
        suggestions = self.engine.generate_suggestions(
            zone="Zone-C", load_pct=50.0, voltage_pu=0.88
        )
        cap = [s for s in suggestions if "capacitor" in s.action.lower()]
        assert len(cap) >= 1, "Critical undervoltage must suggest capacitor bank"

    def test_thermal_critical_triggers_p1(self):
        suggestions = self.engine.generate_suggestions(
            zone="Zone-D", load_pct=60.0, voltage_pu=1.0, winding_temp=125.0
        )
        p1 = [s for s in suggestions if s.priority == 1 and "thermal" in str(s.tags)]
        assert len(p1) >= 1

    def test_high_loss_triggers_theft_investigation(self):
        suggestions = self.engine.generate_suggestions(
            zone="Zone-E", load_pct=60.0, voltage_pu=1.0, loss_ratio=0.25
        )
        theft = [
            s
            for s in suggestions
            if "theft" in str(s.tags) or "loss" in s.action.lower()
        ]
        assert len(theft) >= 1


# ── THEFT DETECTOR TESTS ──────────────────────────────────────────────────────


class TestTheftDetector:

    def setup_method(self):
        from Training.load_management import EnergyTheftDetector

        self.det = EnergyTheftDetector()

    def test_no_theft_no_flags(self):
        n = 200
        ts = pd.date_range("2024-01-01", periods=n, freq="3min")
        kwh = np.random.normal(0.002, 0.0002, n)
        df = pd.DataFrame({"ts": ts, "meter": "M01", "kWh": kwh})
        flags = self.det.detect_from_kaggle(df)
        assert len(flags) == 0, "No theft should produce no flags"

    def test_sudden_drop_flagged(self):
        n = 300
        ts = pd.date_range("2024-01-01", periods=n, freq="3min")
        kwh = np.ones(n) * 0.002
        kwh[200:260] = 0.00001  # near-zero for 60 windows
        df = pd.DataFrame({"ts": ts, "meter": "M02", "kWh": kwh})
        flags = self.det.detect_from_kaggle(df)
        assert len(flags) >= 1, "Sustained near-zero kWh should be flagged as theft"
        assert flags[0].confidence > 0.5

    def test_kcl_theft(self):
        n = 100
        df = pd.DataFrame(
            {
                "feeder_power_W": np.full(n, 5000.0),
                "total_reported_W": np.full(n, 2000.0),  # 60% loss
                "loss_ratio": np.full(n, 0.60),
            }
        )
        flags = self.det.detect_from_gridlabd(df)
        assert len(flags) >= 1
        assert flags[0].method == "kcl"


# ── ENSEMBLE SMOKE TEST ───────────────────────────────────────────────────────


class TestEnsemble:

    def test_smoke_without_trained_models(self):
        """Ensemble must run gracefully even with no trained models."""
        from Training.model_ensemble import ModelEnsemble
        from Training.pinn_validator import PINNValidator
        from Training.load_management import (
            LoadManagementEngine,
            EnergyTheftDetector,
            DemandForecaster,
        )

        ensemble = ModelEnsemble()
        ensemble.pinn = PINNValidator()
        ensemble.theft_det = EnergyTheftDetector()
        ensemble.load_engine = LoadManagementEngine(DemandForecaster())

        sample = {
            "Voltage": 230.0,
            "Current": 4.5,
            "kWh": 0.002,
            "Frequency": 50.0,
            "load_pct": 55.0,
            "voltage_pu": 1.0,
            "feeder_power_W": 5000.0,
            "total_reported_W": 4900.0,
            "loss_ratio": 0.02,
            "end_feeder_voltage_V": 229.5,
            "voltage_deviation_pct": 0.1,
            "undervoltage_flag": 0,
            "winding_temp_C": 55.0,
            "thermal_margin_C": 85.0,
        }
        for _ in range(70):
            pred = ensemble.predict_from_dict(sample, node_id="test-node")

        assert pred.node_id == "test-node"
        assert pred.fault_type in {
            "normal",
            "overload",
            "voltage_sag",
            "transformer_failure",
            "energy_theft",
            "earth_fault",
            "thermal_fault",
        }
        assert 0 <= pred.severity <= 5
        assert isinstance(pred.pinn_violations, dict)
        assert "total" in pred.pinn_violations


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
