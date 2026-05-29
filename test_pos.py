import csv
from datetime import datetime

with open('data/Brigade_Bangalore_10_April_26 (1).csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        count += 1
        if count <= 5:
            print(row['invoice_number'], row['order_date'], row['order_time'], row['total_amount'])
    print(f"Total rows: {count}")