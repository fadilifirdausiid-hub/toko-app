import streamlit as st
import psycopg2
import pandas as pd

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
    "Pembayaran",
    "Pengeluaran",
    "Closing"
])

# ================= DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Dashboard Toko")

    df = get_data("SELECT * FROM produk")

    if not df.empty:
        df["Masuk"] = df["stok_masuk"]
        df["Sisa"] = df["stok"]

        col1, col2 = st.columns(2)
        col1.metric("📥 Total Masuk", int(df["Masuk"].sum()))
        col2.metric("📦 Total Sisa", int(df["Sisa"].sum()))

        st.markdown("---")

        df_tampil = df[["nama", "Masuk", "Sisa"]]
        df_tampil.columns = ["Nama Produk", "Masuk", "Sisa"]

        st.dataframe(df_tampil, use_container_width=True)
    else:
        st.warning("Belum ada data")

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
                c.execute("""
                    UPDATE produk 
                    SET stok = stok + %s,
                        stok_masuk = stok_masuk + %s
                    WHERE id=%s
                """, (int(jumlah), int(jumlah), int(data[0])))
            else:
                c.execute("""
                    INSERT INTO produk (nama,harga,stok,stok_masuk)
                    VALUES (%s,%s,%s,%s)
                """, (nama, int(harga), int(jumlah), int(jumlah)))

            conn.commit()
            st.success("Barang masuk berhasil")

        except Exception as e:
            st.error(f"ERROR: {e}")

# ================= BARANG KELUAR =================
elif menu == "Barang Keluar":
    st.markdown("---")
    st.subheader("📋 Daftar Owner")

    df_trans = get_data("SELECT * FROM transaksi")
    df_bayar = get_data("SELECT * FROM pembayaran")

    if not df_trans.empty:
        owners = df_trans["owner"].unique()

        for o in owners:
            df_o = df_trans[df_trans["owner"] == o]
            total = df_o["total"].sum()

            df_b = df_bayar[df_bayar["owner"] == o] if not df_bayar.empty else pd.DataFrame()
            sudah = df_b["jumlah"].sum() if not df_b.empty else 0

            sisa = total - sudah

            status = "✅ Lunas" if sisa <= 0 else "❌ Belum Lunas"

            # tampilan horizontal
            col1, col2, col3, col4, col5 = st.columns(5)

            col1.markdown(f"**{o}**")
            col2.write(f"Total: {int(total)}")
            col3.write(f"Bayar: {int(sudah)}")
            col4.write(f"Sisa: {int(sisa)}")
            col5.write(status)

            # klik detail
            with st.expander(f"Detail {o}"):
                st.write("📦 Transaksi:")
                st.dataframe(df_o[["produk", "jumlah", "total"]])

                if not df_b.empty:
                    st.write("💳 Pembayaran:")
                    st.dataframe(df_b[["jumlah", "metode"]])
                else:
                    st.write("Belum ada pembayaran")
    st.title("📤 Barang Keluar")

    df = get_data("SELECT * FROM produk")

    if not df.empty:
        produk = st.selectbox("Produk", df["nama"])
        owner = st.text_input("Nama Owner")
        jumlah = st.number_input("Jumlah", 1)

        if st.button("Proses"):
            try:
                row = df[df["nama"] == produk].iloc[0]

                if jumlah > row["stok"]:
                    st.error("Stok tidak cukup")
                else:
                    total = int(jumlah) * int(row["harga"])

                    c.execute(
                        "UPDATE produk SET stok = stok - %s WHERE id=%s",
                        (int(jumlah), int(row["id"]))
                    )

                    c.execute("""
                        INSERT INTO transaksi (owner, produk, jumlah, total)
                        VALUES (%s,%s,%s,%s)
                    """, (owner, produk, int(jumlah), int(total)))

                    conn.commit()
                    st.success("Barang keluar berhasil")

            except Exception as e:
                st.error(f"ERROR: {e}")

# ================= PEMBAYARAN =================
elif menu == "Pembayaran":
    st.title("💳 Pembayaran")

    owner = st.text_input("Nama Owner")
    bayar = st.number_input("Jumlah Bayar", 0)
    metode = st.selectbox("Metode", ["cash", "bank"])

    if st.button("Bayar"):
        try:
            df = get_data(f"SELECT * FROM transaksi WHERE owner='{owner}'")
            total = df["total"].sum() if not df.empty else 0

            df_bayar = get_data(f"SELECT * FROM pembayaran WHERE owner='{owner}'")
            sudah = df_bayar["jumlah"].sum() if not df_bayar.empty else 0

            sisa = total - (sudah + bayar)

            c.execute("""
                INSERT INTO pembayaran (owner, jumlah, metode)
                VALUES (%s,%s,%s)
            """, (owner, int(bayar), metode))

            conn.commit()
            st.success(f"Sisa hutang: {int(sisa)}")

        except Exception as e:
            st.error(f"ERROR: {e}")

# ================= PENGELUARAN =================
elif menu == "Pengeluaran":
    st.title("💸 Pengeluaran")

    jumlah = st.number_input("Jumlah", 0)
    metode = st.selectbox("Metode", ["cash", "bank"])
    ket = st.text_input("Keterangan")

    if st.button("Simpan"):
        try:
            c.execute("""
                INSERT INTO pengeluaran (jumlah, metode, keterangan)
                VALUES (%s,%s,%s)
            """, (int(jumlah), metode, ket))

            conn.commit()
            st.success("Pengeluaran disimpan")

        except Exception as e:
            st.error(f"ERROR: {e}")

# ================= CLOSING =================
elif menu == "Closing":
    st.title("📊 Closing")

    df_produk = get_data("SELECT * FROM produk")
    df_trans = get_data("SELECT * FROM transaksi")
    df_bayar = get_data("SELECT * FROM pembayaran")
    df_keluar = get_data("SELECT * FROM pengeluaran")

    total_masuk_barang = (df_produk["stok_masuk"] * df_produk["harga"]).sum() if not df_produk.empty else 0
    nilai_sisa = (df_produk["stok"] * df_produk["harga"]).sum() if not df_produk.empty else 0
    total_penjualan = df_trans["total"].sum() if not df_trans.empty else 0
    total_bayar = df_bayar["jumlah"].sum() if not df_bayar.empty else 0
    pengeluaran = df_keluar["jumlah"].sum() if not df_keluar.empty else 0

    hutang = total_penjualan - total_bayar
    saldo = total_bayar - pengeluaran

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Nilai Barang Masuk", int(total_masuk_barang))
    col2.metric("📦 Nilai Sisa Stok", int(nilai_sisa))
    col3.metric("💰 Penjualan", int(total_penjualan))

    col4, col5, col6 = st.columns(3)
    col4.metric("💳 Uang Masuk", int(total_bayar))
    col5.metric("💸 Pengeluaran", int(pengeluaran))
    col6.metric("📊 Saldo", int(saldo))

    st.markdown("---")
    st.metric("❗ Total Hutang Owner", int(hutang))