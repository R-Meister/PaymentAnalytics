# Payment Analytics Platform

Enterprise-grade payment intelligence system for merchant performance, fraud detection, customer segmentation, and executive reporting.

## Architecture

```
Simulator (Python + Faker)
    ↓ CSV files (customers, merchants, transactions, reviews, tickets)
PySpark ETL (Delta Lake)
    ↓ Bronze → Silver → Gold
PostgreSQL Warehouse
    ↓ Star Schema + Views
FastAPI Backend
    ↓ REST API
Streamlit Dashboard
```

## Tech Stack

- **Data Engineering**: Python, PySpark, Delta Lake, pandas
- **Warehouse**: PostgreSQL (star schema)
- **Backend**: FastAPI, asyncpg, Pydantic
- **ML / NLP**: scikit-learn, TextBlob, statsmodels (ARIMA)
- **Dashboard**: Streamlit
- **DevOps**: Docker, Docker Compose

## Project Structure

```
PaymentAnalytics/
├── simulator/
│   ├── simulator.py              # CLI data generator (1M+ transactions)
│   └── datasimulator.ipynb       # Original prototype
├── pyspark_jobs/
│   ├── bronze_ingestion.py       # Raw CSV → Delta Lake
│   ├── silver_ingestion.py       # Cleansing + feature engineering
│   └── gold_ingestion.py         # Business aggregations
├── sql/
│   ├── schema.sql                # Star schema DDL + indexes + views
│   └── loader.py                 # CSV → PostgreSQL bulk loader
├── api/
│   ├── main.py                   # FastAPI app entrypoint
│   ├── database.py               # asyncpg connection pool
│   ├── schemas.py                # Pydantic request/response models
│   └── routes/
│       ├── transactions.py
│       ├── merchants.py
│       ├── fraud.py
│       ├── customers.py
│       ├── executive.py
│       └── forecast.py
├── ml/
│   ├── fraud_detection.py        # Isolation Forest (97.4% agreement)
│   ├── customer_segmentation.py  # KMeans clustering (5 segments)
│   ├── sentiment_analysis.py     # TextBlob on 5,000 reviews
│   ├── support_nlp.py            # Ticket sentiment + urgency + topics
│   ├── forecasting.py            # ARIMA(7,1,0) — 30-day forecasts
│   └── genai_summaries.py        # Rule-based executive insight generation
├── dashboard/
│   ├── app.py                    # Streamlit entrypoint
│   ├── utils.py                  # API client helper
│   └── pages/
│       ├── 1_executive.py
│       ├── 2_merchant.py
│       ├── 3_fraud.py
│       ├── 4_customer.py
│       └── 5_forecast.py
├── reports/
│   └── generate_report.py        # Automated HTML executive report
├── docker-compose.yml            # PostgreSQL + API services
├── Dockerfile                    # API container image
└── requirements.txt
```

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/R-Meister/PaymentAnalytics.git
cd PaymentAnalytics
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m textblob.download_corpora lite
```

### 2. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 3. Load Data & Run ML

```bash
# Load CSVs into PostgreSQL
python sql/loader.py

# Train ML models
python ml/fraud_detection.py
python ml/customer_segmentation.py
python ml/sentiment_analysis.py
python ml/support_nlp.py
python ml/forecasting.py
python ml/genai_summaries.py
```

### 4. Start API

```bash
uvicorn api.main:app --port 8000
```

API docs: `http://localhost:8000/docs`

### 5. Start Dashboard

```bash
streamlit run dashboard/app.py --server.port 8501
```

Dashboard: `http://localhost:8501`

### 6. Generate Report

```bash
python reports/generate_report.py
open reports/executive_report.html
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/executive/summary` | KPIs, revenue trends, payment/category distribution |
| `GET /api/transactions` | Paginated, filterable transaction list |
| `GET /api/merchants` | Merchant directory with performance stats |
| `GET /api/merchants/top/by-revenue` | Top N merchants |
| `GET /api/merchants/sentiment` | Merchant sentiment scores |
| `GET /api/fraud/alerts` | Fraud alert feed |
| `GET /api/fraud/summary` | Fraud statistics by hour, category, risk |
| `GET /api/fraud/ml-predictions` | ML-flagged anomalies |
| `GET /api/customers/segments` | Heuristic customer segments |
| `GET /api/customers/segments/ml` | KMeans ML segments |
| `GET /api/customers` | Paginated customer list |
| `GET /api/forecast` | Historical + ARIMA forecast data |

## ML Models

| Model | File | Algorithm | Output |
|-------|------|-----------|--------|
| Fraud Detection | `ml/fraud_detection.py` | Isolation Forest | `ml_fraud_predictions` |
| Customer Segments | `ml/customer_segmentation.py` | KMeans (k=5) | `ml_customer_segments` |
| Sentiment Analysis | `ml/sentiment_analysis.py` | TextBlob | `ml_review_sentiment`, `ml_merchant_sentiment` |
| Support NLP | `ml/support_nlp.py` | TextBlob + rules | `ml_support_ticket_nlp` |
| Forecasting | `ml/forecasting.py` | ARIMA(7,1,0) | `ml_forecasts` |
| Executive Insights | `ml/genai_summaries.py` | Rule-based templates | `ml_executive_summaries` |

## Database Schema

### Dimension Tables
- `dim_customers` — 5,000 customers with spatial coords + spend stats
- `dim_merchants` — 500 merchants with category, risk score, status

### Fact Table
- `fact_transactions` — 100,000 transactions with fraud labels + 13 indexes

### Views
- `v_fraud_alerts` — Enriched fraud transactions
- `v_merchant_performance` — Revenue, fraud %, refund %
- `v_customer_summary` — Spend, recency, merchant diversity

### ML Tables
- `ml_fraud_predictions` — Isolation Forest scores
- `ml_customer_segments` — KMeans segment assignments
- `ml_review_sentiment` — Per-review sentiment
- `ml_merchant_sentiment` — Aggregated merchant sentiment
- `ml_support_ticket_nlp` — Ticket sentiment + urgency + topics
- `ml_forecasts` — ARIMA transaction + revenue forecasts
- `ml_executive_summaries` — AI-generated business insights

## Docker

Spin up everything with one command:

```bash
docker compose up --build
```

Services:
- **PostgreSQL** on `localhost:5433`
- **FastAPI** on `localhost:8000`

## License

MIT
