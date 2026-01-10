import streamlit as st
import pandas as pd
import os
from src.parsers import ingest_analysis_file
# Hapus import cleaning dulu jika belum dipakai agar tidak error
# from src.cleaning import clean_resource_database 

st.set_page_config(page_title="SmartRAB - Ingestion", layout="wide")
st.title("🛠️ SmartRAB - Mesin Penelan Data (Ingestion Engine)")

uploaded_files = st.file_uploader(
    "Upload File CSV (Analisis & Sumber Daya)", 
    accept_multiple_files=True,
    type=['csv']
)

if uploaded_files:
    st.write(f"Menerima {len(uploaded_files)} file.")
    
    # Buat container agar rapi
    for uploaded_file in uploaded_files:
        with st.expander(f"Memproses: {uploaded_file.name}", expanded=True):
            
            # 1. Simpan file sementara (buffer)
            with open(f"temp_{uploaded_file.name}", "wb") as f:
                f.write(uploaded_file.getbuffer())
            file_path = f"temp_{uploaded_file.name}"
            
            try:
                # 2. Panggil Parser Cerdas kita
                df = ingest_analysis_file(file_path)
                
                # 3. Cek Apakah DataFrame Kosong?
                if df.empty:
                    st.error("❌ File terbaca tapi kosong atau format tidak dikenali.")
                    continue
                
                # 4. Tampilkan Kolom yang Terdeteksi (Untuk Debugging Anda)
                cols = df.columns.tolist()
                st.code(f"Kolom ditemukan: {cols}", language="python")
                
                # 5. Logika Deteksi Jenis File (Logika Baru)
                is_analisis = 'koefisien' in cols and 'deskripsi' in cols
                is_sumberdaya = 'harga_satuan' in cols and 'deskripsi' in cols and 'koefisien' not in cols
                
                if is_analisis:
                    st.success("✅ TIPE: FILE ANALISIS (AHSP)")
                    st.dataframe(df.head(3), use_container_width=True)
                    st.caption("Sistem mengenali kolom 'koefisien' dan 'deskripsi'. Siap untuk perhitungan.")
                    
                elif is_sumberdaya:
                    st.info("📦 TIPE: FILE SUMBER DAYA (Upah/Bahan)")
                    st.dataframe(df.head(3), use_container_width=True)
                    st.caption("Sistem mengenali kolom 'harga_satuan'. Siap dijadikan referensi harga.")
                    
                else:
                    st.warning("⚠️ TIPE TIDAK DIKENALI")
                    st.write("File terbaca, tapi kolom wajib tidak lengkap.")
                    st.write("Yang diharapkan: ('deskripsi' + 'koefisien') ATAU ('deskripsi' + 'harga_satuan')")
            
            except Exception as e:
                st.error(f"Error tak terduga: {e}")
            
            finally:
                # Bersihkan file sampah
                if os.path.exists(file_path):
                    os.remove(file_path)
