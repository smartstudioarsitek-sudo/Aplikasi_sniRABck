import pandas as pd
import os

def detect_header_row(file_path, keywords=["No", "Uraian", "Koefisien", "Harga Satuan"]):
    """
    Mencari baris header yang sebenarnya dengan memindai 20 baris pertama.
    Jika baris mengandung minimal 2 kata kunci, itu dianggap header.
    """
    try:
        with open(file_path, 'r', errors='replace') as f:
            for i in range(20):  # Cek 20 baris pertama
                line = f.readline()
                # Hitung berapa keyword yang muncul di baris ini
                matches = sum(1 for k in keywords if k.lower() in line.lower())
                if matches >= 2: # Ambang batas: jika ketemu 2 kata kunci, ini header
                    return i
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
    return 0  # Default ke baris 0 jika gagal

def ingest_analysis_file(file_path):
    """
    Membaca file Analisis (misal: Beton.csv) dengan header dinamis.
    """
    header_row = detect_header_row(file_path)
    
    # Baca CSV mulai dari baris header yang ditemukan
    df = pd.read_csv(file_path, header=header_row)
    
    # Standarisasi Nama Kolom (Normalisasi)
    # Kita ubah berbagai variasi nama kolom menjadi standar internal
    column_mapping = {
        'Uraian': 'deskripsi',
        'Uraian Pekerjaan': 'deskripsi',
        'Item': 'deskripsi',
        'Sat.': 'satuan',
        'Satuan': 'satuan',
        'Koefisien': 'koefisien',
        'Koef': 'koefisien',
        'Harga Satuan (Rp)': 'harga_satuan',
        'Harga Satuan': 'harga_satuan',
        'Jumlah Harga (Rp)': 'total_harga'
    }
    
    # Rename kolom yang cocok
    df = df.rename(columns=column_mapping)
    
    # Bersihkan kolom yang kosong (sering muncul kolom tanpa nama di CSV hasil export)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Tambahkan metadata asal file (penting untuk pelacakan)
    df['sumber_file'] = os.path.basename(file_path)
    
    return df