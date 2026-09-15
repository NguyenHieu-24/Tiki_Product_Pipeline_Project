import pandas as pd


def load_product_ids(csv_file):
    """
    Load product IDs from the first CSV column.

    Works both when the CSV has a header (e.g. product_id) and when it does not.
    Non-numeric rows are ignored and duplicate IDs are removed.
    """
    df = pd.read_csv(csv_file, header=None, dtype=str)

    if df.empty:
        return []

    series = df.iloc[:, 0].astype(str).str.strip()

    # Keep only integer-looking product IDs; this naturally skips a header row.
    series = series[series.str.fullmatch(r"\d+", na=False)]

    # Stable de-duplication.
    return list(dict.fromkeys(series.tolist()))
