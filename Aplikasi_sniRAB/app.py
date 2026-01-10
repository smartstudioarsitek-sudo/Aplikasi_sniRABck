import streamlit as st
import pandas as pd
import io
import xlsxwriter
import altair as alt
import os

# --- IMPORT OTAK BARU (Parser) ---
# Pastikan folder src/parsers.py sudah ada dan berisi kode terakhir yang kita buat
try:
    from src.parsers import ingest_analysis_file
except ImportError:
    st.error("⚠️ File src/parsers.py tidak ditemukan. Pastikan struktur folder sudah benar.")
    st.stop()

# ==========================================
# KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="SmartRAB - SNI System", layout="wide", page_icon="🏗️")

# Inisialisasi Session State (Agar data tidak hilang saat klik tombol)
if 'project_data' not in st.session_state:
    st.session_state['project_data'] = {}
if 'rab_items' not in st.session_state:
    st.session_state['rab_items'] = []
if 'global_overhead' not in st.session_state:
    st.session_state['global_overhead'] = 10.0
# State khusus untuk Database Dinamis
if 'master_database' not in st.session_state:
    st.session_state['master_database'] = pd.DataFrame(columns=["Category", "Item", "Unit", "Price", "Source"])

# ==========================================
# 1. MODUL SIDEBAR (UPLOAD DATABASE)
# ==========================================
with st.sidebar:
    st.header("📂 Database Control")
    st.info("Upload file CSV Analisis & Harga di sini untuk memperbarui database.")
    
    uploaded_db_files = st.file_uploader(
        "Upload File CSV (Beton, Upah, dll)", 
        accept_multiple_files=True,
        type=['csv']
    )
    
    if uploaded_db_files:
        if st.button("🔄 Proses Database Baru"):
            all_data = []
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_db_files):
                # 1. Simpan file sementara
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 2. Proses dengan Parser Cerdas
                try:
                    df_new = ingest_analysis_file(temp_path)
                    
                    # 3. Konversi format ke standar Aplikasi Lama
                    # Aplikasi lama butuh: Category, Item, Unit, Price
                    
                    # Tentukan Kategori berdasarkan nama file (misal: Beton.csv -> Beton)
                    category_name = uploaded_file.name.replace('.csv', '').replace('.xlsx', '').replace('data_rab (2).xlsx - ', '')
                    
                    if not df_new.empty:
                        # Kita ambil kolom yang relevan
                        # Jika file Analisis (ada koefisien), kita ambil Harga Satuan Akhir (asumsi sudah dihitung atau ambil input)
                        # SEMENTARA: Kita ambil harga_satuan dari kolom yang tersedia
                        
                        # Normalisasi kolom agar cocok dengan UI lama
                        df_mapped = pd.DataFrame()
                        df_mapped['Item'] = df_new.get('deskripsi', 'Tanpa Nama')
                        df_mapped['Unit'] = df_new.get('satuan', 'ls')
                        df_mapped['Price'] = df_new.get('harga_satuan', 0)
                        df_mapped['Category'] = category_name
                        df_mapped['Source'] = "Uploaded"
                        
                        # Hanya ambil yang punya harga (bukan header kosong)
                        df_mapped = df_mapped[df_mapped['Price'] > 0]
                        
                        all_data.append(df_mapped)
                        
                except Exception as e:
                    st.error(f"Gagal memproses {uploaded_file.name}: {e}")
                
                # Hapus file temp
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                progress_bar.progress((i + 1) / len(uploaded_db_files))

            # Gabungkan semua data
            if all_data:
                st.session_state['master_database'] = pd.concat(all_data, ignore_index=True)
                st.success(f"✅ Database diperbarui! {len(st.session_state['master_database'])} item masuk.")
            else:
                st.warning("Tidak ada data valid yang ditemukan.")

    st.markdown("---")
    st.write("### ⚙️ Pengaturan Global")
    st.session_state['global_overhead'] = st.number_input("Jasa Konstruksi / Profit (%)", 0.0, 50.0, 10.0)

# ==========================================
# 2. FUNGSI UTILITAS (UI LAMA ANDA)
# ==========================================
def render_header():
    st.title("🏗️ SmartRAB - Sistem Estimasi Konstruksi SNI")
    st.markdown("Transformasi: **Statis** → **Dinamis (Database-Driven)**")
    
