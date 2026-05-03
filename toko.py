import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Toko App", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= AUTO TABLE =================
c.execute("""
CREATE TABLE IF NOT EXISTS pembayaran (
    id SERIAL PRIMARY KEY,
    owner TEXT,
    jumlah INTEGER,
    metode TEXT
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS pengeluaran (
    id SERIAL PRIMARY KEY,
    jumlah INTEGER,
    metode TEXT,
    keterangan TEXT
);
""")

conn.commit()

# ================= SAFE QUERY =================
@st.cache_data(ttl=10)
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
    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")

    if not df_produk.empty:
        df_produk["stok"] = df_produk["stok"].astype(int)
        df_produk["harga"] = df_produk["harga"].astype(int)

        if not df_keluar.empty:
            keluar = df_keluar.groupby("produk")["jumlah"].sum().reset_index()
        else:
            keluar = pd.DataFrame(columns=["produk","jumlah"])

        df = df_produk.merge(keluar, left_on="nama", right_on="produk", how="left")
        df["jumlah"] = df["jumlah"].fillna(0)

        df["Stok Masuk"] = df["stok"] + df["jumlah"]
        df["Sisa Stok"] = df["stok"]

        total_masuk = int((df["Stok Masuk"] * df["harga"]).sum())
        total_sisa = int((df["Sisa Stok"] * df["harga"]).sum())

        # SALDO
        cash_in = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
        bank_in = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

        cash_out = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
        bank_out = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

        saldo_cash = cash_in - cash_out
        saldo_bank = bank_in - bank_out

        c1, c2 = st.columns(2)
        c1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        c2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.markdown("---")

        c3, c4 = st.columns(2)
        c3.metric("💵 Cash", f"Rp {saldo_cash:,}")
        c4.metric("🏦 Bank", f"Rp {saldo_bank:,}")

        if saldo_cash < 0 or saldo_bank < 0:
            st.warning("⚠️ Saldo minus")

        st.dataframe(df[["nama","Stok Masuk","Sisa Stok"]], use_container_width=True)

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
                      (int(jumlah), int(data[0])))
        else:
            c.execute("INSERT INTO produk (nama, harga, stok) VALUES (%s,%s,%s)",
                      (nama, int(harga), int(jumlah)))

        conn.commit()
        st.success("Berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id, nama, harga, stok FROM produk")

    if not df.empty:
        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
            row = df[df["nama"] == produk].iloc[0]

            if int(jumlah) > int(row["stok"]):
                st.error("Stok kurang")
            else:
                total = int(jumlah) * int(row["harga"])

                c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s",
                          (int(jumlah), int(row["id"])))

                c.execute("""
                    INSERT INTO transaksi (owner, produk, jumlah, total)
                    VALUES (%s,%s,%s,%s)
                """, (owner, produk, int(jumlah), int(total)))

                conn.commit()
                st.success("Berhasil")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Owner Order")

    df_t = get_data("SELECT owner, total FROM transaksi")
    df_p = get_data("SELECT owner, jumlah FROM pembayaran")

    if not df_t.empty:
        owners = df_t.groupby("owner")["total"].sum().reset_index()

        for i, row in owners.iterrows():
            owner = row["owner"]
            total = int(row["total"])

            bayar = int(df_p[df_p["owner"] == owner]["jumlah"].sum()) if not df_p.empty else 0
            sisa = total - bayar

            cols = st.columns([3,2,2,2])
            cols[0].write(owner)
            cols[1].write("Lunas" if sisa <= 0 else "Belum")
            cols[2].write(f"Rp {sisa:,}")

            if cols[3].button("Bayar", key=i):
                st.session_state["owner"] = owner

        if "owner" in st.session_state:
            st.markdown("---")
            st.write("Bayar:", st.session_state["owner"])

            jml = st.number_input("Jumlah Bayar")
            metode = st.selectbox("Metode", ["cash","bank"])

            if st.button("Simpan"):
                c.execute("""
                    INSERT INTO pembayaran (owner, jumlah, metode)
                    VALUES (%s,%s,%s)
                """, (st.session_state["owner"], int(jml), metode))

                conn.commit()
                del st.session_state["owner"]
                st.rerun()

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
        st.success("OK")

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_trans = get_data("SELECT total FROM transaksi")
    df_bayar = get_data("SELECT jumlah FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah FROM pengeluaran")

    total_penjualan = int(df_trans["total"].sum()) if not df_trans.empty else 0
    uang_masuk = int(df_bayar["jumlah"].sum()) if not df_bayar.empty else 0
    pengeluaran = int(df_pengeluaran["jumlah"].sum()) if not df_pengeluaran.empty else 0

    saldo = uang_masuk - pengeluaran

    st.metric("Penjualan", f"Rp {total_penjualan:,}")
    st.metric("Uang Masuk", f"Rp {uang_masuk:,}")
    st.metric("Pengeluaran", f"Rp {pengeluaran:,}")
    st.metric("Saldo", f"Rp {saldo:,}")