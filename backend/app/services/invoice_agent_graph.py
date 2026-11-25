from typing import Any, Literal, TypedDict

from langgraph.graph import (
    END,
    START,
    StateGraph,
)


class InvoiceAgentState(
    TypedDict,
    total=False,
):
    """
    Shared state for the invoice review agent.

    The graph generates recommendations only.
    Final financial decisions remain human-controlled.
    """

    invoice_id: int

    # Existing Day 16 / 17 analysis
    analysis_result: dict[str, Any]
    policy_evidence: list[dict[str, Any]]

    # Completeness
    completeness_score: int
    missing_fields: list[str]
    completeness_status: str

    # Risk
    duplicate_risk: bool
    possible_duplicate_invoice_id: int | None
    risk_level: str
    risk_reasons: list[str]

    # RAG
    policy_context_available: bool
    policy_evidence_count: int

    # Agent recommendation
    recommendation: str
    recommendation_reasons: list[str]

    # Human-in-the-loop guardrail
    human_review_required: bool
    final_decision_allowed: bool

    # Explainability
    agent_trace: list[str]


# ============================================================
# NODE 1
# ANALYSIS INTAKE
# ============================================================


def analysis_intake_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    analysis = state.get(
        "analysis_result",
        {},
    )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        "Loaded local invoice analysis."
    )

    return {
        "completeness_score": int(
            analysis.get(
                "completeness_score",
                0,
            )
            or 0
        ),

        "missing_fields": list(
            analysis.get(
                "missing_fields",
                [],
            )
            or []
        ),

        "duplicate_risk": bool(
            analysis.get(
                "duplicate_risk",
                False,
            )
        ),

        "possible_duplicate_invoice_id":
            analysis.get(
                "possible_duplicate_invoice_id"
            ),

        "risk_level": (
            analysis.get(
                "risk_level",
                "needs_review",
            )
            or "needs_review"
        ),

        "risk_reasons": list(
            analysis.get(
                "risk_reasons",
                [],
            )
            or []
        ),

        "agent_trace": trace,
    }


# ============================================================
# NODE 2
# COMPLETENESS
# ============================================================


def completeness_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    score = state.get(
        "completeness_score",
        0,
    )

    missing_fields = state.get(
        "missing_fields",
        [],
    )

    if missing_fields:
        status = "incomplete"

    elif score >= 100:
        status = "complete"

    else:
        status = "needs_review"

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Completeness check: "
            f"{status} ({score}%)."
        )
    )

    if status == "incomplete":
        trace.append(
            (
                "Routing: incomplete invoice "
                "-> document request path."
            )
        )

    else:
        trace.append(
            (
                "Routing: completeness passed "
                "-> risk review path."
            )
        )

    return {
        "completeness_status": status,
        "agent_trace": trace,
    }


# ============================================================
# ROUTER 1
# COMPLETENESS ROUTING
# ============================================================


def route_after_completeness(
    state: InvoiceAgentState,
) -> Literal[
    "risk_check",
    "policy_context",
]:
    """
    Incomplete invoices do not need another
    agent-level risk evaluation before being
    recommended for additional documentation.

    Complete / reviewable invoices continue
    through risk evaluation.
    """

    if (
        state.get(
            "completeness_status"
        )
        == "incomplete"
    ):
        return "policy_context"

    return "risk_check"


# ============================================================
# NODE 3
# RISK CHECK
# ============================================================


def risk_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    duplicate_risk = state.get(
        "duplicate_risk",
        False,
    )

    risk_level = state.get(
        "risk_level",
        "needs_review",
    )

    risk_reasons = list(
        state.get(
            "risk_reasons",
            [],
        )
    )

    if (
        duplicate_risk
        and (
            "Possible duplicate invoice "
            "detected."
        )
        not in risk_reasons
    ):
        risk_reasons.append(
            "Possible duplicate invoice detected."
        )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Risk check: "
            f"{risk_level}; "
            f"duplicate risk="
            f"{duplicate_risk}."
        )
    )

    return {
        "risk_reasons":
            risk_reasons,

        "agent_trace":
            trace,
    }


# ============================================================
# NODE 4
# POLICY RAG CONTEXT
# ============================================================


