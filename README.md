# Mamaearth Returns & Margin Analysis Capstone

This repo connects an SQLite database, a Python/Pandas cleaning and EDA pipeline, and an SCR narrative generator for Mamaearth order data.

## Repo Structure

- `data/` - raw CSVs (`customers.csv`, `products.csv`, `orders.csv`)
- `sql/` - `schema.sql`, `seed_data.sql`, and `reports.sql`
- `analysis/` - `clean_and_eda.py` and `visualize.py`
- `visualizations/` - output charts (`return_rate_by_payment.png`, `monthly_revenue_trend.png`)
- `narrator/` - `findings.json`, `generate_narrative.py`, and `sample_output.txt`

## Data Flow

1. `sql/schema.sql` and `sql/seed_data.sql` load the raw CSVs into SQLite. `sql/reports.sql` runs the raw SQL reports (total raw revenue = 99,860.20).
2. `analysis/clean_and_eda.py` reads the raw CSVs directly, cleans payment method casing, drops 5 duplicate orders (2,501.90 delta -> 97,358.30 cleaned revenue), imputes missing values, checks outliers/correlations/segments, and writes `narrator/findings.json`. `analysis/visualize.py` saves the two PNG charts in `visualizations/`.
3. `narrator/generate_narrative.py` reads `narrator/findings.json` and generates the Situation-Complication-Resolution summary using the Gemini API (or the offline fallback if no key is set), then checks all 5 key figures.

## How to Run (in order)

1. Load SQL schema, seed data, and run reports:
```bash
sqlite3 mamaearth.db < sql/schema.sql
sqlite3 mamaearth.db < sql/seed_data.sql
sqlite3 mamaearth.db < sql/reports.sql
```

2. Run Python cleaning/EDA (this writes `narrator/findings.json`) and then visualizations:
```bash
python analysis/clean_and_eda.py
python analysis/visualize.py
```

3. Run the narrative generator:
- With a Gemini API key:
```bash
export GEMINI_API_KEY="your_api_key_here"
python narrator/generate_narrative.py
```
- Offline (no API key needed; uses `generate_scr_narrative_offline`):
```bash
python narrator/generate_narrative.py
```
