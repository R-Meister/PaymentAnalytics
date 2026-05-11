#!/usr/bin/env python3
"""
Data Loader — loads CSV files from data/ into PostgreSQL.
Run after docker-compose up so the database is available.

Usage:
    python sql/loader.py
    python sql/loader.py --host localhost --db payment_analytics --user postgres
"""

import argparse
import os
import sys

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

COLUMN_MAP = {
    "customers.csv": (
        "dim_customers",
        [
            "customer_id", "customer_name", "email", "phone", "city", "state",
            "x_customer_id", "y_customer_id", "mean_amount", "std_amount",
            "mean_nb_tx_per_day", "registration_date", "device_preference"
        ],
    ),
    "merchants.csv": (
        "dim_merchants",
        [
            "merchant_id", "merchant_name", "category", "city", "state",
            "x_merchant_id", "y_merchant_id", "risk_score", "registration_date",
            "avg_transaction_value", "status"
        ],
    ),
    "transactions.csv": (
        "fact_transactions",
        [
            "transaction_id", "customer_id", "merchant_id", "amount",
            "payment_method", "category", "city", "state", "timestamp",
            "status", "device_type", "is_fraud", "fraud_score", "risk_level",
            "transaction_hour", "weekend_flag", "customer_merchant_distance"
        ],
    ),
}

LOAD_ORDER = ["customers.csv", "merchants.csv", "transactions.csv"]


def connect(host, port, dbname, user, password):
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def load_table(conn, csv_path, table, columns):
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"   (skipped {table} — empty CSV)")
        return 0

    df = df.where(pd.notnull(df), None)
    rows = [tuple(row) for row in df[columns].values]

    cur = conn.cursor()

    # Truncate first so repeated runs are safe
    cur.execute(f"truncate table {table} cascade")

    col_names = ", ".join(columns)
    sql = f"insert into {table} ({col_names}) values %s"
    execute_values(cur, sql, rows, page_size=5000)

    conn.commit()
    cur.close()
    return len(rows)


def run_schema(conn, schema_path):
    with open(schema_path) as f:
        sql = f.read()
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Load CSVs into PostgreSQL")
    parser.add_argument("--host", default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "5433")))
    parser.add_argument("--db", default=os.getenv("DB_NAME", "payment_analytics"))
    parser.add_argument("--user", default=os.getenv("DB_USER", "postgres"))
    parser.add_argument("--password", default=os.getenv("DB_PASSWORD", "postgres"))
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--schema", default="sql/schema.sql")
    parser.add_argument("--skip-schema", action="store_true")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(root_dir, args.data_dir) if not os.path.isabs(args.data_dir) else args.data_dir
    schema_path = os.path.join(root_dir, args.schema) if not os.path.isabs(args.schema) else args.schema

    print("=" * 50)
    print("Payment Analytics — Data Loader")
    print("=" * 50)

    print(f"\nConnecting to postgresql://{args.user}@{args.host}:{args.port}/{args.db} ...")
    conn = connect(args.host, args.port, args.db, args.user, args.password)
    print("Connected.")

    if not args.skip_schema:
        print(f"\nRunning schema from {schema_path} ...")
        run_schema(conn, schema_path)
        print("Schema applied.")

    total = 0
    for csv_file in LOAD_ORDER:
        if csv_file not in COLUMN_MAP:
            continue
        table, columns = COLUMN_MAP[csv_file]
        csv_path = os.path.join(data_dir, csv_file)
        if not os.path.exists(csv_path):
            print(f"\nSkipping {csv_file} — not found in {data_dir}")
            continue

        print(f"\nLoading {csv_file} -> {table} ({len(columns)} columns) ...")
        count = load_table(conn, csv_path, table, columns)
        total += count
        print(f"   Inserted {count:,} rows")

    conn.close()
    print(f"\nDone. {total:,} total rows loaded.")


if __name__ == "__main__":
    main()
