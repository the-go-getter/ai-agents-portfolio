import sqlite3, random, datetime

con = sqlite3.connect("datascribe_demo.db")
c = con.cursor()

c.execute("drop table if exists sales")
c.execute("""
CREATE TABLE sales(
    id INTEGER PRIMARY KEY,
    day TEXT,
    sku TEXT,
    qty INTEGER,
    price REAL
)
""")

start = datetime.date(2025, 1, 1)

for i in range(400):
    d = start + datetime.timedelta(days=i % 180)
    sku = f"SKU{1 + (i % 8)}"
    qty = random.randint(1, 10)
    price = random.choice([9.99, 14.5, 19.0, 29.0])
    c.execute(
        "INSERT INTO sales(day, sku, qty, price) VALUES (?, ?, ?, ?)",
        (str(d), sku, qty, price)
    )

con.commit()
con.close()
print("Seeded datascribe_demo.db with 400 rows.")
