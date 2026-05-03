import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Toko App", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

@st.cache_data(ttl=5)
def get_data(q):
    return pd.read_sql(q, conn)

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

    df = get_data("SELECT nama, harga, stok FROM produk")

    if not df.empty:
        df["harga"] = df["harga"].astype(int)
        df["stok"] = df["stok"].astype(int)

        # kita anggap stok sekarang = stok masuk (akumulasi)
        df["Stok Masuk"] = df["stok"]
        df["Sisa Stok"] = df["stok"]

        total_masuk = int((df["Stok Masuk"] * df["harga"]).sum())
        total_sisa = int((df["Sisa Stok"] * df["harga"]).sum())

        col1, col2 = st.columns(2)
        col1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        col2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.dataframe(
            df[["nama", "Stok Masuk", "Sisa Stok"]],
            use_container_width=True
        )

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

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id, nama, harga, stok FROM produk")

    if not df.empty:
        df["harga"] = df["harga"].astype(int)
        df["stok"] = df["stok"].astype(int)

        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Nama Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
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
                """, (
                    owner,
                    produk,
                    int(jumlah),
                    int(total)
                ))

                conn.commit()
                st.success("Barang keluar berhasil")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Data Owner")

    tgl = st.date_input("Filter Tanggal", value=date.today())

    df_t = get_data(f"""
        SELECT owner, produk, jumlah, total, waktu
        FROM transaksi
        WHERE DATE(waktu) = '{tgl}'
    """)

    df_p = get_data("SELECT owner, jumlah, metode FROM pembayaran")

    if not df_t.empty:
        owners = df_t.groupby("owner").first().reset_index()

        for i, row in owners.iterrows():
            owner = row["owner"]

            df_owner = df_t[df_t["owner"] == owner]
            total = int(df_owner["total"].sum())

            df_b = df_p[df_p["owner"] == owner] if not df_p.empty else pd.DataFrame()
            sudah = int(df_b["jumlah"].sum()) if not df_b.empty else 0

            sisa = total - sudah
            status = "Lunas" if sisa <= 0 else "Belum Lunas"

            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)

            col1.write(i+1)
            col2.write(owner)
            col3.write(status)
            col4.write(f"Rp {sisa:,}")

            with st.expander("Detail"):
                st.dataframe(df_owner)

                bayar = st.number_input("Bayar", key=f"b{i}")
                metode = st.selectbox("Metode", ["cash","bank"], key=f"m{i}")

                if st.button("Simpan", key=f"s{i}"):
                    c.execute("""
                        INSERT INTO pembayaran (owner, jumlah, metode)
                        VALUES (%s,%s,%s)
                    """, (owner, int(bayar), metode))
                    conn.commit()
                    st.success("Pembayaran masuk")

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah")
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("""
            INSERT INTO pengeluaran (jumlah, metode, keterangan)
            VALUES (%s,%s,%s)
        """, (int(jumlah), metode, ket))
        conn.commit()
        st.success("Pengeluaran disimpan")

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    mode = st.radio("Mode", ["Harian","Bulanan"])

    if mode == "Harian":
        tgl = st.date_input("Tanggal", value=date.today())

        df_t = get_data(f"""
            SELECT total, waktu FROM transaksi
            WHERE DATE(waktu) = '{tgl}'
        """)
    else:
        bulan = st.date_input("Pilih Bulan", value=date.today())

        df_t = get_data(f"""
            SELECT total, waktu FROM transaksi
            WHERE DATE_TRUNC('month', waktu) =
                  DATE_TRUNC('month', DATE '{bulan}')
        """)

    if not df_t.empty:
        df_t["tanggal"] = pd.to_datetime(df_t["waktu"]).dt.date
        grafik = df_t.groupby("tanggal")["total"].sum().reset_index()

        st.subheader("Grafik Penjualan")
        fig = px.line(grafik, x="tanggal", y="total", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    df_b = get_data("SELECT jumlah, metode FROM pembayaran")
    df_k = get_data("SELECT jumlah FROM pengeluaran")

    cash = int(df_b[df_b["metode"]=="cash"]["jumlah"].sum()) if not df_b.empty else 0
    bank = int(df_b[df_b["metode"]=="bank"]["jumlah"].sum()) if not df_b.empty else 0
    keluar = int(df_k["jumlah"].sum()) if not df_k.empty else 0

    saldo = (cash + bank) - keluar

    st.metric("Saldo", f"Rp {saldo:,}")