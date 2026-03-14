import pandas as pd

def load_data(path):

    df = pd.read_csv(path)

    df = df.rename(columns={
        "x_Timestamp":"timestamp",
        "t_kWh":"energy_kwh",
        "Voltage":"voltage",
        "Current":"current",
        "Frequency":"frequency",
        "meter":"meter_id"
    })

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = df.dropna()

    return df