def policy_context_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    evidence = state.get(
        "policy_evidence",
        [],
    )

    evidence_count = len(
        evidence
    )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    if evidence_count > 0:
        trace.append(
            (
                "Policy RAG check: "
                f"{evidence_count} relevant "
                "policy chunk(s) available."
            )
        )

    else:
        trace.append(
            (
                "Policy RAG check: "
                "no sufficiently relevant "
                "policy evidence retrieved."
            )
        )

    return {
        "policy_context_available":
            evidence_count > 0,

        "policy_evidence_count":
            evidence_count,

        "agent_trace":
            trace,
    }


# ============================================================
# ROUTER 2
# RECOMMENDATION PATH
# ============================================================


def route_after_policy_context(
    state: InvoiceAgentState,
) -> Literal[
    "needs_documents_recommendation",
    "high_attention_recommendation",
    "standard_recommendation",
]:
    """
    Select the appropriate recommendation path.

    Priority:
    1. Missing information
    2. Duplicate / high attention
    3. Standard review
    """

    if (
        state.get(
            "completeness_status"
        )
        == "incomplete"
    ):
        return (
            "needs_documents_recommendation"
        )

    if (
        state.get(
            "duplicate_risk",
            False,
        )
        or state.get(
            "risk_level"
        )
        == "high_attention"
    ):
        return (
            "high_attention_recommendation"
        )

    return "standard_recommendation"


# ============================================================
# NODE 5A
# NEEDS DOCUMENTS RECOMMENDATION
# ============================================================


def needs_documents_recommendation_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    missing_fields = state.get(
        "missing_fields",
        [],
    )

    reasons = [
        (
            "Required invoice information "
            "or supporting documentation "
            "is missing."
        )
    ]

    if missing_fields:
        reasons.append(
            (
                "Missing fields: "
                + ", ".join(
                    str(field)
                    for field
                    in missing_fields
                )
                + "."
            )
        )

    if state.get(
        "policy_context_available",
        False,
    ):
        reasons.append(
            (
                "Relevant nonprofit policy "
                "evidence was retrieved for "
                "reviewer reference."
            )
        )

    else:
        reasons.append(
            (
                "No sufficiently relevant "
                "policy evidence was retrieved; "
                "manual policy verification "
                "may be needed."
            )
        )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Conditional route selected: "
            "needs documents."
        )
    )

    trace.append(
        (
            "Recommendation generated: "
            "needs_documents."
        )
    )

    return {
        "recommendation":
            "needs_documents",

        "recommendation_reasons":
            reasons,

        "agent_trace":
            trace,
    }


# ============================================================
# NODE 5B
# HIGH ATTENTION RECOMMENDATION
# ============================================================


def high_attention_recommendation_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    reasons: list[str] = []

    if state.get(
        "duplicate_risk",
        False,
    ):
        reasons.append(
            (
                "The invoice may duplicate "
                "an existing invoice."
            )
        )

    if (
        state.get(
            "risk_level"
        )
        == "high_attention"
    ):
        reasons.append(
            (
                "The deterministic risk "
                "analysis identified a "
                "high-attention condition."
            )
        )

    for reason in state.get(
        "risk_reasons",
        [],
    ):
        if reason not in reasons:
            reasons.append(
                str(reason)
            )

    if state.get(
        "policy_context_available",
        False,
    ):
        reasons.append(
            (
                "Relevant nonprofit policy "
                "evidence was retrieved for "
                "reviewer reference."
            )
        )

    else:
        reasons.append(
            (
                "No sufficiently relevant "
                "policy evidence was retrieved; "
                "manual policy verification "
                "may be needed."
            )
        )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Conditional route selected: "
            "high attention."
        )
    )

    trace.append(
        (
            "Recommendation generated: "
            "high_attention."
        )
    )

    return {
        "recommendation":
            "high_attention",

        "recommendation_reasons":
            reasons,

        "agent_trace":
            trace,
    }


# ============================================================
# NODE 5C
# STANDARD RECOMMENDATION
# ============================================================


