# ============================================================
# app.py  —  Gelatik Dashboard  (K-Means Dinamis)
# K optimal dipilih via voting: Silhouette, Davies-Bouldin,
# Calinski-Harabasz — sama persis dengan notebook ipynb.
# Clustering berjalan di background thread agar Flask tidak crash.
# Label cluster otomatis berdasarkan profil Visit vs KPI.
# ============================================================

import os, json, warnings, threading, time
import pandas as pd
import numpy as np
from flask import (
    Flask, render_template, send_file,
    request, redirect, url_for, flash, jsonify,
)
from collections import Counter

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "gelatik-dashboard-2025"

# ── Base directory ────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def base(filename: str) -> str:
    return os.path.join(BASE_DIR, filename)

# ── Path file ─────────────────────────────────────────────────
RAW_DATA_PATH = base("Report_Clean.xlsx")
META_PATH     = base("cluster_meta.json")
STATUS_PATH   = base("cluster_status.json")

_output_excel_path = base("hasil_clustering.xlsx")

# ── Konstanta fitur ───────────────────────────────────────────
FEATURE_COLS = ["visit_count", "Facing", "Is FIFO/FEFO", "Is Price Tag Available"]
KPI_COLS     = ["Facing", "Is FIFO/FEFO", "Is Price Tag Available"]

# Palet warna per label profil
PROFILE_PALETTE = {
    "High Visit High KPI" : {"title": "#D94715", "bar": "#F15A29", "dot": "#F15A29"},
    "High Visit Low KPI"  : {"title": "#C89400", "bar": "#FBBC05", "dot": "#FBBC05"},
    "Low Visit High KPI"  : {"title": "#2C6FAC", "bar": "#4A90D9", "dot": "#4A90D9"},
    "Low Visit Low KPI"   : {"title": "#6b7280", "bar": "#9ca3af", "dot": "#9ca3af"},
    # Tier generik fallback (k>4 atau campuran)
    "Tier 1" : {"title": "#D94715", "bar": "#F15A29", "dot": "#F15A29"},
    "Tier 2" : {"title": "#C89400", "bar": "#FBBC05", "dot": "#FBBC05"},
    "Tier 3" : {"title": "#2C6FAC", "bar": "#4A90D9", "dot": "#4A90D9"},
    "Tier 4" : {"title": "#15803d", "bar": "#22c55e", "dot": "#22c55e"},
    "Tier 5" : {"title": "#7c3aed", "bar": "#a78bfa", "dot": "#a78bfa"},
}
DEFAULT_COLOR = {"title": "#6b7280", "bar": "#9ca3af", "dot": "#9ca3af"}


# ════════════════════════════════════════════════════════════
# AUTO-LABEL: tentukan nama cluster berdasarkan profil visit vs KPI
# ════════════════════════════════════════════════════════════

def _auto_label_clusters(cluster_stats: pd.DataFrame) -> dict:
    """
    cluster_stats: DataFrame dengan index=cluster_id, kolom:
        visit_mean, kpi_mean  (nilai sudah dinormalisasi 0-1)

    Return: dict {cluster_id: label_string}

    Logika:
    - Hitung median visit dan KPI di seluruh cluster
    - Tiap cluster diberi 2 dimensi: Visit (High/Low) dan KPI (High/Low)
    - Gabung jadi label "High Visit High KPI" dst.
    - Jika k > 4 → gunakan kuartil / percentile untuk membagi lebih halus
    """
    n = len(cluster_stats)
    visit_med = cluster_stats["visit_mean"].median()
    kpi_med   = cluster_stats["kpi_mean"].median()

    labels = {}
    for cid, row in cluster_stats.iterrows():
        v_tag = "High Visit" if row["visit_mean"] >= visit_med else "Low Visit"
        k_tag = "High KPI"   if row["kpi_mean"]  >= kpi_med   else "Low KPI"
        labels[cid] = f"{v_tag} {k_tag}"

    # Jika ada duplikat label (bisa terjadi saat k>4), tambahkan suffix angka
    seen = Counter()
    final = {}
    for cid, lbl in labels.items():
        seen[lbl] += 1
        final[cid] = lbl

    # Resolve duplikat: tambah " (2)", " (3)" dst.
    count = Counter()
    resolved = {}
    for cid, lbl in final.items():
        count[lbl] += 1
    occurrences = Counter()
    for cid, lbl in final.items():
        if count[lbl] > 1:
            occurrences[lbl] += 1
            resolved[cid] = f"{lbl} ({occurrences[lbl]})"
        else:
            resolved[cid] = lbl

    return resolved


