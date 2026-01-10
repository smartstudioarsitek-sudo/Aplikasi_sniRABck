import pandas as pd
import os
import io

def detect_header_row(file_path, keywords=["No", "Uraian", "Koefisien", "Harga Satuan", "UPAH", "Kode"]):
    """
    Mencari baris header yang sebenarnya dengan memindai 30 baris pertama.
    """
    try:
        # Gunakan encoding 'latin-1' atau 'cp1252' jika 'utf-8' gagal
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            for i in range(30):
                line = f.readline()
                # Hitung berapa keyword yang muncul
                matches = sum(1 for k in keywords if k.lower() in line.lower())
                # Jika baris ini punya minimal 2 kata kunci, atau ada kata 'Uraian' dan 'Satuan'
                if matches >= 2: 
                    return i
    except Exception as e:
        print(f"Warning scanning file {file_path}: {e}")
    return 0

def ingest_analysis_file(file_path):
    """
    Membaca file CSV yang memiliki baris header tidak konsisten.
    Menggunakan engine='python' untuk menghindari 'tokenizing data error'.
    """
    header_row = detect_header_row(file_path)
    
    try:
        # PENTING: engine='python' lebih lambat tapi jauh lebih kuat menangani file 'kotor'
        # on_bad_lines='skip' akan melewati baris yang rusak daripada membuat error
        df = pd.read_csv(
            file_path, 
            header=header_row, 
            engine='python', 
            on_bad_lines='skip',
            encoding='latin-1' 
        )
    except Exception as e:
        # Fallback jika gagal
        return pd.DataFrame()

    # Standarisasi Nama Kolom
    # Kita buat semua nama kolom jadi huruf kecil dan hapus spasi agar mudah dipanggil
    df.columns = df.columns.astype(str).str.strip().str.lower()
    
    # Mapping nama kolom dari berbagai variasi ke standar internal
    column_mapping = {
        'uraian': 'deskripsi',
        'uraian pekerjaan': 'deskripsi',
        'item': 'deskripsi',
        'upah - material - alat': 'deskripsi', # Khusus file Upah Bahan
        'sat.': 'satuan',
        'satuan': 'satuan',
        'koefisien': 'koefisien',
        'koef': 'koefisien',
        'harga satuan': 'harga_satuan',
        'harga  satuan (rp)': 'harga_satuan',
        'harga satuan (rp)': 'harga_satuan',
        'jumlah harga (rp)': 'total_harga'
    }
    
    # Rename kolom jika ditemukan
    df = df.rename(columns=column_mapping)
    
    # Filter kolom sampah (Unnamed)
    valid_cols = [c for c in df.columns if 'unnamed' not in c]
    df = df[valid_cols]

    # Hapus baris yang 'deskripsi'-nya kosong (biasanya baris total atau footer)
    if 'deskripsi' in df.columns:
        df = df.dropna(subset=['deskripsi'])
        # Hapus baris yang isinya cuma judul bab (misal "A. TENAGA KERJA")
        # Ciri: Koefisien kosong
        if 'koefisien' in df.columns:
            # Kita pertahankan baris hanya jika dia punya koefisien (artinya dia komponen)
            # ATAU jika ini file sumber daya (tidak punya koefisien tapi punya harga)
            pass 

    # Tambahkan metadata
    df['sumber_file'] = os.path.basename(file_path)
    
    return df
