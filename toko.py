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
c.execute("""CREATE TABLE IF NOT EXISTS pembayaran (id SERIAL PRIMARY KEY, owner TEXT, jumlah INTEGER, metode TEXT);""")
c.execute("""CREATE TABLE IF NOT EXISTS pengeluaran (id SERIAL PRIMARY KEY, jumlah INTEGER, metode TEXT, keterangan TEXT);""")
c.execute("""CREATE TABLE IF NOT EXISTS setoran (id SERIAL PRIMARY KEY, jumlah INTEGER);""")
c.execute("""CREATE TABLE IF NOT EXISTS penarikan (id SERIAL PRIMARY KEY, jumlah INTEGER);""")
c.execute("""CREATE TABLE IF NOT EXISTS barang_masuk (id SERIAL PRIMARY KEY, produk TEXT, jumlah INTEGER);""")
conn.commit()

# ================= QUERY =================
@st.cache_data(ttl=5)
def get_data(q):
    try:
        return pd.read_sql(q, conn)
    except:
        return pd.DataFrame()

# ================= MENU =================
menu = st.sidebar.radio("Menu", [
    "Dashboard","Barang Masuk","Barang Keluar",
    "Owner Order","Pengeluaran","Closing"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    df_produk = get_data("SELECT nama, harga, stok FROM produk")
    df_masuk = get_data("SELECT produk, jumlah FROM barang_masuk")
    df_keluar = get_data("SELECT produk, jumlah FROM transaksi")
    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")
    df_setor = get_data("SELECT jumlah FROM setoran")
    df_tarik = get_data("SELECT jumlah FROM penarikan")

    if not df_produk.empty:

        masuk = df_masuk.groupby("produk")["jumlah"].sum().reset_index() if not df_masuk.empty else pd.DataFrame(columns=["produk","jumlah"])
        keluar = df_keluar.groupby("produk")["jumlah"].sum().reset_index() if not df_keluar.empty else pd.DataFrame(columns=["produk","jumlah"])

        df = df_produk.merge(masuk, left_on="nama", right_on="produk", how="left")
        df = df.merge(keluar, left_on="nama", right_on="produk", how="left", suffixes=("_masuk","_keluar"))

        df["jumlah_masuk"] = df["jumlah_masuk"].fillna(0)
        df["jumlah_keluar"] = df["jumlah_keluar"].fillna(0)

        df["Stok Masuk"] = df["jumlah_masuk"]
        df["Barang Keluar"] = df["jumlah_keluar"]
        df["Sisa Stok"] = df["stok"]

        total_masuk = int((df["Stok Masuk"] * df["harga"]).sum())
        total_keluar = int((df["Barang Keluar"] * df["harga"]).sum())
        total_sisa = int((df["Sisa Stok"] * df["harga"]).sum())

        # SALDO
        cash_in = df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum() if not df_bayar.empty else 0
        bank_in = df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum() if not df_bayar.empty else 0
        cash_out = df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum() if not df_pengeluaran.empty else 0
        bank_out = df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum() if not df_pengeluaran.empty else 0
        setor = df_setor["jumlah"].sum() if not df_setor.empty else 0
        tarik = df_tarik["jumlah"].sum() if not df_tarik.empty else 0

        deposit = 2000000
        saldo_cash = cash_in - cash_out + tarik
        saldo_bank = (bank_in - bank_out - setor - tarik) + deposit

        c1, c2, c3 = st.columns(3)
        c1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        c2.metric("📤 Barang Keluar", f"Rp {total_keluar:,}")
        c3.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.markdown("---")

        c4, c5 = st.columns(2)
        c4.metric("💵 Cash", f"Rp {int(saldo_cash):,}")
        c5.metric("🏦 Bank", f"Rp {int(saldo_bank):,}")

        st.dataframe(df[["nama","Stok Masuk","Barang Keluar","Sisa Stok"]])

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    df_produk = get_data("SELECT nama FROM produk")

    if not df_produk.empty:
        produk = st.selectbox("Produk", df_produk["nama"])
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Tambah"):
            c.execute("INSERT INTO barang_masuk (produk, jumlah) VALUES (%s,%s)", (produk, int(jumlah)))
            c.execute("UPDATE produk SET stok = stok + %s WHERE nama=%s", (int(jumlah), produk))
            conn.commit()
            st.rerun()

    st.markdown("---")
    df = get_data("SELECT * FROM barang_masuk ORDER BY id DESC")

    for i, row in df.iterrows():
        st.markdown('<div class="owner-box">', unsafe_allow_html=True)
        col = st.columns([3,2,2,2])

        col[0].write(row["produk"])
        col[1].write(row["jumlah"])

        if col[2].button("Edit", key=f"edit{i}"):
            st.session_state["edit"] = row["id"]

        if col[3].button("Hapus", key=f"del{i}"):
            c.execute("UPDATE produk SET stok = stok - %s WHERE nama=%s", (row["jumlah"], row["produk"]))
            c.execute("DELETE FROM barang_masuk WHERE id=%s", (row["id"],))
            conn.commit()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    if "edit" in st.session_state:
        data = df[df["id"] == st.session_state["edit"]].iloc[0]
        new = st.number_input("Edit jumlah", value=int(data["jumlah"]))

        if st.button("Update"):
            selisih = new - data["jumlah"]
            c.execute("UPDATE produk SET stok = stok + %s WHERE nama=%s", (selisih, data["produk"]))
            c.execute("UPDATE barang_masuk SET jumlah=%s WHERE id=%s", (new, data["id"]))
            conn.commit()
            del st.session_state["edit"]
            st.rerun()

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id, nama, harga, stok FROM produk")

    produk = st.selectbox("Produk", df["nama"])
    owner = st.text_input("Owner")
    jumlah = st.number_input("Jumlah", 1)

    if st.button("Proses"):
        row = df[df["nama"] == produk].iloc[0]

        if jumlah > row["stok"]:
            st.error("Stok kurang")
        else:
            total = jumlah * row["harga"]

            c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s", (int(jumlah), int(row["id"])))
            c.execute("INSERT INTO transaksi (owner, produk, jumlah, total) VALUES (%s,%s,%s,%s)",
                      (owner, produk, int(jumlah), int(total)))
            conn.commit()
            st.success("OK")

# ================= OWNER =================
elif menu == "Owner Order":
    st.title("📋 Owner Order")

    df_t = get_data("SELECT owner, total FROM transaksi")
    df_p = get_data("SELECT owner, jumlah, metode FROM pembayaran")

    owners = df_t.groupby("owner")["total"].sum().reset_index()

    for i, row in owners.iterrows():
        owner = row["owner"]
        total = row["total"]
        bayar = df_p[df_p["owner"] == owner]["jumlah"].sum() if not df_p.empty else 0
        sisa = total - bayar

        st.markdown('<div class="owner-box">', unsafe_allow_html=True)
        col = st.columns([3,2,2,2,2])

        col[0].write(f"👤 {owner}")
        col[1].write("Lunas" if sisa <= 0 else "Belum")
        col[2].write(f"Rp {int(sisa):,}")

        if col[3].button("Bayar", key=i):
            st.session_state["owner"] = owner

        if col[4].button("Cash→TF", key=f"tf{i}"):
            c.execute("UPDATE pembayaran SET metode='bank' WHERE owner=%s AND metode='cash'", (owner,))
            conn.commit()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    if "owner" in st.session_state:
        jml = st.number_input("Jumlah")
        metode = st.selectbox("Metode", ["cash","bank"])

        if st.button("Simpan"):
            c.execute("INSERT INTO pembayaran (owner, jumlah, metode) VALUES (%s,%s,%s)",
                      (st.session_state["owner"], int(jml), metode))
            conn.commit()
            del st.session_state["owner"]
            st.rerun()

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jml = st.number_input("Jumlah")
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("INSERT INTO pengeluaran VALUES (DEFAULT,%s,%s,%s)", (int(jml), metode, ket))
        conn.commit()

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_bayar = get_data("SELECT jumlah, metode FROM pembayaran")
    df_pengeluaran = get_data("SELECT jumlah, metode FROM pengeluaran")
    df_setor = get_data("SELECT jumlah FROM setoran")
    df_tarik = get_data("SELECT jumlah FROM penarikan")

    deposit = 2000000

    cash = df_bayar[df_bayar["metode"]=="cash"]["jumlah"].sum()
    bank = df_bayar[df_bayar["metode"]=="bank"]["jumlah"].sum()

    cash_out = df_pengeluaran[df_pengeluaran["metode"]=="cash"]["jumlah"].sum()
    bank_out = df_pengeluaran[df_pengeluaran["metode"]=="bank"]["jumlah"].sum()

    setor = df_setor["jumlah"].sum()
    tarik = df_tarik["jumlah"].sum()

    saldo_cash = cash - cash_out + tarik
    saldo_bank = (bank - bank_out - setor - tarik) + deposit

    st.metric("Cash", f"Rp {int(saldo_cash):,}")
    st.metric("Bank", f"Rp {int(saldo_bank):,}")

    st.markdown("---")

    if st.button("Setor"):
        c.execute("INSERT INTO setoran VALUES (DEFAULT,%s)", (100000,))
        conn.commit()

    if st.button("Tarik"):
        c.execute("INSERT INTO penarikan VALUES (DEFAULT,%s)", (100000,))
        conn.commit()