def _label_order_by_priority(labels: dict, cluster_stats: pd.DataFrame) -> list:
    """
    Urutan tampilan: High Visit High KPI → High Visit Low KPI →
                     Low Visit High KPI  → Low Visit Low KPI
    Dalam grup yang sama, urutkan descending by visit_mean.
    """
    priority = {
        "High Visit High KPI": 0,
        "High Visit Low KPI" : 1,
        "Low Visit High KPI" : 2,
        "Low Visit Low KPI"  : 3,
    }
    def sort_key(cid):
        lbl = labels[cid]
        # strip suffix "(2)" dst. untuk lookup priority
        base_lbl = lbl.split(" (")[0]
        p = priority.get(base_lbl, 9)
        visit = cluster_stats.loc[cid, "visit_mean"]
        return (p, -visit)

    sorted_cids = sorted(labels.keys(), key=sort_key)
    return [labels[cid] for cid in sorted_cids], sorted_cids


# ════════════════════════════════════════════════════════════
# INTERPRETASI NARATIF per profil label
# ════════════════════════════════════════════════════════════

_TIER_INTERP = {
    "High Visit High KPI": {
        "ringkasan"   : "Karyawan bintang — frekuensi kunjungan tinggi DAN kepatuhan KPI sangat baik.",
        "visit"       : "Kunjungan toko sangat aktif dan konsisten setiap periode.",
        "facing"      : "Penataan produk (facing) dilakukan dengan baik dan sesuai standar planogram.",
        "fifo"        : "Rotasi stok FIFO/FEFO dijalankan dengan disiplin dan benar.",
        "price_tag"   : "Label harga selalu tersedia dan terpantau di setiap kunjungan.",
        "rekomendasi" : "Pertahankan standar kerja. Jadikan referensi dan mentor bagi karyawan lain.",
    },
    "High Visit Low KPI": {
        "ringkasan"   : "Karyawan rajin hadir di lapangan namun kualitas eksekusi KPI masih perlu ditingkatkan.",
        "visit"       : "Frekuensi kunjungan tinggi — aktif di lapangan setiap hari.",
        "facing"      : "Penataan produk sering terlewat meski kunjungan sudah sering — perlu fokus saat di toko.",
        "fifo"        : "Rotasi stok FIFO/FEFO belum konsisten dilakukan — perlu diingatkan prosedurnya.",
        "price_tag"   : "Label harga sering tidak dipasang/dicek meski kunjungan berjalan — perlu penekanan checklist.",
        "rekomendasi" : "Latih kualitas eksekusi saat kunjungan. Gunakan checklist KPI wajib di setiap kunjungan.",
    },
    "Low Visit High KPI": {
        "ringkasan"   : "Karyawan dengan kepatuhan KPI tinggi namun frekuensi kunjungan masih rendah.",
        "visit"       : "Frekuensi kunjungan rendah — jumlah toko yang dikunjungi perlu ditingkatkan.",
        "facing"      : "Saat berkunjung, penataan produk dilakukan dengan baik dan sesuai standar.",
        "fifo"        : "Rotasi stok FIFO/FEFO dijalankan dengan benar setiap kali kunjungan.",
        "price_tag"   : "Label harga selalu dipasang saat kunjungan — kualitas eksekusi baik.",
        "rekomendasi" : "Tingkatkan jumlah dan frekuensi kunjungan toko. Kualitas sudah baik — fokus pada kuantitas.",
    },
    "Low Visit Low KPI": {
        "ringkasan"   : "Karyawan dengan performa terendah — kunjungan jarang DAN kualitas KPI rendah.",
        "visit"       : "Frekuensi kunjungan sangat rendah — banyak toko tidak terlayani.",
        "facing"      : "Penataan produk hampir tidak dilakukan — rak tidak terkelola dengan baik.",
        "fifo"        : "Rotasi stok FIFO/FEFO sangat rendah — risiko produk kadaluarsa tinggi.",
        "price_tag"   : "Label harga sering tidak tersedia — berpotensi kehilangan penjualan.",
        "rekomendasi" : "Perlu pendampingan intensif, evaluasi hambatan lapangan, dan monitoring mingguan.",
    },
}

