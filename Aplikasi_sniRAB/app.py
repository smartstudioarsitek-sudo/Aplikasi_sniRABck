import streamlit as st
import pandas as pd
import io
import xlsxwriter
import altair as alt
import os

# --- IMPORT OTAK BARU (Parser) ---
# Ini wajib ada agar bisa membaca file CSV kakak yang unik itu
try:
    from src.parsers import ingest_analysis_file
except ImportError:
    st.error("⚠️ File src/parsers.py tidak ditemukan. Pastikan folder src sudah dibuat.")
    st.stop()

# ==========================================
# KONFIGURASI HALAMAN (TETAP SAMA)
# ==========================================
st.set_page_config(page_title="SmartRAB - Sistem Estimasi Konstruksi", layout="wide", page_icon="🏗️")

# CSS Styling (TETAP SAMA SESUAI APP 36)
st.markdown("""
<style>
    .main-header {font-size: 30px; font-weight: bold; color: #2E86C1; text-align: center; margin-bottom: 20px;}
    .sub-header {font-size: 18px; color: #555; text-align: center; margin-bottom: 30px;}
    .card {background-color: #f9f9f9; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px;}
    .metric-card {text-align: center; padding: 15px; background: #ffffff; border-radius: 8px; border: 1px solid #eee;}
    div[data-testid="stMetricValue"] {font-size: 24px; color: #2E86C1;}
</style>
""", unsafe_allow_html=True)

# Inisialisasi Session State (Agar data persisten)
if 'project_data' not in st.session_state:
    st.session_state['project_data'] = {}
if 'rab_items' not in st.session_state:
    st.session_state['rab_items'] = []
if 'global_overhead' not in st.session_state:
    st.session_state['global_overhead'] = 10.0
# State baru untuk menyimpan data upload
if 'dynamic_ahsp_data' not in st.session_state:
    st.session_state['dynamic_ahsp_data'] = []

# ==========================================
# 1. MODUL SIDEBAR (BARU: UPLOAD DATABASE)
# ==========================================
# Kita taruh logika upload di sini agar tidak mengganggu UI utama
with st.sidebar:
    st.header("📂 Database Control")
    st.info("Upload file CSV Analisis & Harga di sini (Beton, Upah, dll)")
    
    uploaded_db_files = st.file_uploader(
        "Pilih File CSV", 
        accept_multiple_files=True,
        type=['csv']
    )
    
    if uploaded_db_files:
        if st.button("🔄 Update Database"):
            all_data_list = []
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_db_files):
                # Simpan file sementara
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                try:
                    # PROSES PARSING (OTAK BARU)
                    df_new = ingest_analysis_file(temp_path)
                    
                    # Ambil Nama Kategori dari nama file
                    cat_name = uploaded_file.name.replace('.csv', '').replace('.csv', '') # double clean
                    cat_name = cat_name.replace('data_rab (2).xlsx - ', '').strip()

                    # Konversi DataFrame ke Format List of Dict (sesuai format APP 36)
                    # APP 36 butuh: Category, Item, Unit, Price
                    if not df_new.empty and 'deskripsi' in df_new.columns:
                        for _, row in df_new.iterrows():
                            # Logika: Jika ada harga satuan, ambil. Jika 0 tapi ada koefisien, itu Analisis (skip dulu atau simpan)
                            # Untuk RAB sederhana, kita butuh harga jadi.
                            # Asumsi: File CSV kakak sudah ada harga satuannya (hasil hitungan parser)
                            
                            price = row.get('harga_satuan', 0)
                            # Jika harga 0, mungkin ini file analisis murni tanpa harga terhitung.
                            # Tapi kita masukkan saja agar user tau datanya masuk.
                            
                            item_dict = {
                                "Category": cat_name,
                                "Item": row['deskripsi'],
                                "Unit": row.get('satuan', 'ls'),
                                "Price": price
                            }
                            all_data_list.append(item_dict)
                            
                except Exception as e:
                    st.error(f"Gagal: {uploaded_file.name} - {e}")
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                progress_bar.progress((i + 1) / len(uploaded_db_files))
            
            # Simpan ke Session State untuk menggantikan data statis
            st.session_state['dynamic_ahsp_data'] = all_data_list
            st.success(f"✅ Sukses! {len(all_data_list)} item masuk database.")


# ==========================================
# 2. MODUL DATABASE AHSP (DIMODIFIKASI)
# ==========================================
def load_ahsp_database():
    """
    MODIFIKASI: Sekarang fungsi ini cerdas.
    Jika ada data hasil upload, dia pakai itu.
    Jika tidak, dia kembalikan list kosong (atau data dummy jika mau).
    """
    if st.session_state['dynamic_ahsp_data']:
        return st.session_state['dynamic_ahsp_data']
    
    # Fallback: Data Kosong agar user sadar harus upload
    # Atau bisa Kakak isi data dummy sedikit kalau mau tampilan tidak kosong saat start
    return []

