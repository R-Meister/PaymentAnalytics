#!/usr/bin/env python3
"""
Sentiment Analysis Model
========================
Analyzes merchant review text using TextBlob and writes sentiment scores
to ml_review_sentiment plus merchant-level aggregates.

Usage:
    source venv/bin/activate
    python ml/sentiment_analysis.py
"""

import os
import warnings

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from textblob import TextBlob

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


def load_data():
    import os

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    path = os.path.join(data_dir, "reviews.csv")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def analyze_sentiment(text):
    blob = TextBlob(str(text))
    return blob.sentiment.polarity, blob.sentiment.subjectivity


def classify_sentiment(polarity):
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    return "neutral"


def save_reviews(conn, df):
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_review_sentiment (
            review_id      VARCHAR(10) PRIMARY KEY,
            merchant_id    VARCHAR(10),
            rating         INTEGER,
            polarity       DOUBLE PRECISION,
            subjectivity   DOUBLE PRECISION,
            sentiment      VARCHAR(10),
            review_text    TEXT,
            created_at     TIMESTAMP DEFAULT NOW()
        )
        """
    )

    cur.execute("TRUNCATE TABLE ml_review_sentiment")

    rows = list(
        zip(
            df["review_id"],
            df["merchant_id"],
            df["rating"],
            df["polarity"],
            df["subjectivity"],
            df["sentiment"],
            df["review_text"],
        )
    )

    execute_values(
        cur,
        """
        INSERT INTO ml_review_sentiment
        (review_id, merchant_id, rating, polarity, subjectivity, sentiment, review_text)
        VALUES %s
        """,
        rows,
        page_size=1000,
    )

    conn.commit()
    cur.close()


def save_merchant_aggregates(conn, df):
    agg = (
        df.groupby("merchant_id")
        .agg(
            review_count=("review_id", "count"),
            avg_rating=("rating", "mean"),
            avg_polarity=("polarity", "mean"),
            avg_subjectivity=("subjectivity", "mean"),
            positive_count=("sentiment", lambda x: (x == "positive").sum()),
            negative_count=("sentiment", lambda x: (x == "negative").sum()),
            neutral_count=("sentiment", lambda x: (x == "neutral").sum()),
        )
        .reset_index()
    )

    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_merchant_sentiment (
            merchant_id       VARCHAR(10) PRIMARY KEY,
            review_count      INTEGER,
            avg_rating        DOUBLE PRECISION,
            avg_polarity      DOUBLE PRECISION,
            avg_subjectivity  DOUBLE PRECISION,
            positive_count    INTEGER,
            negative_count    INTEGER,
            neutral_count     INTEGER,
            updated_at        TIMESTAMP DEFAULT NOW()
        )
        """
    )

    cur.execute("TRUNCATE TABLE ml_merchant_sentiment")

    rows = list(
        zip(
            agg["merchant_id"],
            agg["review_count"],
            agg["avg_rating"],
            agg["avg_polarity"],
            agg["avg_subjectivity"],
            agg["positive_count"],
            agg["negative_count"],
            agg["neutral_count"],
        )
    )

    execute_values(
        cur,
        """
        INSERT INTO ml_merchant_sentiment
        (merchant_id, review_count, avg_rating, avg_polarity, avg_subjectivity,
         positive_count, negative_count, neutral_count)
        VALUES %s
        """,
        rows,
        page_size=500,
    )

    conn.commit()
    cur.close()


def main():
    print("=" * 55)
    print("Sentiment Analysis  —  TextBlob")
    print("=" * 55)

    conn = get_connection()

    print("\nLoading reviews...")
    df = load_data()
    print(f"   Loaded {len(df):,} reviews")

    print("\nAnalyzing sentiment...")
    sentiments = df["review_text"].apply(analyze_sentiment)
    df["polarity"] = sentiments.apply(lambda x: x[0])
    df["subjectivity"] = sentiments.apply(lambda x: x[1])
    df["sentiment"] = df["polarity"].apply(classify_sentiment)

    pos = (df["sentiment"] == "positive").sum()
    neg = (df["sentiment"] == "negative").sum()
    neu = (df["sentiment"] == "neutral").sum()
    print(f"   Positive: {pos:,}  Negative: {neg:,}  Neutral: {neu:,}")

    print("\nSaving review sentiment...")
    save_reviews(conn, df)
    print("   Done.")

    print("\nSaving merchant aggregates...")
    save_merchant_aggregates(conn, df)
    print("   Done.")

    # Top positive / negative merchants
    top_pos = df.groupby("merchant_id")["polarity"].mean().sort_values(ascending=False).head(3)
    top_neg = df.groupby("merchant_id")["polarity"].mean().sort_values().head(3)

    print("\nTop positive merchants (by avg polarity):")
    for mid, pol in top_pos.items():
        print(f"   {mid}: {pol:+.3f}")

    print("\nTop negative merchants (by avg polarity):")
    for mid, pol in top_neg.items():
        print(f"   {mid}: {pol:+.3f}")

    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
