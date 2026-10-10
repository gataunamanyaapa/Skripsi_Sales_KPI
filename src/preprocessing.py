import pandas as pd
from sklearn.preprocessing import StandardScaler


def load_data():
    df = pd.read_csv("data/Report.csv", low_memory=False)
    return df


def select_features(df):
   
    # 1. DATA CLEANING
    # Convert tanggal
    df['Tanggal Visit'] = pd.to_datetime(df['Tanggal Visit'], errors='coerce')

    # Normalisasi string
    df['Is FIFO/FEFO'] = df['Is FIFO/FEFO'].astype(str).str.upper().str.strip()
    df['Is Price Tag Available'] = df['Is Price Tag Available'].astype(str).str.upper().str.strip()

    # Replace nilai tidak valid
    df['Is FIFO/FEFO'] = df['Is FIFO/FEFO'].replace(['-1', 'NAN'], pd.NA)
    df['Is Price Tag Available'] = df['Is Price Tag Available'].replace(['-1', 'NAN'], pd.NA)


    # 2. ENCODING (YA/TIDAK → 1/0)
    df['FIFO_num'] = df['Is FIFO/FEFO'].apply(
        lambda x: 1 if str(x) == 'YA' else 0
    )

    df['PriceTag_num'] = df['Is Price Tag Available'].apply(
        lambda x: 1 if str(x) == 'YA' else 0
    )

    # 3. AGGREGASI PER KARYAWAN
    df_grouped = df.groupby('Username').agg({
        'Facing': 'mean',
        'FIFO_num': 'mean',
        'PriceTag_num': 'mean',
        'Tanggal Visit': 'count'
    }).rename(columns={
        'Tanggal Visit': 'visit_count',
        'FIFO_num': 'Is FIFO/FEFO',
        'PriceTag_num': 'Is Price Tag Available'
    }).reset_index()


    # 4. HANDLE DATA INVALID
    df_grouped = df_grouped[df_grouped['visit_count'] > 0]
    df_grouped = df_grouped.fillna(0)

  
    # 5. FINAL FEATURES
    features = df_grouped[
        ['visit_count', 'Facing', 'Is FIFO/FEFO', 'Is Price Tag Available']
    ]

    return features


def scale_data(data):
    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)
    return scaled