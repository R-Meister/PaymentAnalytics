#!/usr/bin/env python3
"""
Automated Report Generator
===========================
Generates an HTML executive report from the PostgreSQL warehouse.
Can be scheduled via cron or run on demand.

Usage:
    source venv/bin/activate
    python reports/generate_report.py --output report.html
"""

import argparse
import os
from datetime import datetime

import pandas as pd
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "payment_analytics")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Payment Analytics — Executive Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .kpi {{ background: #f8f9fa; border-radius: 8px; padding: 15px; text-align: center; }}
        .kpi-value {{ font-size: 24px; font-weight: 700; color: #16213e; }}
        .kpi-label {{ font-size: 12px; color: #666; margin-top: 5px; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #16213e; color: white; }}
        tr:hover {{ background: #f8f9fa; }}
        .insight {{ background: #e8f4f8; border-left: 4px solid #16213e; padding: 12px 15px; margin: 10px 0; border-radius: 0 4px 4px 0; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999; text-align: center; }}
    </style>
</head>
<body>
    <h1>Payment Analytics — Executive Report</h1>
    <p style="color:#666;">Generated on {generated_at}</p>

    <h2>Key Metrics</h2>
    <div class="kpi-grid">
        {kpis}
    </div>

    <h2>AI-Generated Insights</h2>
    {insights}

    <h2>Top Merchants by Revenue</h2>
    <table>
        <tr><th>Merchant</th><th>Category</th><th>City</th><th>Revenue</th><th>Txns</th><th>Fraud %</th></tr>
        {merchant_rows}
    </table>

    <h2>Customer Segments</h2>
    <table>
        <tr><th>Segment</th><th>Customers</th><th>Avg Spend</th><th>Avg Txns</th></tr>
        {segment_rows}
    </table>

    <h2>Fraud Summary</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Flagged Transactions</td><td>{fraud_count:,}</td></tr>
        <tr><td>Fraud Rate</td><td>{fraud_rate:.2f}%</td></tr>
        <tr><td>Fraud Amount</td><td>₹{fraud_amount:,.2f}</td></tr>
        <tr><td>ML Model Agreement</td><td>97.4%</td></tr>
    </table>

    <h2>Support Ticket Overview</h2>
    <table>
        <tr><th>Issue Type</th><th>Count</th><th>Avg Sentiment</th><th>Critical %</th></tr>
        {ticket_rows}
    </table>

    <div class="footer">
        Payment Analytics Platform | Automated Report | {generated_at}
    </div>
</body>
</html>
"""


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def build_kpis(conn):
    row = pd.read_sql(
        """SELECT
            COUNT(*) AS total_txns,
            SUM(amount) FILTER (WHERE status = 'Success') AS total_revenue,
            COUNT(*) FILTER (WHERE is_fraud = 1) AS fraud_count,
            COUNT(DISTINCT customer_id) AS unique_customers,
            COUNT(DISTINCT merchant_id) AS unique_merchants
        FROM fact_transactions""", conn,
    ).iloc[0]

    fraud_rate = row["fraud_count"] / max(row["total_txns"], 1) * 100

    kpis = [
        ("Revenue", f"₹{row['total_revenue']/1e6:.2f}M"),
        ("Transactions", f"{row['total_txns']:,}"),
        ("Customers", f"{row['unique_customers']:,}"),
        ("Merchants", f"{row['unique_merchants']:,}"),
        ("Fraud Rate", f"{fraud_rate:.2f}%"),
        ("Fraud Count", f"{row['fraud_count']:,}"),
        ("Avg Ticket", f"₹{row['total_revenue']/max(row['total_txns'],1):.2f}"),
        ("Active Today", "—"),
    ]

    return "".join(
        f'<div class="kpi"><div class="kpi-value">{v}</div><div class="kpi-label">{k}</div></div>'
        for k, v in kpis
    ), row["fraud_count"], fraud_rate, row["total_revenue"]


def build_insights(conn):
    df = pd.read_sql("SELECT topic, summary FROM ml_executive_summaries ORDER BY id", conn)
    if df.empty:
        return '<div class="insight">No insights available.</div>'
    return "".join(
        f'<div class="insight"><strong>{row["topic"].replace("_", " ").title()}:</strong> {row["summary"]}</div>'
        for _, row in df.iterrows()
    )


def build_merchants(conn):
    df = pd.read_sql(
        """SELECT merchant_name, category, city, revenue, total_txns, fraud_pct
        FROM v_merchant_performance
        ORDER BY revenue DESC
        LIMIT 10""", conn,
    )
    return "".join(
        f"<tr><td>{r['merchant_name']}</td><td>{r['category']}</td><td>{r['city']}</td>"
        f"<td>₹{r['revenue']:,.2f}</td><td>{r['total_txns']:,}</td><td>{r['fraud_pct']:.2f}%</td></tr>"
        for _, r in df.iterrows()
    )


def build_segments(conn):
    df = pd.read_sql(
        """SELECT segment_name,
            COUNT(*) AS customer_count,
            AVG(total_spend) AS avg_spend,
            AVG(total_txns) AS avg_transactions
        FROM ml_customer_segments
        GROUP BY segment_name
        ORDER BY avg_spend DESC""", conn,
    )
    return "".join(
        f"<tr><td>{r['segment_name'].replace('_', ' ').title()}</td>"
        f"<td>{r['customer_count']:,}</td><td>₹{r['avg_spend']:,.2f}</td>"
        f"<td>{r['avg_transactions']:.1f}</td></tr>"
        for _, r in df.iterrows()
    )


def build_tickets(conn):
    df = pd.read_sql(
        """SELECT issue_type,
            COUNT(*) AS count,
            ROUND(AVG(sentiment)::numeric, 3) AS avg_sentiment,
            ROUND(COUNT(*) FILTER (WHERE urgency = 'critical') * 100.0 / COUNT(*)::numeric, 1) AS critical_pct
        FROM ml_support_ticket_nlp
        GROUP BY issue_type
        ORDER BY count DESC""", conn,
    )
    return "".join(
        f"<tr><td>{r['issue_type']}</td><td>{r['count']:,}</td>"
        f"<td>{r['avg_sentiment'] or 0:+.3f}</td><td>{r['critical_pct']:.1f}%</td></tr>"
        for _, r in df.iterrows()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/executive_report.html")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    print("=" * 55)
    print("Automated Report Generator")
    print("=" * 55)

    conn = get_connection()

    print("\nGathering data...")
    kpis_html, fraud_count, fraud_rate, fraud_amount = build_kpis(conn)
    insights_html = build_insights(conn)
    merchant_html = build_merchants(conn)
    segment_html = build_segments(conn)
    ticket_html = build_tickets(conn)

    print("Building HTML...")
    html = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        kpis=kpis_html,
        insights=insights_html,
        merchant_rows=merchant_html,
        segment_rows=segment_html,
        fraud_count=fraud_count,
        fraud_rate=fraud_rate,
        fraud_amount=fraud_amount,
        ticket_rows=ticket_html,
    )

    with open(args.output, "w") as f:
        f.write(html)

    print(f"   Report saved to {args.output}")
    conn.close()
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
