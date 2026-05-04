import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, date

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
    "Barang Keluar",
    "Pembayaran",
    "Pengeluaran",
    "Closing Harian"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard Toko")

    df = get_data("SELECT * FROM produk")

    if not df.empty:
        df["Masuk"] = df["stok"]
        df["Sisa"] = df["stok"]

        total_masuk = int(df["Masuk"].sum())
        total_sisa = int(df["Sisa"].sum())

        col1, col2 = st.columns(2)
        col1.metric("📥 Total Masuk", total_masuk)
        col2.metric("📦 Total Sisa", total_sisa)

        st.markdown("---")

        df_tampil = df[["nama", "Masuk", "Sisa"]]
        df_tampil.columns = ["Nama Produk", "Masuk", "Sisa"]

        st.dataframe(df_tampil, use_container_width=True)

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    nama = st.text_input("Nama Produk")
    harga = st.number_input("Harga", 0)
    jumlah = st.number_input("Jumlah", 0)

    if st.button("Simpan"):
        c.execute("SELECT id FROM produk WHERE nama=%s", (nama,))
        data = c.fetchone()

        if data:
            c.execute("UPDATE produk SET stok = stok + %s WHERE id=%s",
                      (jumlah, data[0]))
        else:
            c.execute("INSERT INTO produk (nama,harga,stok) VALUES (%s,%s,%s)",
                      (nama, harga, jumlah))

        conn.commit()
        st.success("Barang masuk berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT * FROM produk")

    if not df.empty:
        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Nama Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
            row = df[df["nama"] == produk].iloc[0]

            if jumlah > row["stok"]:
                st.error("Stok tidak cukup")
            else:
                total = jumlah * row["harga"]

                # kurangi stok
                c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s",
                          (jumlah, int(row["id"])))

                # simpan transaksi
                c.execute("""
                    INSERT INTO transaksi (owner, produk, jumlah, total, waktu)
                    VALUES (%s,%s,%s,%s,%s)
                """, (owner, produk, jumlah, total, datetime.now()))

                conn.commit()
                st.success("Barang keluar berhasil")

# ================= PEMBAYARAN =================
elif menu == "Pembayaran":
    st.title("💳 Pembayaran")

    owner = st.text_input("Nama Owner")
    bayar = st.number_input("Jumlah Bayar", 0)
    metode = st.selectbox("Metode", ["cash", "bank"])

    if st.button("Bayar"):
        # total hutang
        df = get_data(f"SELECT * FROM transaksi WHERE owner='{owner}'")
        total = df["total"].sum() if not df.empty else 0

        # sudah bayar
        df_bayar = get_data(f"SELECT * FROM pembayaran WHERE owner='{owner}'")
        sudah = df_bayar["jumlah"].sum() if not df_bayar.empty else 0

        sisa = total - (sudah + bayar)

        c.execute("""
            INSERT INTO pembayaran (owner, jumlah, metode, waktu)
            VALUES (%s,%s,%s,%s)
        """, (owner, bayar, metode, datetime.now()))

        conn.commit()

        st.success(f"Sisa hutang: {sisa}")

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah", 0)
    metode = st.selectbox("Metode", ["cash", "bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("""
            INSERT INTO pengeluaran (jumlah, metode, keterangan, waktu)
            VALUES (%s,%s,%s,%s)
        """, (jumlah, metode, ket, datetime.now()))

        conn.commit()
        st.success("Pengeluaran disimpan")

# ================= CLOSING =================
elif menu == "Closing Harian":
    st.title("📅 Closing Harian")

    today = date.today()

    df_trans = get_data(f"SELECT * FROM pembayaran WHERE DATE(waktu)='{today}'")
    df_keluar = get_data(f"SELECT * FROM pengeluaran WHERE DATE(waktu)='{today}'")

    masuk = df_trans["jumlah"].sum() if not df_trans.empty else 0
    keluar = df_keluar["jumlah"].sum() if not df_keluar.empty else 0

    saldo = masuk - keluar

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Uang Masuk", masuk)
    col2.metric("💸 Pengeluaran", keluar)
    col3.metric("📊 Saldo Hari Ini", saldo)

    st.markdown("---")

    st.subheader("Transaksi Hari Ini")
    st.dataframe(df_trans, use_container_width=True)

    st.subheader("Pengeluaran Hari Ini")
    st.dataframe(df_keluar, use_container_width=True)
