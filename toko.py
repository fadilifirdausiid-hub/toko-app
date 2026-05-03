import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Toko App", layout="wide")

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

c.execute("""
CREATE TABLE IF NOT EXISTS setoran (
    id SERIAL PRIMARY KEY,
    jumlah INTEGER
);
""")

conn.commit()

@st.cache_data(ttl=10)
def get_data(q):
    try:
        return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

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
    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")
    df_setor = get_data("SELECT jumlah FROM setoran")

    if not df_produk.empty:
        df_produk["TOTAL"] = df_produk["stok"] * df_produk["harga"]

        total_sisa = int(df_produk["TOTAL"].sum())

        cash_in = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
        bank_in = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

        cash_out = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
        bank_out = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

        setor = int(df_setor["jumlah"].sum()) if not df_setor.empty else 0

        deposit = 2000000

        saldo_cash = cash_in - cash_out
        saldo_bank = (bank_in - bank_out - setor) + deposit

        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")
        c2.metric("💵 Cash", f"Rp {saldo_cash:,}")
        c3.metric("🏦 Bank", f"Rp {saldo_bank:,}")

        if saldo_cash < 0 or saldo_bank < 0:
            st.warning("⚠️ Saldo minus")

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
        st.success("OK")

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
                st.success("OK")

# ================= OWNER =================
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

            col = st.columns([3,2,2,2])
            col[0].write(owner)
            col[1].write("Lunas" if sisa <= 0 else "Belum")
            col[2].write(f"Rp {sisa:,}")

            if col[3].button("Bayar", key=i):
                st.session_state["owner"] = owner

        if "owner" in st.session_state:
            st.markdown("---")
            st.write("Bayar:", st.session_state["owner"])

            jml = st.number_input("Jumlah")
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

    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")
    df_setor = get_data("SELECT jumlah FROM setoran")

    deposit = 2000000

    cash = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
    bank = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

    cash_out = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
    bank_out = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

    setor = int(df_setor["jumlah"].sum()) if not df_setor.empty else 0

    saldo_cash = cash - cash_out
    saldo_bank = (bank - bank_out - setor) + deposit

    st.metric("Cash", f"Rp {saldo_cash:,}")
    st.metric("Bank (deposit 2jt aman)", f"Rp {saldo_bank:,}")

    st.markdown("---")

    st.subheader("Setoran ke Bos")
    jml = st.number_input("Jumlah Setor")

    if st.button("Setor"):
        if jml > (saldo_bank - deposit):
            st.error("Saldo bank tidak cukup (deposit tidak boleh dipakai)")
        else:
            c.execute("INSERT INTO setoran (jumlah) VALUES (%s)", (int(jml),))
            conn.commit()
            st.success("Setor berhasil")
            st.rerun()