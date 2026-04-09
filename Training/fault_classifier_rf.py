"""
fault_classifier_rf.py
======================
Random Forest fault type classifier with SHAP explainability.

Input features (the RF feature matrix built in preprocess.py):
  - sub_recon_err     : substation LSTM reconstruction error
  - xfmr_recon_err    : transformer LSTM reconstruction error
  - meter_recon_err   : meter LSTM reconstruction error
  - pinn_ohm_viol     : Ohm's Law violation score
  - pinn_power_viol   : power balance violation score
  - pinn_kcl_viol     : KCL violation score
  - pinn_thermal      : thermal violation score
  - pinn_composite    : weighted PINN total
  - (optional raw features from each dataset)

Output:
  - fault_type classification (normal / overload / voltage_sag /
                               transformer_failure / energy_theft / earth_fault)
  - class probabilities
  - SHAP values per prediction (top 3 contributing features + direction)

Why Random Forest over XGBoost?
  - Interpretability via SHAP TreeExplainer is fast and exact for RF.
  - No hyperparameter sensitivity on small-to-medium hackathon datasets.
  - Built-in feature importance is a second explainability layer.
"""

import os
import json
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import shap

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    f1_score,
)
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Fault type label definitions ──────────────────────────────────────────────
FAULT_CLASSES = [
    "normal",
    "overload",
    "voltage_sag",
    "transformer_failure",
    "energy_theft",
    "earth_fault",
    "thermal_fault",
]

# ── Severity map (used by load advisor and alert panel) ───────────────────────
FAULT_SEVERITY = {
    "normal": 0,
    "overload": 3,
    "voltage_sag": 2,
    "transformer_failure": 5,
    "energy_theft": 4,
    "earth_fault": 5,
    "thermal_fault": 4,
}


