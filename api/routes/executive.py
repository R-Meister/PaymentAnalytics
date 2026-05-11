from fastapi import APIRouter

from ..database import fetch, fetchrow, fetchval
from ..schemas import ExecutiveSummaryOut

router = APIRouter(tags=["executive"])


@router.get("/executive/summary")
async def executive_summary():
    total_txn = await fetchval("select count(*) from fact_transactions")
    total_rev = await fetchval(
        "select coalesce(sum(amount), 0) from fact_transactions where status = 'Success'"
    )
    total_cust = await fetchval("select count(*) from dim_customers")
    total_merch = await fetchval("select count(*) from dim_merchants where status = 'Active'")
    fraud_cnt = await fetchval("select count(*) from fact_transactions where is_fraud = 1")
    fraud_amt = await fetchval(
        "select coalesce(sum(amount), 0) from fact_transactions where is_fraud = 1"
    )
    success_rate = await fetchval(
        "select round(count(*) filter (where status = 'Success') * 100.0 / count(*), 2) from fact_transactions"
    )

    today = await fetchrow(
        """
        select coalesce(sum(amount) filter (where status = 'Success'), 0) as revenue,
               count(*) as transactions,
               count(*) filter (where is_fraud = 1) as fraud
        from fact_transactions
        where timestamp::date = current_date
        """
    )

    daily_trend = await fetch(
        """
        select timestamp::date as date,
               count(*) as transactions,
               coalesce(sum(amount), 0) as revenue,
               count(*) filter (where status = 'Success') as success,
               count(*) filter (where status = 'Failed') as failed,
               count(*) filter (where is_fraud = 1) as fraud
        from fact_transactions
        where timestamp >= current_date - interval '30 days'
        group by timestamp::date
        order by date
        """
    )

    payment_dist = await fetch(
        """
        select payment_method,
               count(*) as txn_count,
               coalesce(sum(amount), 0) as total_amount,
               round(count(*) * 100.0 / (select count(*) from fact_transactions where status = 'Success'), 2) as percentage
        from fact_transactions
        where status = 'Success'
        group by payment_method
        order by txn_count desc
        """
    )

    category_dist = await fetch(
        """
        select category,
               count(*) as txn_count,
               coalesce(sum(amount), 0) as revenue
        from fact_transactions
        where status = 'Success'
        group by category
        order by revenue desc
        """
    )

    kpis = [
        {"label": "Total Revenue", "value": float(total_rev or 0), "prefix": "₹", "suffix": None},
        {"label": "Transactions", "value": total_txn or 0, "prefix": None, "suffix": None},
        {"label": "Active Customers", "value": total_cust or 0, "prefix": None, "suffix": None},
        {"label": "Active Merchants", "value": total_merch or 0, "prefix": None, "suffix": None},
        {"label": "Fraud Count", "value": fraud_cnt or 0, "prefix": None, "suffix": None},
        {"label": "Fraud Amount", "value": float(fraud_amt or 0), "prefix": "₹", "suffix": None},
        {"label": "Success Rate", "value": float(success_rate or 0), "prefix": None, "suffix": "%"},
        {"label": "Fraud Rate", "value": round(fraud_cnt / total_txn * 100, 2) if total_txn else 0, "prefix": None, "suffix": "%"},
    ]

    return {
        "total_transactions": total_txn,
        "total_revenue": float(total_rev or 0),
        "total_customers": total_cust,
        "total_merchants": total_merch,
        "fraud_count": fraud_cnt,
        "fraud_amount": float(fraud_amt or 0),
        "fraud_rate": round(fraud_cnt / total_txn * 100, 2) if total_txn else 0,
        "today": {
            "revenue": float(today["revenue"] or 0) if today else 0,
            "transactions": today["transactions"] if today else 0,
            "fraud": today["fraud"] if today else 0,
        },
        "kpis": kpis,
        "payment_distribution": [dict(r) for r in payment_dist],
        "category_distribution": [dict(r) for r in category_dist],
        "daily_trend": [dict(r) for r in daily_trend],
    }
