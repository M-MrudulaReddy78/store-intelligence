"""
POS transactions loader – reads CSV and populates the database.
"""
import csv
import os
from datetime import datetime
from .database import SessionLocal, POSTransaction

def load_pos_transactions(csv_path: str):
    """Load POS transactions from CSV file into the database."""
    if not os.path.exists(csv_path):
        print(f"POS CSV not found: {csv_path}")
        return
    
    db = SessionLocal()
    count = 0
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map CSV columns to our model
                # The CSV has columns: store_id, transaction_id, timestamp, basket_value_inr
                store_id = row.get('store_id') or row.get('Store ID') or row.get('store_code')
                trans_id = row.get('transaction_id') or row.get('Transaction ID')
                timestamp_str = row.get('timestamp') or row.get('Timestamp') or row.get('order_date')
                basket_value = row.get('basket_value_inr') or row.get('Basket Value') or row.get('total_amount')
                
                if not all([store_id, trans_id, timestamp_str, basket_value]):
                    continue
                
                # Parse timestamp (handles various formats)
                try:
                    # Try ISO format
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        # Try CSV format from sample: "10-04-2026" but also has time? Actually the CSV has order_date and order_time separately
                        # The provided CSV has order_date and order_time columns; we need to handle that.
                        # For now, try to parse date only or full datetime
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    # If fails, skip this row
                    continue
                
                existing = db.query(POSTransaction).filter(POSTransaction.transaction_id == trans_id).first()
                if existing:
                    continue
                
                pos_record = POSTransaction(
                    store_id=store_id,
                    transaction_id=trans_id,
                    timestamp=timestamp,
                    basket_value_inr=float(basket_value)
                )
                db.add(pos_record)
                count += 1
            db.commit()
            print(f"Loaded {count} POS transactions from {csv_path}")
    except Exception as e:
        print(f"Error loading POS data: {e}")
        db.rollback()
    finally:
        db.close()