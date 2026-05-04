import streamlit as st
import psycopg2
import pandas as pd

# ================= CONFIG =================
st.set_page_config(page_title="Toko App", layout="wide")

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

    df = get_data("SELECT * FROM produk")

    if df.empty:
        st.warning("Belum ada data produk")
    else:
        # ====== DATA ======
        df["stok_masuk"] = df["stok"]   # sementara
        df["stok_sisa"] = df["stok"]

        total_masuk = int(df["stok_masuk"].sum())
        total_sisa = int(df["stok_sisa"].sum())

        # ====== HEADER ======
        col1, col2 = st.columns(2)

        col1.markdown("## 📥 STOK MASUK")
        col1.metric("Total Masuk", total_masuk)

        col2.markdown("## 📦 STOK SISA")
        col2.metric("Total Sisa", total_sisa)

        st.markdown("---")

        # ====== DETAIL ======
        st.subheader("📦 Detail Stok per Produk")

        for i, row in df.iterrows():
            col1, col2, col3 = st.columns([3, 2, 2])

            col1.markdown(f"**{row['nama']}**")

            col2.markdown(
                f"<div style='text-align:center'><b>Masuk</b><br>{int(row['stok_masuk'])}</div>",
                unsafe_allow_html=True
            )

            col3.markdown(
                f"<div style='text-align:center'><b>Sisa</b><br>{int(row['stok_sisa'])}</div>",
                unsafe_allow_html=True
            )

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    nama = st.text_input("Nama Produk")
    harga = st.number_input("Harga", 0)
    jumlah = st.number_input("Jumlah Masuk", 0)

    if st.button("Simpan"):
        c.execute("SELECT id FROM produk WHERE nama=%s", (nama,))
        data = c.fetchone()

        if data:
            c.execute(
                "UPDATE produk SET stok = stok + %s WHERE id=%s",
                (jumlah, data[0])
            )
        else:
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