# ==========================================
# 3. FUNGSI UTILITAS (TETAP SAMA)
# ==========================================
def render_header():
    st.markdown('<div class="main-header">🏗️ SmartRAB - Sistem Estimasi Konstruksi SNI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Perencanaan Anggaran Biaya, Analisis Material & Jadwal Proyek</div>', unsafe_allow_html=True)

def render_footer():
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888; font-size: 12px;'>
        &copy; 2025 SmartRAB System | Berbasis SNI 2024 | Dibuat dengan Streamlit & Python<br>
        Engine v2.0 (Dynamic Parser Integration)
    </div>
    """, unsafe_allow_html=True)

def to_excel_download(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    processed_data = output.getvalue()
    return processed_data

def render_print_button():
    st.button("🖨️ Cetak Laporan (PDF)", help="Fitur ini akan mencetak halaman ini ke PDF (Coming Soon)")

# --- FUNGSI KURVA S (DATA DUMMY UTK VISUALISASI) ---
def generate_s_curve_data():
    if not st.session_state['rab_items']:
        return None, None
    
    df_rab = pd.DataFrame(st.session_state['rab_items'])
    total_cost = df_rab['Jumlah Harga'].sum()
    
    # Simulasi Distribusi Normal (Bell Curve) untuk 12 Minggu
    weeks = list(range(1, 13))
    # Bobot progress per minggu (Total harus 100)
    weights = [2, 4, 7, 10, 15, 20, 18, 12, 6, 3, 2, 1] 
    
    curve_data = []
    cumulative = 0
    for w, weight in zip(weeks, weights):
        cumulative += weight
        weekly_cost = (weight/100) * total_cost
        curve_data.append({
            "Minggu": f"Minggu {w}",
            "Minggu_Int": w,
            "Bobot_Rencana": weight,
            "Rencana_Kumulatif": cumulative,
            "Biaya_Mingguan": weekly_cost
        })
    
    return df_rab, pd.DataFrame(curve_data)


# ==========================================
# 4. APLIKASI UTAMA (MAIN) - STRUKTUR UI TETAP
# ==========================================
def main():
    render_header()
    
    # --- LOAD DATA (DARI UPLOAD) ---
    ahsp_data = load_ahsp_database()
    df_master = pd.DataFrame(ahsp_data)

    # Tab Navigasi (Persis UI Lama)
    tabs = st.tabs(["📋 Data Proyek", "📚 AHSP Master", "✏️ Input RAB", "💰 Preview RAB", "🧱 Rekap Material", "📈 Kurva S"])

    # === TAB 1: DATA PROYEK ===
    with tabs[0]:
        st.header("📋 Informasi Umum Proyek")
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.session_state['project_data']['nama'] = st.text_input("Nama Proyek", value=st.session_state['project_data'].get('nama', 'Pembangunan Gedung Kantor'))
                st.session_state['project_data']['lokasi'] = st.text_input("Lokasi Proyek", value=st.session_state['project_data'].get('lokasi', 'Jakarta Selatan'))
            with col2:
                st.session_state['project_data']['pemilik'] = st.text_input("Pemilik / Owner", value=st.session_state['project_data'].get('pemilik', 'Dinas Pekerjaan Umum'))
                st.session_state['project_data']['tahun'] = st.text_input("Tahun Anggaran", value=st.session_state['project_data'].get('tahun', '2025'))
            st.markdown('</div>', unsafe_allow_html=True)
        render_footer()

    # === TAB 2: AHSP MASTER ===
    with tabs[1]:
        st.header("📚 Katalog Harga Satuan (AHSP)")
        
        if df_master.empty:
            st.warning("⚠️ Database Kosong! Silakan Upload File CSV di Sidebar sebelah kiri.")
            st.info("Format CSV: 'Beton.csv', 'Upah Bahan.csv', dll.")
        else:
            col_filter1, col_filter2 = st.columns([1, 2])
            with col_filter1:
                categories = ["Semua Kategori"] + sorted(list(df_master['Category'].unique()))
                selected_cat = st.selectbox("Filter Kategori:", categories)
            
            with col_filter2:
                search_query = st.text_input("Cari Item Pekerjaan:", placeholder="Contoh: Beton, Galian, Pipa...")
            
            # Filtering Logic
            df_view = df_master.copy()
            if selected_cat != "Semua Kategori":
                df_view = df_view[df_view['Category'] == selected_cat]
            if search_query:
                df_view = df_view[df_view['Item'].str.contains(search_query, case=False)]
                
            st.dataframe(
                df_view[['Category', 'Item', 'Unit', 'Price']], 
                use_container_width=True,
                column_config={
                    "Price": st.column_config.NumberColumn("Harga Satuan", format="Rp %d")
                }
            )
            st.caption(f"Menampilkan {len(df_view)} item dari total {len(df_master)} database.")
        render_footer()

    # === TAB 3: INPUT RAB ===
    with tabs[2]:
        st.header("✏️ Input Item Pekerjaan")
        
        if df_master.empty:
            st.error("Database belum siap. Harap upload data terlebih dahulu.")
        else:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # Input Form
                c1, c2 = st.columns([3, 1])
                
                # Dropdown Cerdas (Gabung Kategori + Item)
                df_master['Display_Label'] = df_master['Category'] + " | " + df_master['Item']
                options = df_master['Display_Label'].tolist()
                
                with c1:
                    selected_label = st.selectbox("Pilih Item Pekerjaan:", options)
                
                # Ambil data baris terpilih
                selected_row = df_master[df_master['Display_Label'] == selected_label].iloc[0]
                
                with c2:
                    st.metric("Harga Satuan", f"Rp {selected_row['Price']:,.0f}")
                
                c3, c4, c5 = st.columns([1, 1, 2])
                with c3:
                    volume_input = st.number_input("Volume:", min_value=0.0, step=0.01, format="%.2f")
                with c4:
                    st.text_input("Satuan:", value=selected_row['Unit'], disabled=True)
                with c5:
                    total_row = volume_input * selected_row['Price']
                    st.text_input("Total Harga (Estimasi):", value=f"Rp {total_row:,.2f}", disabled=True)
                
                if st.button("➕ Tambah ke Daftar RAB", type="primary"):
                    if volume_input > 0:
                        new_item = {
                            "Kategori": selected_row['Category'],
                            "Uraian Pekerjaan": selected_row['Item'],
                            "Volume": volume_input,
                            "Satuan": selected_row['Unit'],
                            "Harga Satuan": selected_row['Price'],
                            "Jumlah Harga": total_row
                        }
                        st.session_state['rab_items'].append(new_item)
                        st.success("Item berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.warning("Volume tidak boleh 0.")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Tabel Preview Kecil
            if st.session_state['rab_items']:
                st.subheader("Daftar Sementara")
                st.dataframe(pd.DataFrame(st.session_state['rab_items']), use_container_width=True)
                if st.button("Hapus Semua Item"):
                    st.session_state['rab_items'] = []
                    st.rerun()

    # === TAB 4: PREVIEW RAB ===
    with tabs[3]:
        st.header("💰 Rencana Anggaran Biaya (RAB)")
        
        if not st.session_state['rab_items']:
            st.info("Belum ada data RAB. Silakan input di Tab Input RAB.")
        else:
            df_rab = pd.DataFrame(st.session_state['rab_items'])
            
            # Rekapitulasi per Kategori
            st.subheader(f"Proyek: {st.session_state['project_data'].get('nama', '-')}")
            
            # Pengaturan Overhead
            st.session_state['global_overhead'] = st.slider("Margin / Jasa Konstruksi (%)", 0, 30, 10)
            
            grand_total_real = 0
            
            unique_cats = df_rab['Kategori'].unique()
            for cat in unique_cats:
                st.markdown(f"**{cat}**")
                df_sub = df_rab[df_rab['Kategori'] == cat]
                st.table(df_sub[['Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 'Jumlah Harga']])
                subtotal = df_sub['Jumlah Harga'].sum()
                grand_total_real += subtotal
                st.caption(f"Sub-Total {cat}: Rp {subtotal:,.2f}")
                st.markdown("---")
            
            overhead_val = grand_total_real * (st.session_state['global_overhead']/100)
            grand_total_final = grand_total_real + overhead_val
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Real Cost", f"Rp {grand_total_real:,.0f}")
            col2.metric("Jasa/Overhead", f"Rp {overhead_val:,.0f}")
            col3.metric("GRAND TOTAL", f"Rp {grand_total_final:,.0f}")
            
            st.download_button("📥 Download Excel RAB", to_excel_download(df_rab, "RAB Final"), "RAB_Export.xlsx")
        render_footer()

    # === TAB 5: REKAP MATERIAL ===
    with tabs[4]:
        st.header("🧱 Rekapitulasi Material (BOM)")
        st.info("Fitur ini akan otomatis memecah Analisis (Beton -> Semen, Pasir) setelah Fase Linking selesai.")
        st.caption("Saat ini data masih berbasis Harga Satuan Jadi dari file CSV yang diupload.")
        render_footer()

    # === TAB 6: KURVA S ===
    with tabs[5]:
        st.header("📈 Kurva S - Jadwal Proyek")
        render_print_button()
        df_rab_curve, df_curve_data = generate_s_curve_data()
        
        if df_curve_data is not None:
            chart = alt.Chart(df_curve_data).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X('Minggu_Int', title='Minggu Ke-', scale=alt.Scale(domainMin=1)),
                y=alt.Y('Rencana_Kumulatif', title='Bobot Kumulatif (%)', scale=alt.Scale(domain=[0, 100])),
                tooltip=['Minggu', 'Rencana_Kumulatif', 'Biaya_Mingguan']
            ).properties(height=400)
            
            st.altair_chart(chart, use_container_width=True)
            
            with st.expander("Lihat Data Tabel Kurva S"):
                st.dataframe(df_curve_data)
        else:
            st.warning("Buat RAB terlebih dahulu untuk menjana Kurva S.")
        render_footer()

if __name__ == "__main__":
    main()