def standard_recommendation_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    risk_level = state.get(
        "risk_level",
        "needs_review",
    )

    risk_reasons = state.get(
        "risk_reasons",
        [],
    )

    reasons: list[str] = []

    if risk_level == "needs_review":
        recommendation = (
            "needs_review"
        )

        reasons.append(
            (
                "The invoice contains "
                "conditions that should "
                "be reviewed manually."
            )
        )

    else:
        recommendation = (
            "low_risk"
        )

        reasons.append(
            (
                "No major automated "
                "risk signal was detected."
            )
        )

    for reason in risk_reasons:
        if reason not in reasons:
            reasons.append(
                str(reason)
            )

    if state.get(
        "policy_context_available",
        False,
    ):
        reasons.append(
            (
                "Relevant nonprofit policy "
                "evidence was retrieved for "
                "reviewer reference."
            )
        )

    else:
        reasons.append(
            (
                "No sufficiently relevant "
                "policy evidence was retrieved; "
                "manual policy verification "
                "may be needed."
            )
        )

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Conditional route selected: "
            "standard review."
        )
    )

    trace.append(
        (
            "Recommendation generated: "
            f"{recommendation}."
        )
    )

    return {
        "recommendation":
            recommendation,

        "recommendation_reasons":
            reasons,

        "agent_trace":
            trace,
    }


# ============================================================
# NODE 6
# HUMAN REVIEW BOUNDARY
# ============================================================


def human_review_node(
    state: InvoiceAgentState,
) -> dict[str, Any]:

    trace = list(
        state.get(
            "agent_trace",
            [],
        )
    )

    trace.append(
        (
            "Human review required before "
            "any final financial decision."
        )
    )

    return {
        "human_review_required":
            True,

        "final_decision_allowed":
            False,

        "agent_trace":
            trace,
    }


# ============================================================
# GRAPH
# ============================================================


def build_invoice_agent_graph():
    """
    Build the conditional LangGraph workflow.

    Flow:

    analysis
        ↓
    completeness
        ├─ incomplete ─────────────┐
        │                          ↓
        └─ complete/reviewable → risk
                                   ↓
                              policy context
                                   ↓
                        conditional recommendation
                         /          |          \
                needs docs     high attention   standard
                         \          |          /
                              human review
                                   ↓
                                  END
    """

    builder = StateGraph(
        InvoiceAgentState
    )

    builder.add_node(
        "analysis_intake",
        analysis_intake_node,
    )

    builder.add_node(
        "completeness_check",
        completeness_node,
    )

    builder.add_node(
        "risk_check",
        risk_node,
    )

    builder.add_node(
        "policy_context",
        policy_context_node,
    )

    builder.add_node(
        "needs_documents_recommendation",
        needs_documents_recommendation_node,
    )

    builder.add_node(
        "high_attention_recommendation",
        high_attention_recommendation_node,
    )

    builder.add_node(
        "standard_recommendation",
        standard_recommendation_node,
    )

    builder.add_node(
        "human_review",
        human_review_node,
    )

    # Entry
    builder.add_edge(
        START,
        "analysis_intake",
    )

    builder.add_edge(
        "analysis_intake",
        "completeness_check",
    )

    # CONDITIONAL ROUTE #1
    builder.add_conditional_edges(
        "completeness_check",
        route_after_completeness,
        {
            "risk_check":
                "risk_check",

            "policy_context":
                "policy_context",
        },
    )

    # Complete invoices pass through
    # the risk stage before policy grounding.
    builder.add_edge(
        "risk_check",
        "policy_context",
    )

    # CONDITIONAL ROUTE #2
    builder.add_conditional_edges(
        "policy_context",
        route_after_policy_context,
        {
            "needs_documents_recommendation":
                "needs_documents_recommendation",

            "high_attention_recommendation":
                "high_attention_recommendation",

            "standard_recommendation":
                "standard_recommendation",
        },
    )

    # Every recommendation still ends
    # at the human review boundary.
    builder.add_edge(
        "needs_documents_recommendation",
        "human_review",
    )

    builder.add_edge(
        "high_attention_recommendation",
        "human_review",
    )

    builder.add_edge(
        "standard_recommendation",
        "human_review",
    )

    builder.add_edge(
        "human_review",
        END,
    )

    return builder.compile()


invoice_agent_graph = (
    build_invoice_agent_graph()
)


# ============================================================
# PUBLIC SERVICE FUNCTION
# ============================================================


def run_invoice_agent(
    invoice_id: int,
    analysis_result: dict[str, Any],
    policy_evidence: (
        list[dict[str, Any]]
        | None
    ) = None,
) -> InvoiceAgentState:

    initial_state: InvoiceAgentState = {
        "invoice_id":
            invoice_id,

        "analysis_result":
            analysis_result,

        "policy_evidence":
            policy_evidence or [],

        "agent_trace":
            [],
    }

    result = (
        invoice_agent_graph.invoke(
            initial_state
        )
    )

    return result