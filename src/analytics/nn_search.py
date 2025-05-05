# src/analytics/nn_search.py
import pandas as pd
from sklearn.neighbors import NearestNeighbors

def knn_search(
    X: pd.DataFrame,
    query_date: pd.Timestamp,
    k: int = 5,
    min_gap: int = 30,          # blackout vs today
    dedup_gap: int = 7          # ensure neighbours ≥7 d apart
) -> pd.DataFrame:

    qts = pd.Timestamp(query_date)
    if qts not in X.index:
        raise ValueError("query_date not in feature matrix")

    base_mask = abs((X.index - qts).days) >= min_gap
    X_train = X.loc[base_mask]

    nbrs = NearestNeighbors(n_neighbors=min(k * 5, len(X_train)))
    nbrs.fit(X_train.values)

    dists, idxs = nbrs.kneighbors(X.loc[[qts]].values)
    cand_dates = X_train.index[idxs[0]]
    cand_dist  = dists[0]

    # --- de‑duplicate within ±dedup_gap days --------------------------
    keep_dates, keep_dist = [], []
    for d, dist in zip(cand_dates, cand_dist):
        if all(abs((d - kdt).days) >= dedup_gap for kdt in keep_dates):
            keep_dates.append(d)
            keep_dist.append(dist)
        if len(keep_dates) == k:
            break

    return pd.DataFrame({"Date": keep_dates,
                         "Distance": keep_dist}).set_index("Date")
