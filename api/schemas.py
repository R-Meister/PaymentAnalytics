from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TransactionOut(BaseModel):
    transaction_id: str
    customer_id: str
    merchant_id: str
    customer_name: Optional[str] = None
    merchant_name: Optional[str] = None
    amount: float
    payment_method: str
    category: str
    city: str
    state: str
    timestamp: datetime
    status: str
    device_type: str
    is_fraud: int
    fraud_score: float
    risk_level: str
    transaction_hour: int
    weekend_flag: int
    customer_merchant_distance: Optional[float] = None


class PaginatedResponse(BaseModel):
    page: int
    limit: int
    total: int
    results: list[dict]


class MerchantOut(BaseModel):
    merchant_id: str
    merchant_name: str
    category: str
    city: str
    state: str
    risk_score: int
    status: str
    avg_transaction_value: float
    registration_date: Optional[date] = None


class MerchantDetailOut(MerchantOut):
    total_txns: int = 0
    revenue: float = 0.0
    unique_customers: int = 0
    fraud_pct: float = 0.0
    refund_pct: float = 0.0


class FraudAlertOut(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount: float
    payment_method: str
    category: str
    city: str
    status: str
    device_type: str
    fraud_score: float
    risk_level: str
    customer_merchant_distance: Optional[float] = None
    transaction_hour: int
    weekend_flag: int
    customer_name: str
    customer_device: Optional[str] = None
    merchant_name: str
    merchant_risk_score: int


class CustomerSummaryOut(BaseModel):
    customer_id: str
    customer_name: str
    city: str
    state: str
    registration_date: Optional[date] = None
    device_preference: str
    total_txns: int
    total_spend: float
    avg_txn_value: float
    last_txn: Optional[datetime] = None
    unique_merchants: int
    fraud_txn_count: int


class KpiCard(BaseModel):
    label: str
    value: float | int
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class TrendPoint(BaseModel):
    date: str
    transactions: int
    revenue: float
    success: int
    failed: int
    fraud: int


class ExecutiveSummaryOut(BaseModel):
    total_transactions: int
    total_revenue: float
    total_customers: int
    total_merchants: int
    fraud_count: int
    fraud_amount: float
    fraud_rate: float
    today: dict
    kpis: list[KpiCard]
    payment_distribution: list[dict]
    category_distribution: list[dict]
    daily_trend: list[dict]
