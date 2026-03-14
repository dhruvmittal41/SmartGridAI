import os

os.environ["TF_USE_LEGACY_KERAS"] = "1"

import pandas as pd
import numpy as np
import joblib
import tensorflow as tf



lstm_model = tf.keras.models.load_model(
    "../models/lstm_autoencoder.keras",
    compile=False
)

classifier = joblib.load("../models/classifier.pkl")
scaler = joblib.load("../models/scaler.pkl")

try:
    threshold = joblib.load("../models/threshold.pkl")
except FileNotFoundError:
    print("Warning: threshold.pkl not found. Falling back to 0.05")
    threshold = 0.001



np.random.seed(42)
num_samples = 24


voltages = np.random.normal(230.0, 1.0, num_samples)
frequencies = np.random.normal(50.0, 0.05, num_samples)
energies = np.random.normal(0.005, 0.001, num_samples)
currents = np.random.normal(5.0, 0.5, num_samples)


voltages[6] = 190.0  
voltages[7] = 270.0  


frequencies[12] = 48.0 
frequencies[13] = 51.0 

energies[18] = 0.025 
energies[19] = 0.030 

mock_data = {
    "x_Timestamp": pd.date_range(start="2020-01-01 00:00:00", periods=num_samples, freq="h"),
    "t_kWh": energies,
    "Voltage": voltages,
    "Current": currents,
    "Frequency": frequencies,
    "meter": ["M1"] * num_samples
}

df = pd.DataFrame(mock_data)

df = df.rename(columns={
    "x_Timestamp": "timestamp",
    "t_kWh": "energy_kwh",
    "Voltage": "voltage",
    "Current": "current",
    "Frequency": "frequency",
    "meter": "meter_id"
})

df["timestamp"] = pd.to_datetime(df["timestamp"])



df["hour"] = df["timestamp"].dt.hour
df["power"] = df["voltage"] * df["current"]
df["rolling_energy"] = df["energy_kwh"].rolling(5).mean()


df = df.dropna()
df = df.reset_index(drop=True)



features = df[
    [
        "voltage",
        "current",
        "frequency",
        "energy_kwh",
        "power",
        "rolling_energy"
    ]
]

scaled = scaler.transform(features)

X = scaled.reshape((scaled.shape[0], 1, scaled.shape[1]))



reconstructed = lstm_model.predict(X, verbose=0)

reconstruction_error = np.mean(np.abs(reconstructed - X), axis=(1, 2))

df["reconstruction_error"] = reconstruction_error
df["anomaly"] = reconstruction_error > threshold



classification_features = df[
    [
        "voltage",
        "current",
        "frequency",
        "energy_kwh",
        "power",
        "rolling_energy",
        "hour"
    ]
]

results = []

for i, row in df.iterrows():

    if row["anomaly"]:

        pred = classifier.predict([[
            row["voltage"],
            row["current"],
            row["frequency"],
            row["energy_kwh"],
            row["power"],
            row["rolling_energy"],
            row["hour"]
        ]])
    
        results.append(pred[0])

    else:

        results.append("normal")

df["prediction"] = results



print("\n===== MODEL TEST RESULTS =====\n")

print(df[[
    "timestamp",
    "voltage",
    "frequency",
    "energy_kwh",
    "prediction"
]].head(20))



print("\nPrediction counts:\n")
print(df["prediction"].value_counts())