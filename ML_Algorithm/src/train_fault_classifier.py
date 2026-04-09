import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from preprocess import load_data
from feature_engineering import create_features
from create_labels import create_labels

df = load_data("../data/Bareilly_2020.csv")

df = create_features(df)

df = create_labels(df)

X = df[
    ["voltage", "current", "frequency", "energy_kwh", "power", "rolling_energy", "hour"]
]

y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier(n_estimators=200)

model.fit(X_train, y_train)

joblib.dump(model, "../models/classifier.pkl")