def _tier_generic_interp(label: str, rank: int, total_k: int) -> dict:
    base_lbl = label.split(" (")[0]
    if base_lbl in _TIER_INTERP:
        d = dict(_TIER_INTERP[base_lbl])
        d["ringkasan"] = f"[Varian {label}] " + d["ringkasan"]
        return d
    pct = round((total_k - rank) / total_k * 100)
    return {
        "ringkasan"   : f"{label} — persentil performa {pct}% teratas.",
        "visit"       : "Lihat rata-rata visit count pada kartu KPI.",
        "facing"      : "Lihat rata-rata facing compliance pada kartu KPI.",
        "fifo"        : "Lihat rata-rata FIFO/FEFO compliance pada kartu KPI.",
        "price_tag"   : "Lihat rata-rata price tag compliance pada kartu KPI.",
        "rekomendasi" : "Bandingkan dengan cluster lain untuk menentukan area prioritas perbaikan.",
    }

def _get_tier_interpretation(label: str, rank: int, total_k: int) -> dict:
    if label in _TIER_INTERP:
        return _TIER_INTERP[label]
    return _tier_generic_interp(label, rank, total_k)


# ── Lock ─────────────────────────────────────────────────────
_cluster_lock = threading.Lock()


# ════════════════════════════════════════════════════════════
# STATUS FILE
# ════════════════════════════════════════════════════════════

