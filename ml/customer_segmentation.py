#!/usr/bin/env python3
"""
Customer Segmentation Model
===========================
Runs KMeans clustering on customer behavioural features and writes
segment assignments to ml_customer_segments.

Usage:
    source venv/bin/activate
    python ml/customer_segmentation.py
"""

import os
import warnings

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sklearn.cluster import KMeans
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
    return pd.read_sql("SELECT * FROM v_customer_summary", conn)


def engineer_features(df):
    df = df.copy()

    # Recency
    df["last_txn"] = pd.to_datetime(df["last_txn"])
    df["days_since_last_txn"] = (
        pd.Timestamp.now() - df["last_txn"]
    ).dt.days.fillna(999).astype(int)

    # Spend per merchant
    df["spend_per_merchant"] = df["total_spend"] / (df["unique_merchants"] + 1)

    features = [
        "total_txns",
        "total_spend",
        "avg_txn_value",
        "unique_merchants",
        "fraud_txn_count",
        "days_since_last_txn",
        "spend_per_merchant",
    ]

    return df, features


def train_model(df, features, n_clusters=5):
    X = df[features].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["segment_id"] = model.fit_predict(X_scaled)

    # Name segments from cluster centroids
    centroids = pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_),
        columns=features,
    )

    # Sort by total_spend descending
    ranked = centroids["total_spend"].rank(ascending=False).astype(int)
    label_map = {
        1: "high_value",
        2: "luxury_spender",
        3: "frequent",
        4: "diverse_shopper",
        5: "casual",
    }

    id_to_label = {}
    for seg_id in range(n_clusters):
        rank = ranked.iloc[seg_id]
        id_to_label[seg_id] = label_map.get(rank, f"segment_{seg_id}")

    df["segment_name"] = df["segment_id"].map(id_to_label)

    return df, model, scaler, centroids


def save_segments(conn, df):
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_customer_segments (
            customer_id          VARCHAR(10) PRIMARY KEY REFERENCES dim_customers(customer_id),
            segment_id           INTEGER,
            segment_name         VARCHAR(50),
            total_txns           INTEGER,
            total_spend          DOUBLE PRECISION,
            avg_txn_value        DOUBLE PRECISION,
            unique_merchants     INTEGER,
            fraud_txn_count      INTEGER,
            days_since_last_txn  INTEGER,
            spend_per_merchant   DOUBLE PRECISION,
            created_at           TIMESTAMP DEFAULT NOW()
        )
        """
    )

    cur.execute("TRUNCATE TABLE ml_customer_segments")

    rows = list(
        zip(
            df["customer_id"],
            df["segment_id"],
            df["segment_name"],
            df["total_txns"],
            df["total_spend"],
            df["avg_txn_value"],
            df["unique_merchants"],
            df["fraud_txn_count"],
            df["days_since_last_txn"],
            df["spend_per_merchant"],
        )
    )

    execute_values(
        cur,
        """
        INSERT INTO ml_customer_segments
        (customer_id, segment_id, segment_name, total_txns, total_spend,
         avg_txn_value, unique_merchants, fraud_txn_count, days_since_last_txn, spend_per_merchant)
        VALUES %s
        """,
        rows,
        page_size=1000,
    )

    conn.commit()
    cur.close()


def main():
    print("=" * 55)
    print("Customer Segmentation Model  —  KMeans")
    print("=" * 55)

    conn = get_connection()

    print("\nLoading customers...")
    df = load_data(conn)
    print(f"   Loaded {len(df):,} customers")

    print("\nEngineering features...")
    df, features = engineer_features(df)
    print(f"   Features: {features}")

    print("\nTraining KMeans (k=5)...")
    df, model, scaler, centroids = train_model(df, features, n_clusters=5)

    print("\nSegments:")
    for seg_id in sorted(df["segment_id"].unique()):
        sub = df[df["segment_id"] == seg_id]
        name = sub["segment_name"].iloc[0]
        print(
            f"   {name:20s}  {len(sub):5,} customers  "
            f"avg spend ₹{sub['total_spend'].mean():,.2f}  "
            f"avg txns {sub['total_txns'].mean():.1f}"
        )

    print("\nSaving segments to PostgreSQL...")
    save_segments(conn, df)
    print("   Done.")

    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
