#!/usr/bin/env python3
"""
Payment Analytics Data Simulator
================================
Generates synthetic datasets for the Payment Analytics Platform:
    - customers.csv
    - merchants.csv
    - transactions.csv
    - reviews.csv
    - support_tickets.csv

Based on the original notebook spatial simulation logic (customer/terminal
profiles with x,y coordinates) and expanded to cover the full merchant
intelligence scope defined in plan.txt.

Usage:
    python simulator.py
    python simulator.py --transactions 500000 --customers 25000 --merchants 2500
"""

import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# =============================================================================
# CONSTANTS
# =============================================================================

INDIAN_CITIES = [
    ("Delhi", "Delhi"), ("Mumbai", "Maharashtra"), ("Bangalore", "Karnataka"),
    ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"), ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Chandigarh", "Punjab"), ("Kochi", "Kerala"),
    ("Indore", "Madhya Pradesh"), ("Nagpur", "Maharashtra"), ("Patna", "Bihar"),
    ("Bhopal", "Madhya Pradesh"), ("Visakhapatnam", "Andhra Pradesh"), ("Surat", "Gujarat")
]

CATEGORIES = [
    "Electronics", "Fashion", "Food & Dining", "Travel", "Entertainment",
    "Groceries", "Health & Wellness", "Education", "Utilities", "Home & Garden"
]

PAYMENT_METHODS = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Wallet"]
DEVICE_TYPES = ["Mobile", "Desktop", "Tablet"]
TXN_STATUS = ["Success", "Failed", "Refunded"]

REVIEW_TEMPLATES = {
    1: [
        "Very poor experience with {merchant}. Worst {category} service ever.",
        "Extremely disappointed with {merchant}. Would not recommend.",
        "Terrible quality at {merchant}. Never going back."
    ],
    2: [
        "Below average experience at {merchant}. Needs improvement in {category}.",
        "Not satisfied with {merchant}. Service was slow.",
        "Disappointed with the {category} purchase from {merchant}."
    ],
    3: [
        "Average experience at {merchant}. Nothing special about their {category}.",
        "Okayish service at {merchant}. Met basic expectations.",
        "Decent {category} products at {merchant}, but overpriced."
    ],
    4: [
        "Good experience with {merchant}. Liked their {category} collection.",
        "Satisfied with {merchant}. Would recommend for {category}.",
        "Nice service and quality at {merchant}."
    ],
    5: [
        "Excellent experience at {merchant}! Best {category} store in {city}.",
        "Absolutely loved {merchant}! Outstanding {category} service.",
        "Amazing quality and fast delivery from {merchant}. Highly recommend!"
    ]
}

TICKET_ISSUES = ["Payment Failed", "Refund Issue", "Fraud Alert", "Account Access", "General Query"]
TICKET_TEMPLATES = {
    "Payment Failed": "My payment of Rs. {amount} failed on {date} but amount was deducted from account.",
    "Refund Issue": "Waiting for refund of Rs. {amount} for transaction dated {date}. It's been {days} days.",
    "Fraud Alert": "I did not authorize a transaction of Rs. {amount} on {date}. Please investigate immediately.",
    "Account Access": "Unable to login to my account. Getting authentication error since {date}.",
    "General Query": "Question about cashback offers and reward points for my recent purchases."
}


# =============================================================================
# GENERATORS
# =============================================================================

def generate_customers(n_customers, random_state=42):
    """
    Generates customer profiles with spatial coordinates and statistical
    transaction behaviour (preserving the original notebook concepts).
    """
    rng = np.random.default_rng(random_state)
    customer_ids = [f"CUST{i:05d}" for i in range(n_customers)]

    # Spatial coordinates (0-100 grid)
    coords = rng.uniform(0, 100, size=(n_customers, 2))

    # Transaction amount distribution per customer
    mean_amounts = rng.uniform(5, 1000, size=n_customers)
    std_amounts = mean_amounts / rng.uniform(1.5, 3.0, size=n_customers)
    mean_nb_tx_per_day = rng.uniform(0, 4, size=n_customers)

    # Geographic & demographic attributes
    city_state_choices = [INDIAN_CITIES[i % len(INDIAN_CITIES)]
                          for i in rng.integers(0, len(INDIAN_CITIES), size=n_customers)]

    today = datetime.today()
    reg_dates = [today - timedelta(days=int(d))
                 for d in rng.integers(30, 1095, size=n_customers)]

    records = []
    for i in range(n_customers):
        records.append({
            "customer_id": customer_ids[i],
            "customer_name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number()[:15],
            "city": city_state_choices[i][0],
            "state": city_state_choices[i][1],
            "x_customer_id": round(coords[i, 0], 6),
            "y_customer_id": round(coords[i, 1], 6),
            "mean_amount": round(mean_amounts[i], 2),
            "std_amount": round(std_amounts[i], 2),
            "mean_nb_tx_per_day": round(mean_nb_tx_per_day[i], 4),
            "registration_date": reg_dates[i].strftime("%Y-%m-%d"),
            "device_preference": rng.choice(DEVICE_TYPES, p=[0.60, 0.30, 0.10])
        })

    return pd.DataFrame(records)


