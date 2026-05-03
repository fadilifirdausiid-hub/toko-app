import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Toko App", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.owner-box {
    border: 1px solid #ddd;
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 12px;
    background-color: #f8fafc;
}
</style>
""", unsafe_allow_html=True)

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= TABLE =================
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

c.execute("""
CREATE TABLE IF NOT EXISTS penarikan (
    id SERIAL PRIMARY KEY,
    jumlah INTEGER
);
""")

conn.commit()

# ================= QUERY =================
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
    df_setor = get_data("SELECT jumlah FROM setoran")
    df_tarik = get_data("SELECT jumlah FROM penarikan")

    if not df_produk.empty:
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

        cash_in = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
        bank_in = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

        cash_out = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
        bank_out = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

        setor = int(df_setor["jumlah"].sum()) if not df_setor.empty else 0
        tarik = int(df_tarik["jumlah"].sum()) if not df_tarik.empty else 0

        deposit = 2000000

        saldo_cash = cash_in - cash_out + tarik
        saldo_bank = (bank_in - bank_out - setor - tarik) + deposit

        c1, c2 = st.columns(2)
        c1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        c2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.markdown("---")

        c3, c4 = st.columns(2)
        c3.metric("💵 Cash", f"Rp {saldo_cash:,}")
        c4.metric("🏦 Bank", f"Rp {saldo_bank:,}")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Owner Order")

    df_t = get_data("SELECT owner, total FROM transaksi")
    df_p = get_data("SELECT owner, jumlah, metode FROM pembayaran")

    if not df_t.empty:
        owners = df_t.groupby("owner")["total"].sum().reset_index()

        for i, row in owners.iterrows():
            owner = row["owner"]
            total = int(row["total"])

            bayar = int(df_p[df_p["owner"] == owner]["jumlah"].sum()) if not df_p.empty else 0
            sisa = total - bayar

            st.markdown('<div class="owner-box">', unsafe_allow_html=True)

            col = st.columns([3,2,2,2,2])

            col[0].write(f"👤 {owner}")
            col[1].write("✅ Lunas" if sisa <= 0 else "❌ Belum")
            col[2].write(f"Rp {sisa:,}")

            if col[3].button("Bayar", key=f"bayar{i}"):
                st.session_state["owner"] = owner

            if col[4].button("Ubah ke TF", key=f"tf{i}"):
                c.execute("""
                    UPDATE pembayaran 
                    SET metode='bank'
                    WHERE owner=%s AND metode='cash'
                """, (owner,))
                conn.commit()
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        if "owner" in st.session_state:
            st.markdown("---")
            st.subheader(f"Bayar: {st.session_state['owner']}")

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
    df_tarik = get_data("SELECT jumlah FROM penarikan")

    deposit = 2000000

    cash = int(df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()) if not df_bayar.empty else 0
    bank = int(df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()) if not df_bayar.empty else 0

    cash_out = int(df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()) if not df_pengeluaran.empty else 0
    bank_out = int(df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()) if not df_pengeluaran.empty else 0

    setor = int(df_setor["jumlah"].sum()) if not df_setor.empty else 0
    tarik = int(df_tarik["jumlah"].sum()) if not df_tarik.empty else 0

    saldo_cash = cash - cash_out + tarik
    saldo_bank = (bank - bank_out - setor - tarik) + deposit

    st.metric("Cash", f"Rp {saldo_cash:,}")
    st.metric("Bank (deposit aman 2jt)", f"Rp {saldo_bank:,}")

    st.markdown("---")

    # ===== SETOR =====
    st.subheader("🏦 Setoran ke Bos")
    setor_jml = st.number_input("Jumlah Setor")

    if st.button("Setor"):
        if setor_jml > (saldo_bank - deposit):
            st.error("Saldo bank tidak cukup")
        else:
            c.execute("INSERT INTO setoran (jumlah) VALUES (%s)", (int(setor_jml),))
            conn.commit()
            st.success("Berhasil setor")
            st.rerun()

    st.markdown("---")

    # ===== TARIK CASH =====
    st.subheader("💸 Tarik Cash dari Bank")
    tarik_jml = st.number_input("Jumlah Tarik")

    if st.button("Tarik"):
        if tarik_jml > (saldo_bank - deposit):
            st.error("Saldo bank tidak cukup")
        else:
            c.execute("INSERT INTO penarikan (jumlah) VALUES (%s)", (int(tarik_jml),))
            conn.commit()
            st.success("Berhasil tarik")
            st.rerun()