import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN

def detect_outliers(df, eps=0.5, min_samples=5):
    try:
        coords = df[["decimalLatitude", "decimalLongitude"]].dropna()

        if len(coords) < min_samples:
            return pd.Series(False, index=df.index)

        scaler = StandardScaler()
        coords_scaled = scaler.fit_transform(coords)

        db = DBSCAN(eps=eps, min_samples=min_samples)
        labels = db.fit_predict(coords_scaled)

        # -1 = outlier in DBSCAN
        outlier_mask = pd.Series(labels == -1, index=coords.index)

        # align back to full df index
        result = pd.Series(False, index=df.index)
        result.update(outlier_mask)

        return result

    except Exception:
        return pd.Series(False, index=df.index)


def outlier_summary(outlier_mask):
    total    = len(outlier_mask)
    n_out    = int(outlier_mask.sum())
    n_clean  = total - n_out
    pct      = round(n_out / total * 100, 1) if total > 0 else 0

    return {
        "total"         : total,
        "outliers"      : n_out,
        "clean"         : n_clean,
        "outlier_pct"   : pct
    }