"""
nn_search.py – thin wrapper around sklearn NearestNeighbors.
"""

import pandas as pd
from sklearn.neighbors import NearestNeighbors

def knn_search(X: pd.DataFrame, query_date: pd.Timestamp, k: int = 5):
    """
    Returns DataFrame of neighbours sorted by distance.
    """
    if query_date not in X.index:
        raise ValueError("query_date not in feature matrix")

    model = NearestNeighbors(n_neighbors=k+1, metric="euclidean")
    model.fit(X.values)

    idx = X.index.get_loc(query_date)
    dists, neigh_idx = model.kneighbors(X.iloc[[idx]].values, n_neighbors=k+1)

    # first neighbour is the query itself – drop it
    neigh_idx, dists = neigh_idx[0][1:], dists[0][1:]
    neigh_dates = X.index[neigh_idx]

    return pd.DataFrame({"Date": neigh_dates, "Distance": dists}).set_index("Date")
