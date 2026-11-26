import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../services/api";


function PaymentsPage() {
    const { user } = useAuth();

    const [payments, setPayments] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [vendors, setVendors] = useState([]);

    const [statusFilter, setStatusFilter] =
        useState("");

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");

    const [success, setSuccess] =
        useState("");

    const [failurePaymentId, setFailurePaymentId] =
        useState(null);

    const [failureReason, setFailureReason] =
        useState("");

    const [actionLoading, setActionLoading] =
        useState(false);


    const canManagePayments =
        ["manager", "admin"].includes(
            user?.role
        );


    const loadData = useCallback(async () => {
        setLoading(true);
        setError("");

        try {
            const params = new URLSearchParams();

            if (statusFilter) {
                params.append(
                    "payment_status",
                    statusFilter
                );
            }

            const query = params.toString();

            const [
                paymentData,
                invoiceData,
                vendorData,
            ] = await Promise.all([
                apiRequest(
                    `/api/payments${query ? `?${query}` : ""
                    }`
                ),

                apiRequest("/api/invoices"),

                apiRequest("/api/vendors")
                    .catch(() => []),
            ]);

            setPayments(paymentData);
            setInvoices(invoiceData);
            setVendors(vendorData);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);


    useEffect(() => {
        loadData();
    }, [loadData]);


    const invoiceMap = useMemo(() => {
        const map = {};

        invoices.forEach((invoice) => {
            map[invoice.id] = invoice;
        });

        return map;
    }, [invoices]);


    const vendorMap = useMemo(() => {
        const map = {};

        vendors.forEach((vendor) => {
            map[vendor.id] = vendor.name;
        });

        return map;
    }, [vendors]);


    const paymentInvoiceIds =
        useMemo(
            () =>
                new Set(
                    payments.map(
                        (payment) =>
                            payment.invoice_id
                    )
                ),
            [payments]
        );


    const payableInvoices =
        useMemo(
            () =>
                invoices.filter(
                    (invoice) =>
                        invoice.status ===
                        "approved" &&
                        !paymentInvoiceIds.has(
                            invoice.id
                        )
                ),
            [
                invoices,
                paymentInvoiceIds,
            ]
        );


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

        return new Date(
            value
        ).toLocaleString();
    };


    const clearMessages = () => {
        setError("");
        setSuccess("");
    };


    const schedulePayment =
        async (invoiceId) => {
            clearMessages();
            setActionLoading(true);

            try {
                await apiRequest(
                    `/api/invoices/${invoiceId}/payments`,
                    {
                        method: "POST",
                    }
                );

                setSuccess(
                    "Payment scheduled successfully."
                );

                await loadData();
            } catch (err) {
                setError(err.message);
            } finally {
                setActionLoading(false);
            }
        };


    const startPayment =
        async (paymentId) => {
            clearMessages();
            setActionLoading(true);

            try {
                await apiRequest(
                    `/api/payments/${paymentId}/start`,
                    {
                        method: "POST",
                    }
                );

                setSuccess(
                    "Payment processing started."
                );

                await loadData();
            } catch (err) {
                setError(err.message);
            } finally {
                setActionLoading(false);
            }
        };


    const completePayment =
        async (paymentId) => {
            clearMessages();
            setActionLoading(true);

            try {
                await apiRequest(
                    `/api/payments/${paymentId}/complete`,
                    {
                        method: "POST",
                    }
                );

                setSuccess(
                    "Payment completed successfully."
                );

                await loadData();
            } catch (err) {
                setError(err.message);
            } finally {
                setActionLoading(false);
            }
        };


    const openFailureForm =
        (paymentId) => {
            clearMessages();

            setFailurePaymentId(
                paymentId
            );

            setFailureReason("");
        };


    const cancelFailure = () => {
        setFailurePaymentId(null);
        setFailureReason("");
    };


    const failPayment = async () => {
        if (!failureReason.trim()) {
            setError(
                "Please enter a failure reason."
            );

            return;
        }

        clearMessages();
        setActionLoading(true);

        try {
            await apiRequest(
                `/api/payments/${failurePaymentId}/fail`,
                {
                    method: "POST",

                    body: JSON.stringify({
                        reason:
                            failureReason.trim(),
                    }),
                }
            );

            setSuccess(
                "Payment marked as failed."
            );

            cancelFailure();

            await loadData();
        } catch (err) {
            setError(err.message);
        } finally {
            setActionLoading(false);
        }
    };


    const completedTotal =
        payments
            .filter(
                (payment) =>
                    payment.status ===
                    "completed"
            )
            .reduce(
                (sum, payment) =>
                    sum +
                    Number(payment.amount),
                0
            );


    const processingCount =
        payments.filter(
            (payment) =>
                payment.status ===
                "processing"
        ).length;


    const failedCount =
        payments.filter(
            (payment) =>
                payment.status ===
                "failed"
        ).length;


    return (
        <div className="page">
            <div className="page-header">
                <div>
                    <p className="page-eyebrow">
                        Financial Operations
                    </p>

                    <h1>Payments</h1>

                    <p>
                        Schedule and monitor
                        approved invoice payments.
                    </p>
                </div>
            </div>


            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {success && (
                <div className="success-message">
                    {success}
                </div>
            )}


            <section className="payment-summary-grid">
                <div className="stat-card">
                    <p>Total Payments</p>

                    <h2>
                        {payments.length}
                    </h2>

                    <span>
                        Payment records
                    </span>
                </div>

                <div className="stat-card">
                    <p>Processing</p>

                    <h2>
                        {processingCount}
                    </h2>

                    <span>
                        Currently processing
                    </span>
                </div>

                <div className="stat-card">
                    <p>Completed Value</p>

                    <h2>
                        {formatMoney(
                            completedTotal
                        )}
                    </h2>

                    <span>
                        Successfully completed
                    </span>
                </div>

                <div className="stat-card">
                    <p>Failed</p>

                    <h2>
                        {failedCount}
                    </h2>

                    <span>
                        Failed payments
                    </span>
                </div>
            </section>


            {canManagePayments &&
                payableInvoices.length >
                0 && (
                    <section className="dashboard-section">
                        <div className="section-header">
                            <div>
                                <h2>
                                    Approved Invoices
                                </h2>

                                <p>
                                    Ready to be scheduled
                                    for payment
                                </p>
                            </div>
                        </div>

                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Invoice</th>
                                        <th>Vendor</th>
                                        <th>Amount</th>
                                        <th>Status</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {payableInvoices.map(
                                        (invoice) => (
                                            <tr key={invoice.id}>
                                                <td>
                                                    <strong>
                                                        {
                                                            invoice.invoice_number
                                                        }
                                                    </strong>
                                                </td>

                                                <td>
                                                    {vendorMap[
                                                        invoice.vendor_id
                                                    ] ||
                                                        `Vendor #${invoice.vendor_id}`}
                                                </td>

                                                <td>
                                                    {formatMoney(
                                                        invoice.total_amount,
                                                        invoice.currency
                                                    )}
                                                </td>

                                                <td>
                                                    <span className="table-status status-approved">
                                                        Approved
                                                    </span>
                                                </td>

                                                <td>
                                                    <button
                                                        className="primary-button small-button"
                                                        disabled={
                                                            actionLoading
                                                        }
                                                        onClick={() =>
                                                            schedulePayment(
                                                                invoice.id
                                                            )
                                                        }
                                                    >
                                                        Schedule Payment
                                                    </button>
                                                </td>
                                            </tr>
                                        )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}


            <section className="dashboard-section">
                <div className="section-header payment-list-header">
                    <div>
                        <h2>
                            Payment History
                        </h2>

                        <p>
                            {payments.length} payment
                            {payments.length === 1
                                ? ""
                                : "s"}
                        </p>
                    </div>

                    <select
                        className="payment-filter"
                        value={statusFilter}
                        onChange={(event) =>
                            setStatusFilter(
                                event.target.value
                            )
                        }
                    >
                        <option value="">
                            All statuses
                        </option>

                        <option value="scheduled">
                            Scheduled
                        </option>

                        <option value="processing">
                            Processing
                        </option>

                        <option value="completed">
                            Completed
                        </option>

                        <option value="failed">
                            Failed
                        </option>
                    </select>
                </div>


                {loading ? (
                    <div className="loading-state">
                        <span className="loading-spinner" />
                        <span>Loading payments...</span>
                    </div>
                ) : payments.length === 0 ? (
                    <div className="empty-state">
                        <div>
                            <strong>No payments found</strong>
                            <p>
                                Payments will appear here after approved invoices are scheduled.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Payment</th>
                                    <th>Invoice</th>
                                    <th>Vendor</th>
                                    <th>Amount</th>
                                    <th>Method</th>
                                    <th>Status</th>
                                    <th>Scheduled</th>
                                    <th>Transaction</th>

                                    {canManagePayments && (
                                        <th>Actions</th>
                                    )}
                                </tr>
                            </thead>

                            <tbody>
                                {payments.map(
                                    (payment) => {
                                        const invoice =
                                            invoiceMap[
                                            payment.invoice_id
                                            ];

                                        return (
                                            <tr key={payment.id}>
                                                <td>
                                                    #{payment.id}
                                                </td>

                                                <td>
                                                    <strong>
                                                        {invoice
                                                            ?.invoice_number ||
                                                            `Invoice #${payment.invoice_id}`}
                                                    </strong>
                                                </td>

                                                <td>
                                                    {invoice
                                                        ? vendorMap[
                                                        invoice.vendor_id
                                                        ] ||
                                                        `Vendor #${invoice.vendor_id}`
                                                        : "—"}
                                                </td>

                                                <td>
                                                    {formatMoney(
                                                        payment.amount,
                                                        payment.currency
                                                    )}
                                                </td>

                                                <td>
                                                    {
                                                        payment.payment_method
                                                    }
                                                </td>

                                                <td>
                                                    <span className={`table-status status-${payment.status}`}>
                                                        {payment.status.replaceAll(
                                                            "_",
                                                            " "
                                                        )}
                                                    </span>
                                                </td>

                                                <td>
                                                    {formatDateTime(
                                                        payment.scheduled_at
                                                    )}
                                                </td>

                                                <td>
                                                    {payment.transaction_reference ||
                                                        "—"}
                                                </td>

                                                {canManagePayments && (
                                                    <td>
                                                        <div className="payment-actions">
                                                            {payment.status ===
                                                                "scheduled" && (
                                                                    <button
                                                                        className="text-button"
                                                                        disabled={
                                                                            actionLoading
                                                                        }
                                                                        onClick={() =>
                                                                            startPayment(
                                                                                payment.id
                                                                            )
                                                                        }
                                                                    >
                                                                        Start
                                                                    </button>
                                                                )}

                                                            {payment.status ===
                                                                "processing" && (
                                                                    <>
                                                                        <button
                                                                            className="text-button payment-complete"
                                                                            disabled={
                                                                                actionLoading
                                                                            }
                                                                            onClick={() =>
                                                                                completePayment(
                                                                                    payment.id
                                                                                )
                                                                            }
                                                                        >
                                                                            Complete
                                                                        </button>

                                                                        <button
                                                                            className="text-button danger"
                                                                            disabled={
                                                                                actionLoading
                                                                            }
                                                                            onClick={() =>
                                                                                openFailureForm(
                                                                                    payment.id
                                                                                )
                                                                            }
                                                                        >
                                                                            Fail
                                                                        </button>
                                                                    </>
                                                                )}
                                                        </div>
                                                    </td>
                                                )}
                                            </tr>
                                        );
                                    }
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>


            {failurePaymentId && (
                <section className="form-card payment-failure-card">
                    <div className="section-header">
                        <div>
                            <h2>
                                Mark Payment as Failed
                            </h2>

                            <p>
                                Payment #
                                {failurePaymentId}
                            </p>
                        </div>
                    </div>

                    <div className="form-group">
                        <label>
                            Failure Reason
                        </label>

                        <textarea
                            rows="4"
                            value={failureReason}
                            onChange={(event) =>
                                setFailureReason(
                                    event.target.value
                                )
                            }
                            placeholder="Example: Sandbox bank processing failure."
                        />
                    </div>

                    <div className="form-actions payment-failure-actions">
                        <button
                            className="decision-button reject"
                            onClick={failPayment}
                            disabled={actionLoading}
                        >
                            Mark Failed
                        </button>

                        <button
                            className="secondary-button"
                            onClick={cancelFailure}
                            disabled={actionLoading}
                        >
                            Cancel
                        </button>
                    </div>
                </section>
            )}
        </div>
    );
}

export default PaymentsPage;