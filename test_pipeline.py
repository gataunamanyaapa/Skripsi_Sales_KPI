from src.preprocessing import load_data, select_features, scale_data
from src.clustering import run_kmeans


# 1. Load data
df = load_data()

print("DAFTAR KOLOM:")
print(df.columns)

# 2. Feature engineering
features = select_features(df)

# 3. Scaling
scaled = scale_data(features)

# 4. Clustering
model, cluster = run_kmeans(scaled)

# 5. Assign cluster ke data agregasi (BENAR)
features['cluster'] = cluster

# 6. Preview
print("\nSample Data:")
print(features.head())

# 7. Analisis cluster
print("\nRata-rata tiap cluster:")
print(features.groupby("cluster").mean())

# 8. Simpan hasil
features.to_excel("hasil_clustering.xlsx", index=False)

print("\n✅ Clustering selesai, file tersimpan: hasil_clustering.xlsx")