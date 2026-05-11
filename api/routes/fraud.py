from typing import Optional

from fastapi import APIRouter, Query

from ..database import fetch, fetchval
from ..schemas import PaginatedResponse

router = APIRouter(tags=["fraud"])


@router.get("/fraud/alerts", response_model=PaginatedResponse)
async def fraud_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    risk_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    where = []
    params = []

    if risk_level:
        where.append(f"risk_level = ${len(params) + 1}")
        params.append(risk_level)
    if date_from:
        where.append(f"timestamp >= ${len(params) + 1}")
        params.append(date_from)
    if date_to:
        where.append(f"timestamp <= ${len(params) + 1}")
        params.append(date_to)

    clause = "where " + " and ".join(where) if where else ""

    total = await fetchval(f"select count(*) from v_fraud_alerts {clause}", *params)

    offset = (page - 1) * limit
    rows = await fetch(
        f"""
        select * from v_fraud_alerts
        {clause}
        order by timestamp desc
        limit ${len(params) + 1} offset ${len(params) + 2}
        """,
        *params,
        limit,
        offset,
    )

    return PaginatedResponse(
        page=page, limit=limit, total=total or 0, results=[dict(r) for r in rows]
    )


@router.get("/fraud/summary")
async def fraud_summary():
    total_txn = await fetchval("select count(*) from fact_transactions")
    fraud_txn = await fetchval("select count(*) from fact_transactions where is_fraud = 1")
    fraud_amount = await fetchval("select coalesce(sum(amount), 0) from fact_transactions where is_fraud = 1")
    total_amount = await fetchval("select coalesce(sum(amount), 0) from fact_transactions")

    high = await fetchval("select count(*) from fact_transactions where risk_level = 'High'")
    medium = await fetchval("select count(*) from fact_transactions where risk_level = 'Medium'")
    low = await fetchval("select count(*) from fact_transactions where risk_level = 'Low'")

    by_hour = await fetch("""
        select transaction_hour, count(*) as fraud_count, sum(amount) as fraud_amount
        from fact_transactions
        where is_fraud = 1
        group by transaction_hour
        order by transaction_hour
    """)

    by_category = await fetch("""
        select category, count(*) as fraud_count, sum(amount) as fraud_amount
        from fact_transactions
        where is_fraud = 1
        group by category
        order by fraud_count desc
    """)

    daily = await fetch("""
        select timestamp::date as date,
               count(*) as fraud_count,
               sum(amount) as fraud_amount
        from fact_transactions
        where is_fraud = 1
          and timestamp >= current_date - interval '30 days'
        group by timestamp::date
        order by date
    """)

    return {
        "fraud_transactions": fraud_txn,
        "fraud_amount": float(fraud_amount or 0),
        "fraud_rate": round(fraud_txn / total_txn * 100, 2) if total_txn else 0,
        "fraud_amount_pct": round(fraud_amount / total_amount * 100, 2) if total_amount else 0,
        "risk_distribution": {"high": high, "medium": medium, "low": low},
        "fraud_by_hour": [dict(r) for r in by_hour],
        "fraud_by_category": [dict(r) for r in by_category],
        "daily_trend": [dict(r) for r in daily],
    }
