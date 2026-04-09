"""
lstm_models.py
==============
Three LSTM autoencoder models — one per grid asset type.

Architecture: LSTM Autoencoder (unsupervised anomaly detection).
  - Trained ONLY on normal (label=0) data.
  - At inference, reconstruction error on unseen data is the anomaly score.
  - High reconstruction error → the sequence is unlike anything seen in normal ops.

Why autoencoders instead of supervised?
  Grid fault data is heavily imbalanced (normal >> faulty).
  Autoencoders sidestep this by learning the manifold of normal behaviour.
  Any deviation from that manifold produces a high MSE score.

Models
------
  SubstationLSTM   — temporal pattern anomaly (sparse features + time)
  TransformerLSTM  — winding temp, load, thermal stress
  MeterLSTM        — kWh, V, I, f + derived physics features (Kaggle dataset)
  MeterGridLabLSTM — feeder loss, voltage deviation, theft features

Usage
-----
  model = SubstationLSTM()
  model.train(X_train_normal)
  scores = model.predict_anomaly_scores(X_test)
  threshold = model.compute_threshold(X_train_normal, percentile=95)
"""

import os
import numpy as np
import joblib
import warnings

warnings.filterwarnings("ignore")

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (
    Input,
    LSTM,
    Dense,
    RepeatVector,
    TimeDistributed,
    Dropout,
    BatchNormalization,
)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "saved")
os.makedirs(MODELS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# BASE CLASS
# ─────────────────────────────────────────────────────────────────────────────


class BaseLSTMAutoencoder:
    """
    Shared LSTM autoencoder logic.
    Subclasses override `model_name`, `seq_len`, and `n_features`.
    """

    model_name = "base_lstm"
    seq_len = 48
    n_features = 4
    latent_dim = 32  # bottleneck LSTM units
    epochs = 50
    batch_size = 64
    lr = 1e-3

    def __init__(self):
        self.model: tf.keras.Model = None
        self.threshold: float = None
        self._built: bool = False

    def build(self, seq_len: int = None, n_features: int = None):
        """
        LSTM Autoencoder:
          Encoder: LSTM(64) → LSTM(latent_dim)
          RepeatVector → replicate latent for each timestep
          Decoder: LSTM(latent_dim) → LSTM(64) → TimeDistributed Dense → reconstruction
        """
        seq_len = seq_len or self.seq_len
        n_features = n_features or self.n_features

        inp = Input(shape=(seq_len, n_features), name="encoder_input")

        # ── Encoder ─────────────────────────────────────────────────────────
        x = LSTM(64, return_sequences=True, name="enc_lstm1")(inp)
        x = BatchNormalization()(x)
        x = Dropout(0.20)(x)
        x = LSTM(self.latent_dim, return_sequences=False, name="enc_lstm2")(x)

        # ── Bottleneck ───────────────────────────────────────────────────────
        x = RepeatVector(seq_len, name="bottleneck")(x)

        # ── Decoder ─────────────────────────────────────────────────────────
        x = LSTM(self.latent_dim, return_sequences=True, name="dec_lstm1")(x)
        x = Dropout(0.20)(x)
        x = LSTM(64, return_sequences=True, name="dec_lstm2")(x)
        out = TimeDistributed(
            Dense(n_features, activation="linear"), name="reconstruction"
        )(x)

        self.model = Model(inputs=inp, outputs=out, name=self.model_name)
        self.model.compile(
            optimizer=Adam(learning_rate=self.lr), loss="mse", metrics=["mae"]
        )
        self._built = True
        print(f"[{self.model_name}] Built: input=({seq_len}, {n_features})")
        return self

    def train(self, X_normal: np.ndarray, X_val: np.ndarray = None, verbose: int = 1):
        """
        Train autoencoder on normal-only data.
        The model learns to reconstruct normal patterns;
        anomalies will have high reconstruction error.

        Parameters
        ----------
        X_normal : (N, seq_len, n_features) — normal sequences only
        X_val    : optional validation set
        """
        if not self._built:
            self.build(X_normal.shape[1], X_normal.shape[2])

        if X_val is None:
            n_val = max(1, int(len(X_normal) * 0.10))
            X_val = X_normal[-n_val:]
            X_normal = X_normal[:-n_val]

        callbacks = [
            EarlyStopping(
                patience=8,
                restore_best_weights=True,
                monitor="val_loss",
                verbose=verbose,
            ),
            ReduceLROnPlateau(
                patience=4, factor=0.5, min_lr=1e-5, monitor="val_loss", verbose=verbose
            ),
            ModelCheckpoint(
                filepath=os.path.join(MODELS_DIR, f"{self.model_name}_best.keras"),
                save_best_only=True,
                monitor="val_loss",
                verbose=0,
            ),
        ]

        history = self.model.fit(
            X_normal,
            X_normal,  # autoencoder: input == target
            validation_data=(X_val, X_val),
            epochs=self.epochs,
            batch_size=self.batch_size,
            callbacks=callbacks,
            verbose=verbose,
        )
        print(
            f"[{self.model_name}] Training done. "
            f"Best val_loss={min(history.history['val_loss']):.6f}"
        )
        return history

    def reconstruction_errors(self, X: np.ndarray) -> np.ndarray:
        """
        Returns per-sample mean squared reconstruction error.
        Shape: (N,)
        """
        X_hat = self.model.predict(X, batch_size=128, verbose=0)
        mse = np.mean(np.square(X - X_hat), axis=(1, 2))
        return mse

    def compute_threshold(
        self, X_normal: np.ndarray, percentile: float = 95.0
    ) -> float:
        """
        Set anomaly threshold from normal data distribution.
        A sample is anomalous if its MSE > threshold.
        percentile=95 means we accept 5% false positive rate.
        """
        errors = self.reconstruction_errors(X_normal)
        self.threshold = float(np.percentile(errors, percentile))
        print(
            f"[{self.model_name}] Threshold @ p{percentile:.0f}: "
            f"{self.threshold:.6f}  "
            f"(mean={errors.mean():.6f}, std={errors.std():.6f})"
        )
        return self.threshold

    def predict_anomaly_scores(
        self, X: np.ndarray, normalise: bool = True
    ) -> np.ndarray:
        """
        Returns anomaly scores in [0, inf) or [0, 1] if normalised.
        Score > threshold → anomaly detected.
        """
        errors = self.reconstruction_errors(X)
        if normalise and self.threshold and self.threshold > 0:
            return errors / (self.threshold + 1e-10)
        return errors

    def predict_binary(self, X: np.ndarray) -> np.ndarray:
        """Returns binary labels: 1=anomaly, 0=normal."""
        if self.threshold is None:
            raise RuntimeError("Call compute_threshold() before predict_binary()")
        return (self.reconstruction_errors(X) > self.threshold).astype(int)

    def save(self, path: str = None):
        path = path or os.path.join(MODELS_DIR, f"{self.model_name}.keras")
        self.model.save(path)
        meta = {"threshold": self.threshold, "model_name": self.model_name}
        joblib.dump(meta, path.replace(".keras", "_meta.pkl"))
        print(f"[{self.model_name}] Saved to {path}")

    def load(self, path: str = None):
        path = path or os.path.join(MODELS_DIR, f"{self.model_name}.keras")
        self.model = load_model(path)
        meta = joblib.load(path.replace(".keras", "_meta.pkl"))
        self.threshold = meta["threshold"]
        self._built = True
        print(f"[{self.model_name}] Loaded from {path}  threshold={self.threshold:.6f}")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# 1. SUBSTATION LSTM
# ─────────────────────────────────────────────────────────────────────────────


class SubstationLSTM(BaseLSTMAutoencoder):
    """
    Monitors substation temporal patterns.
    Features: hour_sin, hour_cos, day_sin, day_cos  (+ any added electrical readings)
    Learns normal diurnal and weekly patterns of substation operation.
    Anomalies = unusual patterns outside normal operating hours or load cycles.
    """

    model_name = "substation_lstm"
    seq_len = 48
    n_features = 4  # cyclic time features
    latent_dim = 16  # smaller bottleneck → tighter normal manifold
    epochs = 40
    batch_size = 32


# ─────────────────────────────────────────────────────────────────────────────
# 2. TRANSFORMER LSTM
# ─────────────────────────────────────────────────────────────────────────────


class TransformerLSTM(BaseLSTMAutoencoder):
    """
    Monitors transformer health.
    Features: winding_temp_C, load_pct, thermal_margin_C,
              thermal_stress (load²/margin), temp_grad,
              hour_sin, hour_cos, day_sin, day_cos
    Key failure mode: winding temperature exceeding rated limit under overload.
    The LSTM learns normal thermal cycling patterns; rapid rises are anomalies.
    """

    model_name = "transformer_lstm"
    seq_len = 48
    n_features = 9
    latent_dim = 32
    epochs = 50
    batch_size = 64


# ─────────────────────────────────────────────────────────────────────────────
# 3. METER LSTM (Kaggle Indian Smart Meter)
# ─────────────────────────────────────────────────────────────────────────────


class MeterLSTM(BaseLSTMAutoencoder):
    """
    Monitors individual smart meter readings.
    Features: kWh, Voltage, Current, Frequency,
              apparent_VA, pf_est, voltage_dev, freq_dev,
              kwh_zscore, hour_sin, hour_cos, day_sin, day_cos

    Key failure modes:
      - Energy theft: kWh drop while apparent power stays normal
      - Tampered meter: V/I relationship breaks Ohm's law
      - Phase imbalance: abnormal frequency deviation

    The PINN layer adds an additional signal for energy theft detection:
    if the meter LSTM is normal but KCL is violated → likely theft.
    """

    model_name = "meter_lstm"
    seq_len = 60  # 60 × 3min = 3 hours
    n_features = 13
    latent_dim = 48
    epochs = 60
    batch_size = 128


# ─────────────────────────────────────────────────────────────────────────────
# 4. METER GRIDLAB LSTM (feeder / loss data)
# ─────────────────────────────────────────────────────────────────────────────


class MeterGridLabLSTM(BaseLSTMAutoencoder):
    """
    Monitors feeder-level meter data from GridLAB-D.
    Features: feeder_power_W, total_reported_W, loss_ratio,
              apparent_loss, log_excess, loss_trend,
              end_feeder_voltage_V, voltage_deviation_pct, undervoltage_flag,
              hour_sin, hour_cos, day_sin, day_cos

    This model is particularly sensitive to energy theft (excess loss)
    and voltage regulation problems.
    """

    model_name = "meter_gridlab_lstm"
    seq_len = 48
    n_features = 13
    latent_dim = 40
    epochs = 50
    batch_size = 64


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def train_model_on_normals(
    model_class: type,
    X_all: np.ndarray,
    y_all: np.ndarray,
    threshold_percentile: float = 95.0,
    verbose: int = 1,
) -> BaseLSTMAutoencoder:
    """
    Convenience function:
      1. Filters X_all to normal-only rows (y_all == 0)
      2. Builds and trains the autoencoder
      3. Computes threshold from the normal training set
      4. Saves model and threshold to disk

    Parameters
    ----------
    model_class          : e.g. SubstationLSTM
    X_all                : (N, seq_len, n_features) — all sequences
    y_all                : (N,) — binary labels (0=normal, 1=fault)
    threshold_percentile : anomaly threshold percentile on normal data

    Returns trained model instance.
    """
    # Filter to normal only for training (unsupervised anomaly detection principle)
    normal_mask = y_all == 0
    X_normal = X_all[normal_mask]

    if len(X_normal) < 10:
        print(
            f"WARNING: Only {len(X_normal)} normal samples found. "
            "Training on all data."
        )
        X_normal = X_all

    model = model_class()
    model.build(X_normal.shape[1], X_normal.shape[2])
    model.train(X_normal, verbose=verbose)
    model.compute_threshold(X_normal, percentile=threshold_percentile)
    model.save()
    return model


def evaluate_model(
    model: BaseLSTMAutoencoder, X_test: np.ndarray, y_test: np.ndarray
) -> dict:
    """
    Evaluate anomaly detection performance.
    Returns precision, recall, F1, AUC metrics.
    """
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

    scores = model.reconstruction_errors(X_test)
    y_pred = (scores > model.threshold).astype(int)

    metrics = {}
    try:
        metrics["auc"] = roc_auc_score(y_test, scores)
    except Exception:
        metrics["auc"] = 0.0

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    metrics["precision"] = report.get("1", {}).get("precision", 0)
    metrics["recall"] = report.get("1", {}).get("recall", 0)
    metrics["f1"] = report.get("1", {}).get("f1-score", 0)
    metrics["accuracy"] = report.get("accuracy", 0)

    print(f"\n[{model.model_name}] Evaluation:")
    print(
        f"  AUC={metrics['auc']:.3f}  P={metrics['precision']:.3f}  "
        f"R={metrics['recall']:.3f}  F1={metrics['f1']:.3f}"
    )
    cm = confusion_matrix(y_test, y_pred)
    print(f"  Confusion matrix:\n{cm}")
    return metrics


# ── Quick build test (no data needed) ────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("LSTM MODEL BUILD TEST")
    print("=" * 55)
    np.random.seed(42)

    for cls, sl, nf in [
        (SubstationLSTM, 48, 4),
        (TransformerLSTM, 48, 9),
        (MeterLSTM, 60, 13),
        (MeterGridLabLSTM, 48, 13),
    ]:
        model = cls()
        model.build(sl, nf)
        model.model.summary(print_fn=lambda x: None)  # silent
        # Quick forward pass
        dummy = np.random.randn(8, sl, nf).astype(np.float32)
        out = model.model.predict(dummy, verbose=0)
        assert out.shape == dummy.shape, f"Shape mismatch: {out.shape} != {dummy.shape}"
        print(f"  {cls.__name__}: input={dummy.shape} → output={out.shape} ✓")

    print("\nAll LSTM models built successfully ✓")
