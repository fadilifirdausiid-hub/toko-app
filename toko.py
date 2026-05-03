import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.set_page_config(page_title="Toko App", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= SAFE QUERY =================
@st.cache_data(ttl=5)
def get_data(q):
    try:
        return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

# ================= MENU =================
menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Barang Masuk",
    "Barang Keluar",
    "Owner Order",
    "Pengeluaran",
    "Closing"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    df_produk = get_data("SELECT nama, harga, stok FROM produk")
    df_keluar = get_data("SELECT produk, jumlah FROM transaksi")

    if not df_produk.empty:

        df_produk["stok"] = df_produk["stok"].astype(int)
        df_produk["harga"] = df_produk["harga"].astype(int)

        # hitung barang keluar
        if not df_keluar.empty:
            keluar = df_keluar.groupby("produk")["jumlah"].sum().reset_index()
        else:
            keluar = pd.DataFrame(columns=["produk","jumlah"])

        df = df_produk.copy()
        df = df.merge(keluar, left_on="nama", right_on="produk", how="left")
        df["jumlah"] = df["jumlah"].fillna(0)

        # LOGIKA FINAL (AMAN)
        df["Stok Masuk"] = df["stok"] + df["jumlah"]
        df["Sisa Stok"] = df["stok"]

        total_masuk = int((df["Stok Masuk"] * df["harga"]).sum())
        total_sisa = int((df["Sisa Stok"] * df["harga"]).sum())

        col1, col2 = st.columns(2)
        col1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        col2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.dataframe(df[["nama","Stok Masuk","Sisa Stok"]], use_container_width=True)

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    nama = st.text_input("Nama Produk")
    harga = st.number_input("Harga", 0)
    jumlah = st.number_input("Jumlah", 0)

    if st.button("Simpan"):
        try:
            c.execute("SELECT id FROM produk WHERE nama=%s", (nama,))
            data = c.fetchone()

            if data:
                c.execute(
                    "UPDATE produk SET stok = stok + %s WHERE id=%s",
                    (int(jumlah), int(data[0]))
                )
            else:
                c.execute(
                    "INSERT INTO produk (nama, harga, stok) VALUES (%s,%s,%s)",
                    (nama, int(harga), int(jumlah))
                )

            conn.commit()
            st.success("Barang masuk berhasil")

        except:
            st.error("Error barang masuk")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id, nama, harga, stok FROM produk")

    if not df.empty:
        df["stok"] = df["stok"].astype(int)
        df["harga"] = df["harga"].astype(int)

        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
            try:
                row = df[df["nama"] == produk].iloc[0]

                if int(jumlah) > int(row["stok"]):
                    st.error("Stok tidak cukup")
                else:
                    total = int(jumlah) * int(row["harga"])

                    c.execute(
                        "UPDATE produk SET stok = stok - %s WHERE id=%s",
                        (int(jumlah), int(row["id"]))
                    )

                    c.execute("""
                        INSERT INTO transaksi (owner, produk, jumlah, total, waktu)
                        VALUES (%s,%s,%s,%s,NOW())
                    """, (owner, produk, int(jumlah), int(total)))

                    conn.commit()
                    st.success("Barang keluar berhasil")

            except:
                st.error("Error barang keluar")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Data Owner")

    tgl = st.date_input("Tanggal", value=date.today())

    df_t = get_data(f"""
        SELECT owner, produk, jumlah, total, waktu
        FROM transaksi
        WHERE DATE(waktu) = '{tgl}'
    """)

    if not df_t.empty:
        owners = df_t.groupby("owner").first().reset_index()

        for i, row in owners.iterrows():
            owner = row["owner"]
            df_owner = df_t[df_t["owner"] == owner]
            total = int(df_owner["total"].sum())

            col1, col2 = st.columns(2)
            col1.write(owner)
            col2.write(f"Rp {total:,}")

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah")
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        try:
            c.execute("""
                INSERT INTO pengeluaran (jumlah, metode, keterangan)
                VALUES (%s,%s,%s)
            """, (int(jumlah), metode, ket))

            conn.commit()
            st.success("Pengeluaran disimpan")

        except:
            st.error("Error pengeluaran")

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_keluar = get_data("SELECT total FROM transaksi")
    df_stok = get_data("SELECT harga, stok FROM produk")

    total_keluar = int(df_keluar["total"].sum()) if not df_keluar.empty else 0
    total_sisa = int((df_stok["stok"] * df_stok["harga"]).sum()) if not df_stok.empty else 0

    st.metric("Penjualan", f"Rp {total_keluar:,}")
    st.metric("Sisa Barang", f"Rp {total_sisa:,}")

    st.success(f"Balance: Rp {total_keluar + total_sisa:,}")