def generate_merchants(n_merchants, random_state=42):
    """
    Generates merchant (formerly 'terminal') profiles with spatial coordinates,
    category, risk score and operational attributes.
    """
    rng = np.random.default_rng(random_state)
    merchant_ids = [f"MER{i:05d}" for i in range(n_merchants)]

    coords = rng.uniform(0, 100, size=(n_merchants, 2))
    city_state_choices = [INDIAN_CITIES[i % len(INDIAN_CITIES)]
                          for i in rng.integers(0, len(INDIAN_CITIES), size=n_merchants)]
    categories = rng.choice(CATEGORIES, size=n_merchants)
    risk_scores = rng.integers(10, 95, size=n_merchants)

    today = datetime.today()
    reg_dates = [today - timedelta(days=int(d))
                 for d in rng.integers(60, 1825, size=n_merchants)]

    records = []
    for i in range(n_merchants):
        records.append({
            "merchant_id": merchant_ids[i],
            "merchant_name": fake.company(),
            "category": categories[i],
            "city": city_state_choices[i][0],
            "state": city_state_choices[i][1],
            "x_merchant_id": round(coords[i, 0], 6),
            "y_merchant_id": round(coords[i, 1], 6),
            "risk_score": int(risk_scores[i]),
            "registration_date": reg_dates[i].strftime("%Y-%m-%d"),
            "avg_transaction_value": round(rng.uniform(50, 2000), 2),
            "status": rng.choice(["Active", "Inactive"], p=[0.90, 0.10])
        })

    return pd.DataFrame(records)


