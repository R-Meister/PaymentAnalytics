from fastapi import APIRouter

from ..database import fetch

router = APIRouter(tags=["forecast"])


@router.get("/forecast")
async def get_forecasts():
    txn = await fetch(
        """
        SELECT forecast_date, forecast_value, lower_bound, upper_bound
        FROM ml_forecasts
        WHERE metric_name = 'transactions'
        ORDER BY forecast_date
        """
    )
    rev = await fetch(
        """
        SELECT forecast_date, forecast_value, lower_bound, upper_bound
        FROM ml_forecasts
        WHERE metric_name = 'revenue'
        ORDER BY forecast_date
        """
    )
    hist = await fetch(
        """
        SELECT timestamp::date as date,
               count(*) as transactions,
               sum(amount) filter (where status = 'Success') as revenue
        FROM fact_transactions
        WHERE timestamp >= current_date - interval '60 days'
        GROUP BY timestamp::date
        ORDER BY date
        """
    )

    return {
        "historical": [dict(r) for r in hist],
        "forecast_transactions": [dict(r) for r in txn],
        "forecast_revenue": [dict(r) for r in rev],
    }
