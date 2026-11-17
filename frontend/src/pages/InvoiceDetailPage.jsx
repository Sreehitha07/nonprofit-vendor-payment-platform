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
  
    const [invoice, setInvoice] = useState(null);
    const [vendor, setVendor] = useState(null);
    const [documents, setDocuments] = useState([]);
    const [reviews, setReviews] = useState([]);
  
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
  
    const [file, setFile] = useState(null);
    const [documentType, setDocumentType] =
      useState("supporting_document");
  
    const [uploading, setUploading] =
      useState(false);
  
    const [reviewComments, setReviewComments] =
      useState("");
  
    const [decisionComments, setDecisionComments] =
      useState("");
  
    const [actionLoading, setActionLoading] =
      useState(false);
  
  
    const loadInvoiceData = useCallback(async () => {
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
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }, [invoiceId]);
  
  
    useEffect(() => {
      loadInvoiceData();
    }, [loadInvoiceData]);
  
  
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
        ).format(Number(value || 0));
      } catch {
        return `${currency} ${value}`;
      }
    };
  
  
    const formatDateTime = (value) => {
      if (!value) {
        return "—";
      }
  
      return new Date(value).toLocaleString();
    };
  
  
    const formatFileSize = (bytes) => {
      if (bytes < 1024) {
        return `${bytes} B`;
      }
  
      if (bytes < 1024 * 1024) {
        return `${(
          bytes / 1024
        ).toFixed(1)} KB`;
      }
  
      return `${(
        bytes /
        (1024 * 1024)
      ).toFixed(1)} MB`;
    };
  
  
    const handleUpload = async (event) => {
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
        const formData = new FormData();
  
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
  
        setDocuments(documentData);
  
        const input =
          document.getElementById(
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
  
  
    const handleDownload = async (document) => {
      setError("");
  
      try {
        const token =
          localStorage.getItem(
            "access_token"
          );
  
        const response = await fetch(
          `${API_BASE_URL}/api/documents/${document.id}/download`,
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
              data.detail || message;
          } catch {
            // Keep fallback message.
          }
  
          throw new Error(message);
        }
  
        const blob =
          await response.blob();
  
        const url =
          window.URL.createObjectURL(
            blob
          );
  
        const link =
          document.createElement("a");
  
        link.href = url;
        link.download =
          document.original_filename;
  
        document.body.appendChild(link);
        link.click();
        link.remove();
  
        window.URL.revokeObjectURL(url);
      } catch (err) {
        setError(err.message);
      }
    };
  
  
    const handleDeleteDocument =
      async (document) => {
        const confirmed =
          window.confirm(
            `Delete "${document.original_filename}"?`
          );
  
        if (!confirmed) {
          return;
        }
  
        setError("");
        setSuccess("");
  
        try {
          await apiRequest(
            `/api/documents/${document.id}`,
            {
              method: "DELETE",
            }
          );
  
          setSuccess(
            "Document deleted successfully."
          );
  
          setDocuments((current) =>
            current.filter(
              (item) =>
                item.id !== document.id
            )
          );
        } catch (err) {
          setError(err.message);
        }
      };
  
  
    const handleStartReview = async () => {
      setActionLoading(true);
      setError("");
      setSuccess("");
  
      try {
        await apiRequest(
          `/api/invoices/${invoiceId}/review/start`,
          {
            method: "POST",
  
            body: JSON.stringify({
              comments:
                reviewComments.trim() ||
                null,
            }),
          }
        );
  
        setReviewComments("");
  
        setSuccess(
          "Invoice review started."
        );
  
        await loadInvoiceData();
      } catch (err) {
        setError(err.message);
      } finally {
        setActionLoading(false);
      }
    };
  
  
    const handleDecision = async (
      decision
    ) => {
      const comments =
        decisionComments.trim();
  
      if (
        ["rejected", "needs_documents"]
          .includes(decision) &&
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
  
            body: JSON.stringify({
              decision,
              comments:
                comments || null,
            }),
          }
        );
  
        setDecisionComments("");
  
        if (decision === "approved") {
          setSuccess(
            "Invoice approved successfully."
          );
        }
  
        if (decision === "rejected") {
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
        setError(err.message);
      } finally {
        setActionLoading(false);
      }
    };

    const latestDocumentRequest = [...reviews]
        .filter(
            (review) =>
                review.action === "requested_documents"
        )
    .sort(
        (a, b) =>
            new Date(b.created_at) -
            new Date(a.created_at)
    )[0];

    const hasNewVendorDocument =
        latestDocumentRequest &&
        documents.some(
            (documentItem) =>
                documentItem.uploaded_by_user_id ===
                    user?.id &&
                new Date(documentItem.uploaded_at) >=
                    new Date(
                        latestDocumentRequest.created_at
                    )
        );
  
        const handleResubmit = async () => {
            if (!hasNewVendorDocument) {
              setError(
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
  
            body: JSON.stringify({
              comments:
                reviewComments.trim() ||
                null,
            }),
          }
        );
  
        setReviewComments("");
  
        setSuccess(
          "Invoice resubmitted successfully."
        );
  
        await loadInvoiceData();
      } catch (err) {
        setError(err.message);
      } finally {
        setActionLoading(false);
      }
    };
  
  
    if (loading) {
      return (
        <div className="page">
          <p>Loading invoice...</p>
        </div>
      );
    }
  
  
    if (!invoice) {
      return (
        <div className="page">
          <div className="error-message">
            {error || "Invoice not found."}
          </div>
        </div>
      );
    }
  
  
    const canStartReview =
      ["staff", "manager", "admin"].includes(
        user?.role
      ) &&
      invoice.status === "submitted";
  
  
    const canDecide =
      ["manager", "admin"].includes(
        user?.role
      ) &&
      invoice.status === "under_review";
  
  
    const canResubmit =
      user?.role === "vendor" &&
      invoice.status === "needs_documents";
  
  
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
              {invoice.invoice_number}
            </h1>
  
            <p>
              {vendor?.name ||
                `Vendor #${invoice.vendor_id}`}
            </p>
          </div>
  
          <span className="detail-status">
            {invoice.status.replaceAll(
              "_",
              " "
            )}
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
  
        <section className="invoice-summary-grid">
          <div className="invoice-summary-card">
            <span>Invoice Date</span>
  
            <strong>
              {invoice.invoice_date}
            </strong>
          </div>
  
          <div className="invoice-summary-card">
            <span>Due Date</span>
  
            <strong>
              {invoice.due_date || "—"}
            </strong>
          </div>
  
          <div className="invoice-summary-card">
            <span>Total Amount</span>
  
            <strong>
              {formatMoney(
                invoice.total_amount,
                invoice.currency
              )}
            </strong>
          </div>
  
          <div className="invoice-summary-card">
            <span>Currency</span>
  
            <strong>
              {invoice.currency}
            </strong>
          </div>
        </section>
  
        <section className="dashboard-section">
          <div className="section-header">
            <div>
              <h2>Line Items</h2>
  
              <p>
                Invoice charges and categories
              </p>
            </div>
          </div>
  
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Category</th>
                  <th>Quantity</th>
                  <th>Unit Price</th>
                  <th>Line Total</th>
                </tr>
              </thead>
  
              <tbody>
                {invoice.line_items.map(
                  (item) => (
                    <tr key={item.id}>
                      <td>
                        {item.description}
                      </td>
  
                      <td>
                        {item.category || "—"}
                      </td>
  
                      <td>
                        {item.quantity}
                      </td>
  
                      <td>
                        {formatMoney(
                          item.unit_price,
                          invoice.currency
                        )}
                      </td>
  
                      <td>
                        <strong>
                          {formatMoney(
                            item.line_total,
                            invoice.currency
                          )}
                        </strong>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </section>
  
        <section className="dashboard-section">
          <div className="section-header">
            <div>
              <h2>Supporting Documents</h2>
  
              <p>
                Upload invoices, purchase
                orders, receipts and other
                supporting files.
              </p>
            </div>
          </div>
  
          <form
            className="document-upload-form"
            onSubmit={handleUpload}
          >
            <div className="form-group">
              <label htmlFor="document_type">
                Document Type
              </label>
  
              <select
                id="document_type"
                value={documentType}
                onChange={(event) =>
                  setDocumentType(
                    event.target.value
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
              <label htmlFor="document_file">
                File
              </label>
  
              <input
                id="document_file"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                onChange={(event) =>
                  setFile(
                    event.target.files?.[0] ||
                    null
                  )
                }
                required
              />
            </div>
  
            <button
              className="primary-button"
              type="submit"
              disabled={uploading}
            >
              {uploading
                ? "Uploading..."
                : "Upload Document"}
            </button>
          </form>
  
          <p className="upload-note">
            PDF, PNG, JPG or JPEG · Maximum
            file size 10 MB
          </p>
  
          {documents.length === 0 ? (
            <div className="empty-state">
              No supporting documents uploaded.
            </div>
          ) : (
            <div className="document-list">
              {documents.map(
                (documentItem) => (
                  <div
                    className="document-card"
                    key={documentItem.id}
                  >
                    <div>
                      <strong>
                        {
                          documentItem.original_filename
                        }
                      </strong>
  
                      <div className="document-meta">
                        <span>
                          {documentItem.document_type.replaceAll(
                            "_",
                            " "
                          )}
                        </span>
  
                        <span>
                          {formatFileSize(
                            documentItem.file_size
                          )}
                        </span>
  
                        <span>
                          {
                            documentItem.verification_status
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
              )}
            </div>
          )}
        </section>
  
        {(canStartReview ||
          canDecide ||
          canResubmit) && (
          <section className="dashboard-section">
            <div className="section-header">
              <div>
                <h2>Review Actions</h2>
  
                <p>
                  Take the next permitted
                  workflow action.
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
                    value={reviewComments}
                    onChange={(event) =>
                      setReviewComments(
                        event.target.value
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
                    onChange={(event) =>
                      setDecisionComments(
                        event.target.value
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
                    value={reviewComments}
                    onChange={(event) =>
                      setReviewComments(
                        event.target.value
                      )
                    }
                    placeholder="Describe the additional documents or changes"
                  />
                </div>
  
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
  
        <section className="dashboard-section">
          <div className="section-header">
            <div>
              <h2>Review History</h2>
  
              <p>
                Complete invoice decision
                history
              </p>
            </div>
          </div>
  
          {reviews.length === 0 ? (
            <div className="empty-state">
              No review activity yet.
            </div>
          ) : (
            <div className="review-timeline">
              {reviews.map((review) => (
                <div
                  className="review-event"
                  key={review.id}
                >
                  <div className="timeline-marker" />
  
                  <div className="review-event-content">
                    <div className="review-event-header">
                      <strong>
                        {review.action.replaceAll(
                          "_",
                          " "
                        )}
                      </strong>
  
                      <span>
                        {formatDateTime(
                          review.created_at
                        )}
                      </span>
                    </div>
  
                    <p>
                      {review.previous_status.replaceAll(
                        "_",
                        " "
                      )}
                      {" → "}
                      {review.new_status.replaceAll(
                        "_",
                        " "
                      )}
                    </p>
  
                    {review.comments && (
                      <blockquote>
                        {review.comments}
                      </blockquote>
                    )}
  
                    <small>
                      Performed by User #
                      {
                        review.performed_by_user_id
                      }
                    </small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    );
  }
  
  export default InvoiceDetailPage;