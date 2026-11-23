from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db

from app.dependencies.auth import (
    ensure_vendor_access,
    get_current_user,
    require_roles,
)

from app.models.ai_invoice_analysis import (
    AIInvoiceAnalysis,
)
from app.models.document import Document
from app.models.invoice import Invoice
from app.models.user import User

from app.schemas.ai_analysis import (
    AIAnalysisRequest,
    AIInvoiceAnalysisResponse,
)

from app.services.document_ai_extraction import (
    extract_invoice_document,
)

from app.services.invoice_analysis import (
    analyze_invoice_rules,
    compare_extracted_invoice,
)


router = APIRouter(
    prefix="/api/ai/invoices",
    tags=["AI Invoice Analysis"],
)


@router.post(
    "/{invoice_id}/analyze",
    response_model=AIInvoiceAnalysisResponse,
)
def analyze_invoice(
    invoice_id: int,
    payload: AIAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "staff",
            "manager",
            "admin",
        )
    ),
):
    invoice = db.get(
        Invoice,
        invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    if (
        invoice.nonprofit_id
        != current_user.nonprofit_id
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have access "
                "to this invoice"
            ),
        )

    document = None

    if payload.source_document_id:
        document = db.get(
            Document,
            payload.source_document_id,
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        if (
            document.invoice_id
            != invoice.id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Document does not belong "
                    "to this invoice"
                ),
            )

    result = analyze_invoice_rules(
        db,
        invoice,
    )

    ai_extraction = None
    document_mismatches: list[str] = []

    if document is not None:
        try:
            ai_extraction = (
                extract_invoice_document(
                    document
                )
            )

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            )

        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            )

        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI document extraction "
                    f"failed: {str(exc)}"
                ),
            )

        document_mismatches = (
            compare_extracted_invoice(
                invoice,
                ai_extraction,
            )
        )

        if document_mismatches:
            result["risk_reasons"].extend(
                document_mismatches
            )

            if (
                result["risk_level"]
                == "low_risk"
            ):
                result["risk_level"] = (
                    "needs_review"
                )

        result["extracted_data"] = {
            "source":
                "ai_document_extraction",

            "document_id":
                document.id,

            "document":
                ai_extraction.model_dump(),

            "system_record":
                result["extracted_data"],

            "mismatches":
                document_mismatches,
        }

    analysis = db.scalar(
        select(
            AIInvoiceAnalysis
        ).where(
            AIInvoiceAnalysis.invoice_id
            == invoice.id
        )
    )

    if analysis is None:
        analysis = AIInvoiceAnalysis(
            invoice_id=invoice.id,

            analyzed_by_user_id=
                current_user.id,

            source_document_id=(
                document.id
                if document
                else None
            ),

            analysis_status="completed",

            completeness_score=
                result[
                    "completeness_score"
                ],

            missing_fields=
                result[
                    "missing_fields"
                ],

            duplicate_risk=
                result[
                    "duplicate_risk"
                ],

            possible_duplicate_invoice_id=
                result[
                    "possible_duplicate_invoice_id"
                ],

            risk_level=
                result[
                    "risk_level"
                ],

            risk_reasons=
                result[
                    "risk_reasons"
                ],

            extracted_data=
                result[
                    "extracted_data"
                ],

            analysis_version=(
                "local_document_v1"
                if ai_extraction
                else "rules_v1"
            ),
        )

        db.add(analysis)

    else:
        analysis.analyzed_by_user_id = (
            current_user.id
        )

        analysis.source_document_id = (
            document.id
            if document
            else None
        )

        analysis.analysis_status = (
            "completed"
        )

        analysis.completeness_score = (
            result[
                "completeness_score"
            ]
        )

        analysis.missing_fields = (
            result[
                "missing_fields"
            ]
        )

        analysis.duplicate_risk = (
            result[
                "duplicate_risk"
            ]
        )

        analysis.possible_duplicate_invoice_id = (
            result[
                "possible_duplicate_invoice_id"
            ]
        )

        analysis.risk_level = (
            result[
                "risk_level"
            ]
        )

        analysis.risk_reasons = (
            result[
                "risk_reasons"
            ]
        )

        analysis.extracted_data = (
            result[
                "extracted_data"
            ]
        )

        analysis.analysis_version = (
            "local_document_v1"
            if ai_extraction
            else "rules_v1"
        )

    db.commit()
    db.refresh(analysis)

    return analysis
@router.get(
    "/{invoice_id}/analysis",
    response_model=AIInvoiceAnalysisResponse,
)
def get_invoice_analysis(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    invoice = db.get(
        Invoice,
        invoice_id,
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    ensure_vendor_access(
        current_user,
        invoice.vendor_id,
        invoice.nonprofit_id,
    )

    analysis = db.scalar(
        select(
            AIInvoiceAnalysis
        ).where(
            AIInvoiceAnalysis.invoice_id
            == invoice.id
        )
    )

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=(
                "AI analysis has not "
                "been run for this invoice"
            ),
        )

    return analysis