# src/analytics/nn_search.py
import pandas as pd
from sklearn.neighbors import NearestNeighbors

def knn_search(
    X: pd.DataFrame,
    query_date: pd.Timestamp,
    k: int = 5,
    min_gap: int = 0          # blackout window (days)
) -> pd.DataFrame:
    """
    Return the k nearest neighbours that are at least `min_gap`
    calendar days away from `query_date`.
    """
    qts = pd.Timestamp(query_date)
    if qts not in X.index:
        raise ValueError("query_date not in feature matrix")

    # --------------------------------------------  gap filter
    if min_gap > 0:
        mask = (abs((X.index - qts).days) >= min_gap)
        X_train = X.loc[mask]
    else:
        X_train = X

    if len(X_train) < k:
        raise ValueError("Not enough historical rows after gap filter")

    nbrs = NearestNeighbors(n_neighbors=k, metric="euclidean")
    nbrs.fit(X_train.values)

    dists, idxs = nbrs.kneighbors(X.loc[[qts]].values, n_neighbors=k)
    neigh_dates = X_train.index[idxs[0]]

    return pd.DataFrame({"Date": neigh_dates,
                         "Distance": dists[0]}).set_index("Date")
