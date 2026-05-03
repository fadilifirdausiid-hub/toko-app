import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

# ================= CONFIG =================
st.set_page_config(page_title="Toko App", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(
    "postgresql://postgres.hnetawqayprlvubnouui:Fadili161299@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
)
c = conn.cursor()

# ================= HELPER =================
def get_data(q):
    try:
        return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

# ================= MENU =================
menu = st.sidebar.selectbox("Menu", [
    "Dashboard",
    "Barang Masuk",
    "Barang Keluar",
    "Owner Order",
    "Pembayaran",
    "Pengeluaran",
    "Closing"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    df = get_data("SELECT * FROM produk")

    if not df.empty:
        df["Masuk"] = df["stok_masuk"]
        df["Sisa"] = df["stok"]

        col1, col2 = st.columns(2)
        col1.metric("📥 Masuk", int(df["Masuk"].sum()))
        col2.metric("📦 Sisa", int(df["Sisa"].sum()))

        st.dataframe(df[["nama", "Masuk", "Sisa"]], use_container_width=True)

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
            c.execute("""
                UPDATE produk SET stok = stok + %s,
                stok_masuk = stok_masuk + %s WHERE id=%s
            """, (jumlah, jumlah, data[0]))
        else:
            c.execute("""
                INSERT INTO produk (nama,harga,stok,stok_masuk)
                VALUES (%s,%s,%s,%s)
            """, (nama, harga, jumlah, jumlah))

        conn.commit()
        st.success("Berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT * FROM produk")

    produk = st.selectbox("Produk", df["nama"])
    owner = st.text_input("Owner")
    jumlah = st.number_input("Jumlah", 1)

    if st.button("Proses"):
        row = df[df["nama"] == produk].iloc[0]

        if jumlah > row["stok"]:
            st.error("Stok tidak cukup")
        else:
            total = jumlah * row["harga"]

            c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s",
                      (jumlah, int(row["id"])))

            c.execute("""
                INSERT INTO transaksi (owner, produk, jumlah, total)
                VALUES (%s,%s,%s,%s)
            """, (owner, produk, jumlah, total))

            conn.commit()
            st.success("Berhasil")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Data Owner")

    # FILTER TANGGAL
    tgl = st.date_input("Filter Tanggal", value=date.today())

    df_t = get_data("SELECT * FROM transaksi")
    df_p = get_data("SELECT * FROM pembayaran")

    if not df_t.empty:
        df_t["tanggal"] = pd.to_datetime(df_t["waktu"]).dt.date
        df_t = df_t[df_t["tanggal"] == tgl]

        owners = df_t.groupby("owner").first().reset_index()

        st.markdown("### List Owner")

        for i, row in owners.iterrows():
            owner = row["owner"]

            df_owner = df_t[df_t["owner"] == owner]
            total = df_owner["total"].sum()

            df_b = df_p[df_p["owner"] == owner] if not df_p.empty else pd.DataFrame()
            sudah = df_b["jumlah"].sum() if not df_b.empty else 0

            sisa = total - sudah
            status = "✅ Lunas" if sisa <= 0 else "❌ Belum"

            col1, col2, col3, col4 = st.columns([1,3,2,2])

            col1.write(i+1)
            col2.write(owner)
            col3.write(status)

            if col4.button("Edit", key=f"edit_{i}"):

                st.markdown(f"### Detail {owner}")

                st.dataframe(df_owner[["produk","jumlah","total"]])

                st.write(f"Total: {total}")
                st.write(f"Sudah Bayar: {sudah}")
                st.write(f"Sisa: {sisa}")

                bayar = st.number_input("Tambah Bayar", key=f"bayar_{i}")

                if st.button("Simpan Pembayaran", key=f"simpan_{i}"):
                    c.execute("""
                        INSERT INTO pembayaran (owner, jumlah, metode)
                        VALUES (%s,%s,%s)
                    """, (owner, bayar, "cash"))

                    conn.commit()
                    st.success("Pembayaran masuk")

# ================= PEMBAYARAN =================
elif menu == "Pembayaran":
    st.title("💳 Pembayaran Manual")

    owner = st.text_input("Owner")
    jumlah = st.number_input("Jumlah")

    if st.button("Simpan"):
        c.execute("INSERT INTO pembayaran (owner,jumlah,metode) VALUES (%s,%s,%s)",
                  (owner, jumlah, "cash"))
        conn.commit()

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah")
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("""
            INSERT INTO pengeluaran (jumlah,keterangan,metode)
            VALUES (%s,%s,%s)
        """, (jumlah, ket, "cash"))

        conn.commit()

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_p = get_data("SELECT * FROM produk")
    df_t = get_data("SELECT * FROM transaksi")
    df_b = get_data("SELECT * FROM pembayaran")
    df_k = get_data("SELECT * FROM pengeluaran")

    masuk = (df_p["stok_masuk"] * df_p["harga"]).sum()
    sisa = (df_p["stok"] * df_p["harga"]).sum()
    jual = df_t["total"].sum()
    bayar = df_b["jumlah"].sum()
    keluar = df_k["jumlah"].sum()

    hutang = jual - bayar
    saldo = bayar - keluar

    st.metric("Nilai Masuk", masuk)
    st.metric("Sisa Stok", sisa)
    st.metric("Penjualan", jual)
    st.metric("Uang Masuk", bayar)
    st.metric("Pengeluaran", keluar)
    st.metric("Saldo", saldo)
    st.metric("Hutang", hutang)