from typing import Optional

from fastapi import APIRouter, Query

from ..database import fetch, fetchrow, fetchval
from ..schemas import PaginatedResponse

router = APIRouter(tags=["customers"])


@router.get("/customers/segments")
async def customer_segments():
    rows = await fetch("""
        select
            case
                when total_spend >= 50000 and total_txns >= 100 then 'high_value'
                when total_txns >= 50 then 'frequent'
                when last_txn < current_date - interval '90 days' then 'dormant'
                when avg_txn_value >= 500 then 'luxury_spender'
                when unique_merchants >= 20 then 'diverse_shopper'
                else 'casual'
            end as segment,
            count(*) as customer_count,
            round(avg(total_spend)::numeric, 2) as avg_spend,
            round(avg(total_txns)::numeric, 1) as avg_transactions,
            sum(total_spend) as total_revenue
        from v_customer_summary
        group by segment
        order by avg_spend desc
    """)
    return [dict(r) for r in rows]


@router.get("/customers", response_model=PaginatedResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    city: Optional[str] = None,
    search: Optional[str] = None,
):
    where = []
    params = []

    if city:
        where.append(f"c.city = ${len(params) + 1}")
        params.append(city)
    if search:
        where.append(f"c.customer_name ilike ${len(params) + 1}")
        params.append(f"%{search}%")

    clause = "where " + " and ".join(where) if where else ""

    total = await fetchval(f"select count(*) from dim_customers c {clause}", *params)

    offset = (page - 1) * limit
    rows = await fetch(
        f"""
        select c.customer_id, c.customer_name, c.city, c.state,
               c.registration_date, c.device_preference,
               coalesce(v.total_txns, 0) as total_txns,
               coalesce(v.total_spend, 0) as total_spend,
               coalesce(v.avg_txn_value, 0) as avg_txn_value,
               v.last_txn,
               coalesce(v.unique_merchants, 0) as unique_merchants,
               coalesce(v.fraud_txn_count, 0) as fraud_txn_count
        from dim_customers c
        left join v_customer_summary v on c.customer_id = v.customer_id
        {clause}
        order by total_spend desc
        limit ${len(params) + 1} offset ${len(params) + 2}
        """,
        *params,
        limit,
        offset,
    )

    return PaginatedResponse(
        page=page, limit=limit, total=total or 0, results=[dict(r) for r in rows]
    )


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    row = await fetchrow(
        """
        select c.*, v.total_txns, v.total_spend, v.avg_txn_value,
               v.last_txn, v.unique_merchants, v.fraud_txn_count
        from dim_customers c
        left join v_customer_summary v on c.customer_id = v.customer_id
        where c.customer_id = $1
        """,
        customer_id,
    )
    if not row:
        return {"detail": "not found"}

    recent_txns = await fetch(
        """
        select t.*, m.merchant_name
        from fact_transactions t
        join dim_merchants m on t.merchant_id = m.merchant_id
        where t.customer_id = $1
        order by t.timestamp desc
        limit 20
        """,
        customer_id,
    )

    monthly = await fetch(
        """
        select date_trunc('month', timestamp)::date as month,
               count(*) as transactions,
               sum(amount) filter (where status = 'Success') as spend,
               count(*) filter (where is_fraud = 1) as fraud_count
        from fact_transactions
        where customer_id = $1
        group by date_trunc('month', timestamp)
        order by month
        """,
        customer_id,
    )

    return {
        **dict(row),
        "recent_transactions": [dict(r) for r in recent_txns],
        "monthly_spend": [dict(r) for r in monthly],
    }
