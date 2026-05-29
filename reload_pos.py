# reload_pos.py
import csv
import sqlite3
from datetime import datetime

csv_path = "data/Brigade_Bangalore_10_April_26 (1).csv"
db_path = "store_intelligence.db"

# Connect to the database (will create a new one)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS pos_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id TEXT,
        transaction_id TEXT UNIQUE,
        timestamp DATETIME,
        basket_value_inr REAL
    )
""")

count = 0
errors = 0
seen = set()

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        trans_id = row.get('invoice_number')
        if not trans_id or trans_id in seen:
            continue
        seen.add(trans_id)

        store_id = row.get('store_id', 'ST1008')
        date_str = row.get('order_date')
        time_str = row.get('order_time')
        if not date_str or not time_str:
            errors += 1
            continue
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")
        except:
            errors += 1
            continue

        basket_str = row.get('total_amount')
        if not basket_str:
            errors += 1
            continue
        try:
            basket_value = float(basket_str)
        except:
            errors += 1
            continue

        # Insert with ON CONFLICT IGNORE (SQLite syntax)
        cursor.execute("""
            INSERT OR IGNORE INTO pos_transactions
            (store_id, transaction_id, timestamp, basket_value_inr)
            VALUES (?, ?, ?, ?)
        """, (store_id, trans_id, dt, basket_value))
        count += 1

conn.commit()
print(f"✅ Inserted {count} unique transactions (skipped {errors} problematic rows).")
cursor.close()
conn.close()