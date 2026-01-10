import streamlit as st
import pandas as pd
import os
# Pastikan ini sesuai dengan nama folder Anda
from src.parsers import ingest_analysis_file

st.set_page_config(page_title="SmartRAB - Ingestion", layout="wide")
st.title("🛠️ SmartRAB - Mesin Penelan Data")

uploaded_files = st.file_uploader(
    "Upload File CSV (Analisis & Sumber Daya)", 
    accept_multiple_files=True,
    type=['csv']
)

if uploaded_files:
    st.write(f"Menerima {len(uploaded_files)} file.")
    
    for uploaded_file in uploaded_files:
        with st.expander(f"Memproses: {uploaded_file.name}", expanded=True):
            
            # 1. Simpan file sementara
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                # 2. Panggil Parser
                df = ingest_analysis_file(temp_path)
                
                # 3. Tampilkan Kolom yang Ditemukan (Untuk Debugging)
                cols = df.columns.tolist()
                st.code(f"Kolom terdeteksi: {cols}", language="python")
                
                # 4. Logika Deteksi Tipe File (YANG DIPERBAIKI)
                # Cek apakah kolom kunci ada di dalam daftar kolom yang sudah dibersihkan parser
                
                # File Analisis (Beton, Pondasi, dll) biasanya punya koefisien
                is_analisis = 'koefisien' in cols and 'deskripsi' in cols
                
                # File Sumber Daya (Upah Bahan) TIDAK punya koefisien, tapi punya harga_satuan
                is_sumberdaya = 'harga_satuan' in cols and 'deskripsi' in cols and 'koefisien' not in cols
                
                if is_analisis:
                    st.success("✅ TIPE: FILE ANALISIS (AHSP)")
                    st.dataframe(df.head(3), use_container_width=True)
                elif is_sumberdaya:
                    st.info("📦 TIPE: FILE SUMBER DAYA (Upah/Bahan)")
                    st.dataframe(df.head(3), use_container_width=True)
                else:
                    # Jika gagal, beri tahu user kolom apa yang kurang
                    st.warning("⚠️ Format Belum Dikenali")
                    st.write("Sistem membutuhkan kolom: 'deskripsi' DAN ('koefisien' ATAU 'harga_satuan')")
            
            except Exception as e:
                st.error(f"Error: {e}")
            
            finally:
                # Hapus file sementara
                if os.path.exists(temp_path):
                    os.remove(temp_path)
