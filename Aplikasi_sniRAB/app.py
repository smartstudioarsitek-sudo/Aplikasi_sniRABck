import streamlit as st
import pandas as pd
import io
import xlsxwriter
import altair as alt
import os

# --- IMPORT OTAK BARU ---
try:
    from src.parsers import extract_ahsp_items
except ImportError:
    st.error("⚠️ File src/parsers.py tidak ditemukan.")
    st.stop()

# ==========================================
# KONFIGURASI HALAMAN (ASLI APP 36)
# ==========================================
st.set_page_config(page_title="SmartRAB - Sistem Estimasi Konstruksi", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    .main-header {font-size: 30px; font-weight: bold; color: #2E86C1; text-align: center; margin-bottom: 20px;}
    .sub-header {font-size: 18px; color: #555; text-align: center; margin-bottom: 30px;}
    .card {background-color: #f9f9f9; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# Inisialisasi Session State
if 'project_data' not in st.session_state: st.session_state['project_data'] = {}
if 'rab_items' not in st.session_state: st.session_state['rab_items'] = []
if 'global_overhead' not in st.session_state: st.session_state['global_overhead'] = 10.0
if 'dynamic_ahsp_data' not in st.session_state: st.session_state['dynamic_ahsp_data'] = []

# ==========================================
# LOGIKA PEMETAAN DIVISI (STANDAR PU)
# ==========================================
def map_filename_to_division(filename):
    """
    Deep Thinking: Memetakan nama file sembarang ke Standar Divisi PU.
    """
    fname = filename.lower()
    
    # Divisi 1: Umum
    if any(x in fname for x in ['persiapan', 'k3', 'mobilisasi', 'bongkaran', 'angkut']):
        return "Divisi 1: Umum & Persiapan"
    
    # Divisi 2: Tanah & Pondasi
    if any(x in fname for x in ['tanah', 'galian', 'urugan', 'timbunan', 'pondasi', 'drainase', 'sumur']):
        return "Divisi 2: Pekerjaan Tanah & Pondasi"
    
    # Divisi 3: Struktur
    if any(x in fname for x in ['beton', 'baja', 'risha', 'tiang pancang', 'sloof', 'kolom', 'balok', 'plat']):
        return "Divisi 3: Pekerjaan Struktur"
    
    # Divisi 4: Arsitektur
    if any(x in fname for x in ['dinding', 'lantai', 'plafon', 'cat', 'pengecatan', 'keramik', 'pintu', 'jendela', 'kaca', 'alumunium', 'atap', 'sanitair', 'ornamen', 'railing']):
        return "Divisi 4: Pekerjaan Arsitektur"
    
    # Divisi 5: MEP
    if any(x in fname for x in ['listrik', 'elektrikal', 'mekanikal', 'pipa', 'plambing', 'air minum', 'air limbah', 'ac', 'stop kontak']):
        return "Divisi 5: Mekanikal & Elektrikal"
    
    # Divisi 6: Eksternal / Lansekap
    if any(x in fname for x in ['lansekap', 'jalan', 'paving', 'pagar', 'signage', 'taman']):
        return "Divisi 6: Lansekap & Luar Gedung"
        
    return "Divisi Lainnya"

# ==========================================
# SIDEBAR: UPLOAD DATABASE
# ==========================================
with st.sidebar:
    st.header("📂 Database Control")
    st.info("Upload Semua File AHSP (Beton, Arsitek, MEP, dll) di sini.")
    
    uploaded_db_files = st.file_uploader(
        "Pilih File CSV", 
        accept_multiple_files=True,
        type=['csv']
    )
    
    if uploaded_db_files:
        if st.button("🔄 Update Full Database"):
            all_data_list = []
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_db_files):
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                try:
                    # 1. Tentukan Divisi berdasarkan Nama File
                    division = map_filename_to_division(uploaded_file.name)
                    
                    # 2. Ekstrak Item & Harga (Pakai Parser Baru)
                    df_items = extract_ahsp_items(temp_path)
                    
                    if not df_items.empty:
                        for _, row in df_items.iterrows():
                            all_data_list.append({
                                "Category": division, # Kategori sekarang adalah DIVISI
                                "SubCategory": uploaded_file.name.replace('.csv', '').replace('data_rab (2).xlsx - ', ''),
                                "Item": row['Item'],
                                "Unit": row['Unit'],
                                "Price": row['Price']
                            })
                            
                except Exception as e:
                    st.error(f"Error {uploaded_file.name}: {e}")
                
                if os.path.exists(temp_path): os.remove(temp_path)
                progress_bar.progress((i + 1) / len(uploaded_db_files))
            
            st.session_state['dynamic_ahsp_data'] = all_data_list
            st.success(f"✅ Database Update! {len(all_data_list)} item pekerjaan masuk.")

# ==========================================
# MAIN APP (LOGIKA UI TETAP)
# ==========================================
def load_ahsp_database():
    return st.session_state['dynamic_ahsp_data']

def render_header():
    st.markdown('<div class="main-header">🏗️ SmartRAB - Sistem Estimasi Konstruksi SNI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Perencanaan Anggaran Biaya, Analisis Material & Jadwal Proyek</div>', unsafe_allow_html=True)

def render_footer():
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #888; font-size: 12px;'>&copy; 2025 SmartRAB System | Berbasis SNI 2024</div>", unsafe_allow_html=True)

def to_excel_download(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- FUNGSI DUMMY KURVA S ---
def generate_s_curve_data():
    if not st.session_state['rab_items']: return None, None
    df = pd.DataFrame(st.session_state['rab_items'])
    total = df['Jumlah Harga'].sum()
    weeks = list(range(1, 13))
    weights = [2, 4, 7, 10, 15, 20, 18, 12, 6, 3, 2, 1]
    data = []
    cum = 0
    for w, wei in zip(weeks, weights):
        cum += wei
        data.append({"Minggu": w, "Rencana_Kumulatif": cum})
    return df, pd.DataFrame(data)

def main():
    render_header()
    
    # Load Data (Format Baru: Ada Divisi)
    ahsp_data = load_ahsp_database()
    df_master = pd.DataFrame(ahsp_data)

    tabs = st.tabs(["📋 Data Proyek", "📚 AHSP Master", "✏️ Input RAB", "💰 Preview RAB", "🧱 Rekap Material", "📈 Kurva S"])

    # === TAB 1: DATA PROYEK ===
    with tabs[0]:
        st.header("📋 Informasi Umum Proyek")
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            st.session_state['project_data']['nama'] = c1.text_input("Nama Proyek", value=st.session_state['project_data'].get('nama', ''))
            st.session_state['project_data']['lokasi'] = c1.text_input("Lokasi", value=st.session_state['project_data'].get('lokasi', ''))
            st.session_state['project_data']['pemilik'] = c2.text_input("Pemilik", value=st.session_state['project_data'].get('pemilik', ''))
            st.session_state['project_data']['tahun'] = c2.text_input("Tahun", value=st.session_state['project_data'].get('tahun', '2025'))
            st.markdown('</div>', unsafe_allow_html=True)
        render_footer()

    # === TAB 2: AHSP MASTER (UI BARU: GROUP BY DIVISI) ===
    with tabs[1]:
        st.header("📚 Katalog Harga Satuan (AHSP)")
        if df_master.empty:
            st.warning("⚠️ Database Kosong! Upload file CSV di Sidebar.")
        else:
            # Filter Divisi
            divisi_list = sorted(df_master['Category'].unique())
            selected_div = st.selectbox("Pilih Divisi Pekerjaan:", ["Semua Divisi"] + divisi_list)
            
            df_view = df_master.copy()
            if selected_div != "Semua Divisi":
                df_view = df_view[df_view['Category'] == selected_div]
            
            search = st.text_input("Cari Item:", placeholder="Contoh: Beton K-250...")
            if search:
                df_view = df_view[df_view['Item'].str.contains(search, case=False)]
            
            st.dataframe(
                df_view[['Category', 'SubCategory', 'Item', 'Unit', 'Price']], 
                use_container_width=True,
                column_config={"Price": st.column_config.NumberColumn("Harga Satuan", format="Rp %d")}
            )
            st.caption(f"Total Item: {len(df_view)}")
        render_footer()

    # === TAB 3: INPUT RAB ===
    with tabs[2]:
        st.header("✏️ Input Item Pekerjaan")
        if df_master.empty:
            st.error("Upload database dulu.")
        else:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # Dropdown Bertingkat (Divisi -> Item)
                div_opts = sorted(df_master['Category'].unique())
                sel_div_input = st.selectbox("1. Pilih Divisi:", div_opts, key="div_input")
                
                # Filter Item berdasarkan Divisi
                df_filtered = df_master[df_master['Category'] == sel_div_input]
                df_filtered['Label'] = df_filtered['SubCategory'] + " | " + df_filtered['Item']
                
                item_opts = df_filtered['Label'].tolist()
                sel_item_label = st.selectbox("2. Pilih Item:", item_opts, key="item_input")
                
                # Ambil Data
                sel_row = df_filtered[df_filtered['Label'] == sel_item_label].iloc[0]
                
                c1, c2, c3 = st.columns([1,1,2])
                vol = c1.number_input("Volume:", min_value=0.0, step=0.01)
                c2.text_input("Satuan:", value=sel_row['Unit'], disabled=True)
                total = vol * sel_row['Price']
                c3.text_input("Total:", value=f"Rp {total:,.0f}", disabled=True)
                
                if st.button("➕ Tambah Item"):
                    st.session_state['rab_items'].append({
                        "Divisi": sel_row['Category'],
                        "Uraian": sel_row['Item'],
                        "Volume": vol,
                        "Satuan": sel_row['Unit'],
                        "Harga Satuan": sel_row['Price'],
                        "Jumlah Harga": total
                    })
                    st.success("Item Masuk!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state['rab_items']:
                st.dataframe(pd.DataFrame(st.session_state['rab_items']))
                if st.button("Hapus Semua"): st.session_state['rab_items'] = []; st.rerun()

    # === TAB 4: PREVIEW RAB ===
    with tabs[3]:
        st.header("💰 Rencana Anggaran Biaya")
        if st.session_state['rab_items']:
            df_rab = pd.DataFrame(st.session_state['rab_items'])
            
            grand_total = 0
            # Grouping by Divisi
            for div in sorted(df_rab['Divisi'].unique()):
                st.subheader(div)
                df_sub = df_rab[df_rab['Divisi'] == div]
                st.table(df_sub[['Uraian', 'Volume', 'Satuan', 'Harga Satuan', 'Jumlah Harga']])
                sub_tot = df_sub['Jumlah Harga'].sum()
                st.markdown(f"**Subtotal {div}: Rp {sub_tot:,.0f}**")
                grand_total += sub_tot
                st.markdown("---")
            
            st.metric("GRAND TOTAL", f"Rp {grand_total:,.0f}")
            st.download_button("Download Excel", to_excel_download(df_rab, "RAB"), "RAB.xlsx")
        else:
            st.info("RAB Kosong")
        render_footer()

    # === TAB 5 & 6 (Standard) ===
    with tabs[4]: st.header("🧱 Rekap Material"); st.info("Coming Soon"); render_footer()
    with tabs[5]: 
        st.header("📈 Kurva S")
        _, df_curve = generate_s_curve_data()
        if df_curve is not None:
            chart = alt.Chart(df_curve).mark_line().encode(x='Minggu', y='Rencana_Kumulatif')
            st.altair_chart(chart, use_container_width=True)
        render_footer()

if __name__ == "__main__":
    main()
