from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RecentInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    vendor_id: int
    invoice_date: date
    total_amount: Decimal
    status: str


class DashboardResponse(BaseModel):
    total_invoices: int

    invoice_status_counts: dict[str, int]

    total_payments: int

    payment_status_counts: dict[str, int]

    completed_payment_total: Decimal

    unread_notifications: int

    recent_invoices: list[RecentInvoiceResponse]