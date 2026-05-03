import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

# ================= CONFIG =================
st.set_page_config(page_title="Toko App", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.main {background-color:#f5f7fa;}
.card {
    border-radius:12px;
    padding:18px;
    background:white;
    box-shadow:0 2px 8px rgba(0,0,0,0.05);
    margin-bottom:12px;
}
</style>
""", unsafe_allow_html=True)

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= CACHE =================
@st.cache_data(ttl=10)
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
        masuk = (df["stok"] * df["harga"]).sum()
        sisa = (df["stok"] * df["harga"]).sum()

        col1, col2 = st.columns(2)
        col1.markdown(f"<div class='card'><h3>Barang Masuk</h3><h2>Rp {masuk:,.0f}</h2></div>", unsafe_allow_html=True)
        col2.markdown(f"<div class='card'><h3>Sisa Stok</h3><h2>Rp {sisa:,.0f}</h2></div>", unsafe_allow_html=True)

    st.markdown("### 📈 Grafik Penjualan")

    df_t = get_data("""
        SELECT total, waktu FROM transaksi 
        ORDER BY waktu DESC LIMIT 200
    """)

    if not df_t.empty:
        df_t["tanggal"] = pd.to_datetime(df_t["waktu"]).dt.date
        grafik = df_t.groupby("tanggal")["total"].sum().reset_index()

        fig = px.line(grafik, x="tanggal", y="total", markers=True)
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

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
                UPDATE produk 
                SET stok = stok + %s
                WHERE id=%s
            """, (jumlah, data[0]))
        else:
            c.execute("""
                INSERT INTO produk (nama,harga,stok)
                VALUES (%s,%s,%s)
            """, (nama, harga, jumlah))

        conn.commit()
        st.success("Barang masuk berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id, nama, harga, stok FROM produk")

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

                c.execute("UPDATE produk SET stok = stok - %s WHERE id=%s",
                          (jumlah, int(row["id"])))

                c.execute("""
                    INSERT INTO transaksi (owner, produk, jumlah, total, waktu)
                    VALUES (%s,%s,%s,%s,NOW())
                """, (owner, produk, jumlah, total))

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
            total = df_owner["total"].sum()

            df_b = df_p[df_p["owner"] == owner] if not df_p.empty else pd.DataFrame()
            sudah = df_b["jumlah"].sum() if not df_b.empty else 0

            sisa = total - sudah
            status = "✅ Lunas" if sisa <= 0 else "❌ Belum Lunas"

            st.markdown("<div class='card'>", unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([1,3,2,2])
            col1.write(i+1)
            col2.write(f"**{owner}**")
            col3.write(status)
            col4.write(f"Rp {sisa:,.0f}")

            with st.expander("Detail & Pembayaran"):
                st.dataframe(df_owner)

                st.write(f"Total: Rp {total:,.0f}")
                st.write(f"Sudah Bayar: Rp {sudah:,.0f}")
                st.write(f"Sisa: Rp {sisa:,.0f}")

                bayar = st.number_input("Bayar", key=f"bayar{i}")
                metode = st.selectbox("Metode", ["cash","bank"], key=f"metode{i}")

                if st.button("Simpan Pembayaran", key=f"simpan{i}"):
                    c.execute("""
                        INSERT INTO pembayaran (owner,jumlah,metode)
                        VALUES (%s,%s,%s)
                    """, (owner, bayar, metode))
                    conn.commit()
                    st.success("Pembayaran masuk")

            st.markdown("</div>", unsafe_allow_html=True)

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah")
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("""
            INSERT INTO pengeluaran (jumlah,metode,keterangan)
            VALUES (%s,%s,%s)
        """, (jumlah, metode, ket))
        conn.commit()
        st.success("Pengeluaran disimpan")

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_p = get_data("SELECT harga, stok FROM produk")
    df_t = get_data("SELECT total FROM transaksi")
    df_b = get_data("SELECT jumlah, metode FROM pembayaran")
    df_k = get_data("SELECT jumlah FROM pengeluaran")

    masuk = (df_p["stok"] * df_p["harga"]).sum() if not df_p.empty else 0
    sisa = (df_p["stok"] * df_p["harga"]).sum() if not df_p.empty else 0
    jual = df_t["total"].sum() if not df_t.empty else 0

    cash = df_b[df_b["metode"]=="cash"]["jumlah"].sum() if not df_b.empty else 0
    bank = df_b[df_b["metode"]=="bank"]["jumlah"].sum() if not df_b.empty else 0
    keluar = df_k["jumlah"].sum() if not df_k.empty else 0

    saldo = (cash + bank) - keluar
    hutang = jual - (cash + bank)

    col1, col2, col3 = st.columns(3)
    col1.metric("Barang Masuk", f"Rp {masuk:,.0f}")
    col2.metric("Sisa Stok", f"Rp {sisa:,.0f}")
    col3.metric("Penjualan", f"Rp {jual:,.0f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Cash", f"Rp {cash:,.0f}")
    col5.metric("Bank", f"Rp {bank:,.0f}")
    col6.metric("Pengeluaran", f"Rp {keluar:,.0f}")

    st.markdown("---")

    st.metric("Saldo", f"Rp {saldo:,.0f}")
    st.metric("Hutang Owner", f"Rp {hutang:,.0f}")