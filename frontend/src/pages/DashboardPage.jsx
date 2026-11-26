import { useEffect, useState } from "react";
import { Link } from "react-router";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../services/api";


function DashboardPage() {
    const { user } = useAuth();

    const [dashboard, setDashboard] =
        useState(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");


    useEffect(() => {
        const loadDashboard = async () => {
            try {
                const data = await apiRequest(
                    "/api/dashboard/summary"
                );

                setDashboard(data);

            } catch (err) {
                setError(err.message);

            } finally {
                setLoading(false);
            }
        };

        loadDashboard();
    }, []);


    if (loading) {
        return (
            <div className="page">
                <div className="loading-state">
                    <span className="loading-spinner" />
                    <span>Loading dashboard...</span>
                </div>
            </div>
        );
    }


    if (error) {
        return (
            <div className="page">
                <div className="error-message">
                    {error}
                </div>
            </div>
        );
    }


    const formatMoney = (
        value,
        currency = "USD"
    ) =>
        new Intl.NumberFormat(
            "en-US",
            {
                style: "currency",
                currency,
            }
        ).format(
            Number(value || 0)
        );


    const canViewAI = [
        "staff",
        "manager",
        "admin",
    ].includes(user?.role);


    return (
        <div className="page">

            {/* PAGE HEADER */}

            <div className="page-header">

                <div>
                    <p className="page-eyebrow">
                        Overview
                    </p>

                    <h1>
                        Dashboard
                    </h1>

                    <p>
                        Welcome back,{" "}
                        {
                            user?.full_name
                            || user?.email
                        }.
                    </p>
                </div>

                <span className="role-pill">
                    {user?.role}
                </span>

            </div>


            {/* MAIN SUMMARY */}

            <section className="dashboard-grid">

                <div className="stat-card">
                    <p>
                        Total Invoices
                    </p>

                    <h2>
                        {
                            dashboard
                                ?.total_invoices
                            ?? 0
                        }
                    </h2>

                    <span>
                        Across your accessible records
                    </span>
                </div>


                <div className="stat-card">
                    <p>
                        Total Payments
                    </p>

                    <h2>
                        {
                            dashboard
                                ?.total_payments
                            ?? 0
                        }
                    </h2>

                    <span>
                        Payment records created
                    </span>
                </div>


                <div className="stat-card">
                    <p>
                        Completed Payments
                    </p>

                    <h2>
                        {
                            formatMoney(
                                dashboard
                                    ?.completed_payment_total
                            )
                        }
                    </h2>

                    <span>
                        Successfully processed
                    </span>
                </div>


                <div className="stat-card">
                    <p>
                        Unread Notifications
                    </p>

                    <h2>
                        {
                            dashboard
                                ?.unread_notifications
                            ?? 0
                        }
                    </h2>

                    <span>
                        Require your attention
                    </span>
                </div>

            </section>


            {/* INVOICE STATUS */}

            <section className="dashboard-section">

                <div className="section-header">
                    <div>
                        <h2>
                            Invoice Status
                        </h2>

                        <p>
                            Current workflow distribution
                        </p>
                    </div>
                </div>


                <div className="status-grid">

                    {
                        Object.entries(
                            dashboard
                                ?.invoice_status_counts
                            || {}
                        ).map(
                            ([status, count]) => (
                                <div
                                    className="status-card"
                                    key={status}
                                >
                                    <span>
                                        {
                                            status.replaceAll(
                                                "_",
                                                " "
                                            )
                                        }
                                    </span>

                                    <strong>
                                        {count}
                                    </strong>
                                </div>
                            )
                        )
                    }

                </div>

            </section>


            {/* AI REVIEW OVERVIEW */}

            {canViewAI && (

                <section className="dashboard-section">

                    <div className="section-header">
                        <div>
                            <h2>
                                AI Review Overview
                            </h2>

                            <p>
                                Agentic AI recommendations
                                across analyzed invoices
                            </p>
                        </div>
                    </div>


                    <div className="dashboard-grid">

                        <div className="stat-card">
                            <p>
                                Analyzed Invoices
                            </p>

                            <h2>
                                {
                                    dashboard
                                        ?.ai_review_summary
                                        ?.analyzed_invoices
                                    ?? 0
                                }
                            </h2>

                            <span>
                                Processed by the AI
                                review pipeline
                            </span>
                        </div>


                        <div className="stat-card">
                            <p>
                                Duplicate Risks
                            </p>

                            <h2>
                                {
                                    dashboard
                                        ?.ai_review_summary
                                        ?.duplicate_risks
                                    ?? 0
                                }
                            </h2>

                            <span>
                                Potential duplicate invoices
                            </span>
                        </div>


                        <div className="stat-card">
                            <p>
                                High Attention
                            </p>

                            <h2>
                                {
                                    dashboard
                                        ?.ai_review_summary
                                        ?.high_attention_risks
                                    ?? 0
                                }
                            </h2>

                            <span>
                                Require closer human review
                            </span>
                        </div>


                        <div className="stat-card">
                            <p>
                                Average Completeness
                            </p>

                            <h2>
                                {
                                    dashboard
                                        ?.ai_review_summary
                                        ?.average_completeness_score
                                    ?? 0
                                }
                                %
                            </h2>

                            <span>
                                Average invoice
                                completeness score
                            </span>
                        </div>


                        <div className="stat-card">
                            <p>
                                Policy Grounded
                            </p>

                            <h2>
                                {
                                    dashboard
                                        ?.ai_review_summary
                                        ?.policy_grounded_reviews
                                    ?? 0
                                }
                            </h2>

                            <span>
                                Reviews supported
                                by RAG evidence
                            </span>
                        </div>

                    </div>


                    <div className="ai-dashboard-summary">

                        {
                            Object.entries(
                                dashboard
                                    ?.ai_review_summary
                                    ?.recommendation_counts
                                || {}
                            ).map(
                                (
                                    [
                                        recommendation,
                                        count,
                                    ]
                                ) => (
                                    <div
                                        className={
                                            `ai-dashboard-card ` +
                                            `ai-dashboard-${recommendation}`
                                        }
                                        key={
                                            recommendation
                                        }
                                    >
                                        <span>
                                            {
                                                recommendation
                                                    .replaceAll(
                                                        "_",
                                                        " "
                                                    )
                                            }
                                        </span>

                                        <strong>
                                            {count}
                                        </strong>
                                    </div>
                                )
                            )
                        }

                    </div>

                </section>

            )}


            {/* AI PRIORITY REVIEW QUEUE */}

            {canViewAI && (

                <section className="dashboard-section">

                    <div className="section-header">
                        <div>
                            <h2>
                                AI Priority Review Queue
                            </h2>

                            <p>
                                Invoices ordered by
                                agentic AI review priority
                            </p>
                        </div>
                    </div>


                    {
                        dashboard
                            ?.ai_review_summary
                            ?.priority_invoices
                            ?.length
                            ? (

                                <div className="table-wrapper">

                                    <table>

                                        <thead>
                                            <tr>
                                                <th>
                                                    Invoice
                                                </th>

                                                <th>
                                                    Vendor
                                                </th>

                                                <th>
                                                    Amount
                                                </th>

                                                <th>
                                                    Completeness
                                                </th>

                                                <th>
                                                    Risk
                                                </th>

                                                <th>
                                                    Recommendation
                                                </th>
                                            </tr>
                                        </thead>


                                        <tbody>

                                            {
                                                dashboard
                                                    .ai_review_summary
                                                    .priority_invoices
                                                    .map(
                                                        (item) => (

                                                            <tr
                                                                key={
                                                                    item.invoice_id
                                                                }
                                                            >

                                                                <td>
                                                                    <Link
                                                                        to={
                                                                            `/invoices/${item.invoice_id}`
                                                                        }
                                                                        className="dashboard-invoice-link"
                                                                    >
                                                                        {
                                                                            item.invoice_number
                                                                        }
                                                                    </Link>
                                                                </td>


                                                                <td>
                                                                    {
                                                                        item.vendor_name
                                                                    }
                                                                </td>


                                                                <td>
                                                                    {
                                                                        formatMoney(
                                                                            item.total_amount,
                                                                            item.currency
                                                                        )
                                                                    }
                                                                </td>


                                                                <td>
                                                                    {
                                                                        Number(
                                                                            item
                                                                                .completeness_score
                                                                        ).toFixed(0)
                                                                    }
                                                                    %
                                                                </td>


                                                                <td>

                                                                    <div className="ai-risk-cell">

                                                                        <span>
                                                                            {
                                                                                item
                                                                                    .risk_level
                                                                                    .replaceAll(
                                                                                        "_",
                                                                                        " "
                                                                                    )
                                                                            }
                                                                        </span>


                                                                        {
                                                                            item
                                                                                .duplicate_risk
                                                                            && (

                                                                                <span className="duplicate-risk-label">
                                                                                    Duplicate
                                                                                </span>

                                                                            )
                                                                        }

                                                                    </div>

                                                                </td>


                                                                <td>

                                                                    <span
                                                                        className={
                                                                            `priority-recommendation ` +
                                                                            `priority-${item.recommendation}`
                                                                        }
                                                                    >
                                                                        {
                                                                            item
                                                                                .recommendation
                                                                                .replaceAll(
                                                                                    "_",
                                                                                    " "
                                                                                )
                                                                        }
                                                                    </span>

                                                                </td>

                                                            </tr>

                                                        )
                                                    )
                                            }

                                        </tbody>

                                    </table>

                                </div>

                            )
                            : (

                                <div className="empty-state">
                                    <div>
                                        <strong>No AI reviews yet</strong>
                                        <p>
                                            AI-analyzed invoices will appear here once analysis is completed.
                                        </p>
                                    </div>
                                </div>

                            )
                    }

                </section>

            )}


            {/* PAYMENT STATUS */}

            <section className="dashboard-section">

                <div className="section-header">
                    <div>
                        <h2>
                            Payment Status
                        </h2>

                        <p>
                            Current payment processing state
                        </p>
                    </div>
                </div>


                <div className="status-grid">

                    {
                        Object.entries(
                            dashboard
                                ?.payment_status_counts
                            || {}
                        ).map(
                            ([status, count]) => (

                                <div
                                    className="status-card"
                                    key={status}
                                >
                                    <span>
                                        {
                                            status.replaceAll(
                                                "_",
                                                " "
                                            )
                                        }
                                    </span>

                                    <strong>
                                        {count}
                                    </strong>
                                </div>

                            )
                        )
                    }

                </div>

            </section>


            {/* RECENT INVOICES */}

            <section className="dashboard-section">

                <div className="section-header">
                    <div>
                        <h2>
                            Recent Invoices
                        </h2>

                        <p>
                            Latest invoice activity
                        </p>
                    </div>
                </div>


                {
                    dashboard
                        ?.recent_invoices
                        ?.length
                        ? (

                            <div className="table-wrapper">

                                <table>

                                    <thead>
                                        <tr>
                                            <th>
                                                Invoice
                                            </th>

                                            <th>
                                                Vendor
                                            </th>

                                            <th>
                                                Date
                                            </th>

                                            <th>
                                                Amount
                                            </th>

                                            <th>
                                                Status
                                            </th>
                                        </tr>
                                    </thead>


                                    <tbody>

                                        {
                                            dashboard
                                                .recent_invoices
                                                .map(
                                                    (invoice) => (

                                                        <tr
                                                            key={
                                                                invoice.id
                                                            }
                                                        >

                                                            <td>
                                                                <Link
                                                                    to={
                                                                        `/invoices/${invoice.id}`
                                                                    }
                                                                    className="dashboard-invoice-link"
                                                                >
                                                                    {
                                                                        invoice
                                                                            .invoice_number
                                                                    }
                                                                </Link>
                                                            </td>


                                                            <td>
                                                                Vendor #
                                                                {
                                                                    invoice
                                                                        .vendor_id
                                                                }
                                                            </td>


                                                            <td>
                                                                {
                                                                    invoice
                                                                        .invoice_date
                                                                }
                                                            </td>


                                                            <td>
                                                                {
                                                                    formatMoney(
                                                                        invoice
                                                                            .total_amount
                                                                    )
                                                                }
                                                            </td>


                                                            <td>
                                                                <span className={`table-status status-${invoice.status}`}>
                                                                    {
                                                                        invoice
                                                                            .status
                                                                            .replaceAll(
                                                                                "_",
                                                                                " "
                                                                            )
                                                                    }
                                                                </span>
                                                            </td>

                                                        </tr>

                                                    )
                                                )
                                        }

                                    </tbody>

                                </table>

                            </div>

                        )
                        : (

                            <div className="empty-state">
                                <div>
                                    <strong>No invoices yet</strong>
                                    <p>
                                        Recent invoices will appear here once they are submitted.
                                    </p>
                                </div>
                            </div>

                        )
                }

            </section>

        </div>
    );
}


export default DashboardPage;