class FaultClassifierRF:
    """
    Random Forest fault type classifier with integrated SHAP explainability.
    """

    def __init__(
        self, n_estimators: int = 300, max_depth: int = 12, random_state: int = 42
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.rf: RandomForestClassifier = None
        self.explainer: shap.TreeExplainer = None
        self.label_encoder: LabelEncoder = None
        self.feature_names: list = None
        self._trained: bool = False

    # ── Build ─────────────────────────────────────────────────────────────────
    def build(self, class_weight: str = "balanced") -> "FaultClassifierRF":
        self.rf = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=4,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight=class_weight,
            n_jobs=-1,
            random_state=self.random_state,
            oob_score=True,  # free OOB estimate of generalisation
        )
        self.label_encoder = LabelEncoder()
        print(
            "[RF] Built RandomForestClassifier"
            f"  n_estimators={self.n_estimators}  max_depth={self.max_depth}"
        )
        return self

    # ── Train ─────────────────────────────────────────────────────────────────
    def train(
        self,
        df: pd.DataFrame,
        target_col: str = "fault_type",
        exclude_cols: list = None,
    ) -> "FaultClassifierRF":
        """
        Train on the RF feature matrix (output of preprocess.build_rf_feature_matrix).

        Parameters
        ----------
        df          : full feature DataFrame including target column
        target_col  : column name for fault type labels
        exclude_cols: columns to drop from feature set
        """
        if self.rf is None:
            self.build()

        drop = set(exclude_cols or []) | {"fault_label", target_col}
        feature_cols = [c for c in df.columns if c not in drop]
        self.feature_names = feature_cols

        X = df[feature_cols].fillna(0).values
        y_raw = df[target_col].astype(str).values
        y = self.label_encoder.fit_transform(y_raw)

        print(
            f"[RF] Training on {X.shape[0]} samples, "
            f"{X.shape[1]} features, "
            f"{len(self.label_encoder.classes_)} classes"
        )
        print(f"     Classes: {list(self.label_encoder.classes_)}")

        # ── Cross-validation first ─────────────────────────────────────────
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        cv_f1 = cross_val_score(self.rf, X, y, cv=cv, scoring="f1_weighted", n_jobs=-1)
        print(f"[RF] 5-fold CV F1 = {cv_f1.mean():.3f} ± {cv_f1.std():.3f}")

        # ── Full training ──────────────────────────────────────────────────
        self.rf.fit(X, y)
        print(f"[RF] OOB score = {self.rf.oob_score_:.3f}")

        # ── SHAP explainer ──────────────────────────────────────────────────
        print("[RF] Building SHAP TreeExplainer...")
        self.explainer = shap.TreeExplainer(
            self.rf, feature_perturbation="tree_path_dependent"
        )
        self._trained = True
        return self

    # ── Predict ───────────────────────────────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Returns class label strings."""
        y_enc = self.rf.predict(X)
        return self.label_encoder.inverse_transform(y_enc)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns probability matrix (N, n_classes)."""
        return self.rf.predict_proba(X)

    def predict_with_explanation(self, X: np.ndarray, top_k: int = 3) -> list[dict]:
        """
        For each sample, return:
          {
            "fault_type":    str,
            "confidence":    float,
            "severity":      int (0-5),
            "probabilities": {class: prob, ...},
            "explanation": [
              {"feature": str, "value": float, "impact": float, "direction": str},
              ...  (top_k entries)
            ]
          }
        """
        if not self._trained:
            raise RuntimeError("Model not trained. Call train() first.")

        proba = self.predict_proba(X)
        classes = self.label_encoder.classes_

        # SHAP values: list of arrays, one per class, each (N, n_features)
        shap_values = self.explainer.shap_values(
            X, check_additivity=False  # skip slow additivity check
        )

        results = []
        for i in range(len(X)):
            best_class_idx = int(np.argmax(proba[i]))
            fault_type = classes[best_class_idx]
            confidence = float(proba[i][best_class_idx])
            proba_dict = {c: float(proba[i][j]) for j, c in enumerate(classes)}

            # SHAP for the predicted class
            sv = shap_values[best_class_idx][i]  # (n_features,)
            importance = np.abs(sv)
            top_indices = np.argsort(importance)[::-1][:top_k]

            explanation = []
            for idx in top_indices:
                fname = self.feature_names[idx] if self.feature_names else f"f{idx}"
                impact = float(sv[idx])
                explanation.append(
                    {
                        "feature": fname,
                        "value": float(X[i, idx]),
                        "impact": abs(impact),
                        "direction": (
                            "increases_risk" if impact > 0 else "decreases_risk"
                        ),
                    }
                )

            results.append(
                {
                    "fault_type": fault_type,
                    "confidence": round(confidence, 4),
                    "severity": FAULT_SEVERITY.get(fault_type, 0),
                    "probabilities": {k: round(v, 4) for k, v in proba_dict.items()},
                    "explanation": explanation,
                }
            )

        return results

    # ── Evaluation ────────────────────────────────────────────────────────────
    def evaluate(self, X_test: np.ndarray, y_test_raw: np.ndarray) -> dict:
        y_test_enc = self.label_encoder.transform(y_test_raw.astype(str))
        y_pred = self.rf.predict(X_test)
        proba = self.predict_proba(X_test)

        report = classification_report(
            y_test_enc,
            y_pred,
            target_names=list(self.label_encoder.classes_),
            output_dict=True,
            zero_division=0,
        )
        f1_w = f1_score(y_test_enc, y_pred, average="weighted", zero_division=0)

        print("\n[RF] Evaluation Results:")
        print(
            classification_report(
                y_test_enc,
                y_pred,
                target_names=list(self.label_encoder.classes_),
                zero_division=0,
            )
        )
        cm = confusion_matrix(y_test_enc, y_pred)
        print(f"Confusion matrix:\n{cm}")

        metrics = {
            "f1_weighted": float(f1_w),
            "oob_score": float(self.rf.oob_score_),
            "per_class": report,
        }
        return metrics

    # ── Feature importance ────────────────────────────────────────────────────
    def get_feature_importance(self) -> pd.DataFrame:
        """Returns a sorted DataFrame of RF feature importances."""
        importances = self.rf.feature_importances_
        names = self.feature_names or [f"f{i}" for i in range(len(importances))]
        df = (
            pd.DataFrame({"feature": names, "importance": importances})
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        return df

    def get_shap_summary(
        self, X_sample: np.ndarray, max_display: int = 10
    ) -> pd.DataFrame:
        """
        Returns mean |SHAP| per feature across all classes (global importance).
        """
        sv = self.explainer.shap_values(X_sample, check_additivity=False)
        # sv is list of (N, features) per class
        mean_abs = np.mean([np.abs(v).mean(axis=0) for v in sv], axis=0)
        names = self.feature_names or [f"f{i}" for i in range(len(mean_abs))]
        df = (
            pd.DataFrame({"feature": names, "mean_abs_shap": mean_abs})
            .sort_values("mean_abs_shap", ascending=False)
            .head(max_display)
        )
        return df

    # ── Persist ───────────────────────────────────────────────────────────────
    def save(self):
        joblib.dump(self.rf, os.path.join(MODELS_DIR, "rf_classifier.pkl"))
        joblib.dump(
            self.label_encoder, os.path.join(MODELS_DIR, "rf_label_encoder.pkl")
        )
        meta = {"feature_names": self.feature_names}
        joblib.dump(meta, os.path.join(MODELS_DIR, "rf_meta.pkl"))
        print("[RF] Saved to models/saved/")

    def load(self):
        self.rf = joblib.load(os.path.join(MODELS_DIR, "rf_classifier.pkl"))
        self.label_encoder = joblib.load(
            os.path.join(MODELS_DIR, "rf_label_encoder.pkl")
        )
        meta = joblib.load(os.path.join(MODELS_DIR, "rf_meta.pkl"))
        self.feature_names = meta["feature_names"]
        self.explainer = shap.TreeExplainer(
            self.rf, feature_perturbation="tree_path_dependent"
        )
        self._trained = True
        print("[RF] Loaded from models/saved/")
        return self


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    n = 1000

    # Synthetic RF feature matrix
    classes = [
        "normal",
        "overload",
        "voltage_sag",
        "transformer_failure",
        "energy_theft",
    ]
    y_raw = np.random.choice(classes, size=n, p=[0.60, 0.15, 0.10, 0.08, 0.07])

    # Make features correlate with fault type
    features = pd.DataFrame(
        {
            "sub_recon_err": np.where(y_raw == "overload", 1.5, 0.1)
            + np.random.randn(n) * 0.2,
            "xfmr_recon_err": np.where(y_raw == "transformer_failure", 2.0, 0.1)
            + np.random.randn(n) * 0.2,
            "meter_recon_err": np.where(y_raw == "energy_theft", 1.8, 0.1)
            + np.random.randn(n) * 0.2,
            "pinn_ohm_viol": np.where(y_raw == "energy_theft", 0.7, 0.05)
            + np.random.randn(n) * 0.05,
            "pinn_power_viol": np.where(y_raw == "overload", 0.6, 0.05)
            + np.random.randn(n) * 0.05,
            "pinn_kcl_viol": np.where(y_raw == "energy_theft", 0.8, 0.03)
            + np.random.randn(n) * 0.03,
            "pinn_thermal": np.where(y_raw == "transformer_failure", 0.9, 0.05)
            + np.random.randn(n) * 0.05,
            "pinn_composite": np.random.rand(n) * 0.3,
            "voltage_dev": np.where(y_raw == "voltage_sag", -0.12, 0.01)
            + np.random.randn(n) * 0.02,
            "load_pct": np.where(y_raw == "overload", 115.0, 45.0)
            + np.random.randn(n) * 5,
            "fault_type": y_raw,
            "fault_label": (y_raw != "normal").astype(int),
        }
    )
    features = features.clip(lower=0)

    split = int(0.8 * n)
    df_tr = features.iloc[:split]
    df_te = features.iloc[split:]

    clf = FaultClassifierRF(n_estimators=100)
    clf.train(df_tr)
    metrics = clf.evaluate(
        df_te.drop(columns=["fault_type", "fault_label"]).values,
        df_te["fault_type"].values,
    )

    # SHAP explanation for 3 samples
    X_sample = df_te.drop(columns=["fault_type", "fault_label"]).values[:3]
    explanations = clf.predict_with_explanation(X_sample, top_k=3)
    print("\nSample Explanations:")
    for i, e in enumerate(explanations):
        print(
            f"\n  Sample {i+1}: {e['fault_type']} (conf={e['confidence']:.2f}, sev={e['severity']})"
        )
        for ex in e["explanation"]:
            print(
                f"    {ex['feature']:20s} | impact={ex['impact']:.4f} | {ex['direction']}"
            )

    imp = clf.get_feature_importance()
    print(f"\nTop-5 features: {imp['feature'].head(5).tolist()}")

    clf.save()
    print("\nRF Classifier test passed ✓")
