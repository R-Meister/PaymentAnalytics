from typing import Optional

from fastapi import APIRouter, Query

from ..database import fetch, fetchrow, fetchval
from ..schemas import PaginatedResponse, TransactionOut

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=PaginatedResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    payment_method: Optional[str] = None,
    is_fraud: Optional[int] = None,
    risk_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: Optional[str] = "timestamp",
    sort_order: Optional[str] = "desc",
):
    allowed_sort = {"timestamp", "amount", "status", "category", "risk_level"}
    col = sort_by if sort_by in allowed_sort else "timestamp"
    order = "desc" if sort_order == "desc" else "asc"

    where = []
    params = []

    if status:
        where.append(f"t.status = ${len(params) + 1}")
        params.append(status)
    if category:
        where.append(f"t.category = ${len(params) + 1}")
        params.append(category)
    if city:
        where.append(f"t.city = ${len(params) + 1}")
        params.append(city)
    if payment_method:
        where.append(f"t.payment_method = ${len(params) + 1}")
        params.append(payment_method)
    if is_fraud is not None:
        where.append(f"t.is_fraud = ${len(params) + 1}")
        params.append(is_fraud)
    if risk_level:
        where.append(f"t.risk_level = ${len(params) + 1}")
        params.append(risk_level)
    if date_from:
        where.append(f"t.timestamp >= ${len(params) + 1}")
        params.append(date_from)
    if date_to:
        where.append(f"t.timestamp <= ${len(params) + 1}")
        params.append(date_to)

    clause = "where " + " and ".join(where) if where else ""

    total = await fetchval(
        f"select count(*) from fact_transactions t {clause}", *params
    )

    offset = (page - 1) * limit
    rows = await fetch(
        f"""
        select t.*, c.customer_name, m.merchant_name
        from fact_transactions t
        join dim_customers c on t.customer_id = c.customer_id
        join dim_merchants m on t.merchant_id = m.merchant_id
        {clause}
        order by t.{col} {order}
        limit ${len(params) + 1} offset ${len(params) + 2}
        """,
        *params,
        limit,
        offset,
    )

    results = [dict(r) for r in rows]

    return PaginatedResponse(page=page, limit=limit, total=total or 0, results=results)


@router.get("/transactions/{txn_id}")
async def get_transaction(txn_id: str):
    row = await fetchrow(
        """
        select t.*, c.customer_name, m.merchant_name
        from fact_transactions t
        join dim_customers c on t.customer_id = c.customer_id
        join dim_merchants m on t.merchant_id = m.merchant_id
        where t.transaction_id = $1
        """,
        txn_id,
    )
    if not row:
        return {"detail": "not found"}
    return dict(row)


@router.get("/transactions/stats/summary")
async def transaction_stats():
    total = await fetchval("select count(*) from fact_transactions")
    total_revenue = await fetchval(
        "select coalesce(sum(amount), 0) from fact_transactions where status = 'Success'"
    )
    avg_amount = await fetchval(
        "select coalesce(avg(amount), 0) from fact_transactions where status = 'Success'"
    )
    success = await fetchval(
        "select count(*) from fact_transactions where status = 'Success'"
    )
    failed = await fetchval(
        "select count(*) from fact_transactions where status = 'Failed'"
    )
    refunded = await fetchval(
        "select count(*) from fact_transactions where status = 'Refunded'"
    )

    return {
        "total_transactions": total,
        "total_revenue": float(total_revenue or 0),
        "avg_transaction_value": float(avg_amount or 0),
        "success_rate": round(success / total * 100, 2) if total else 0,
        "failure_rate": round(failed / total * 100, 2) if total else 0,
        "refund_rate": round(refunded / total * 100, 2) if total else 0,
    }
