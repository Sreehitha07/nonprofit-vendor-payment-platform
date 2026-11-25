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

from app.services.invoice_policy_rag import (
    retrieve_invoice_policy_evidence,
)

from app.services.invoice_agent_graph import (
    run_invoice_agent,
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
    # ---------------------------------------------------------
    # 1. LOAD AND AUTHORIZE INVOICE
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 2. LOAD OPTIONAL SOURCE DOCUMENT
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 3. RUN LOCAL DETERMINISTIC ANALYSIS
    #
    # Day 16:
    # - completeness
    # - duplicate detection
    # - risk rules
    # ---------------------------------------------------------

    result = analyze_invoice_rules(
        db,
        invoice,
    )

    ai_extraction = None

    document_mismatches: list[str] = []

    # ---------------------------------------------------------
    # 4. RUN LOCAL DOCUMENT EXTRACTION
    # ---------------------------------------------------------

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

        # Add document mismatches to the
        # deterministic risk analysis.
        if document_mismatches:
            result[
                "risk_reasons"
            ].extend(
                document_mismatches
            )

            if (
                result["risk_level"]
                == "low_risk"
            ):
                result["risk_level"] = (
                    "needs_review"
                )

    # ---------------------------------------------------------
    # 5. RUN LOCAL RAG POLICY RETRIEVAL
    #
    # This happens after document comparison so the RAG query
    # receives the final risk/mismatch context.
    # ---------------------------------------------------------

    policy_evidence = (
        retrieve_invoice_policy_evidence(
            db=db,
            nonprofit_id=(
                current_user.nonprofit_id
            ),
            invoice=invoice,
            analysis_result=result,
            limit=5,
        )
    )

    # ---------------------------------------------------------
    # 6. BUILD EXPLAINABLE ANALYSIS PAYLOAD
    # ---------------------------------------------------------

    if ai_extraction:
        system_record = dict(
            result[
                "extracted_data"
            ]
        )

        result["extracted_data"] = {
            "source":
                "local_document_extraction",

            "document_id":
                document.id,

            "document":
                ai_extraction.model_dump(),

            "system_record":
                system_record,

            "mismatches":
                document_mismatches,

            "policy_evidence":
                policy_evidence,
        }

    else:
        system_record = dict(
            result[
                "extracted_data"
            ]
        )

        result["extracted_data"] = {
            "source":
                "rules_analysis",

            "system_record":
                system_record,

            "mismatches":
                [],

            "policy_evidence":
                policy_evidence,
        }

    # ---------------------------------------------------------
    # 7. RUN LANGGRAPH AGENTIC WORKFLOW
    #
    # Day 18:
    #
    # Analysis
    #   -> Completeness
    #   -> Risk
    #   -> Policy context
    #   -> Recommendation
    #   -> Human review guardrail
    #
    # IMPORTANT:
    # The agent never approves, rejects, or pays an invoice.
    # ---------------------------------------------------------

    try:
        agent_result = run_invoice_agent(
            invoice_id=invoice.id,
            analysis_result=result,
            policy_evidence=policy_evidence,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Agentic invoice analysis "
                f"failed: {str(exc)}"
            ),
        )

    # Only store the useful agent-facing output.
    #
    # We intentionally do not store the entire LangGraph
    # internal state because it would duplicate the complete
    # analysis payload and policy evidence.

    agent_output = {
        "recommendation":
            agent_result.get(
                "recommendation",
                "needs_review",
            ),

        "recommendation_reasons":
            agent_result.get(
                "recommendation_reasons",
                [],
            ),

        "completeness_status":
            agent_result.get(
                "completeness_status",
                "needs_review",
            ),

        "policy_context_available":
            agent_result.get(
                "policy_context_available",
                False,
            ),

        "policy_evidence_count":
            agent_result.get(
                "policy_evidence_count",
                0,
            ),

        "human_review_required":
            agent_result.get(
                "human_review_required",
                True,
            ),

        "final_decision_allowed":
            agent_result.get(
                "final_decision_allowed",
                False,
            ),

        "agent_trace":
            agent_result.get(
                "agent_trace",
                [],
            ),
    }

    result[
        "extracted_data"
    ][
        "agent"
    ] = agent_output

    # ---------------------------------------------------------
    # 8. SAVE / UPDATE ANALYSIS
    # ---------------------------------------------------------

    analysis = db.scalar(
        select(
            AIInvoiceAnalysis
        ).where(
            AIInvoiceAnalysis.invoice_id
            == invoice.id
        )
    )

    analysis_version = (
        "local_document_agentic_rag_v1"
        if ai_extraction
        else "rules_agentic_rag_v1"
    )

    if analysis is None:
        analysis = AIInvoiceAnalysis(
            invoice_id=invoice.id,

            analyzed_by_user_id=(
                current_user.id
            ),

            source_document_id=(
                document.id
                if document
                else None
            ),

            analysis_status=(
                "completed"
            ),

            completeness_score=(
                result[
                    "completeness_score"
                ]
            ),

            missing_fields=(
                result[
                    "missing_fields"
                ]
            ),

            duplicate_risk=(
                result[
                    "duplicate_risk"
                ]
            ),

            possible_duplicate_invoice_id=(
                result[
                    "possible_duplicate_invoice_id"
                ]
            ),

            risk_level=(
                result[
                    "risk_level"
                ]
            ),

            risk_reasons=(
                result[
                    "risk_reasons"
                ]
            ),

            extracted_data=(
                result[
                    "extracted_data"
                ]
            ),

            analysis_version=(
                analysis_version
            ),
        )

        db.add(
            analysis
        )

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
            analysis_version
        )

    db.commit()
    db.refresh(
        analysis
    )

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