def generate_transactions(customers_df, merchants_df, n_transactions,
                          start_date, end_date, random_state=42):
    """
    Generates the main fact table linking customers and merchants.
    Applies heuristic fraud scoring and preserves spatial distance logic.
    """
    rng = np.random.default_rng(random_state)
    n_cust = len(customers_df)
    n_merch = len(merchants_df)

    # Extract numpy arrays for speed
    cust_ids = customers_df["customer_id"].values
    cust_mean = customers_df["mean_amount"].values.astype(np.float64)
    cust_std = customers_df["std_amount"].values.astype(np.float64)
    cust_tx_rate = customers_df["mean_nb_tx_per_day"].values.astype(np.float64)
    cust_x = customers_df["x_customer_id"].values.astype(np.float64)
    cust_y = customers_df["y_customer_id"].values.astype(np.float64)

    merch_ids = merchants_df["merchant_id"].values
    merch_x = merchants_df["x_merchant_id"].values.astype(np.float64)
    merch_y = merchants_df["y_merchant_id"].values.astype(np.float64)
    merch_cat = merchants_df["category"].values
    merch_city = merchants_df["city"].values
    merch_state = merchants_df["state"].values
    merch_risk = merchants_df["risk_score"].values.astype(np.float64)

    # Select customers weighted by daily transaction rate
    weights = cust_tx_rate / cust_tx_rate.sum()
    cust_indices = rng.choice(n_cust, size=n_transactions, p=weights)

    # Draw transaction amounts from customer-specific normal distribution
    amounts = rng.normal(cust_mean[cust_indices], cust_std[cust_indices])
    amounts = np.clip(amounts, 1.0, None)

    # Random merchant for each transaction
    merch_indices = rng.integers(0, n_merch, size=n_transactions)

    # Spatial distance (fraud / feature engineering)
    distances = np.sqrt(
        (cust_x[cust_indices] - merch_x[merch_indices]) ** 2 +
        (cust_y[cust_indices] - merch_y[merch_indices]) ** 2
    )

    # Timestamps uniformly across range (can be enriched with hourly weights later)
    total_seconds = int((end_date - start_date).total_seconds())
    random_seconds = rng.integers(0, total_seconds, size=n_transactions)
    timestamps = [start_date + timedelta(seconds=int(s)) for s in random_seconds]
    hours = np.array([t.hour for t in timestamps])

    # -------------------------------------------------------------------------
    # Fraud heuristics (ground-truth labels + engineered features)
    # -------------------------------------------------------------------------
    high_amount = amounts > 3 * cust_mean[cust_indices]
    midnight_txn = (hours >= 0) & (hours <= 4)
    far_distance = distances > 50.0
    high_risk_merchant = merch_risk[merch_indices] > 70
    random_noise = rng.random(n_transactions) < 0.005

    fraud_score = (
        high_amount * 0.30 +
        midnight_txn * 0.20 +
        far_distance * 0.25 +
        high_risk_merchant * 0.15 +
        random_noise * 0.10
    )
    fraud_score = np.clip(fraud_score, 0.0, 1.0)

    # Ground-truth fraud label: exactly top ~1.5 % by score
    fraud_target = max(1, int(0.015 * n_transactions))
    top_fraud_indices = np.argpartition(fraud_score, -fraud_target)[-fraud_target:]
    is_fraud = np.zeros(n_transactions, dtype=bool)
    is_fraud[top_fraud_indices] = True

    risk_levels = np.where(
        fraud_score < 0.20, "Low",
        np.where(fraud_score < 0.45, "Medium", "High")
    )

    # Transaction status
    status_probs_normal = np.array([0.92, 0.06, 0.02])
    status_probs_fraud = np.array([0.30, 0.50, 0.20])
    statuses = []
    for i in range(n_transactions):
        probs = status_probs_fraud if is_fraud[i] else status_probs_normal
        statuses.append(rng.choice(TXN_STATUS, p=probs))

    # Payment method & device
    payment_methods = rng.choice(
        PAYMENT_METHODS, size=n_transactions, p=[0.35, 0.25, 0.25, 0.10, 0.05]
    )
    devices = rng.choice(DEVICE_TYPES, size=n_transactions, p=[0.65, 0.25, 0.10])

    # Build records in chunks for progress feedback
    records = []
    chunk_size = 100_000
    for chunk_start in range(0, n_transactions, chunk_size):
        chunk_end = min(chunk_start + chunk_size, n_transactions)
        for i in range(chunk_start, chunk_end):
            ts = timestamps[i]
            records.append({
                "transaction_id": f"TXN{i + 1:09d}",
                "customer_id": cust_ids[cust_indices[i]],
                "merchant_id": merch_ids[merch_indices[i]],
                "amount": round(amounts[i], 2),
                "payment_method": payment_methods[i],
                "category": merch_cat[merch_indices[i]],
                "city": merch_city[merch_indices[i]],
                "state": merch_state[merch_indices[i]],
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "status": statuses[i],
                "device_type": devices[i],
                "is_fraud": int(is_fraud[i]),
                "fraud_score": round(fraud_score[i], 4),
                "risk_level": risk_levels[i],
                "transaction_hour": ts.hour,
                "weekend_flag": int(ts.weekday() >= 5),
                "customer_merchant_distance": round(distances[i], 2)
            })
        print(f"       Chunk {chunk_end:,} / {n_transactions:,} written")

    return pd.DataFrame(records)


def generate_reviews(transactions_df, merchants_df, n_reviews, random_state=42):
    """Generates merchant reviews sampled from successful transactions."""
    rng = np.random.default_rng(random_state)
    success_txns = transactions_df[transactions_df["status"] == "Success"]
    if success_txns.empty:
        success_txns = transactions_df

    n = min(n_reviews, len(success_txns))
    sample = success_txns.sample(n=n, random_state=random_state).reset_index(drop=True)
    ratings = rng.integers(1, 6, size=n)

    merchant_map = merchants_df.set_index("merchant_id")["merchant_name"].to_dict()
    merchant_cat_map = merchants_df.set_index("merchant_id")["category"].to_dict()
    merchant_city_map = merchants_df.set_index("merchant_id")["city"].to_dict()

    records = []
    for i in range(n):
        mid = sample.at[i, "merchant_id"]
        rating = int(ratings[i])
        text = rng.choice(REVIEW_TEMPLATES[rating]).format(
            merchant=merchant_map.get(mid, "Unknown Merchant"),
            category=merchant_cat_map.get(mid, "General"),
            city=merchant_city_map.get(mid, "Unknown")
        )
        records.append({
            "review_id": f"REV{i + 1:06d}",
            "transaction_id": sample.at[i, "transaction_id"],
            "customer_id": sample.at[i, "customer_id"],
            "merchant_id": mid,
            "rating": rating,
            "review_text": text,
            "timestamp": sample.at[i, "timestamp"]
        })

    return pd.DataFrame(records)


