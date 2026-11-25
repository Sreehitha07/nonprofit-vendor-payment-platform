from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class RecentInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    vendor_id: int
    invoice_date: date
    total_amount: Decimal
    status: str


class AIPriorityInvoiceResponse(BaseModel):
    invoice_id: int
    invoice_number: str

    vendor_id: int
    vendor_name: str

    total_amount: Decimal
    currency: str

    invoice_status: str

    completeness_score: float

    risk_level: str
    duplicate_risk: bool

    recommendation: str

    analysis_updated_at: datetime


class AIReviewSummaryResponse(BaseModel):
    analyzed_invoices: int

    recommendation_counts: dict[str, int]

    duplicate_risks: int

    high_attention_risks: int

    average_completeness_score: float

    policy_grounded_reviews: int

    priority_invoices: list[AIPriorityInvoiceResponse]


class DashboardResponse(BaseModel):
    total_invoices: int

    invoice_status_counts: dict[str, int]

    total_payments: int

    payment_status_counts: dict[str, int]

    completed_payment_total: Decimal

    unread_notifications: int

    recent_invoices: list[RecentInvoiceResponse]

    ai_review_summary: AIReviewSummaryResponse