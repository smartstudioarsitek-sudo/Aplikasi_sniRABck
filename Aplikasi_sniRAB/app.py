import streamlit as st
import pandas as pd
import io
import xlsxwriter
import altair as alt
import os

# --- IMPORT OTAK BARU (Parser) ---
try:
    from src.parsers import ingest_analysis_file
except ImportError:
    st.error("⚠️ File src/parsers.py tidak ditemukan. Pastikan folder 'src' ada.")
    st.stop()

st.set_page_config(page_title="SmartRAB - Debug Mode", layout="wide", page_icon="🏗️")

# Inisialisasi Session State
if 'project_data' not in st.session_state:
    st.session_state['project_data'] = {}
if 'rab_items' not in st.session_state:
    st.session_state['rab_items'] = []
if 'global_overhead' not in st.session_state:
    st.session_state['global_overhead'] = 10.0
if 'master_database' not in st.session_state:
    st.session_state['master_database'] = pd.DataFrame(columns=["Category", "Item", "Unit", "Price", "Source"])

# ==========================================
# 1. MODUL SIDEBAR (DENGAN FITUR DIAGNOSA)
# ==========================================
with st.sidebar:
    st.header("📂 Database Control")
    
    uploaded_db_files = st.file_uploader(
        "Upload File CSV", 
        accept_multiple_files=True,
        type=['csv']
    )
    
    if uploaded_db_files:
        if st.button("🔄 Proses Database"):
            all_data = []
            
            for uploaded_file in uploaded_db_files:
                st.write(f"--- Memproses: **{uploaded_file.name}** ---")
                
                # 1. Simpan file sementara
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                try:
                    # 2. Baca Data Mentah
                    df_new = ingest_analysis_file(temp_path)
                    
                    # --- FITUR DIAGNOSA (Cek Kolom) ---
                    st.caption(f"Kolom ditemukan: {list(df_new.columns)}")
                    
                    # Cek apakah kolom kunci ada
                    if 'deskripsi' not in df_new.columns:
                        st.error(f"❌ Kolom 'deskripsi' hilang di {uploaded_file.name}")
                        st.dataframe(df_new.head()) # Tampilkan apa yang salah
                        continue

                    # 3. Mapping (Penyambungan Kabel Data)
                    # Kita buat mapping lebih fleksibel
                    df_mapped = pd.DataFrame()
                    
                    # Ambil deskripsi
                    df_mapped['Item'] = df_new['deskripsi']
                    
                    # Ambil Satuan (Jika tidak ada, isi strip)
                    if 'satuan' in df_new.columns:
                        df_mapped['Unit'] = df_new['satuan']
                    else:
                        df_mapped['Unit'] = '-'
                        
                    # Ambil Harga (Cari 'harga_satuan', kalau gak ada cari 'price')
                    if 'harga_satuan' in df_new.columns:
                        df_mapped['Price'] = df_new['harga_satuan']
                    else:
                        df_mapped['Price'] = 0
                        
                    # Kategori & Sumber
                    category_name = uploaded_file.name.replace('.csv', '').replace('.xlsx', '').split('-')[-1].strip()
                    df_mapped['Category'] = category_name
                    df_mapped['Source'] = "Uploaded"
                    
                    # --- DIAGNOSA FILTER HARGA ---
                    # Jangan filter harga 0 dulu, biar ketahuan masuk atau tidak
                    jumlah_awal = len(df_mapped)
                    # Hanya buang yang Item-nya kosong/NaN
                    df_mapped = df_mapped.dropna(subset=['Item'])
                    
                    st.success(f"✅ Berhasil baca {len(df_mapped)} baris.")
                    
                    all_data.append(df_mapped)
                        
                except Exception as e:
                    st.error(f"Error teknis: {e}")
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # Gabungkan semua data
            if all_data:
                st.session_state['master_database'] = pd.concat(all_data, ignore_index=True)
                st.success("🎉 Database Terupdate! Cek Tab 2.")
            else:
                st.warning("Tidak ada data yang berhasil masuk.")

# ==========================================
# UI UTAMA (TABEL)
# ==========================================
st.title("🏗️ SmartRAB - Monitor")

tabs = st.tabs(["📚 AHSP Master (Database)", "🔍 Debug Data Mentah"])

with tabs[0]:
    st.header("Database Hasil Upload")
    df_master = st.session_state['master_database']
    
    if df_master.empty:
        st.info("Data masih kosong. Upload file di kiri, lalu klik tombol 'Proses Database'.")
    else:
        st.metric("Total Item Tersimpan", len(df_master))
        st.dataframe(df_master, use_container_width=True)

with tabs[1]:
    st.header("Cek Apakah Harga Masuk?")
    if not st.session_state['master_database'].empty:
        df = st.session_state['master_database']
        # Tampilkan data yang harganya 0 (Potensi masalah)
        st.write("Item dengan Harga Rp 0 (Perlu dicek):")
        st.dataframe(df[df['Price'] == 0])
        
        st.write("Item dengan Harga Valid:")
        st.dataframe(df[df['Price'] > 0])
