import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.set_page_config(page_title="Toko App", layout="wide")

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= AUTO CREATE TABLE =================
c.execute("""
CREATE TABLE IF NOT EXISTS pembayaran (
    id SERIAL PRIMARY KEY,
    owner TEXT,
    jumlah INTEGER,
    metode TEXT,
    waktu TIMESTAMP DEFAULT NOW()
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS pengeluaran (
    id SERIAL PRIMARY KEY,
    jumlah INTEGER,
    metode TEXT,
    keterangan TEXT,
    waktu TIMESTAMP DEFAULT NOW()
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS setoran (
    id SERIAL PRIMARY KEY,
    jumlah INTEGER,
    waktu TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()

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

        # ===== SALDO =====
        cash_masuk = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
        bank_masuk = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

        cash_keluar = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
        bank_keluar = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

        saldo_cash = cash_masuk - cash_keluar
        saldo_bank = bank_masuk - bank_keluar

        col1, col2 = st.columns(2)
        col1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        col2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.markdown("---")

        col3, col4 = st.columns(2)
        col3.metric("💵 Saldo Cash", f"Rp {saldo_cash:,}")
        col4.metric("🏦 Saldo Bank", f"Rp {saldo_bank:,}")

        # ===== WARNING =====
        if saldo_cash < 0 or saldo_bank < 0:
            st.warning("⚠️ Saldo minus! Periksa pengeluaran / pembayaran")

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
                c.execute("UPDATE produk SET stok = stok + %s WHERE id=%s",
                          (int(jumlah), int(data[0])))
            else:
                c.execute("INSERT INTO produk (nama, harga, stok) VALUES (%s,%s,%s)",
                          (nama, int(harga), int(jumlah)))

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

                    c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s",
                              (int(jumlah), int(row["id"])))

                    c.execute("""
                        INSERT INTO transaksi (owner, produk, jumlah, total, waktu)
                        VALUES (%s,%s,%s,%s,NOW())
                    """, (owner, produk, int(jumlah), int(total)))

                    conn.commit()
                    st.success("Barang keluar berhasil")
            except:
                st.error("Error transaksi")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Data Owner")

    tgl = st.date_input("Tanggal", value=date.today())

    df_t = get_data(f"""
        SELECT owner, produk, jumlah, total, waktu
        FROM transaksi
        WHERE DATE(waktu) = '{tgl}'
    """)

    df_p = get_data("SELECT owner, jumlah FROM pembayaran")

    if not df_t.empty:
        owners = df_t.groupby("owner").first().reset_index()

        col1, col2, col3, col4, col5 = st.columns([1,3,2,2,2])
        col1.write("No")
        col2.write("Owner")
        col3.write("Status")
        col4.write("Sisa")
        col5.write("Edit")

        st.markdown("---")

        for i, row in owners.iterrows():
            owner = row["owner"]
            df_owner = df_t[df_t["owner"] == owner]
            total = int(df_owner["total"].sum())

            bayar = int(df_p[df_p["owner"] == owner]["jumlah"].sum()) if not df_p.empty else 0
            sisa = total - bayar

            status = "✅ Lunas" if sisa <= 0 else "❌ Belum Lunas"

            c1, c2, c3, c4, c5 = st.columns([1,3,2,2,2])
            c1.write(i+1)
            c2.write(owner)
            c3.write(status)
            c4.write(f"Rp {sisa:,}")

            if c5.button("Edit", key=f"edit{i}"):
                st.session_state[f"show_{i}"] = True

            if st.session_state.get(f"show_{i}", False):
                st.dataframe(df_owner)

                bayar_input = st.number_input("Bayar", key=f"bayar{i}")
                metode = st.selectbox("Metode", ["cash","bank"], key=f"metode{i}")

                if st.button("Simpan", key=f"simpan{i}"):
                    c.execute("""
                        INSERT INTO pembayaran (owner, jumlah, metode)
                        VALUES (%s,%s,%s)
                    """, (owner, int(bayar_input), metode))
                    conn.commit()
                    st.success("Pembayaran masuk")

                if st.button("Tutup", key=f"tutup{i}"):
                    st.session_state[f"show_{i}"] = False

            st.markdown("---")

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

    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")
    df_setor = get_data("SELECT jumlah FROM setoran")

    cash_masuk = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
    bank_masuk = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

    cash_keluar = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
    bank_keluar = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

    setor = int(df_setor["jumlah"].sum()) if not df_setor.empty else 0

    saldo_cash = cash_masuk - cash_keluar
    saldo_bank = bank_masuk - bank_keluar - setor

    st.metric("Cash", f"Rp {saldo_cash:,}")
    st.metric("Bank", f"Rp {saldo_bank:,}")

    st.markdown("---")

    st.subheader("Setoran ke Bos")
    jumlah_setor = st.number_input("Jumlah Setoran")

    if st.button("Setor"):
        c.execute("INSERT INTO setoran (jumlah) VALUES (%s)", (int(jumlah_setor),))
        conn.commit()
        st.success("Setoran berhasil")