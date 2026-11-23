from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIInvoiceAnalysis(Base):
    __tablename__ = "ai_invoice_analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey(
            "invoices.id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    analyzed_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    analysis_status: Mapped[str] = mapped_column(
        String(50),
        default="completed",
        nullable=False,
    )

    completeness_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    missing_fields: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    duplicate_risk: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    possible_duplicate_invoice_id: Mapped[int | None] = (
        mapped_column(
            ForeignKey(
                "invoices.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        )
    )

    risk_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    risk_reasons: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    extracted_data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    analysis_version: Mapped[str] = mapped_column(
        String(50),
        default="rules_v1",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )