import streamlit as st
import pandas as pd
from src.parsers import ingest_analysis_file
from src.cleaning import clean_resource_database

st.title("🛠️ SmartRAB - Data Ingestion Engine")

uploaded_files = st.file_uploader("Upload File CSV (Analisis & Sumber Daya)", accept_multiple_files=True)

if uploaded_files:
    st.write(f"Menerima {len(uploaded_files)} file.")
    
    for uploaded_file in uploaded_files:
        # Simpan sementara untuk dibaca pandas
        with open(f"temp_{uploaded_file.name}", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        file_path = f"temp_{uploaded_file.name}"
        
        try:
            # Coba parsing
            st.subheader(f"Memproses: {uploaded_file.name}")
            df = ingest_analysis_file(file_path)
            
            # Tampilkan 5 baris pertama untuk validasi mata
            st.dataframe(df.head())
            
            # Cek apakah kolom standar berhasil dikenali
            if 'koefisien' in df.columns and 'deskripsi' in df.columns:
                st.success("✅ Struktur Analisis Terdeteksi")
            elif 'UPAH' in str(df.columns) or 'Harga' in str(df.columns): 
                 # Logika sederhana untuk mendeteksi file resource
                st.info("ℹ️ Kemungkinan File Sumber Daya")
            else:
                st.warning("⚠️ Header tidak standar, cek parsers.py")
                
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")