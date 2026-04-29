# Oil City Hackers — AI Agency 2026

## Amendment Growth Tracker (Streamlit)

### Run locally

```bash
python -m pip install -r requirements.txt
export DB_CONNECTION_STRING='postgresql://<user>:<password>@<host>/<database>'
python -m streamlit run app.py
```

### Data source behavior

- Primary: live PostgreSQL query (`DB_CONNECTION_STRING`) using `dev1-sql/DEV1_CANONICAL_SQL_CONTRACT.sql`
- Fallback: `data/contracts.csv` when `DB_CONNECTION_STRING` is not set
