import os

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import pandas as pd
import joblib
import tensorflow as tf


class GridPredictor:
    def __init__(self):
        print("Loading models into memory...")
        self.lstm_model = tf.keras.models.load_model(
            "/Users/namanmittal/Desktop/SmartGridAI/ML_Algorithm/models/lstm_autoencoder.keras",
            compile=False,
        )
        self.classifier = joblib.load(
            "/Users/namanmittal/Desktop/SmartGridAI/ML_Algorithm/models/classifier.pkl"
        )
        self.scaler = joblib.load(
            "/Users/namanmittal/Desktop/SmartGridAI/ML_Algorithm/models/scaler.pkl"
        )

        try:
            self.threshold = joblib.load(
                "/Users/namanmittal/Desktop/SmartGridAI/ML_Algorithm/models/threshold.pkl"
            )
        except FileNotFoundError:
            self.threshold = 0.05
        print("Models loaded successfully.")

    def predict(self, data_point: dict) -> dict:
        """
        Expects a dict with: voltage, current, frequency, energy_kwh, timestamp
        """
        power = data_point["voltage"] * data_point["current"]
        hour = pd.to_datetime(data_point["timestamp"]).hour

        scaler_cols = [
            "voltage",
            "current",
            "frequency",
            "energy_kwh",
            "power",
            "rolling_energy",
        ]
        classifier_cols = [
            "voltage",
            "current",
            "frequency",
            "energy_kwh",
            "power",
            "rolling_energy",
            "hour",
        ]

        features_df = pd.DataFrame(
            [
                [
                    data_point["voltage"],
                    data_point["current"],
                    data_point["frequency"],
                    data_point["energy_kwh"],
                    power,
                    data_point["energy_kwh"],
                ]
            ],
            columns=scaler_cols,
        )

        scaled = self.scaler.transform(features_df)
        X = scaled.reshape((1, 1, 6))

        reconstructed = self.lstm_model.predict(X, verbose=0)
        reconstruction_error = np.mean(np.abs(reconstructed - X))
        is_anomaly = bool(reconstruction_error > self.threshold)

        base_power = power
        forecast_data = []
        for i in range(1, 6):

            future_power = base_power + np.random.normal(0, 0.5)
            forecast_data.append(
                {"step": f"+{i}h", "predicted_power": round(future_power, 2)}
            )

        prediction_label = "normal"
        if is_anomaly:

            class_features_df = pd.DataFrame(
                [
                    [
                        data_point["voltage"],
                        data_point["current"],
                        data_point["frequency"],
                        data_point["energy_kwh"],
                        power,
                        data_point["energy_kwh"],
                        hour,
                    ]
                ],
                columns=classifier_cols,
            )

            pred = self.classifier.predict(class_features_df)[0]
            prediction_label = pred

        return {
            "timestamp": data_point["timestamp"],
            "meter_id": data_point["meter_id"],
            "raw_metrics": {
                "voltage": round(data_point["voltage"], 2),
                "current": round(data_point["current"], 2),
                "frequency": round(data_point["frequency"], 2),
                "energy_kwh": round(data_point["energy_kwh"], 4),
                "power": round(power, 2),
            },
            "ml_analysis": {
                "reconstruction_error": round(float(reconstruction_error), 4),
                "is_anomaly": is_anomaly,
                "status": prediction_label,
            },
            "forecast": forecast_data,
        }
