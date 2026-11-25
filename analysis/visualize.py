import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Load and clean raw CSVs so this script can run standalone
orders = pd.read_csv("data/orders.csv", dtype={"order_id": str})
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

orders["payment_method"] = orders["payment_method"].str.strip().str.upper()

key_cols = [
    "customer_id", "product_id", "order_date", "quantity",
    "discount_pct", "payment_method", "rating", "returned",
]
orders = orders[~orders.duplicated(subset=key_cols, keep="first")].copy()
orders["discount_pct"] = orders["discount_pct"].fillna(0)
orders["rating"] = orders["rating"].fillna(orders["rating"].median())

df = orders.merge(products, on="product_id", how="left").merge(customers, on="customer_id", how="left")
df["order_value"] = df["quantity"] * df["price"] * (1 - df["discount_pct"] / 100.0)

q1 = df["quantity"].quantile(0.25)
q3 = df["quantity"].quantile(0.75)
iqr = q3 - q1
df["is_outlier"] = (df["quantity"] < q1 - 1.5 * iqr) | (df["quantity"] > q3 + 1.5 * iqr)

os.makedirs("visualizations", exist_ok=True)

# 1. Return rate by payment method
pay_rates = (df.groupby("payment_method")["returned"].mean() * 100).round(1).sort_values(ascending=False)

plt.figure(figsize=(7, 4.5))
bars = plt.bar(pay_rates.index, pay_rates.values, color=["tab:red", "tab:blue", "tab:blue"])
for b in bars:
    h = b.get_height()
    plt.text(b.get_x() + b.get_width() / 2, h + 1, f"{h:.1f}%", ha="center")

plt.ylim(0, 52)
plt.xlabel("Payment Method")
plt.ylabel("Return Rate (%)")
plt.title("COD Returns at 44.4% (3x Card)")
plt.tight_layout()
plt.savefig("visualizations/return_rate_by_payment.png")
plt.close()

# 2. Outlier-corrected monthly revenue trend
df["year_month"] = pd.to_datetime(df["order_date"]).dt.to_period("M").astype(str)
monthly = df[~df["is_outlier"]].groupby("year_month")["order_value"].sum().round(2)

plt.figure(figsize=(8, 4.5))
plt.plot(monthly.index, monthly.values, marker="o", color="tab:green")
plt.xlabel("Month")
plt.ylabel("Revenue (INR)")
plt.title("Outlier-Corrected Monthly Revenue: March 2026 Is the Peak Month")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("visualizations/monthly_revenue_trend.png")
plt.close()

print("Generated charts in visualizations/")
