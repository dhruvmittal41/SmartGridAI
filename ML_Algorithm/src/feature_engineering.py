def create_features(df):

    df["hour"] = df["timestamp"].dt.hour

    df["power"] = df["voltage"] * df["current"]

    df["rolling_energy"] = df["energy_kwh"].rolling(5).mean()

    df = df.dropna()

    return df