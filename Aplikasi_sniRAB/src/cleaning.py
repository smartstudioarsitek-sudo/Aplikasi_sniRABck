import pandas as pd
import hashlib

def generate_id(text):
    """Membuat ID unik pendek dari nama material (hash)"""
    if pd.isna(text): return None
    clean_text = text.lower().strip()
    return hashlib.md5(clean_text.encode()).hexdigest()[:8]

def clean_resource_database(df_raw):
    """
    Membersihkan Upah Bahan.csv:
    1. Hapus baris kosong
    2. Hapus duplikat
    3. Buat ID unik
    """
    # Ambil hanya kolom penting (sesuaikan dengan hasil audit parsers.py)
    # Asumsi kolom sudah di-rename jadi: 'deskripsi', 'satuan', 'harga_dasar'
    
    # 1. Bersihkan Nama
    df_raw['deskripsi'] = df_raw['deskripsi'].astype(str).str.strip()
    
    # 2. Hapus Duplikat (Ambil harga rata-rata jika ada duplikat nama)
    # Ini menangani kasus "Pasir Beton" muncul 2x dengan harga beda tipis
    df_clean = df_raw.groupby(['deskripsi', 'satuan'], as_index=False)['harga_satuan'].mean()
    
    # 3. Generate ID Unik (Primary Key Buatan)
    df_clean['resource_id'] = df_clean['deskripsi'].apply(generate_id)
    
    return df_clean