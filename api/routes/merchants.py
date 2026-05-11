from typing import Optional

from fastapi import APIRouter, Query

from ..database import fetch, fetchrow, fetchval
from ..schemas import PaginatedResponse

router = APIRouter(tags=["merchants"])


@router.get("/merchants", response_model=PaginatedResponse)
async def list_merchants(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    where = []
    params = []

    if category:
        where.append(f"m.category = ${len(params) + 1}")
        params.append(category)
    if city:
        where.append(f"m.city = ${len(params) + 1}")
        params.append(city)
    if status:
        where.append(f"m.status = ${len(params) + 1}")
        params.append(status)
    if search:
        where.append(f"m.merchant_name ilike ${len(params) + 1}")
        params.append(f"%{search}%")

    clause = "where " + " and ".join(where) if where else ""

    total = await fetchval(f"select count(*) from dim_merchants m {clause}", *params)

    offset = (page - 1) * limit
    rows = await fetch(
        f"""
        select m.merchant_id, m.merchant_name, m.category, m.city, m.state,
               m.risk_score, m.status, m.avg_transaction_value, m.registration_date,
               coalesce(vp.total_txns, 0) as total_txns,
               coalesce(vp.revenue, 0) as revenue,
               coalesce(vp.unique_customers, 0) as unique_customers,
               coalesce(vp.fraud_pct, 0) as fraud_pct,
               coalesce(vp.refund_pct, 0) as refund_pct
        from dim_merchants m
        left join v_merchant_performance vp on m.merchant_id = vp.merchant_id
        {clause}
        order by revenue desc
        limit ${len(params) + 1} offset ${len(params) + 2}
        """,
        *params,
        limit,
        offset,
    )

    return PaginatedResponse(
        page=page, limit=limit, total=total or 0, results=[dict(r) for r in rows]
    )


@router.get("/merchants/{merchant_id}")
async def get_merchant(merchant_id: str):
    merchant = await fetchrow(
        "select * from dim_merchants where merchant_id = $1", merchant_id
    )
    if not merchant:
        return {"detail": "not found"}

    stats = await fetchrow(
        "select * from v_merchant_performance where merchant_id = $1", merchant_id
    )

    daily = await fetch(
        """
        select timestamp::date as date,
               count(*) as transactions,
               sum(amount) as revenue,
               count(*) filter (where status = 'Failed') as failed,
               count(*) filter (where is_fraud = 1) as fraud
        from fact_transactions
        where merchant_id = $1
          and timestamp >= current_date - interval '30 days'
        group by timestamp::date
        order by date
        """,
        merchant_id,
    )

    return {
        **dict(merchant),
        **(dict(stats) if stats else {}),
        "daily_trend": [dict(r) for r in daily],
    }


@router.get("/merchants/top/by-revenue")
async def top_merchants(
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = None,
):
    params = []
    cat_filter = ""
    if category:
        cat_filter = "where m.category = $1"
        params.append(category)

    params.append(limit)
    rows = await fetch(
        f"""
        select m.merchant_id, m.merchant_name, m.category, m.city,
               coalesce(vp.revenue, 0) as revenue,
               coalesce(vp.total_txns, 0) as total_txns,
               coalesce(vp.unique_customers, 0) as unique_customers,
               coalesce(vp.fraud_pct, 0) as fraud_pct
        from dim_merchants m
        left join v_merchant_performance vp on m.merchant_id = vp.merchant_id
        {cat_filter}
        order by revenue desc
        limit ${len(params)}
        """,
        *params,
    )
    return [dict(r) for r in rows]
