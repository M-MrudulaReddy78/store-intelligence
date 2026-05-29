import csv
from datetime import datetime
from app.database import SessionLocal, POSTransaction, Base, engine

# Create tables if they don't exist (just in case)
Base.metadata.create_all(bind=engine)

csv_path = "data/Brigade_Bangalore_10_April_26 (1).csv"
db = SessionLocal()
count = 0
errors = 0

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trans_id = row.get('invoice_number')
            if not trans_id:
                continue
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

            # Check for duplicate transaction_id (some rows may have same invoice_number)
            existing = db.query(POSTransaction).filter(POSTransaction.transaction_id == trans_id).first()
            if existing:
                continue

            pos_record = POSTransaction(
                store_id=store_id,
                transaction_id=trans_id,
                timestamp=dt,
                basket_value_inr=basket_value
            )
            db.add(pos_record)
            count += 1
            if count % 100 == 0:
                db.commit()
                print(f"Inserted {count} rows so far...")
    db.commit()
    print(f" Loaded {count} POS transactions. Errors: {errors}")
except Exception as e:
    print(f" Error: {e}")
    db.rollback()
finally:
    db.close()