def to_excel_download(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    processed_data = output.getvalue()
    return processed_data

# ==========================================
# 3. TAB LOGIC (INTI APLIKASI)
# ==========================================
def main():
    render_header()
    
    # Navigasi Tab (Sama persis seperti permintaan Anda)
    tabs = st.tabs([
        "📋 Data Proyek", 
        "📚 AHSP Master (Database)", 
        "✏️ Input Volume", 
        "💰 Preview RAB", 
        "🧱 Rekap Material",
        "📈 Kurva S"
    ])

    # === TAB 1: DATA PROYEK ===
    with tabs[0]:
        st.header("📋 Informasi Umum Proyek")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state['project_data']['nama'] = st.text_input("Nama Proyek", value=st.session_state['project_data'].get('nama', 'Pembangunan Gedung Serbaguna'))
            st.session_state['project_data']['lokasi'] = st.text_input("Lokasi", value=st.session_state['project_data'].get('lokasi', 'Jakarta Selatan'))
        with col2:
            st.session_state['project_data']['pemilik'] = st.text_input("Pemilik", value=st.session_state['project_data'].get('pemilik', 'Dinas PU'))
            st.session_state['project_data']['tahun'] = st.text_input("Tahun Anggaran", value=st.session_state['project_data'].get('tahun', '2025'))
        
        st.success("Data proyek tersimpan di memori sementara.")

    # === TAB 2: AHSP MASTER (DATABASE) ===
    with tabs[1]:
        st.header("📚 Database Harga Satuan (AHSP & Sumber Daya)")
        
        # Cek apakah database sudah diisi lewat sidebar
        if st.session_state['master_database'].empty:
            st.warning("⚠️ Database masih kosong. Silakan upload file CSV di Sidebar sebelah kiri.")
            st.info("Tips: Upload file 'Beton.csv.csv' dan 'Upah Bahan.csv' Anda.")
        else:
            df_master = st.session_state['master_database']
            
            # Filter Kategori
            categories = ["Semua"] + list(df_master['Category'].unique())
            selected_cat = st.selectbox("Filter Kategori:", categories)
            
            if selected_cat != "Semua":
                df_view = df_master[df_master['Category'] == selected_cat]
            else:
                df_view = df_master
            
            st.dataframe(df_view, use_container_width=True)
            st.caption(f"Total Item: {len(df_view)}")

    # === TAB 3: INPUT VOLUME (ESTIMASI) ===
    with tabs[2]:
        st.header("✏️ Penyusunan RAB")
        
        if st.session_state['master_database'].empty:
            st.error("Harap isi database terlebih dahulu di Sidebar.")
        else:
            df_master = st.session_state['master_database']
            
            # Form Input Item Baru
            with st.form("add_item_form"):
                c1, c2, c3 = st.columns([3, 1, 1])
                
                # Dropdown Item dari Database
                # Kita gabungkan Category + Item untuk memudahkan pencarian
                df_master['Display'] = df_master['Category'] + " - " + df_master['Item']
                item_options = df_master['Display'].tolist()
                
                with c1:
                    selected_display = st.selectbox("Pilih Item Pekerjaan (Cari...)", item_options)
                
                with c2:
                    volume = st.number_input("Volume", min_value=0.0, step=0.01)
                    
                # Cari data unit dan harga berdasarkan pilihan
                selected_row = df_master[df_master['Display'] == selected_display].iloc[0]
                unit = selected_row['Unit']
                base_price = selected_row['Price']
                
                with c3:
                    st.text_input("Satuan", value=unit, disabled=True)
                    st.caption(f"Harga Dasar: Rp {base_price:,.0f}")

                submit = st.form_submit_button("➕ Tambah ke RAB")
                
                if submit and volume > 0:
                    # Hitung Total
                    total_price = volume * base_price
                    
                    new_entry = {
                        "Uraian": selected_row['Item'],
                        "Kategori": selected_row['Category'],
                        "Volume": volume,
                        "Satuan": unit,
                        "Harga Satuan": base_price,
                        "Jumlah Harga": total_price
                    }
                    st.session_state['rab_items'].append(new_entry)
                    st.success(f"Berhasil menambahkan: {selected_row['Item']}")

            # Tabel Sementara
            if st.session_state['rab_items']:
                st.subheader("Daftar Item Sementara")
                df_rab_temp = pd.DataFrame(st.session_state['rab_items'])
                st.dataframe(df_rab_temp, use_container_width=True)
                
                if st.button("🗑️ Reset RAB"):
                    st.session_state['rab_items'] = []
                    st.rerun()

    # === TAB 4: PREVIEW RAB ===
    with tabs[3]:
        st.header("💰 Rencana Anggaran Biaya (RAB)")
        
        if not st.session_state['rab_items']:
            st.info("Belum ada item RAB. Silakan input di Tab 3.")
        else:
            df_rab = pd.DataFrame(st.session_state['rab_items'])
            
            # Grouping by Category (Sub-Total)
            st.subheader(f"Proyek: {st.session_state['project_data'].get('nama', '-')}")
            
            # Kalkulasi Overhead Global
            overhead_pct = st.session_state['global_overhead'] / 100
            
            grand_total = 0
            
            # Loop per kategori untuk tampilan rapi
            unique_cats = df_rab['Kategori'].unique()
            
            final_view = []
            
            for cat in unique_cats:
                st.markdown(f"**{cat}**")
                df_cat = df_rab[df_rab['Kategori'] == cat]
                
                # Tampilkan tabel per kategori
                st.table(df_cat[['Uraian', 'Volume', 'Satuan', 'Harga Satuan', 'Jumlah Harga']])
                
                subtotal = df_cat['Jumlah Harga'].sum()
                grand_total += subtotal
                st.markdown(f"*Sub-Total {cat}: Rp {subtotal:,.2f}*")
                st.markdown("---")
            
            # Rekapitulasi Akhir
            total_overhead = grand_total * overhead_pct
            total_final = grand_total + total_overhead
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Biaya Dasar", f"Rp {grand_total:,.2f}")
            c2.metric(f"Jasa/Profit ({st.session_state['global_overhead']}%)", f"Rp {total_overhead:,.2f}")
            c3.metric("GRAND TOTAL RAB", f"Rp {total_final:,.2f}")
            
            # Tombol Download
            st.download_button("📥 Download Excel RAB", to_excel_download(df_rab, "RAB Final"), "SmartRAB_Export.xlsx")

    # === TAB 5: REKAP MATERIAL (DUMMY/PLACEHOLDER) ===
    with tabs[4]:
        st.header("🧱 Rekapitulasi Kebutuhan Material")
        st.info("Fitur ini akan aktif setelah Logika Penautan (Linked List) di Fase 2 selesai.")
        st.caption("Saat ini sistem baru menghitung berdasarkan Harga Satuan Jadi, belum memecah ke semen/pasir secara otomatis.")

    # === TAB 6: KURVA S (VISUALISASI) ===
    with tabs[5]:
        st.header("📈 Kurva S - Jadwal Proyek")
        
        if not st.session_state['rab_items']:
            st.warning("Buat RAB terlebih dahulu.")
        else:
            # Simulasi Data Kurva S Sederhana
            df_rab = pd.DataFrame(st.session_state['rab_items'])
            total_cost = df_rab['Jumlah Harga'].sum()
            
            # Buat data dummy per minggu (distribusi normal sederhana)
            weeks = list(range(1, 13)) # 12 Minggu
            bobot_per_minggu = [2, 5, 8, 10, 15, 20, 15, 10, 8, 4, 2, 1] # Total 100%
            
            cumulative = 0
            curve_data = []
            for w, b in zip(weeks, bobot_per_minggu):
                cumulative += b
                cost_week = (b/100) * total_cost
                curve_data.append({"Minggu": w, "Bobot Rencana": cumulative, "Biaya": cost_week})
            
            df_curve = pd.DataFrame(curve_data)
            
            # Plot Chart
            chart = alt.Chart(df_curve).mark_line(point=True, color='red').encode(
                x='Minggu',
                y='Bobot Rencana',
                tooltip=['Minggu', 'Bobot Rencana']
            ).properties(title="Rencana Kumulatif (%)")
            
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(df_curve)

if __name__ == "__main__":
    main()
