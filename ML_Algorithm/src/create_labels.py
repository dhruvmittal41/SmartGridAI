def create_labels(df):

    labels = []

    for _, row in df.iterrows():

        if row["voltage"] < 210 or row["voltage"] > 260:
            labels.append("fault")

        elif row["frequency"] < 49.5 or row["frequency"] > 50.5:
            labels.append("grid_fault")

        elif row["energy_kwh"] > 0.01:
            labels.append("theft")

        else:
            labels.append("normal")

    df["label"] = labels

    return df
