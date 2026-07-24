import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    return df.to_csv(index=False).encode("utf-8")
