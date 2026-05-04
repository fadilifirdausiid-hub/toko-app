import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# ================= CONFIG =================
st.set_page_config(page_title="Aplikasi Toko", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(
    "postgresql://postgres.slikespgjmlzpgqjimno:Fadili161299@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
)
c = conn.cursor()

# ================= HELPER =================
def get_data(q):
    return pd.read_sql(q, conn)

# ================= MENU =================
menu = st.sidebar.selectbox("Menu", [
    "Dashboard",
    "Barang Masuk",
    "Barang Keluar"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard Toko")

    df_produk = get_data("SELECT * FROM produk")
    df_keu = get_data("SELECT * FROM keuangan")

    # ================= RINGKASAN =================
    total_stok = int(df_produk["stok"].sum()) if not df_produk.empty else 0

    cash = int(df_keu[df_keu["metode"]=="cash"]["jumlah"].sum()) if not df_keu.empty else 0
    bank = int(df_keu[df_keu["metode"]=="bank"]["jumlah"].sum()) if not df_keu.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Produk", len(df_produk))
    col2.metric("📊 Total Stok", total_stok)
    col3.metric("💵 Cash", f"Rp {cash:,}")

    st.metric("🏦 Bank", f"Rp {bank:,}")

    st.markdown("---")

    # ================= STOK PER PRODUK =================
    st.subheader("📦 Stok Barang per Merk")

    if not df_produk.empty:
        df_view = df_produk[["nama", "stok"]]
        df_view.columns = ["Nama Produk", "Sisa Stok"]

        st.dataframe(df_view, use_container_width=True)

        # tampil per baris biar lebih jelas
        st.markdown("### Detail Stok:")
        for i, row in df_view.iterrows():
            col1, col2 = st.columns([3,1])
            col1.write(f"🔹 {row['Nama Produk']}")
            col2.write(f"📦 {int(row['Sisa Stok'])}")

    else:
        st.warning("Belum ada data produk")

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    nama = st.text_input("Nama Produk")
    harga = st.number_input("Harga", 0)
    jumlah = st.number_input("Jumlah Masuk", 0)

    if st.button("Simpan"):
        # cek apakah produk sudah ada
        c.execute("SELECT id, stok FROM produk WHERE nama=%s", (nama,))
        data = c.fetchone()

        if data:
            # update stok
            c.execute(
                "UPDATE produk SET stok = stok + %s WHERE id=%s",
                (jumlah, data[0])
            )
        else:
            # insert baru
            c.execute(
                "INSERT INTO produk (nama,harga,stok) VALUES (%s,%s,%s)",
                (nama, int(harga), int(jumlah))
            )

        conn.commit()
        st.success("Barang masuk berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT * FROM produk")

    if df.empty:
        st.warning("Belum ada produk")
    else:
        produk = st.selectbox("Pilih Produk", df["nama"])
        jumlah = st.number_input("Jumlah Keluar", 1)

        if st.button("Proses"):
            row = df[df["nama"] == produk].iloc[0]

            if jumlah > row["stok"]:
                st.error("Stok tidak cukup")
            else:
                c.execute(
                    "UPDATE produk SET stok = stok - %s WHERE id=%s",
                    (jumlah, int(row["id"]))
                )
                conn.commit()
                st.success("Barang keluar berhasil")
