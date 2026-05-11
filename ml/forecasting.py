#!/usr/bin/env python3
"""
Forecasting Model
=================
Fits an ARIMA model on daily transaction volume and revenue,
then writes 30-day forecasts to ml_forecasts.

Usage:
    source venv/bin/activate
    python ml/forecasting.py
"""

import os
import warnings

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "payment_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def load_daily_data(conn):
    return pd.read_sql(
        """
        SELECT
            timestamp::date AS date,
            COUNT(*) AS transactions,
            SUM(amount) FILTER (WHERE status = 'Success') AS revenue,
            COUNT(*) FILTER (WHERE status = 'Failed') AS failed,
            COUNT(*) FILTER (WHERE is_fraud = 1) AS fraud
        FROM fact_transactions
        GROUP BY timestamp::date
        ORDER BY date
        """,
        conn,
        parse_dates=["date"],
    )


def fit_forecast(series, periods=30, order=(7, 1, 0)):
    """Fit ARIMA and forecast. Returns forecast df."""
    if len(series) < 14:
        return pd.DataFrame()

    try:
        model = ARIMA(series, order=order)
        fitted = model.fit()
        forecast = fitted.get_forecast(steps=periods)
        pred_mean = forecast.predicted_mean
        conf_int = forecast.conf_int()

        last_date = series.index[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods)

        df = pd.DataFrame(
            {
                "date": future_dates,
                "forecast": pred_mean.values,
                "lower_bound": conf_int.iloc[:, 0].values,
                "upper_bound": conf_int.iloc[:, 1].values,
            }
        )
        return df
    except Exception as e:
        print(f"   Forecast failed: {e}")
        return pd.DataFrame()


def save_forecasts(conn, df, metric_name):
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_forecasts (
            metric_name    VARCHAR(30),
            forecast_date  DATE,
            forecast_value DOUBLE PRECISION,
            lower_bound    DOUBLE PRECISION,
            upper_bound    DOUBLE PRECISION,
            model_name     VARCHAR(30) DEFAULT 'arima',
            created_at     TIMESTAMP   DEFAULT NOW(),
            PRIMARY KEY (metric_name, forecast_date)
        )
        """
    )

    # Delete old forecasts for this metric
    cur.execute("DELETE FROM ml_forecasts WHERE metric_name = %s", (metric_name,))

    rows = list(
        zip(
            [metric_name] * len(df),
            df["date"],
            df["forecast"],
            df["lower_bound"],
            df["upper_bound"],
        )
    )

    execute_values(
        cur,
        """
        INSERT INTO ml_forecasts
        (metric_name, forecast_date, forecast_value, lower_bound, upper_bound)
        VALUES %s
        """,
        rows,
        page_size=100,
    )

    conn.commit()
    cur.close()


def main():
    print("=" * 55)
    print("Forecasting Model  —  ARIMA")
    print("=" * 55)

    conn = get_connection()

    print("\nLoading daily aggregates...")
    df = load_daily_data(conn)
    print(f"   {len(df):,} days of history")

    # Forecast transactions
    print("\nForecasting daily transactions (ARIMA 7,1,0)...")
    ts_txn = df.set_index("date")["transactions"]
    fc_txn = fit_forecast(ts_txn, periods=30, order=(7, 1, 0))
    if not fc_txn.empty:
        fc_txn["forecast"] = fc_txn["forecast"].clip(lower=0).round(0)
        fc_txn["lower_bound"] = fc_txn["lower_bound"].clip(lower=0).round(0)
        fc_txn["upper_bound"] = fc_txn["upper_bound"].clip(lower=0).round(0)
        save_forecasts(conn, fc_txn, "transactions")
        print(f"   Saved {len(fc_txn)} days of transaction forecasts")

    # Forecast revenue
    print("\nForecasting daily revenue (ARIMA 7,1,0)...")
    ts_rev = df.set_index("date")["revenue"].fillna(0)
    fc_rev = fit_forecast(ts_rev, periods=30, order=(7, 1, 0))
    if not fc_rev.empty:
        fc_rev["forecast"] = fc_rev["forecast"].clip(lower=0)
        fc_rev["lower_bound"] = fc_rev["lower_bound"].clip(lower=0)
        fc_rev["upper_bound"] = fc_rev["upper_bound"].clip(lower=0)
        save_forecasts(conn, fc_rev, "revenue")
        print(f"   Saved {len(fc_rev)} days of revenue forecasts")

    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