def write_status(state: str, message: str = "", progress: int = 0):
    data = {"state": state, "message": message, "progress": progress, "ts": time.time()}
    try:
        with open(STATUS_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def read_status() -> dict:
    if not os.path.exists(STATUS_PATH):
        return {"state": "idle", "message": "", "progress": 0}
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except Exception:
        return {"state": "idle", "message": "", "progress": 0}


# ════════════════════════════════════════════════════════════
# PIPELINE CLUSTERING
# ════════════════════════════════════════════════════════════

def _run_clustering_task(source_path: str):
    global _output_excel_path

    if not _cluster_lock.acquire(blocking=False):
        write_status("error", "Clustering sedang berjalan, coba lagi nanti.", 0)
        return

    try:
        write_status("running", "Memuat library…", 5)
        from sklearn.preprocessing import MinMaxScaler
        from sklearn.cluster import KMeans
        from sklearn.metrics import (
            silhouette_score, silhouette_samples,
            davies_bouldin_score, calinski_harabasz_score,
        )

        # ── 1. Baca file ──────────────────────────────────────
        write_status("running", "Membaca data…", 15)
        if not os.path.exists(source_path):
            write_status("error", f"File tidak ditemukan: {source_path}", 0)
            return

        ext = os.path.splitext(source_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(source_path, engine="openpyxl")
        else:
            df = pd.read_csv(source_path, low_memory=False, sep=None, engine="python")

        required = {"Username", "Report Product", "Facing",
                    "Is FIFO/FEFO", "Is Price Tag Available"}
        missing_cols = required - set(df.columns)
        if missing_cols:
            write_status("error",
                f"Kolom wajib tidak ada: {', '.join(sorted(missing_cols))}", 0)
            return

        # ── 2. Preprocessing & Cleaning ───────────────────────
        write_status("running", "Preprocessing & cleaning data…", 25)
        df["Report Product"] = pd.to_datetime(df["Report Product"], errors="coerce")
        df["Facing"]        = pd.to_numeric(df["Facing"], errors="coerce").fillna(0).clip(lower=0)
        df["Is FIFO/FEFO"]           = df["Is FIFO/FEFO"].astype(str).str.upper().str.strip()
        df["Is Price Tag Available"] = df["Is Price Tag Available"].astype(str).str.upper().str.strip()

        n_before = len(df)
        df = df[df["Username"].astype(str).str.match(r"^ID-", na=False)].copy()
        if len(df) < n_before:
            print(f"[Filter-1] {n_before - len(df)} baris dibuang — Username bukan format ID-xxx")

        mask_neg1 = df["Is FIFO/FEFO"] == "-1"
        if mask_neg1.sum():
            print(f"[Filter-2] {mask_neg1.sum()} baris dibuang — FIFO/FEFO = -1")
            df = df[~mask_neg1].copy()

        # FILTER 3 — Normalisasi KPI dengan mapping diperluas
        # Format YA  : 'YA', '1', 'TRUE', 'YES'
        # Format TIDAK: 'TIDAK', '0', 'FALSE', 'NO', 'N/A', dll.
        _MAP_YA = {"YA", "1", "TRUE", "YES"}

        def _norm_kpi(val: str) -> str:
            return "YA" if str(val).upper().strip() in _MAP_YA else "TIDAK"

        df["Is FIFO/FEFO"]           = df["Is FIFO/FEFO"].apply(_norm_kpi)
        df["Is Price Tag Available"] = df["Is Price Tag Available"].apply(_norm_kpi)

        if df.empty:
            write_status("error", "Tidak ada data karyawan valid setelah filtering.", 0)
            return

        # ── 3. Groupby per Username ───────────────────────────
        df_grouped = (
            df.groupby("Username")
            .agg(
                Facing      = ("Facing",                 "mean"),
                Is_FIFO     = ("Is FIFO/FEFO",           lambda x: (x == "YA").mean()),
                Is_PriceTag = ("Is Price Tag Available", lambda x: (x == "YA").mean()),
                visit_count = ("Report Product",          "count"),
            )
            .rename(columns={
                "Is_FIFO"    : "Is FIFO/FEFO",
                "Is_PriceTag": "Is Price Tag Available",
            })
            .reset_index()
            .fillna(0)
        )

        info_cols = ["Username"]
        for col in ["Nama Karyawan", "Area", "Region", "Role"]:
            if col in df.columns:
                info_cols.append(col)
        employee_info = df[info_cols].drop_duplicates("Username")

        if "Nama Store" in df.columns:
            store_map = (
                df.groupby("Username")["Nama Store"]
                .apply(lambda x: sorted(x.dropna().astype(str).unique().tolist()))
                .reset_index()
                .rename(columns={"Nama Store": "stores"})
            )
            employee_info = employee_info.merge(store_map, on="Username", how="left")
            employee_info["stores"] = employee_info["stores"].apply(
                lambda x: x if isinstance(x, list) else []
            )
        else:
            employee_info["stores"] = [[] for _ in range(len(employee_info))]

        if len(df_grouped) < 2:
            write_status("error",
                f"Data terlalu sedikit ({len(df_grouped)}) untuk clustering.", 0)
            return

        # ── 4. Scaling ────────────────────────────────────────
        write_status("running", "MinMax Scaling fitur…", 38)
        scaler   = MinMaxScaler()
        X_scaled = scaler.fit_transform(df_grouped[FEATURE_COLS])

        # ── 5. Evaluasi K range ───────────────────────────────
        write_status("running", "Mengevaluasi K=2…10 (Silhouette, DBI, CH)…", 50)
        k_max_valid = min(10, len(df_grouped) - 1)
        k_range_eff = range(2, k_max_valid + 1)

        inertia_list, sil_list, dbi_list, ch_list = [], [], [], []
        for k in k_range_eff:
            km     = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)
            inertia_list.append(km.inertia_)
            sil_list.append(silhouette_score(X_scaled, labels))
            dbi_list.append(davies_bouldin_score(X_scaled, labels))
            ch_list.append(calinski_harabasz_score(X_scaled, labels))

        best_sil_k = list(k_range_eff)[sil_list.index(max(sil_list))]
        best_dbi_k = list(k_range_eff)[dbi_list.index(min(dbi_list))]
        best_ch_k  = list(k_range_eff)[ch_list.index(max(ch_list))]

        votes      = [best_sil_k, best_dbi_k, best_ch_k]
        vote_count = Counter(votes)
        BEST_K     = vote_count.most_common(1)[0][0]
        if vote_count.most_common(1)[0][1] == 1:
            BEST_K = best_sil_k

        print(f"[Clustering] K optimal = {BEST_K}  "
              f"(sil={best_sil_k}, dbi={best_dbi_k}, ch={best_ch_k})")

        # ── 6. Training model final ───────────────────────────
        write_status("running", f"Training KMeans k={BEST_K}…", 65)
        kmeans_final = KMeans(n_clusters=BEST_K, random_state=42, n_init=10)
        labels_final = kmeans_final.fit_predict(X_scaled)
        df_grouped["cluster"] = labels_final

        # ── 7. AUTO-LABEL berdasarkan profil Visit vs KPI ─────
        write_status("running", "Menentukan label cluster otomatis (Visit vs KPI)…", 72)

        # Hitung KPI score per cluster = rata-rata Facing + FIFO + PriceTag (skala 0-1)
        # visit_mean juga dinormalisasi antar cluster untuk perbandingan relatif
        cluster_stats_raw = df_grouped.groupby("cluster").agg(
            visit_mean  = ("visit_count",              "mean"),
            facing_mean = ("Facing",                   "mean"),
            fifo_mean   = ("Is FIFO/FEFO",             "mean"),
            price_mean  = ("Is Price Tag Available",   "mean"),
        )
        cluster_stats_raw["kpi_mean"] = cluster_stats_raw[
            ["facing_mean", "fifo_mean", "price_mean"]
        ].mean(axis=1)

        # Normalisasi visit_mean dan kpi_mean ke 0-1 antar cluster
        # agar threshold median lebih adil
        def _norm_col(s: pd.Series) -> pd.Series:
            mn, mx = s.min(), s.max()
            if mx == mn:
                return pd.Series([0.5] * len(s), index=s.index)
            return (s - mn) / (mx - mn)

        cluster_stats_raw["visit_norm"] = _norm_col(cluster_stats_raw["visit_mean"])
        cluster_stats_raw["kpi_norm"]   = _norm_col(cluster_stats_raw["kpi_mean"])

        # Buat DataFrame untuk auto-label menggunakan nilai ternormalisasi
        cs_for_label = cluster_stats_raw[["visit_norm", "kpi_norm"]].rename(
            columns={"visit_norm": "visit_mean", "kpi_norm": "kpi_mean"}
        )
        rank_labels = _auto_label_clusters(cs_for_label)
        label_order_names, label_order_cids = _label_order_by_priority(rank_labels, cs_for_label)

        df_grouped["cluster_label"] = df_grouped["cluster"].map(rank_labels)

        print(f"[Clustering] Label otomatis: {rank_labels}")

        # ── 8. Evaluasi model ─────────────────────────────────
        write_status("running", "Menghitung metrik evaluasi…", 78)
        sil_score   = round(silhouette_score(X_scaled, labels_final),        4)
        dbi_score   = round(davies_bouldin_score(X_scaled, labels_final),    4)
        ch_score    = round(calinski_harabasz_score(X_scaled, labels_final), 2)
        sse         = round(kmeans_final.inertia_,                           2)
        sil_samples = silhouette_samples(X_scaled, labels_final)
        df_grouped["silhouette_sample"] = sil_samples.round(4)

        # ── 9. Simpan hasil ───────────────────────────────────
        write_status("running", "Menyimpan hasil ke Excel…", 90)
        final_df = employee_info.merge(df_grouped, on="Username", how="right")

        import json as _json
        if "stores" in final_df.columns:
            final_df["stores"] = final_df["stores"].apply(
                lambda x: _json.dumps(x, ensure_ascii=False) if isinstance(x, list) else "[]"
            )

        output_excel = base(f"hasil_clustering_k{BEST_K}.xlsx")
        _output_excel_path = output_excel
        final_df.to_excel(output_excel, index=False, engine="openpyxl")

        # Simpan cluster_stats ke meta untuk kebutuhan dashboard
        cluster_stats_dict = {}
        for cid, row in cluster_stats_raw.iterrows():
            lbl = rank_labels[cid]
            cluster_stats_dict[lbl] = {
                "visit_mean" : round(row["visit_mean"], 2),
                "kpi_mean"   : round(row["kpi_mean"],   4),
                "facing_mean": round(row["facing_mean"], 4),
                "fifo_mean"  : round(row["fifo_mean"],   4),
                "price_mean" : round(row["price_mean"],  4),
            }

        meta = {
            "k"                 : BEST_K,
            "output_file"       : os.path.basename(output_excel),
            "k_selection"       : {
                "silhouette"        : best_sil_k,
                "davies_bouldin"    : best_dbi_k,
                "calinski_harabasz" : best_ch_k,
                "winner"            : BEST_K,
            },
            "cluster_labels"    : {str(k): v for k, v in rank_labels.items()},
            "label_order"       : label_order_names,
            "cluster_stats"     : cluster_stats_dict,
            "silhouette_score"  : sil_score,
            "davies_bouldin"    : dbi_score,
            "calinski_harabasz" : ch_score,
            "inertia"           : sse,
            "n_karyawan"        : len(final_df),
        }
        with open(META_PATH, "w") as f:
            json.dump(meta, f, indent=2)

        msg = (f"Selesai! k={BEST_K} · {len(final_df)} karyawan · "
               f"Silhouette={sil_score} · DBI={dbi_score}")
        write_status("done", msg, 100)
        print(f"[Clustering] {msg}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        write_status("error", f"Error: {e}", 0)

    finally:
        _cluster_lock.release()


def start_clustering_thread(source_path: str):
    t = threading.Thread(target=_run_clustering_task, args=(source_path,), daemon=True)
    t.start()


# ════════════════════════════════════════════════════════════
# LOAD DATA & HELPER
# ════════════════════════════════════════════════════════════

def _get_output_excel() -> str:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH) as f:
                meta = json.load(f)
            fname = meta.get("output_file", "")
            path  = base(fname)
            if fname and os.path.exists(path):
                return path
        except Exception:
            pass
    import glob
    candidates = glob.glob(base("hasil_clustering_k*.xlsx"))
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return base("hasil_clustering.xlsx")


def _sanitize_str_cols(df: pd.DataFrame) -> pd.DataFrame:
    import re
    str_cols = ["Nama Karyawan", "Area", "Region", "Username", "Role"]
    for col in str_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace('"', '', regex=False)
                .str.replace("'", "", regex=False)
                .str.replace(r'[\r\n\t]', ' ', regex=True)
                .str.strip()
            )
    return df


