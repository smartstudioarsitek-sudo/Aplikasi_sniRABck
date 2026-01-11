import pandas as pd
import re
import os

def clean_currency(x):
    """
    Membersihkan format uang yang kotor
    Contoh: "Rp 1.500.000,00" -> 1500000.0
    """
    if isinstance(x, (int, float)):
        return x
    if pd.isna(x) or x == '':
        return 0.0
    
    # Ubah ke string
    s = str(x)
    # Buang Rp dan spasi
    s = s.replace('Rp', '').replace(' ', '').strip()
    
    # Deteksi Format:
    # Kasus A: 1.000,00 (Ribuan titik, Desimal koma) -> Standar Indo
    # Kasus B: 1,000.00 (Ribuan koma, Desimal titik) -> Standar US/Excel
    
    if ',' in s and '.' in s:
        # Cek mana yang ada di posisi akhir (itu desimalnya)
        last_comma = s.rfind(',')
        last_dot = s.rfind('.')
        
        if last_comma > last_dot: 
            # Format Indo (1.000,00) -> Buang titik, ganti koma jadi titik
            s = s.replace('.', '').replace(',', '.')
        else:
            # Format US (1,000.00) -> Buang koma
            s = s.replace(',', '')
    elif ',' in s:
        # Cuma ada koma (misal 100,00) atau (1,000)
        # Asumsi aman: Jika ada 3 angka di belakang koma, itu ribuan. Jika 2, itu desimal.
        parts = s.split(',')
        if len(parts[-1]) == 2: # Kemungkinan desimal
            s = s.replace(',', '.')
        else: # Kemungkinan ribuan
            s = s.replace(',', '')
    
    try:
        return float(s)
    except:
        return 0.0

def detect_separator(file_path):
    """Mendeteksi apakah CSV pakai koma (,) atau titik koma (;)"""
    try:
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            for _ in range(5):
                line = f.readline()
                if ';' in line: return ';'
                if ',' in line: return ','
    except:
        pass
    return ',' # Default

def extract_ahsp_items(file_path):
    """
    FUNGSI UTAMA:
    Membaca CSV AHSP dan mengambil baris 'Judul Pekerjaan' beserta 'Harga Jadinya'.
    Mengabaikan rincian bahan/upah, fokus pada Output.
    """
    sep = detect_separator(file_path)
    items = []
    
    try:
        with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
            lines = f.readlines()
            
        for line in lines:
            # Lewati baris kosong
            if not line.strip(): continue
            
            parts = line.strip().split(sep)
            
            # Kita butuh baris yang panjang (banyak kolom) untuk memastikan ini data tabel
            if len(parts) < 4: continue

            # --- DETEKTIF KODE ---
            col0 = parts[0].strip().replace('"', '') # Kolom Kode (misal: 2.2.1.1)
            col1 = parts[1].strip().replace('"', '') # Kolom Uraian
            
            # Cek apakah Kolom 0 adalah Kode Analisa (Angka dan Titik)
            # Contoh Valid: "2.1", "3.4.1.1", "A.1"
            # Contoh Tidak Valid: "No", "Tenaga Kerja", "Koefisien"
            
            is_code_format = False
            # Regex: Mulai dengan angka/huruf, diikuti titik/angka berulang
            if re.match(r'^[A-Za-z0-9]+[\.\d]*$', col0):
                is_code_format = True
            
            # Filter Header Tabel
            if "Uraian" in col1 or "Satuan" in col1 or "Harga" in col1:
                continue
            
            # --- PENGAMBILAN HARGA ---
            # Harga biasanya ada di kolom terakhir atau dekat terakhir yang bukan kosong
            # Kita cari dari belakang ke depan
            price_found = 0
            unit_found = "ls"
            
            # Cari Harga (Loop mundur)
            for part in reversed(parts):
                val = clean_currency(part)
                # Harga satuan pekerjaan biasanya > 100 rupiah dan bukan koefisien (0.001)
                if val > 100: 
                    price_found = val
                    break
            
            # Cari Satuan (Cari string pendek umum: m3, m2, m', bh, unit, kg)
            common_units = ['m3', 'm2', "m'", 'm', 'kg', 'buah', 'bh', 'unit', 'ls', 'zak', 'batang', 'titik']
            for part in parts:
                clean_part = part.lower().strip().replace('"', '')
                if clean_part in common_units:
                    unit_found = clean_part
                    break
            
            # LOGIKA PENYIMPANAN:
            # Jika Kode Valid DAN Ada Harga DAN Deskripsi Panjang -> Masukkan Database
            if is_code_format and price_found > 0 and len(col1) > 5:
                # Bersihkan deskripsi dari tanda kutip
                desc_clean = col1.replace('"', '').strip()
                
                items.append({
                    "Kode": col0,
                    "Item": desc_clean,
                    "Unit": unit_found,
                    "Price": price_found
                })
                
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return pd.DataFrame(items)

# Fungsi lama untuk kompatibilitas (biar gak error kalau dipanggil)
def ingest_analysis_file(file_path):
    return extract_ahsp_items(file_path)
