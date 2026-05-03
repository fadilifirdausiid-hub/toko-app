import streamlit as st
st.title("VERSI BARU 🔥🔥🔥")
import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

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
    "Pengeluaran"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    df_produk = get_data("SELECT * FROM produk")
    df_keu = get_data("SELECT * FROM keuangan")

    total_stok = int(df_produk["stok"].sum()) if not df_produk.empty else 0

    cash = int(df_keu[df_keu["metode"]=="cash"]["jumlah"].sum()) if not df_keu.empty else 0
    bank = int(df_keu[df_keu["metode"]=="bank"]["jumlah"].sum()) if not df_keu.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Jumlah Produk", len(df_produk))
    col2.metric("Total Stok", total_stok)
    col3.metric("Saldo Cash", f"Rp {cash:,}")

    st.metric("Saldo Bank", f"Rp {bank:,}")

    st.subheader("📦 Stok Barang")
    st.dataframe(df_produk)

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    nama = st.text_input("Nama Barang")
    harga = st.number_input("Harga", 0)
    stok = st.number_input("Jumlah", 0)

    if st.button("Simpan"):
        c.execute(
            "INSERT INTO produk (nama,harga,stok) VALUES (%s,%s,%s)",
            (nama, int(harga), int(stok))
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
        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
            row = df[df["nama"] == produk].iloc[0]

            if jumlah > row["stok"]:
                st.error("Stok tidak cukup")
            else:
                total = int(row["harga"]) * int(jumlah)
                waktu = datetime.now()

                # update stok
                c.execute(
                    "UPDATE produk SET stok = stok - %s WHERE id=%s",
                    (jumlah, int(row["id"]))
                )

                # simpan transaksi
                c.execute("""
                INSERT INTO transaksi (owner,produk_id,jumlah,total,waktu)
                VALUES (%s,%s,%s,%s,%s)
                """, (owner, int(row["id"]), jumlah, total, waktu))

                conn.commit()
                st.success("Barang keluar berhasil")

# ================= PEMBAYARAN =================
elif menu == "Pembayaran":
    st.title("💰 Pembayaran")

    df_t = get_data("SELECT * FROM transaksi")
    df_b = get_data("SELECT * FROM pembayaran")

    if df_t.empty:
        st.warning("Belum ada transaksi")
    else:
        bayar = df_b.groupby("transaksi_id")["jumlah"].sum() if not df_b.empty else {}

        df_t["sudah"] = df_t["id"].map(bayar).fillna(0)
        df_t["sisa"] = df_t["total"] - df_t["sudah"]

        st.dataframe(df_t[["owner","total","sudah","sisa","waktu"]])

        st.subheader("Input Pembayaran")

        owner = st.selectbox("Owner", df_t["owner"].unique())
        df_o = df_t[df_t["owner"] == owner]

        trx_id = st.selectbox("Pilih ID Transaksi", df_o["id"])

        jumlah = st.number_input("Jumlah Bayar", 0)
        metode = st.selectbox("Metode", ["cash","bank"])

        if st.button("Bayar"):
            waktu = datetime.now()

            c.execute("""
            INSERT INTO pembayaran (transaksi_id,jumlah,metode,waktu)
            VALUES (%s,%s,%s,%s)
            """, (trx_id, int(jumlah), metode, waktu))

            c.execute("""
            INSERT INTO keuangan (tipe,jumlah,metode,keterangan,waktu)
            VALUES (%s,%s,%s,%s,%s)
            """, ("masuk", int(jumlah), metode, "pembayaran", waktu))

            conn.commit()
            st.success("Pembayaran berhasil")

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah", 0)
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        waktu = datetime.now()

        c.execute("""
        INSERT INTO keuangan (tipe,jumlah,metode,keterangan,waktu)
        VALUES (%s,%s,%s,%s,%s)
        """, ("keluar", -int(jumlah), metode, ket, waktu))

        conn.commit()
        st.success("Pengeluaran tersimpan")