def load_data():
    path = _get_output_excel()
    if os.path.exists(path):
        try:
            df = pd.read_excel(path, engine="openpyxl")
            if "cluster_label" in df.columns and not df["cluster_label"].isna().all():
                df = _sanitize_str_cols(df)
                return df, None
        except Exception as e:
            return pd.DataFrame(), f"Gagal baca cache Excel: {e}"
    return pd.DataFrame(), "File hasil clustering belum ada."


def load_meta() -> dict:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ════════════════════════════════════════════════════════════
# BUILD CLUSTER SECTIONS
# ════════════════════════════════════════════════════════════

def build_cluster_sections(df: pd.DataFrame, meta: dict) -> list:
    for col in FEATURE_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    max_visit = df["visit_count"].max() or 1
    med_visit = df["visit_count"].median()
    total_k   = meta.get("k", df["cluster_label"].nunique())

    label_order = meta.get("label_order", sorted(df["cluster_label"].dropna().unique().tolist()))

    def rating(val):
        if val >= 70: return "Tinggi"
        if val >= 40: return "Sedang"
        return "Rendah"

    sections = []
    for rank, lbl in enumerate(label_order):
        subset = df[df["cluster_label"] == lbl].copy()

        # Ambil warna dari PROFILE_PALETTE; fallback ke index-based atau default
        base_lbl = lbl.split(" (")[0]
        if base_lbl in PROFILE_PALETTE:
            colors = PROFILE_PALETTE[base_lbl]
        elif f"Tier {rank+1}" in PROFILE_PALETTE:
            colors = PROFILE_PALETTE[f"Tier {rank+1}"]
        else:
            colors = DEFAULT_COLOR

        cls_key = lbl.lower().replace("-", "_").replace(" ", "_").replace("(", "").replace(")", "")

        avg = {
            "visit"    : round(subset["visit_count"].mean(), 1) if len(subset) else 0,
            "facing"   : round(subset["Facing"].mean() * 100, 1) if len(subset) else 0,
            "fifo"     : round(subset["Is FIFO/FEFO"].mean() * 100, 1) if len(subset) else 0,
            "price_tag": round(subset["Is Price Tag Available"].mean() * 100, 1) if len(subset) else 0,
        }
        avg["kpi_score"] = round(
            (avg["facing"] + avg["fifo"] + avg["price_tag"]) / 3, 1
        )

        interp = {
            "visit"    : "Aktif"  if avg["visit"] >= med_visit else "Jarang",
            "facing"   : rating(avg["facing"]),
            "fifo"     : rating(avg["fifo"]),
            "price_tag": rating(avg["price_tag"]),
            "kpi"      : rating(avg["kpi_score"]),
        }

        tier_text = _get_tier_interpretation(base_lbl, rank, total_k)

        def _clean(val) -> str:
            import re
            s = str(val or "").strip()
            s = s.replace('"', '').replace("'", "")
            s = re.sub(r'[\r\n\t]', ' ', s)
            return s or "-"

        rows = []
        for _, r in subset.sort_values("visit_count", ascending=False).iterrows():
            nama_kar = str(r.get("Nama Karyawan") or "").strip()
            username = str(r.get("Username") or "").strip()
            nama_raw = nama_kar if (nama_kar and nama_kar.lower() not in ("nan", "none", "")) else username or "-"

            facing_pct    = max(0.0, round(r["Facing"] * 100, 1))
            fifo_pct      = max(0.0, min(100.0, round(r["Is FIFO/FEFO"] * 100, 1)))
            price_tag_pct = max(0.0, min(100.0, round(r["Is Price Tag Available"] * 100, 1)))
            kpi_score     = round((facing_pct + fifo_pct + price_tag_pct) / 3, 1)

            role_raw = str(r.get("Role") or "").strip()
            role     = _clean(role_raw) if role_raw and role_raw.lower() not in ("nan","none","") else "-"

            import json as _j
            raw_stores = r.get("stores", "[]")
            try:
                if isinstance(raw_stores, list):
                    stores_list = [_clean(s) for s in raw_stores if s and str(s).lower() not in ("nan","none","")]
                else:
                    parsed = _j.loads(str(raw_stores)) if raw_stores and str(raw_stores) not in ("nan","None","[]","") else []
                    stores_list = [_clean(s) for s in parsed if s and str(s).lower() not in ("nan","none","")]
            except Exception:
                stores_list = []

            rows.append({
                "nama"     : _clean(nama_raw),
                "role"     : role,
                "area"     : _clean(r.get("Area") or "-"),
                "region"   : _clean(r.get("Region") or "-"),
                "stores"   : stores_list,
                "work_rate": round(r["visit_count"] / max_visit * 100, 1),
                "facing"   : facing_pct,
                "fifo"     : fifo_pct,
                "price_tag": price_tag_pct,
                "kpi_score": kpi_score,
                "sil"      : round(float(r.get("silhouette_sample") or 0), 3),
            })

        sections.append({
            "label"           : lbl,
            "title"           : lbl,          # label IS the title (sudah deskriptif)
            "cls"             : cls_key,
            "count"           : len(subset),
            "title_color"     : colors["title"],
            "bar_color"       : colors["bar"],
            "dot_color"       : colors["dot"],
            "avg"             : avg,
            "interp"          : interp,
            "tier_ringkasan"  : tier_text["ringkasan"],
            "tier_visit"      : tier_text["visit"],
            "tier_facing"     : tier_text["facing"],
            "tier_fifo"       : tier_text["fifo"],
            "tier_price_tag"  : tier_text["price_tag"],
            "tier_rekomendasi": tier_text["rekomendasi"],
            "data"            : rows,
        })

    return sections


