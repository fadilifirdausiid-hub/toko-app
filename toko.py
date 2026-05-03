import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Toko App", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
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
        df["Masuk"] = df["stok"]
        df["Sisa"] = df["stok"]

        col1, col2 = st.columns(2)

        col1.markdown(f"""
        <div class='card'>
        <h3>📥 Stok Masuk</h3>
        <h2>Rp {int((df['Masuk']*df['harga']).sum()):,}</h2>
        </div>
        """, unsafe_allow_html=True)

        col2.markdown(f"""
        <div class='card'>
        <h3>📦 Sisa Stok</h3>
        <h2>Rp {int((df['Sisa']*df['harga']).sum()):,}</h2>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(df[["nama","Masuk","Sisa"]], use_container_width=True)

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
                      (jumlah, data[0]))
        else:
            c.execute("INSERT INTO produk (nama,harga,stok) VALUES (%s,%s,%s)",
                      (nama, harga, jumlah))

        conn.commit()
        st.success("Berhasil")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.title("📤 Barang Keluar")

    df = get_data("SELECT id,nama,harga,stok FROM produk")

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
                INSERT INTO transaksi (owner,produk,jumlah,total,waktu)
                VALUES (%s,%s,%s,%s,NOW())
            """, (owner, produk, jumlah, total))

            conn.commit()
            st.success("Berhasil")

# ================= OWNER ORDER =================
elif menu == "Owner Order":
    st.title("📋 Data Owner")

    tgl = st.date_input("Tanggal", value=date.today())

    df_t = get_data(f"""
        SELECT owner, produk, jumlah, total, waktu
        FROM transaksi
        WHERE DATE(waktu) = '{tgl}'
    """)

    df_p = get_data("SELECT owner,jumlah,metode FROM pembayaran")

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
            col2.write(owner)
            col3.write(status)
            col4.write(f"Rp {sisa:,}")

            with st.expander("Detail"):
                st.dataframe(df_owner)

                bayar = st.number_input("Bayar", key=f"b{i}")
                metode = st.selectbox("Metode", ["cash","bank"], key=f"m{i}")

                if st.button("Simpan", key=f"s{i}"):
                    c.execute("""
                        INSERT INTO pembayaran (owner,jumlah,metode)
                        VALUES (%s,%s,%s)
                    """, (owner, bayar, metode))
                    conn.commit()
                    st.success("OK")

            st.markdown("</div>", unsafe_allow_html=True)

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah")
    metode = st.selectbox("Metode", ["cash","bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        c.execute("INSERT INTO pengeluaran (jumlah,metode,keterangan) VALUES (%s,%s,%s)",
                  (jumlah, metode, ket))
        conn.commit()
        st.success("OK")

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
            WHERE DATE_TRUNC('month', waktu) = DATE_TRUNC('month', DATE '{bulan}')
        """)

    if not df_t.empty:
        df_t["tanggal"] = pd.to_datetime(df_t["waktu"]).dt.date
        grafik = df_t.groupby("tanggal")["total"].sum().reset_index()

        st.markdown("### 📈 Grafik Penjualan")
        fig = px.line(grafik, x="tanggal", y="total", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    df_b = get_data("SELECT jumlah,metode FROM pembayaran")
    df_k = get_data("SELECT jumlah FROM pengeluaran")

    cash = df_b[df_b["metode"]=="cash"]["jumlah"].sum() if not df_b.empty else 0
    bank = df_b[df_b["metode"]=="bank"]["jumlah"].sum() if not df_b.empty else 0
    keluar = df_k["jumlah"].sum() if not df_k.empty else 0

    saldo = (cash + bank) - keluar

    st.metric("Saldo", f"Rp {saldo:,}")