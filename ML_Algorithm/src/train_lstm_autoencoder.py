import os

os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import numpy as np
import tensorflow as tf
import tf_keras as keras
from tf_keras import layers
from sklearn.preprocessing import StandardScaler
import joblib

from preprocess import load_data
from feature_engineering import create_features


def main():
  
    df = load_data("../data/Bareilly_2020.csv")
    df = create_features(df)

    feature_cols = [
        "voltage", 
        "current", 
        "frequency", 
        "energy_kwh", 
        "power", 
        "rolling_energy"
    ]
    features = df[feature_cols]

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    X_reshaped = X.reshape((X.shape[0], 1, X.shape[1]))

    model = keras.Sequential([
        layers.InputLayer(input_shape=(1, X_reshaped.shape[2])),
        layers.LSTM(32, activation="relu", return_sequences=True),
        layers.LSTM(16, activation="relu"),
        
        layers.RepeatVector(1),
        
        layers.LSTM(16, activation="relu", return_sequences=True),
        layers.LSTM(32, activation="relu", return_sequences=True),
        
        layers.TimeDistributed(layers.Dense(X_reshaped.shape[2]))
    ])

    model.compile(optimizer="adam", loss="mse")

    print("Starting training with tf_keras...")
    model.fit(
        X_reshaped, X_reshaped,
        epochs=20,
        batch_size=128,
        validation_split=0.1,
        verbose=1
    )

  
    print("\nCalculating reconstruction error threshold from training data...")
  
    reconstructed_X = model.predict(X_reshaped, verbose=0)

    reconstruction_errors = np.mean(np.abs(reconstructed_X - X_reshaped), axis=(1, 2))
    

    threshold = np.mean(reconstruction_errors) + 3 * np.std(reconstruction_errors)
    print(f"Calculated Threshold: {threshold:.5f}")


    os.makedirs("../models", exist_ok=True)
    model.save("../models/lstm_autoencoder.keras")
    joblib.dump(scaler, "../models/scaler.pkl")
    joblib.dump(threshold, "../models/threshold.pkl")
    
    print("Model, scaler, and threshold saved successfully in ../models/")

if __name__ == "__main__":
    main()