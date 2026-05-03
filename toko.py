import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Toko App", layout="wide")

# ================= STYLE =================
st.markdown("""
<style>
.box {
    border: 1px solid #ddd;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 10px;
    background-color: #f9fafb;
}
</style>
""", unsafe_allow_html=True)

# ================= KONEKSI =================
conn = psycopg2.connect(st.secrets["DB_URL"])
c = conn.cursor()

# ================= TABLE =================
c.execute("""
CREATE TABLE IF NOT EXISTS barang_masuk (
    id SERIAL PRIMARY KEY,
    produk TEXT,
    jumlah INTEGER
);
""")

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
    "Dashboard",
    "Barang Masuk"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    df_produk = get_data("SELECT nama, harga, stok FROM produk")
    df_masuk = get_data("SELECT produk, jumlah FROM barang_masuk")

    if not df_produk.empty:

        # ===== HITUNG STOK MASUK =====
        if not df_masuk.empty:
            masuk = df_masuk.groupby("produk")["jumlah"].sum().reset_index()
        else:
            masuk = pd.DataFrame(columns=["produk","jumlah"])

        df = df_produk.merge(masuk, left_on="nama", right_on="produk", how="left")
        df["jumlah"] = df["jumlah"].fillna(0)

        df["Stok Masuk"] = df["jumlah"]
        df["Sisa Stok"] = df["stok"]

        total_masuk = int((df["Stok Masuk"] * df["harga"]).sum())
        total_sisa = int((df["Sisa Stok"] * df["harga"]).sum())

        col1, col2 = st.columns(2)
        col1.metric("📥 Stok Masuk", f"Rp {total_masuk:,}")
        col2.metric("📦 Sisa Stok", f"Rp {total_sisa:,}")

        st.markdown("---")

        st.dataframe(df[["nama","Stok Masuk","Sisa Stok"]], use_container_width=True)

# ================= BARANG MASUK =================
elif menu == "Barang Masuk":
    st.title("📥 Barang Masuk")

    df_produk = get_data("SELECT nama FROM produk")

    if not df_produk.empty:
        produk = st.selectbox("Produk", df_produk["nama"])
        jumlah = st.number_input("Jumlah", min_value=1, value=1)

        # ===== TAMBAH =====
        if st.button("Tambah"):
            c.execute("""
                INSERT INTO barang_masuk (produk, jumlah)
                VALUES (%s,%s)
            """, (produk, int(jumlah)))

            c.execute("""
                UPDATE produk SET stok = stok + %s
                WHERE nama=%s
            """, (int(jumlah), produk))

            conn.commit()
            st.success("Berhasil tambah stok")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Riwayat Barang Masuk")

    df = get_data("SELECT * FROM barang_masuk ORDER BY id DESC")

    # ================= LIST =================
    for i, row in df.iterrows():
        st.markdown('<div class="box">', unsafe_allow_html=True)

        col = st.columns([3,2,2,2])

        col[0].write(f"📦 {row['produk']}")
        col[1].write(f"{int(row['jumlah'])}")

        # ===== EDIT =====
        if col[2].button("Edit", key=f"edit{i}"):
            st.session_state["edit_id"] = int(row["id"])

        # ===== HAPUS =====
        if col[3].button("Hapus", key=f"hapus{i}"):
            c.execute("""
                UPDATE produk SET stok = stok - %s
                WHERE nama=%s
            """, (int(row["jumlah"]), row["produk"]))

            c.execute("DELETE FROM barang_masuk WHERE id=%s", (int(row["id"]),))
            conn.commit()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ================= EDIT MODE =================
    if "edit_id" in st.session_state:
        data = df[df["id"] == st.session_state["edit_id"]].iloc[0]

        st.markdown("---")
        st.subheader("✏️ Edit Barang Masuk")

        new_jumlah = st.number_input(
            "Jumlah Baru",
            value=int(data["jumlah"])
        )

        if st.button("Update"):
            selisih = int(new_jumlah) - int(data["jumlah"])

            # update stok sesuai selisih
            c.execute("""
                UPDATE produk SET stok = stok + %s
                WHERE nama=%s
            """, (selisih, data["produk"]))

            # update log
            c.execute("""
                UPDATE barang_masuk
                SET jumlah=%s
                WHERE id=%s
            """, (int(new_jumlah), int(data["id"]))

            )

            conn.commit()

            del st.session_state["edit_id"]
            st.success("Berhasil update")
            st.rerun()