import pandas as pd
import os
import io

def clean_currency(x):
    """
    Membersihkan format uang string 'Rp 100,000.00' menjadi float 100000.0
    Menangani koma sebagai ribuan.
    """
    if isinstance(x, (int, float)):
        return x
    if pd.isna(x) or x == '':
        return 0.0
    
    # Ubah ke string, buang "Rp", buang spasi
    s = str(x).replace('Rp', '').replace(' ', '').strip()
    
    # Hapus koma (pemisah ribuan format US) -> 100,000.00 jadi 100000.00
    if ',' in s:
        s = s.replace(',', '')
    
    try:
        return float(s)
    except ValueError:
        return 0.0

def detect_separator(file_path):
    """Mendeteksi apakah file pakai koma (,) atau titik koma (;)"""
    try:
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            for _ in range(5): # Cek 5 baris pertama
                line = f.readline()
                if ';' in line: return ';'
                if ',' in line: return ','
    except:
        pass
    return ',' # Default

def detect_header_row(file_path, separator):
    """Mencari baris header yang mengandung kata kunci"""
    keywords = ["No", "Uraian", "Koefisien", "Harga", "Kode", "Komponen"]
    try:
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            for i in range(30):
                line = f.readline()
                # Hitung kecocokan keyword
                if sum(1 for k in keywords if k.lower() in line.lower()) >= 2:
                    return i
    except:
        pass
    return 0

def ingest_analysis_file(file_path):
    # 1. Deteksi Pemisah (Koma atau Titik Koma?)
    sep = detect_separator(file_path)
    
    # 2. Cari baris Header
    header_row = detect_header_row(file_path, separator=sep)
    
    try:
        # 3. Baca File
        df = pd.read_csv(
            file_path, 
            header=header_row, 
            sep=sep,  # Gunakan pemisah yang dideteksi
            engine='python', 
            on_bad_lines='skip',
            encoding='latin-1'
        )
    except Exception as e:
        return pd.DataFrame() # Return kosong jika gagal total

    # 4. Bersihkan Nama Kolom (Huruf kecil & tanpa spasi aneh)
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace('\n', ' ')
    
    # 5. Mapping Kamus Bahasa (Agar aplikasi mengerti bahasa file Anda)
    column_mapping = {
        # Variasi Nama Barang
        'uraian': 'deskripsi',
        'uraian pekerjaan': 'deskripsi',
        'komponen': 'deskripsi', # Ditemukan di Upah Bahan.csv
        'nama bahan': 'deskripsi',
        
        # Variasi Satuan
        'sat.': 'satuan',
        'satuan': 'satuan',
        'unit': 'satuan',
        
        # Variasi Koefisien
        'koefisien': 'koefisien',
        'koef': 'koefisien',
        
        # Variasi Harga
        'harga satuan': 'harga_satuan',
        'harga satuan (rp)': 'harga_satuan',
        'harga_dasar': 'harga_satuan', # Ditemukan di Upah Bahan.csv
        'harga': 'harga_satuan',
        
        # Variasi Kategori
        'kategori': 'kategori'
    }
    
    df = df.rename(columns=column_mapping)
    
    # 6. Bersihkan Data Angka (PENTING!)
    if 'harga_satuan' in df.columns:
        df['harga_satuan'] = df['harga_satuan'].apply(clean_currency)
        
    if 'koefisien' in df.columns:
         df['koefisien'] = df['koefisien'].apply(clean_currency)

    # 7. Validasi Akhir (Hapus kolom hantu)
    valid_cols = [c for c in df.columns if 'unnamed' not in c and c != '']
    df = df[valid_cols]

    # Hapus baris kosong yang tidak punya deskripsi
    if 'deskripsi' in df.columns:
        df = df.dropna(subset=['deskripsi'])

    df['sumber_file'] = os.path.basename(file_path)
    
    return df
