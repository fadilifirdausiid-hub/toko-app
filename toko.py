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
        df["Masuk"] = df["stok"]   # sementara
        df["Sisa"] = df["stok"]

        total_masuk = int(df["Masuk"].sum())
        total_sisa = int(df["Sisa"].sum())

        # ====== HEADER TOTAL ======
        col1, col2 = st.columns(2)
        col1.metric("📥 Total Stok Masuk", total_masuk)
        col2.metric("📦 Total Stok Sisa", total_sisa)

        st.markdown("---")

        # ====== TABEL UTAMA ======
        st.subheader("📦 Stok Produk")

        df_tampil = df[["nama", "Masuk", "Sisa"]]
        df_tampil.columns = ["Nama Produk", "Masuk", "Sisa"]

        st.dataframe(df_tampil, use_container_width=True)

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
