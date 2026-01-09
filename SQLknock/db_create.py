import random
import sqlite3
from datetime import datetime, timedelta

# 1. データベース接続（なければ作る）
db_path = "practice.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 2. テーブル作成（商品マスタ と 売上履歴）
cur.execute("DROP TABLE IF EXISTS products")
cur.execute("DROP TABLE IF EXISTS sales")

cur.execute("""
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        price INTEGER
    )
""")

cur.execute("""
    CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TEXT,
        product_id INTEGER,
        quantity INTEGER
    )
""")

# 3. 商品データの投入
products_data = [
    (1, "高性能センサーA", "センサー", 5000),
    (2, "普及型センサーB", "センサー", 2000),
    (3, "小型スイッチ", "スイッチ", 500),
    (4, "防水スイッチ", "スイッチ", 1200),
    (5, "M4ボルト(100本)", "ネジ", 800),
    (6, "M6ナット(100個)", "ネジ", 400),
    (7, "制御ケーブル3m", "ケーブル", 3000),
    (8, "特注ケーブル10m", "ケーブル", 15000),
]
cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products_data)

# 4. 売上データの投入（ランダムに50件くらい）
sales_data = []
start_date = datetime(2023, 1, 1)
for i in range(50):
    date = start_date + timedelta(days=random.randint(0, 30))
    p_id = random.randint(1, 8)
    qty = random.randint(1, 10)
    sales_data.append((date.strftime("%Y-%m-%d"), p_id, qty))

cur.executemany(
    "INSERT INTO sales (sale_date, product_id, quantity) VALUES (?,?,?)", sales_data
)

conn.commit()
conn.close()
print(f"作成完了！ {db_path} をDBeaverで開いてください。")
