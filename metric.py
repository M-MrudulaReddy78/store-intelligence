pos_df = pd.read_csv("data/pos_transactions.csv", parse_dates=["timestamp"])
pos_df = pos_df[pos_df["store_id"] == store_id]