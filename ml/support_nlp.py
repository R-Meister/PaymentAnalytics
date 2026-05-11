#!/usr/bin/env python3
"""
Support Ticket NLP
==================
Topic extraction + urgency classification on support tickets.
Writes results to ml_support_ticket_nlp.

Usage:
    source venv/bin/activate
    python ml/support_nlp.py
"""

import os
import re

import pandas as pd
import psycopg2
from textblob import TextBlob

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "payment_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def load_tickets():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    df = pd.read_csv(os.path.join(data_dir, "support_tickets.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def extract_keywords(text):
    """Extract noun phrases from ticket description."""
    blob = TextBlob(str(text))
    phrases = [phrase for phrase in blob.noun_phrases if len(phrase) > 3]
    return ", ".join(phrases[:5]) if phrases else "general"


def classify_urgency(row):
    """Rule-based urgency from priority + issue type + description."""
    score = 0
    if row["priority"] == "High":
        score += 3
    if row["issue_type"] in ("Fraud Alert", "Account Access"):
        score += 2
    if row["issue_type"] == "Payment Failed":
        score += 1

    text = str(row["description"]).lower()
    urgent_words = ["immediately", "urgent", "asap", "emergency", "critical"]
    if any(w in text for w in urgent_words):
        score += 2

    if score >= 4:
        return "critical"
    if score >= 2:
        return "high"
    return "normal"


def analyze_sentiment(text):
    return TextBlob(str(text)).sentiment.polarity


def extract_topics(text):
    """Simple keyword-based topic tags."""
    text = str(text).lower()
    topics = []
    if any(w in text for w in ["refund", "waiting", "days"]):
        topics.append("refund_delay")
    if any(w in text for w in ["failed", "declined", "deducted"]):
        topics.append("payment_failure")
    if any(w in text for w in ["fraud", "authorize", "unauthorized"]):
        topics.append("fraud_concern")
    if any(w in text for w in ["login", "access", "authentication", "password"]):
        topics.append("account_access")
    if any(w in text for w in ["cashback", "reward", "offer"]):
        topics.append("loyalty_query")
    if not topics:
        topics.append("general")
    return ", ".join(topics)


def save_results(conn, df):
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS ml_support_ticket_nlp (
            ticket_id        VARCHAR(10) PRIMARY KEY,
            issue_type       VARCHAR(30),
            sentiment        DOUBLE PRECISION,
            polarity_label   VARCHAR(10),
            urgency          VARCHAR(10),
            keywords         TEXT,
            topics           TEXT,
            created_at       TIMESTAMP DEFAULT NOW()
        )"""
    )
    cur.execute("TRUNCATE TABLE ml_support_ticket_nlp")

    for _, row in df.iterrows():
        cur.execute(
            """INSERT INTO ml_support_ticket_nlp
            (ticket_id, issue_type, sentiment, polarity_label, urgency, keywords, topics)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                row["ticket_id"],
                row["issue_type"],
                row["sentiment"],
                row["polarity_label"],
                row["urgency"],
                row["keywords"],
                row["topics"],
            ),
        )

    conn.commit()
    cur.close()


def main():
    print("=" * 55)
    print("Support Ticket NLP")
    print("=" * 55)

    conn = get_connection()

    print("\nLoading tickets...")
    df = load_tickets()
    print(f"   {len(df):,} tickets")

    print("\nAnalyzing sentiment...")
    df["sentiment"] = df["description"].apply(analyze_sentiment)
    df["polarity_label"] = df["sentiment"].apply(
        lambda x: "positive" if x > 0.1 else ("negative" if x < -0.1 else "neutral")
    )

    print("Classifying urgency...")
    df["urgency"] = df.apply(classify_urgency, axis=1)

    print("Extracting keywords...")
    df["keywords"] = df["description"].apply(extract_keywords)

    print("Tagging topics...")
    df["topics"] = df["description"].apply(extract_topics)

    print("\nResults:")
    print(f"   Urgency: {df['urgency'].value_counts().to_dict()}")
    print(f"   Sentiment: {df['polarity_label'].value_counts().to_dict()}")

    print("\nSaving to PostgreSQL...")
    save_results(conn, df)
    print("   Done.")

    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
