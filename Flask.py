# ============================================================
# flask_helpers.py
# Fungsi helper untuk mengubah output script clustering
# menjadi variabel siap pakai di render_template()
# ============================================================

# Palet warna per tier (urutan: terbaik → terburuk)
TIER_COLORS = ['#F15A29', '#FBBC05', '#4A90D9', '#22c55e', '#a855f7', '#0ea5e9']
TITLE_COLORS = ['#D94715', '#C89400', '#2C6FAC', '#15803d', '#7e22ce', '#0369a1']


def build_cluster_sections(final_df, label_order, rank_labels=None):
    """
    Mengubah final_df hasil clustering menjadi `cluster_sections`
    — list of dict yang langsung dikonsumsi template index.html.

    Parameter
    ---------
    final_df    : pd.DataFrame dengan kolom:
                    Nama Karyawan, Area, visit_count, Facing,
                    Is FIFO/FEFO, Is Price Tag Available,
                    cluster_label, performance_score (opsional)
    label_order : list[str] — urutan label dari terbaik ke terburuk,
                    mis. ['High','Low'] atau ['High','Medium','Low']
                    atau ['Tier 1','Tier 2', ...]

    Mengembalikan
    -------------
    list of dict, satu item per cluster tier, siap di-pass ke render_template
    """
    # Nama judul per tier (otomatis)
    tier_title_map = {
        'High'  : 'High Performance',
        'Medium': 'Middle Performance',
        'Low'   : 'Low Performance',
    }

    max_visit = final_df['visit_count'].max() or 1
    sections  = []

    for rank, lbl in enumerate(label_order):
        subset = final_df[final_df['cluster_label'] == lbl].copy()

        # Judul — gunakan mapping atau generik
        title = tier_title_map.get(lbl, f'{lbl} Performance')

        # CSS class untuk ID unik tabel
        cls = lbl.lower().replace(' ', '-')

        # Apakah kolom performance_score ada?
        has_score = 'performance_score' in subset.columns

        rows = []
        for _, r in subset.iterrows():
            row = {
                'nama'     : r.get('Nama Karyawan', r.get('Username', '-')),
                'area'     : r.get('Area', '-'),
                'work_rate': round(r['visit_count'] / max_visit * 100, 1),
                'facing'   : round(r['Facing'] * 100, 1),
                'fifo'     : round(r['Is FIFO/FEFO'] * 100, 1),
                'price_tag': round(r['Is Price Tag Available'] * 100, 1),
            }
            if has_score:
                row['performance_score'] = round(r['performance_score'], 1)
            rows.append(row)

        sections.append({
            'title'      : title,
            'cls'        : cls,
            'show_score' : has_score,
            'data'       : rows,
        })

    return sections


# ── Contoh penggunaan di Flask route ──────────────────────────
"""
from flask_helpers import build_cluster_sections

@app.route('/')
def dashboard():
    # --- jalankan pipeline clustering (dari notebook) ---
    # final_df, label_order, BEST_K, sil, dbi sudah tersedia

    cluster_sections = build_cluster_sections(final_df, label_order)

    # Hitung agregat untuk summary card
    total_visit  = int(df_grouped['visit_count'].sum())
    fifo_avg     = round(df_grouped['Is FIFO/FEFO'].mean() * 100, 1)
    price_avg    = round(df_grouped['Is Price Tag Available'].mean() * 100, 1)
    facing_avg   = round(df_grouped['Facing'].mean() * 100, 1)
    area_name    = df['Area'].mode()[0] if 'Area' in df.columns else '-'

    # Chart data (urut sesuai label_order, untuk donut)
    chart_data = [
        len(s['data']) for s in cluster_sections
    ]

    return render_template(
        'index.html',

        # Dinamis — dipakai template baru
        cluster_sections  = cluster_sections,
        best_k            = BEST_K,

        # Summary card
        area              = area_name,
        total_store_visit = total_visit,
        fifo_avg          = fifo_avg,
        price_avg         = price_avg,
        facing_avg        = facing_avg,
        chart_data        = chart_data,

        # Backward-compat (bisa diisi 0 kalau sudah pakai cluster_sections)
        total_high        = 0,
        total_middle      = 0,
        total_low         = 0,
        high_data         = [],
        middle_data       = [],
        low_data          = [],
    )
"""