def generate_support_tickets(customers_df, transactions_df, n_tickets,
                             start_date, end_date, random_state=42):
    """Generates support tickets with realistic issue descriptions."""
    rng = np.random.default_rng(random_state)
    n_cust = len(customers_df)
    cust_ids = customers_df["customer_id"].values

    cust_indices = rng.integers(0, n_cust, size=n_tickets)
    total_seconds = int((end_date - start_date).total_seconds())
    random_seconds = rng.integers(0, total_seconds, size=n_tickets)
    timestamps = [start_date + timedelta(seconds=int(s)) for s in random_seconds]
    issue_types = rng.choice(TICKET_ISSUES, size=n_tickets, p=[0.30, 0.25, 0.15, 0.15, 0.15])

    # Fast lookup: group transactions by customer
    grouped = transactions_df.groupby("customer_id")

    records = []
    for i in range(n_tickets):
        cid = cust_ids[cust_indices[i]]
        issue = issue_types[i]
        ts = timestamps[i]

        if cid in grouped.groups:
            cust_txns = grouped.get_group(cid)
            ref_txn = cust_txns.sample(1, random_state=random_state + i).iloc[0]
            amount = ref_txn["amount"]
            date_str = ref_txn["timestamp"][:10]
        else:
            amount = round(rng.uniform(50, 5000), 2)
            date_str = ts.strftime("%Y-%m-%d")

        days = rng.integers(1, 15)
        desc = TICKET_TEMPLATES[issue].format(amount=amount, date=date_str, days=days)

        records.append({
            "ticket_id": f"TKT{i + 1:06d}",
            "customer_id": cid,
            "issue_type": issue,
            "description": desc,
            "status": rng.choice(["Open", "Resolved", "Escalated"], p=[0.20, 0.65, 0.15]),
            "priority": rng.choice(["Low", "Medium", "High"], p=[0.30, 0.50, 0.20]),
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S")
        })

    return pd.DataFrame(records)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic payment analytics data.")
    parser.add_argument("--customers", type=int, default=50_000, help="Number of customers")
    parser.add_argument("--merchants", type=int, default=5_000, help="Number of merchants")
    parser.add_argument("--transactions", type=int, default=1_000_000, help="Number of transactions")
    parser.add_argument("--reviews", type=int, default=50_000, help="Number of reviews")
    parser.add_argument("--tickets", type=int, default=20_000, help="Number of support tickets")
    parser.add_argument("--output", type=str, default="../data", help="Output directory (relative to script)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(output_dir, exist_ok=True)

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 5, 10)

    print("=" * 60)
    print("Payment Analytics Data Simulator")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # 1. Customers
    # -------------------------------------------------------------------------
    print(f"\n[1/5] Generating {args.customers:,} customers...")
    customers = generate_customers(args.customers, random_state=args.seed)
    customers.to_csv(os.path.join(output_dir, "customers.csv"), index=False)
    print(f"       -> Saved customers.csv ({len(customers):,} rows)")

    # -------------------------------------------------------------------------
    # 2. Merchants
    # -------------------------------------------------------------------------
    print(f"\n[2/5] Generating {args.merchants:,} merchants...")
    merchants = generate_merchants(args.merchants, random_state=args.seed + 1)
    merchants.to_csv(os.path.join(output_dir, "merchants.csv"), index=False)
    print(f"       -> Saved merchants.csv ({len(merchants):,} rows)")

    # -------------------------------------------------------------------------
    # 3. Transactions
    # -------------------------------------------------------------------------
    print(f"\n[3/5] Generating {args.transactions:,} transactions...")
    transactions = generate_transactions(
        customers, merchants, args.transactions,
        start_date, end_date, random_state=args.seed + 2
    )
    transactions.to_csv(os.path.join(output_dir, "transactions.csv"), index=False)
    fraud_count = int(transactions["is_fraud"].sum())
    print(f"       -> Saved transactions.csv ({len(transactions):,} rows)")
    print(f"       -> Fraud rate: {fraud_count:,} ({100 * fraud_count / len(transactions):.2f}%)")

    # -------------------------------------------------------------------------
    # 4. Reviews
    # -------------------------------------------------------------------------
    print(f"\n[4/5] Generating {args.reviews:,} reviews...")
    reviews = generate_reviews(transactions, merchants, args.reviews, random_state=args.seed + 3)
    reviews.to_csv(os.path.join(output_dir, "reviews.csv"), index=False)
    print(f"       -> Saved reviews.csv ({len(reviews):,} rows)")

    # -------------------------------------------------------------------------
    # 5. Support Tickets
    # -------------------------------------------------------------------------
    print(f"\n[5/5] Generating {args.tickets:,} support tickets...")
    tickets = generate_support_tickets(
        customers, transactions, args.tickets,
        start_date, end_date, random_state=args.seed + 4
    )
    tickets.to_csv(os.path.join(output_dir, "support_tickets.csv"), index=False)
    print(f"       -> Saved support_tickets.csv ({len(tickets):,} rows)")

    print("\n" + "=" * 60)
    print("All datasets generated successfully!")
    print(f"Output directory: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