# ════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    status = read_status()

    if status["state"] == "running":
        return render_template("waiting.html",
                               message=status.get("message", ""),
                               progress=status.get("progress", 0))

    df, err = load_data()

    if df.empty and status["state"] not in ("running",):
        if os.path.exists(RAW_DATA_PATH):
            write_status("running", "Memulai clustering awal…", 0)
            start_clustering_thread(RAW_DATA_PATH)
            return render_template("waiting.html",
                                   message="Clustering pertama kali…",
                                   progress=0)
        else:
            return render_template("no_data.html"), 404

    if err and df.empty:
        return render_template("no_data.html", error=err), 500

    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    meta             = load_meta()
    cluster_sections = build_cluster_sections(df, meta)
    total_per_tier   = {s["label"]: s["count"] for s in cluster_sections}

    area_list    = sorted(df["Area"].dropna().unique().tolist()) if "Area" in df.columns else []
    area_display = ", ".join(area_list[:5])
    if len(area_list) > 5:
        area_display += f" (+{len(area_list)-5} lainnya)"

    chart_data   = [s["count"]     for s in cluster_sections]
    chart_colors = [s["dot_color"] for s in cluster_sections]
    chart_labels = [s["title"]     for s in cluster_sections]

    k_sel = meta.get("k_selection", {})

    if status["state"] == "done":
        flash(f"✅ {status['message']}", "success")
        write_status("idle")
    elif status["state"] == "error":
        flash(f"❌ {status['message']}", "error")
        write_status("idle")

    label_order  = meta.get("label_order", [s["label"] for s in cluster_sections])
    total_high   = total_per_tier.get(label_order[0], 0) if len(label_order) > 0 else 0
    total_low    = total_per_tier.get(label_order[-1], 0) if len(label_order) > 0 else 0
    total_middle = sum(total_per_tier.get(lbl, 0)
                       for lbl in label_order[1:-1]) if len(label_order) > 2 else 0

    return render_template(
        "dashboard.html",
        cluster_sections  = cluster_sections,
        best_k            = meta.get("k", "?"),
        k_selection       = k_sel,
        area              = area_display,
        total_store_visit = int(df["visit_count"].sum()),
        fifo_avg          = round(df["Is FIFO/FEFO"].mean() * 100, 2),
        price_avg         = round(df["Is Price Tag Available"].mean() * 100, 2),
        facing_avg        = round(df["Facing"].mean() * 100, 2),
        chart_data        = chart_data,
        chart_colors      = chart_colors,
        chart_labels      = chart_labels,
        sil_score         = meta.get("silhouette_score", "-"),
        dbi_score         = meta.get("davies_bouldin", "-"),
        ch_score          = meta.get("calinski_harabasz", "-"),
        total_high        = total_high,
        total_middle      = total_middle,
        total_low         = total_low,
        high_data=[], middle_data=[], low_data=[],
    )


