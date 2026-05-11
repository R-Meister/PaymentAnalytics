#!/usr/bin/env python3
"""
Fraud Detection Model
=====================
Trains an Isolation Forest on raw transaction + customer + merchant features
and writes anomaly scores to ml_fraud_predictions.

Usage:
    source venv/bin/activate
    python ml/fraud_detection.py
"""

import os
import warnings

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

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


def load_data(conn):
    query = """
    SELECT
        t.transaction_id,
        t.amount,
        t.transaction_hour,
        t.weekend_flag,
        t.customer_merchant_distance,
        t.payment_method,
        t.device_type,
        t.category,
        t.status,
        c.mean_amount    AS customer_mean,
        c.std_amount     AS customer_std,
        c.mean_nb_tx_per_day AS customer_tx_rate,
        m.risk_score     AS merchant_risk
    FROM fact_transactions t
    JOIN dim_customers c ON t.customer_id = c.customer_id
    JOIN dim_merchants m ON t.merchant_id = m.merchant_id
    """
    return pd.read_sql(query, conn)


def engineer_features(df):
    df = df.copy()

    # Encode categoricals
    df["payment_method_enc"] = pd.Categorical(df["payment_method"]).codes
    df["device_type_enc"] = pd.Categorical(df["device_type"]).codes
    df["category_enc"] = pd.Categorical(df["category"]).codes
    df["status_enc"] = pd.Categorical(df["status"]).codes

    # Ratios
    df["amount_vs_customer_mean"] = df["amount"] / (df["customer_mean"] + 1)
    df["amount_vs_merchant_risk"] = df["amount"] / (df["merchant_risk"] + 1)

    features = [
        "amount",
        "transaction_hour",
        "weekend_flag",
        "customer_merchant_distance",
        "payment_method_enc",
        "device_type_enc",
        "category_enc",
        "status_enc",
        "customer_mean",
        "customer_std",
        "customer_tx_rate",
        "merchant_risk",
        "amount_vs_customer_mean",
    ]

    return df, features


def train_model(df, features):
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.015,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    predictions = model.predict(X_scaled)  # -1 = anomaly, 1 = normal
    scores = model.decision_function(X_scaled)  # higher = more normal

    df["model_prediction"] = (predictions == -1).astype(int)
    df["model_score"] = -scores  # invert: higher = more anomalous

    return df, model, scaler


def save_predictions(conn, df):
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_fraud_predictions (
            transaction_id   VARCHAR(15) PRIMARY KEY,
            model_prediction SMALLINT    DEFAULT 0,
            model_score      DOUBLE PRECISION,
            model_name       VARCHAR(50) DEFAULT 'isolation_forest',
            created_at       TIMESTAMP   DEFAULT NOW()
        )
        """
    )

    cur.execute("TRUNCATE TABLE ml_fraud_predictions")

    rows = list(
        zip(
            df["transaction_id"],
            df["model_prediction"],
            df["model_score"],
        )
    )

    execute_values(
        cur,
        "INSERT INTO ml_fraud_predictions (transaction_id, model_prediction, model_score) VALUES %s",
        rows,
        page_size=5000,
    )

    conn.commit()
    cur.close()


def main():
    print("=" * 55)
    print("Fraud Detection Model  —  Isolation Forest")
    print("=" * 55)

    conn = get_connection()

    print("\nLoading transactions...")
    df = load_data(conn)
    print(f"   Loaded {len(df):,} rows")

    print("\nEngineering features...")
    df, features = engineer_features(df)
    print(f"   Using {len(features)} features")

    print("\nTraining Isolation Forest (contamination=1.5%)...")
    df, model, scaler = train_model(df, features)

    flagged = int(df["model_prediction"].sum())
    print(f"   Flagged {flagged:,} anomalies ({flagged / len(df) * 100:.2f}%)")

    # Compare with heuristic fraud labels
    heuristic_fraud = pd.read_sql(
        "SELECT transaction_id, is_fraud FROM fact_transactions", conn
    )
    merged = df[["transaction_id", "model_prediction"]].merge(
        heuristic_fraud, on="transaction_id"
    )
    agreement = (
        (merged["model_prediction"] == merged["is_fraud"]).sum()
        / len(merged)
        * 100
    )
    print(f"   Agreement with heuristic labels: {agreement:.1f}%")

    print("\nSaving predictions to PostgreSQL...")
    save_predictions(conn, df)
    print("   Done.")

    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
