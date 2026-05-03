import psycopg2

conn = psycopg2.connect(
    "postgresql://postgres.slikespgjmlzpgqjimno:Fadili161299@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
)

cur = conn.cursor()
cur.execute("SELECT NOW();")

print(cur.fetchone())