@app.route("/status")
def cluster_status():
    return jsonify(read_status())


@app.route("/recluster", methods=["POST"])
def recluster():
    status = read_status()
    if status["state"] == "running":
        flash("⚠️ Clustering sedang berjalan, tunggu sebentar.", "error")
        return redirect(url_for("dashboard"))

    if not os.path.exists(RAW_DATA_PATH):
        flash(f"❌ File Report_Clean.xlsx tidak ditemukan di folder: {BASE_DIR}", "error")
        return redirect(url_for("dashboard"))

    import glob
    for p in glob.glob(base("hasil_clustering_k*.xlsx")) + [META_PATH]:
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

    write_status("running", "Memulai re-clustering…", 0)
    start_clustering_thread(RAW_DATA_PATH)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(url_for("dashboard"))


@app.route("/import", methods=["POST"])
def import_file():
    status = read_status()
    if status["state"] == "running":
        flash("⚠️ Clustering sedang berjalan, tunggu sebentar.", "error")
        return redirect(url_for("dashboard"))

    if "file" not in request.files:
        flash("❌ Tidak ada file yang dikirim.", "error")
        return redirect(url_for("dashboard"))

    f = request.files["file"]
    if not f or f.filename == "":
        flash("❌ Pilih file terlebih dahulu.", "error")
        return redirect(url_for("dashboard"))

    fname    = f.filename.lower()
    is_csv   = fname.endswith(".csv")
    is_excel = fname.endswith((".xlsx", ".xls"))

    if not (is_csv or is_excel):
        flash("❌ Format tidak didukung. Gunakan .csv, .xlsx, atau .xls.", "error")
        return redirect(url_for("dashboard"))

    ext      = ".csv" if is_csv else ".xlsx"
    tmp_path = base(f"_import_tmp{ext}")
    try:
        f.save(tmp_path)

        if is_csv:
            df_check = pd.read_csv(tmp_path, nrows=5, low_memory=False, sep=None, engine="python")
        else:
            df_check = pd.read_excel(tmp_path, engine="openpyxl", nrows=5)

        needed  = {"Username", "Report Product", "Facing",
                   "Is FIFO/FEFO", "Is Price Tag Available"}
        missing = needed - set(df_check.columns)
        if missing:
            os.remove(tmp_path)
            flash(
                f"❌ Kolom wajib tidak ditemukan: {', '.join(sorted(missing))}. "
                f"Pastikan file adalah data Report yang benar.",
                "error",
            )
            return redirect(url_for("dashboard"))

        import glob
        for p in glob.glob(base("hasil_clustering_k*.xlsx")) + [META_PATH]:
            if os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

        write_status("running", f"Mengimport {f.filename} dan menjalankan clustering…", 0)
        start_clustering_thread(tmp_path)

    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        flash(f"❌ Gagal membaca file: {e}", "error")
        return redirect(url_for("dashboard"))

    return redirect(url_for("dashboard"))


@app.route("/export")
def export_file():
    path = _get_output_excel()
    if not os.path.exists(path):
        flash("❌ Belum ada hasil clustering untuk diekspor.", "error")
        return redirect(url_for("dashboard"))
    try:
        return send_file(
            path,
            as_attachment = True,
            download_name = os.path.basename(path),
            mimetype      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        flash(f"❌ Export gagal: {e}", "error")
        return redirect(url_for("dashboard"))


# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("WARNING: jalankan --> pip install openpyxl")

    write_status("idle")
    app.run(debug=False, threaded=True)
