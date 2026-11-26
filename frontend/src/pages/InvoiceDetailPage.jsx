import {
    useCallback,
    useEffect,
    useState,
} from "react";

import {
    Link,
    useParams,
} from "react-router";

import { useAuth } from "../context/AuthContext";

import {
    API_BASE_URL,
    apiRequest,
} from "../services/api";


function InvoiceDetailPage() {
    const { invoiceId } = useParams();
    const { user } = useAuth();

    const [invoice, setInvoice] =
        useState(null);

    const [vendor, setVendor] =
        useState(null);

    const [resubmitError, setResubmitError] =
        useState("");

    const [documents, setDocuments] =
        useState([]);

    const [reviews, setReviews] =
        useState([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");

    const [file, setFile] =
        useState(null);

    const [documentType, setDocumentType] =
        useState("supporting_document");

    const [uploading, setUploading] =
        useState(false);

    const [
        reviewComments,
        setReviewComments,
    ] = useState("");

    const [
        decisionComments,
        setDecisionComments,
    ] = useState("");

    const [
        actionLoading,
        setActionLoading,
    ] = useState(false);


    // -------------------------
    // AI ANALYSIS STATE
    // -------------------------

    const [
        aiAnalysis,
        setAiAnalysis,
    ] = useState(null);

    const [
        aiLoading,
        setAiLoading,
    ] = useState(false);

    const [
        selectedAnalysisDocument,
        setSelectedAnalysisDocument,
    ] = useState("");


    // -------------------------
    // LOAD INVOICE DATA
    // -------------------------

    const loadInvoiceData =
        useCallback(async () => {
            setLoading(true);
            setError("");

            try {
                const invoiceData =
                    await apiRequest(
                        `/api/invoices/${invoiceId}`
                    );

                setInvoice(invoiceData);

                const [
                    documentData,
                    reviewData,
                    vendorData,
                ] = await Promise.all([
                    apiRequest(
                        `/api/invoices/${invoiceId}/documents`
                    ),

                    apiRequest(
                        `/api/invoices/${invoiceId}/reviews`
                    ),

                    apiRequest(
                        `/api/vendors/${invoiceData.vendor_id}`
                    ),
                ]);

                setDocuments(documentData);
                setReviews(reviewData);
                setVendor(vendorData);


                // Automatically select an
                // invoice document for analysis.

                const invoiceDocument =
                    documentData.find(
                        (item) =>
                            item.document_type ===
                            "invoice"
                    );

                if (invoiceDocument) {
                    setSelectedAnalysisDocument(
                        String(
                            invoiceDocument.id
                        )
                    );
                } else {
                    setSelectedAnalysisDocument(
                        ""
                    );
                }


                // Load existing AI analysis.

                try {
                    const analysisData =
                        await apiRequest(
                            `/api/ai/invoices/${invoiceId}/analysis`
                        );

                    setAiAnalysis(
                        analysisData
                    );

                } catch {
                    // A missing analysis is normal
                    // until analysis has been run.

                    setAiAnalysis(null);
                }

            } catch (err) {
                setError(err.message);

            } finally {
                setLoading(false);
            }
        }, [invoiceId]);


    useEffect(() => {
        loadInvoiceData();
    }, [loadInvoiceData]);


    // -------------------------
    // FORMATTERS
    // -------------------------

    const formatMoney = (
        value,
        currency = "USD"
    ) => {
        try {
            return new Intl.NumberFormat(
                "en-US",
                {
                    style: "currency",
                    currency,
                }
            ).format(
                Number(value || 0)
            );

        } catch {
            return `${currency} ${value}`;
        }
    };


    const formatDateTime =
        (value) => {
            if (!value) {
                return "—";
            }

            return new Date(
                value
            ).toLocaleString();
        };


    const formatFileSize =
        (bytes) => {
            if (bytes < 1024) {
                return `${bytes} B`;
            }

            if (
                bytes <
                1024 * 1024
            ) {
                return `${(
                    bytes / 1024
                ).toFixed(1)} KB`;
            }

            return `${(
                bytes /
                (1024 * 1024)
            ).toFixed(1)} MB`;
        };


    // -------------------------
    // DOCUMENT UPLOAD
    // -------------------------

    const handleUpload =
        async (event) => {
            event.preventDefault();

            if (!file) {
                setError(
                    "Please select a document."
                );

                return;
            }

            setUploading(true);
            setError("");
            setSuccess("");

            try {
                const formData =
                    new FormData();

                formData.append(
                    "document_type",
                    documentType
                );

                formData.append(
                    "file",
                    file
                );

                await apiRequest(
                    `/api/invoices/${invoiceId}/documents`,
                    {
                        method: "POST",
                        body: formData,
                    }
                );

                setSuccess(
                    "Document uploaded successfully."
                );

                setFile(null);

                const documentData =
                    await apiRequest(
                        `/api/invoices/${invoiceId}/documents`
                    );

                setDocuments(
                    documentData
                );


                // Automatically select
                // uploaded invoice document.

                const invoiceDocument =
                    documentData.find(
                        (item) =>
                            item.document_type ===
                            "invoice"
                    );

                if (invoiceDocument) {
                    setSelectedAnalysisDocument(
                        String(
                            invoiceDocument.id
                        )
                    );
                }


                const input =
                    window.document
                        .getElementById(
                            "document_file"
                        );

                if (input) {
                    input.value = "";
                }

            } catch (err) {
                setError(err.message);

            } finally {
                setUploading(false);
            }
        };


    // -------------------------
    // DOCUMENT DOWNLOAD
    // -------------------------

    const handleDownload =
        async (documentItem) => {
            setError("");

            try {
                const token =
                    localStorage.getItem(
                        "access_token"
                    );

                const response =
                    await fetch(
                        `${API_BASE_URL}/api/documents/${documentItem.id}/download`,
                        {
                            headers: {
                                Authorization:
                                    `Bearer ${token}`,
                            },
                        }
                    );

                if (!response.ok) {
                    let message =
                        "Document download failed.";

                    try {
                        const data =
                            await response.json();

                        message =
                            data.detail ||
                            message;

                    } catch {
                        // Keep fallback.
                    }

                    throw new Error(
                        message
                    );
                }

                const blob =
                    await response.blob();

                const url =
                    window.URL
                        .createObjectURL(
                            blob
                        );

                const link =
                    window.document
                        .createElement("a");

                link.href = url;

                link.download =
                    documentItem
                        .original_filename;

                window.document.body
                    .appendChild(link);

                link.click();

                link.remove();

                window.URL
                    .revokeObjectURL(
                        url
                    );

            } catch (err) {
                setError(
                    err.message
                );
            }
        };


    // -------------------------
    // DOCUMENT DELETE
    // -------------------------

    const handleDeleteDocument =
        async (documentItem) => {
            const confirmed =
                window.confirm(
                    `Delete "${documentItem.original_filename}"?`
                );

            if (!confirmed) {
                return;
            }

            setError("");
            setSuccess("");

            try {
                await apiRequest(
                    `/api/documents/${documentItem.id}`,
                    {
                        method: "DELETE",
                    }
                );

                setSuccess(
                    "Document deleted successfully."
                );

                setDocuments(
                    (current) =>
                        current.filter(
                            (item) =>
                                item.id !==
                                documentItem.id
                        )
                );

                if (
                    String(
                        documentItem.id
                    ) ===
                    selectedAnalysisDocument
                ) {
                    setSelectedAnalysisDocument(
                        ""
                    );
                }

            } catch (err) {
                setError(
                    err.message
                );
            }
        };


    // -------------------------
    // STEP 3:
    // RUN LOCAL AI ANALYSIS
    // -------------------------

    const handleRunAIAnalysis =
        async () => {
            if (
                !selectedAnalysisDocument
            ) {
                setError(
                    "Please upload or select an invoice document before running analysis."
                );

                return;
            }

            setAiLoading(true);

            setError("");
            setSuccess("");

            try {
                const result =
                    await apiRequest(
                        `/api/ai/invoices/${invoiceId}/analyze`,
                        {
                            method: "POST",

                            body:
                                JSON.stringify({
                                    source_document_id:
                                        Number(
                                            selectedAnalysisDocument
                                        ),
                                }),
                        }
                    );

                setAiAnalysis(
                    result
                );

                setSuccess(
                    "Invoice analysis completed successfully."
                );

            } catch (err) {
                setError(
                    err.message
                );

            } finally {
                setAiLoading(false);
            }
        };


    // -------------------------
    // REVIEW WORKFLOW
    // -------------------------

    const handleStartReview =
        async () => {
            setActionLoading(true);

            setError("");
            setSuccess("");

            try {
                await apiRequest(
                    `/api/invoices/${invoiceId}/review/start`,
                    {
                        method: "POST",

                        body:
                            JSON.stringify({
                                comments:
                                    reviewComments
                                        .trim() ||
                                    null,
                            }),
                    }
                );

                setReviewComments(
                    ""
                );

                setSuccess(
                    "Invoice review started."
                );

                await loadInvoiceData();

            } catch (err) {
                setError(
                    err.message
                );

            } finally {
                setActionLoading(
                    false
                );
            }
        };


    const handleDecision =
        async (decision) => {
            const comments =
                decisionComments
                    .trim();

            if (
                [
                    "rejected",
                    "needs_documents",
                ].includes(
                    decision
                ) &&
                !comments
            ) {
                setError(
                    "Comments are required when rejecting an invoice or requesting documents."
                );

                return;
            }

            setActionLoading(true);

            setError("");
            setSuccess("");

            try {
                await apiRequest(
                    `/api/invoices/${invoiceId}/review/decision`,
                    {
                        method: "POST",

                        body:
                            JSON.stringify({
                                decision,

                                comments:
                                    comments ||
                                    null,
                            }),
                    }
                );

                setDecisionComments(
                    ""
                );

                if (
                    decision ===
                    "approved"
                ) {
                    setSuccess(
                        "Invoice approved successfully."
                    );
                }

                if (
                    decision ===
                    "rejected"
                ) {
                    setSuccess(
                        "Invoice rejected."
                    );
                }

                if (
                    decision ===
                    "needs_documents"
                ) {
                    setSuccess(
                        "Additional documents requested."
                    );
                }

                await loadInvoiceData();

            } catch (err) {
                setError(
                    err.message
                );

            } finally {
                setActionLoading(
                    false
                );
            }
        };


    const latestDocumentRequest =
        [...reviews]
            .filter(
                (review) =>
                    review.action ===
                    "requested_documents"
            )
            .sort(
                (a, b) =>
                    new Date(
                        b.created_at
                    ) -
                    new Date(
                        a.created_at
                    )
            )[0];


    const hasNewVendorDocument =
        latestDocumentRequest &&
        documents.some(
            (documentItem) =>
                documentItem
                    .uploaded_by_user_id ===
                user?.id &&
                new Date(
                    documentItem
                        .uploaded_at
                ) >=
                new Date(
                    latestDocumentRequest
                        .created_at
                )
        );


    const handleResubmit =
        async () => {
            setResubmitError(
                ""
            );

            if (
                !hasNewVendorDocument
            ) {
                setResubmitError(
                    "No document is uploaded. Please upload the requested document before resubmitting."
                );

                return;
            }

            setActionLoading(true);

            setError("");
            setSuccess("");

            try {
                await apiRequest(
                    `/api/invoices/${invoiceId}/resubmit`,
                    {
                        method: "POST",

                        body:
                            JSON.stringify({
                                comments:
                                    reviewComments
                                        .trim() ||
                                    null,
                            }),
                    }
                );

                setReviewComments(
                    ""
                );

                setResubmitError(
                    ""
                );

                setSuccess(
                    "Invoice resubmitted successfully."
                );

                await loadInvoiceData();

            } catch (err) {
                setResubmitError(
                    err.message
                );

            } finally {
                setActionLoading(
                    false
                );
            }
        };


    // -------------------------
    // LOADING / ERROR STATES
    // -------------------------

    if (loading) {
        return (
            <div className="page">
                <div className="loading-state">
                    <span className="loading-spinner" />
                    <span>Loading invoice...</span>
                </div>
            </div>
        );
    }


    if (!invoice) {
        return (
            <div className="page">
                <div className="error-message">
                    {error ||
                        "Invoice not found."}
                </div>
            </div>
        );
    }


    // -------------------------
    // PERMISSIONS
    // -------------------------

    const canStartReview =
        [
            "staff",
            "manager",
            "admin",
        ].includes(
            user?.role
        ) &&
        invoice.status ===
        "submitted";


    const canDecide =
        [
            "manager",
            "admin",
        ].includes(
            user?.role
        ) &&
        invoice.status ===
        "under_review";


    const canResubmit =
        user?.role ===
        "vendor" &&
        invoice.status ===
        "needs_documents";


    const canRunAIAnalysis =
        [
            "staff",
            "manager",
            "admin",
        ].includes(
            user?.role
        );


    // -------------------------
    // PAGE
    // -------------------------

    return (
        <div className="page">

            <div className="invoice-detail-nav">
                <Link
                    to="/invoices"
                    className="back-link"
                >
                    ← Back to Invoices
                </Link>
            </div>


            <div className="page-header">
                <div>
                    <p className="page-eyebrow">
                        Invoice Detail
                    </p>

                    <h1>
                        {
                            invoice
                                .invoice_number
                        }
                    </h1>

                    <p>
                        {vendor?.name ||
                            `Vendor #${invoice.vendor_id}`}
                    </p>
                </div>

                <span className={`detail-status status-${invoice.status}`}>
                    {
                        invoice.status
                            .replaceAll(
                                "_",
                                " "
                            )
                    }
                </span>
            </div>


            {error && (
                <div className="error-message detail-message">
                    {error}
                </div>
            )}


            {success && (
                <div className="success-message detail-message">
                    {success}
                </div>
            )}


            {/* -------------------------
            INVOICE SUMMARY
        -------------------------- */}

            <section className="invoice-summary-grid">

                <div className="invoice-summary-card">
                    <span>
                        Invoice Date
                    </span>

                    <strong>
                        {
                            invoice
                                .invoice_date
                        }
                    </strong>
                </div>


                <div className="invoice-summary-card">
                    <span>
                        Due Date
                    </span>

                    <strong>
                        {
                            invoice
                                .due_date ||
                            "—"
                        }
                    </strong>
                </div>


                <div className="invoice-summary-card">
                    <span>
                        Total Amount
                    </span>

                    <strong>
                        {formatMoney(
                            invoice
                                .total_amount,

                            invoice
                                .currency
                        )}
                    </strong>
                </div>


                <div className="invoice-summary-card">
                    <span>
                        Currency
                    </span>

                    <strong>
                        {
                            invoice
                                .currency
                        }
                    </strong>
                </div>

            </section>


            {/* -------------------------
            LINE ITEMS
        -------------------------- */}

            <section className="dashboard-section">

                <div className="section-header">
                    <div>
                        <h2>
                            Line Items
                        </h2>

                        <p>
                            Invoice charges
                            and categories
                        </p>
                    </div>
                </div>


                <div className="table-wrapper">

                    <table>

                        <thead>
                            <tr>
                                <th>
                                    Description
                                </th>

                                <th>
                                    Category
                                </th>

                                <th>
                                    Quantity
                                </th>

                                <th>
                                    Unit Price
                                </th>

                                <th>
                                    Line Total
                                </th>
                            </tr>
                        </thead>


                        <tbody>
                            {
                                invoice
                                    .line_items
                                    .map(
                                        (item) => (
                                            <tr
                                                key={
                                                    item.id
                                                }
                                            >
                                                <td>
                                                    {
                                                        item
                                                            .description
                                                    }
                                                </td>

                                                <td>
                                                    {
                                                        item
                                                            .category ||
                                                        "—"
                                                    }
                                                </td>

                                                <td>
                                                    {
                                                        item
                                                            .quantity
                                                    }
                                                </td>

                                                <td>
                                                    {formatMoney(
                                                        item
                                                            .unit_price,

                                                        invoice
                                                            .currency
                                                    )}
                                                </td>

                                                <td>
                                                    <strong>
                                                        {formatMoney(
                                                            item
                                                                .line_total,

                                                            invoice
                                                                .currency
                                                        )}
                                                    </strong>
                                                </td>
                                            </tr>
                                        )
                                    )
                            }
                        </tbody>

                    </table>

                </div>

            </section>


            {/* -------------------------
            SUPPORTING DOCUMENTS
        -------------------------- */}

            <section className="dashboard-section">

                <div className="section-header">
                    <div>
                        <h2>
                            Supporting Documents
                        </h2>

                        <p>
                            Upload invoices,
                            purchase orders,
                            receipts and other
                            supporting files.
                        </p>
                    </div>
                </div>


                <form
                    className="document-upload-form"
                    onSubmit={
                        handleUpload
                    }
                >

                    <div className="form-group">

                        <label
                            htmlFor="document_type"
                        >
                            Document Type
                        </label>

                        <select
                            id="document_type"

                            value={
                                documentType
                            }

                            onChange={
                                (event) =>
                                    setDocumentType(
                                        event
                                            .target
                                            .value
                                    )
                            }
                        >

                            <option value="invoice">
                                Invoice
                            </option>

                            <option value="purchase_order">
                                Purchase Order
                            </option>

                            <option value="receipt">
                                Receipt
                            </option>

                            <option value="supporting_document">
                                Supporting Document
                            </option>

                        </select>

                    </div>


                    <div className="form-group">

                        <label
                            htmlFor="document_file"
                        >
                            File
                        </label>

                        <input
                            id="document_file"

                            type="file"

                            accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"

                            onChange={
                                (event) =>
                                    setFile(
                                        event
                                            .target
                                            .files?.[0] ||
                                        null
                                    )
                            }

                            required
                        />

                    </div>


                    <button
                        className="primary-button"

                        type="submit"

                        disabled={
                            uploading
                        }
                    >
                        {uploading
                            ? "Uploading..."
                            : "Upload Document"}
                    </button>

                </form>


                <p className="upload-note">
                    PDF, PNG, JPG or
                    JPEG · Maximum file
                    size 10 MB
                </p>


                {documents.length ===
                    0 ? (
                    <div className="empty-state">
                        <div>
                            <strong>No supporting documents</strong>
                            <p>
                                Supporting invoice documents have not been uploaded yet.
                            </p>
                        </div>
                    </div>
                ) : (

                    <div className="document-list">

                        {
                            documents.map(
                                (
                                    documentItem
                                ) => (
                                    <div
                                        className="document-card"

                                        key={
                                            documentItem
                                                .id
                                        }
                                    >

                                        <div>

                                            <strong>
                                                {
                                                    documentItem
                                                        .original_filename
                                                }
                                            </strong>


                                            <div className="document-meta">

                                                <span>
                                                    {
                                                        documentItem
                                                            .document_type
                                                            .replaceAll(
                                                                "_",
                                                                " "
                                                            )
                                                    }
                                                </span>

                                                <span>
                                                    {formatFileSize(
                                                        documentItem
                                                            .file_size
                                                    )}
                                                </span>

                                                <span>
                                                    {
                                                        documentItem
                                                            .verification_status
                                                    }
                                                </span>

                                            </div>

                                        </div>


                                        <div className="document-actions">

                                            <button
                                                className="text-button"

                                                onClick={() =>
                                                    handleDownload(
                                                        documentItem
                                                    )
                                                }
                                            >
                                                Download
                                            </button>


                                            <button
                                                className="text-button danger"

                                                onClick={() =>
                                                    handleDeleteDocument(
                                                        documentItem
                                                    )
                                                }
                                            >
                                                Delete
                                            </button>

                                        </div>

                                    </div>
                                )
                            )
                        }

                    </div>
                )}

            </section>


            {/* ======================================
            STEP 4:
            AI INVOICE ANALYSIS PANEL
        ====================================== */}

            <section className="dashboard-section">

                <div className="section-header">

                    <div>
                        <h2>
                            AI Invoice Analysis
                        </h2>

                        <p>
                            Automated completeness,
                            duplicate and document
                            consistency checks.
                        </p>
                    </div>

                </div>


                {/* Only staff / manager / admin
              can run analysis */}

                {canRunAIAnalysis && (

                    <div className="ai-analysis-controls">

                        <div className="form-group">

                            <label
                                htmlFor="analysis_document"
                            >
                                Invoice Document
                            </label>


                            <select
                                id="analysis_document"

                                value={
                                    selectedAnalysisDocument
                                }

                                onChange={
                                    (event) =>
                                        setSelectedAnalysisDocument(
                                            event
                                                .target
                                                .value
                                        )
                                }
                            >

                                <option value="">
                                    Select invoice document
                                </option>


                                {
                                    documents
                                        .filter(
                                            (item) =>
                                                item
                                                    .document_type ===
                                                "invoice"
                                        )
                                        .map(
                                            (item) => (
                                                <option
                                                    key={
                                                        item.id
                                                    }

                                                    value={
                                                        item.id
                                                    }
                                                >
                                                    {
                                                        item
                                                            .original_filename
                                                    }
                                                </option>
                                            )
                                        )
                                }

                            </select>

                        </div>


                        <button
                            className="primary-button"

                            onClick={
                                handleRunAIAnalysis
                            }

                            disabled={
                                aiLoading ||
                                !selectedAnalysisDocument
                            }
                        >
                            {aiLoading
                                ? "Analyzing..."
                                : "Run Invoice Analysis"}
                        </button>

                    </div>
                )}


                {!aiAnalysis ? (

                    <div className="empty-state">

                        {documents.some(
                            (item) =>
                                item.document_type ===
                                "invoice"
                        )
                            ? "No analysis has been run yet."
                            : "Upload an invoice document to run analysis."}

                    </div>

                ) : (

                    <>

                        {/* AI SUMMARY */}

                        <div className="ai-summary-grid">

                            <div className="ai-summary-card">

                                <span>
                                    Completeness
                                </span>

                                <strong>
                                    {
                                        aiAnalysis
                                            .completeness_score
                                    }
                                    %
                                </strong>

                            </div>


                            <div className="ai-summary-card">

                                <span>
                                    Risk Level
                                </span>

                                <strong
                                    className={
                                        `risk-${aiAnalysis.risk_level}`
                                    }
                                >
                                    {
                                        aiAnalysis
                                            .risk_level
                                            .replaceAll(
                                                "_",
                                                " "
                                            )
                                    }
                                </strong>

                            </div>


                            <div className="ai-summary-card">

                                <span>
                                    Duplicate Risk
                                </span>

                                <strong>
                                    {
                                        aiAnalysis
                                            .duplicate_risk
                                            ? "Yes"
                                            : "No"
                                    }
                                </strong>

                            </div>


                            <div className="ai-summary-card">

                                <span>
                                    Extraction
                                </span>

                                <strong>
                                    {
                                        aiAnalysis
                                            .extracted_data
                                            ?.document
                                            ?.extraction_method ||
                                        "Rules"
                                    }
                                </strong>

                            </div>

                        </div>


                        {/* ANALYSIS VERSION */}

                        <div className="ai-analysis-block">

                            <h3>
                                Analysis Details
                            </h3>

                            <p>
                                Version:{" "}
                                <strong>
                                    {
                                        aiAnalysis
                                            .analysis_version
                                    }
                                </strong>
                            </p>

                        </div>
                        {/* AGENTIC REVIEW RECOMMENDATION */}

                        {aiAnalysis
                            .extracted_data
                            ?.agent && (

                                <div className="agentic-review-card">

                                    <div className="agentic-review-header">

                                        <div>
                                            <p className="agentic-review-eyebrow">
                                                LangGraph Agent
                                            </p>

                                            <h3>
                                                Agentic Review Recommendation
                                            </h3>
                                        </div>


                                        <span
                                            className={
                                                `agent-recommendation-badge agent-recommendation-${aiAnalysis
                                                    .extracted_data
                                                    .agent
                                                    .recommendation
                                                }`
                                            }
                                        >
                                            {
                                                aiAnalysis
                                                    .extracted_data
                                                    .agent
                                                    .recommendation
                                                    ?.replaceAll(
                                                        "_",
                                                        " "
                                                    )
                                            }
                                        </span>

                                    </div>


                                    <div className="agentic-review-grid">

                                        <div>
                                            <span>
                                                Completeness Status
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .agent
                                                        .completeness_status
                                                        ?.replaceAll(
                                                            "_",
                                                            " "
                                                        )
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Policy Context
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .agent
                                                        .policy_context_available
                                                        ? `${aiAnalysis
                                                            .extracted_data
                                                            .agent
                                                            .policy_evidence_count
                                                        } evidence chunk(s)`
                                                        : "Not available"
                                                }
                                            </strong>
                                        </div>

                                    </div>
                                    {/* AGENT ROUTE */}

                                    <div className="agent-route-section">

                                        <h4>
                                            Agent Route Taken
                                        </h4>

                                        <div className="agent-route-flow">

                                            <span className="agent-route-step">
                                                Analysis
                                            </span>

                                            <span className="agent-route-arrow">
                                                →
                                            </span>

                                            <span className="agent-route-step">
                                                Completeness
                                            </span>

                                            <span className="agent-route-arrow">
                                                →
                                            </span>


                                            {aiAnalysis
                                                .extracted_data
                                                .agent
                                                .agent_trace
                                                ?.some(
                                                    (step) =>
                                                        step.startsWith(
                                                            "Risk check:"
                                                        )
                                                ) && (
                                                    <>
                                                        <span className="agent-route-step">
                                                            Risk
                                                        </span>

                                                        <span className="agent-route-arrow">
                                                            →
                                                        </span>
                                                    </>
                                                )}


                                            <span className="agent-route-step">
                                                Policy RAG
                                            </span>

                                            <span className="agent-route-arrow">
                                                →
                                            </span>


                                            <span
                                                className={
                                                    `agent-route-step agent-route-result agent-route-${aiAnalysis
                                                        .extracted_data
                                                        .agent
                                                        .recommendation
                                                    }`
                                                }
                                            >
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .agent
                                                        .recommendation
                                                        ?.replaceAll(
                                                            "_",
                                                            " "
                                                        )
                                                }
                                            </span>

                                            <span className="agent-route-arrow">
                                                →
                                            </span>

                                            <span className="agent-route-step agent-route-human">
                                                Human Review
                                            </span>

                                        </div>

                                    </div>


                                    <div className="agentic-review-section">

                                        <h4>
                                            Recommendation Reasons
                                        </h4>


                                        {aiAnalysis
                                            .extracted_data
                                            .agent
                                            .recommendation_reasons
                                            ?.length ? (

                                            <ul>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .agent
                                                        .recommendation_reasons
                                                        .map(
                                                            (
                                                                reason,
                                                                index
                                                            ) => (

                                                                <li
                                                                    key={
                                                                        index
                                                                    }
                                                                >
                                                                    {
                                                                        reason
                                                                    }
                                                                </li>

                                                            )
                                                        )
                                                }
                                            </ul>

                                        ) : (

                                            <p>
                                                No recommendation reasons
                                                were generated.
                                            </p>

                                        )}

                                    </div>


                                    <div className="human-review-guardrail">

                                        <div className="human-review-icon">
                                            !
                                        </div>


                                        <div>

                                            <strong>
                                                Human Review Required
                                            </strong>

                                            <p>
                                                This recommendation is
                                                advisory only. The AI agent
                                                cannot approve, reject, or
                                                authorize payment for this
                                                invoice. A manager or admin
                                                must make the final financial
                                                decision.
                                            </p>

                                        </div>

                                    </div>


                                    {aiAnalysis
                                        .extracted_data
                                        .agent
                                        .agent_trace
                                        ?.length > 0 && (

                                            <details className="agent-trace">

                                                <summary>
                                                    View Agent Execution Trace
                                                </summary>


                                                <ol>
                                                    {
                                                        aiAnalysis
                                                            .extracted_data
                                                            .agent
                                                            .agent_trace
                                                            .map(
                                                                (
                                                                    step,
                                                                    index
                                                                ) => (

                                                                    <li
                                                                        key={
                                                                            index
                                                                        }
                                                                    >
                                                                        {
                                                                            step
                                                                        }
                                                                    </li>

                                                                )
                                                            )
                                                    }
                                                </ol>

                                            </details>

                                        )}

                                </div>

                            )}


                        {/* RISK REASONS */}

                        <div className="ai-analysis-block">

                            <h3>
                                Risk Reasons
                            </h3>


                            {aiAnalysis
                                .risk_reasons
                                ?.length ? (

                                <ul>

                                    {
                                        aiAnalysis
                                            .risk_reasons
                                            .map(
                                                (
                                                    reason,
                                                    index
                                                ) => (
                                                    <li
                                                        key={
                                                            index
                                                        }
                                                    >
                                                        {
                                                            reason
                                                        }
                                                    </li>
                                                )
                                            )
                                    }

                                </ul>

                            ) : (

                                <p>
                                    No risk reasons
                                    detected.
                                </p>

                            )}

                        </div>


                        {/* MISSING FIELDS */}

                        <div className="ai-analysis-block">

                            <h3>
                                Missing Fields
                            </h3>


                            {aiAnalysis
                                .missing_fields
                                ?.length ? (

                                <ul>

                                    {
                                        aiAnalysis
                                            .missing_fields
                                            .map(
                                                (
                                                    field,
                                                    index
                                                ) => (
                                                    <li
                                                        key={
                                                            index
                                                        }
                                                    >
                                                        {
                                                            field
                                                        }
                                                    </li>
                                                )
                                            )
                                    }

                                </ul>

                            ) : (

                                <p>
                                    No required fields
                                    are missing.
                                </p>

                            )}

                        </div>


                        {/* DOCUMENT MISMATCHES */}

                        <div className="ai-analysis-block">

                            <h3>
                                Document Mismatches
                            </h3>


                            {aiAnalysis
                                .extracted_data
                                ?.mismatches
                                ?.length ? (

                                <ul>

                                    {
                                        aiAnalysis
                                            .extracted_data
                                            .mismatches
                                            .map(
                                                (
                                                    mismatch,
                                                    index
                                                ) => (
                                                    <li
                                                        key={
                                                            index
                                                        }
                                                    >
                                                        {
                                                            mismatch
                                                        }
                                                    </li>
                                                )
                                            )
                                    }

                                </ul>

                            ) : (

                                <p>
                                    No mismatches
                                    detected between
                                    the uploaded document
                                    and submitted invoice.
                                </p>

                            )}

                        </div>

                        {/* POLICY EVIDENCE */}

                        <div className="ai-analysis-block">

                            <h3>
                                Policy Evidence
                            </h3>

                            {aiAnalysis
                                .extracted_data
                                ?.policy_evidence
                                ?.length ? (

                                <div className="policy-evidence-list">

                                    {aiAnalysis
                                        .extracted_data
                                        .policy_evidence
                                        .map((evidence) => {
                                            const similarity =
                                                Math.max(
                                                    0,
                                                    (
                                                        1 -
                                                        Number(
                                                            evidence.distance
                                                        )
                                                    ) * 100
                                                );

                                            return (
                                                <div
                                                    className="policy-evidence-card"
                                                    key={
                                                        evidence.chunk_id
                                                    }
                                                >

                                                    <div className="policy-evidence-header">

                                                        <div>
                                                            <strong>
                                                                {
                                                                    evidence
                                                                        .policy_title
                                                                }
                                                            </strong>

                                                            <span>
                                                                Policy evidence
                                                            </span>
                                                        </div>

                                                        <span className="policy-similarity">
                                                            {
                                                                similarity.toFixed(
                                                                    1
                                                                )
                                                            }
                                                            % match
                                                        </span>

                                                    </div>


                                                    <p className="policy-evidence-content">
                                                        {
                                                            evidence.content
                                                        }
                                                    </p>


                                                    <div className="policy-evidence-meta">

                                                        <span>
                                                            Policy ID #
                                                            {
                                                                evidence
                                                                    .policy_document_id
                                                            }
                                                        </span>

                                                        <span>
                                                            Chunk #
                                                            {
                                                                evidence
                                                                    .chunk_index +
                                                                1
                                                            }
                                                        </span>

                                                    </div>

                                                </div>
                                            );
                                        })}

                                </div>

                            ) : (

                                <p>
                                    No relevant policy evidence
                                    was found for this invoice.
                                </p>

                            )}

                        </div>

                        {/* POSSIBLE DUPLICATE */}

                        {aiAnalysis
                            .duplicate_risk && (

                                <div className="ai-analysis-block">

                                    <h3>
                                        Possible Duplicate
                                    </h3>

                                    <p>
                                        The system found
                                        another invoice that
                                        may be a duplicate.
                                    </p>

                                    {aiAnalysis
                                        .possible_duplicate_invoice_id && (

                                            <p>
                                                Possible duplicate
                                                invoice ID:{" "}

                                                <strong>
                                                    {
                                                        aiAnalysis
                                                            .possible_duplicate_invoice_id
                                                    }
                                                </strong>
                                            </p>

                                        )}

                                </div>

                            )}


                        {/* EXTRACTED DOCUMENT DATA */}

                        {aiAnalysis
                            .extracted_data
                            ?.document && (

                                <div className="ai-analysis-block">

                                    <h3>
                                        Extracted Document Data
                                    </h3>


                                    <div className="extracted-data-grid">

                                        <div>
                                            <span>
                                                Vendor
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .vendor_name ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Invoice Number
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .invoice_number ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Invoice Date
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .invoice_date ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Due Date
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .due_date ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Currency
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .currency ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Total
                                            </span>

                                            <strong>

                                                {aiAnalysis
                                                    .extracted_data
                                                    .document
                                                    .total_amount !==
                                                    null
                                                    ? formatMoney(
                                                        aiAnalysis
                                                            .extracted_data
                                                            .document
                                                            .total_amount,

                                                        aiAnalysis
                                                            .extracted_data
                                                            .document
                                                            .currency ||
                                                        invoice
                                                            .currency
                                                    )
                                                    : "—"}

                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Extraction Method
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .extraction_method ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Document Type
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .document_type_guess ||
                                                    "—"
                                                }
                                            </strong>
                                        </div>


                                        <div>
                                            <span>
                                                Extracted Line Items
                                            </span>

                                            <strong>
                                                {
                                                    aiAnalysis
                                                        .extracted_data
                                                        .document
                                                        .line_items
                                                        ?.length ||
                                                    0
                                                }
                                            </strong>
                                        </div>

                                    </div>

                                </div>

                            )}

                    </>

                )}

            </section>


            {/* -------------------------
            REVIEW ACTIONS
        -------------------------- */}

            {(canStartReview ||
                canDecide ||
                canResubmit) && (

                    <section className="dashboard-section">

                        <div className="section-header">

                            <div>
                                <h2>
                                    Review Actions
                                </h2>

                                <p>
                                    Take the next
                                    permitted workflow
                                    action.
                                </p>
                            </div>

                        </div>


                        {canStartReview && (

                            <div className="review-action-panel">

                                <div className="form-group">

                                    <label>
                                        Review Comments
                                    </label>

                                    <textarea
                                        rows="4"

                                        value={
                                            reviewComments
                                        }

                                        onChange={
                                            (event) =>
                                                setReviewComments(
                                                    event
                                                        .target
                                                        .value
                                                )
                                        }

                                        placeholder="Optional comments before starting review"
                                    />

                                </div>


                                <button
                                    className="primary-button"

                                    onClick={
                                        handleStartReview
                                    }

                                    disabled={
                                        actionLoading
                                    }
                                >
                                    Start Review
                                </button>

                            </div>

                        )}


                        {canDecide && (

                            <div className="review-action-panel">

                                <div className="form-group">

                                    <label>
                                        Decision Comments
                                    </label>

                                    <textarea
                                        rows="4"

                                        value={
                                            decisionComments
                                        }

                                        onChange={
                                            (event) =>
                                                setDecisionComments(
                                                    event
                                                        .target
                                                        .value
                                                )
                                        }

                                        placeholder="Required for rejection or document requests"
                                    />

                                </div>


                                <div className="decision-actions">

                                    <button
                                        className="decision-button approve"

                                        onClick={() =>
                                            handleDecision(
                                                "approved"
                                            )
                                        }

                                        disabled={
                                            actionLoading
                                        }
                                    >
                                        Approve
                                    </button>


                                    <button
                                        className="decision-button request"

                                        onClick={() =>
                                            handleDecision(
                                                "needs_documents"
                                            )
                                        }

                                        disabled={
                                            actionLoading
                                        }
                                    >
                                        Request Documents
                                    </button>


                                    <button
                                        className="decision-button reject"

                                        onClick={() =>
                                            handleDecision(
                                                "rejected"
                                            )
                                        }

                                        disabled={
                                            actionLoading
                                        }
                                    >
                                        Reject
                                    </button>

                                </div>

                            </div>

                        )}


                        {canResubmit && (

                            <div className="review-action-panel">

                                <div className="form-group">

                                    <label>
                                        Resubmission Comments
                                    </label>

                                    <textarea
                                        rows="4"

                                        value={
                                            reviewComments
                                        }

                                        onChange={
                                            (event) =>
                                                setReviewComments(
                                                    event
                                                        .target
                                                        .value
                                                )
                                        }

                                        placeholder="Describe the additional documents or changes"
                                    />

                                </div>


                                {resubmitError && (
                                    <div className="inline-action-error">
                                        {
                                            resubmitError
                                        }
                                    </div>
                                )}


                                <button
                                    className="primary-button"

                                    onClick={
                                        handleResubmit
                                    }

                                    disabled={
                                        actionLoading
                                    }
                                >
                                    Resubmit Invoice
                                </button>

                            </div>

                        )}

                    </section>

                )}


            {/* -------------------------
            REVIEW HISTORY
        -------------------------- */}

            <section className="dashboard-section">

                <div className="section-header">

                    <div>
                        <h2>
                            Review History
                        </h2>

                        <p>
                            Complete invoice
                            decision history
                        </p>
                    </div>

                </div>


                {reviews.length === 0 ? (

                    <div className="empty-state">
                        <div>
                            <strong>No review activity yet</strong>
                            <p>
                                Review actions will appear here as the invoice moves through the workflow.
                            </p>
                        </div>
                    </div>

                ) : (

                    <div className="review-timeline">

                        {
                            reviews.map(
                                (review) => (

                                    <div
                                        className="review-event"

                                        key={
                                            review.id
                                        }
                                    >

                                        <div className="timeline-marker" />


                                        <div className="review-event-content">

                                            <div className="review-event-header">

                                                <strong>
                                                    {
                                                        review
                                                            .action
                                                            .replaceAll(
                                                                "_",
                                                                " "
                                                            )
                                                    }
                                                </strong>


                                                <span>
                                                    {formatDateTime(
                                                        review
                                                            .created_at
                                                    )}
                                                </span>

                                            </div>


                                            <p>
                                                {
                                                    review
                                                        .previous_status
                                                        .replaceAll(
                                                            "_",
                                                            " "
                                                        )
                                                }

                                                {" → "}

                                                {
                                                    review
                                                        .new_status
                                                        .replaceAll(
                                                            "_",
                                                            " "
                                                        )
                                                }
                                            </p>


                                            {review.comments && (

                                                <blockquote>
                                                    {
                                                        review
                                                            .comments
                                                    }
                                                </blockquote>

                                            )}


                                            <small>
                                                Performed by
                                                User #
                                                {
                                                    review
                                                        .performed_by_user_id
                                                }
                                            </small>

                                        </div>

                                    </div>
                                )
                            )
                        }

                    </div>

                )}

            </section>

        </div>
    );
}


export default InvoiceDetailPage;