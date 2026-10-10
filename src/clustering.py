from sklearn.cluster import KMeans


def run_kmeans(data, k=3):
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster = model.fit_predict(data)
    return model, cluster