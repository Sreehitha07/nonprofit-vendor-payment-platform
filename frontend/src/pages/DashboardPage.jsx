import { useEffect, useState } from "react";

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
        <p>Loading dashboard...</p>
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

  const formatMoney = (value) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(Number(value || 0));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="page-eyebrow">
            Overview
          </p>

          <h1>Dashboard</h1>

          <p>
            Welcome back,{" "}
            {user?.full_name || user?.email}.
          </p>
        </div>

        <span className="role-pill">
          {user?.role}
        </span>
      </div>

      <section className="dashboard-grid">
        <div className="stat-card">
          <p>Total Invoices</p>

          <h2>
            {dashboard?.total_invoices ?? 0}
          </h2>

          <span>
            Across your accessible records
          </span>
        </div>

        <div className="stat-card">
          <p>Total Payments</p>

          <h2>
            {dashboard?.total_payments ?? 0}
          </h2>

          <span>
            Payment records created
          </span>
        </div>

        <div className="stat-card">
          <p>Completed Payments</p>

          <h2>
            {formatMoney(
              dashboard?.completed_payment_total
            )}
          </h2>

          <span>
            Successfully processed
          </span>
        </div>

        <div className="stat-card">
          <p>Unread Notifications</p>

          <h2>
            {dashboard?.unread_notifications ?? 0}
          </h2>

          <span>
            Require your attention
          </span>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h2>Invoice Status</h2>
            <p>
              Current workflow distribution
            </p>
          </div>
        </div>

        <div className="status-grid">
          {Object.entries(
            dashboard?.invoice_status_counts || {}
          ).map(([status, count]) => (
            <div
              className="status-card"
              key={status}
            >
              <span>
                {status.replaceAll("_", " ")}
              </span>

              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h2>Payment Status</h2>
            <p>
              Current payment processing state
            </p>
          </div>
        </div>

        <div className="status-grid">
          {Object.entries(
            dashboard?.payment_status_counts || {}
          ).map(([status, count]) => (
            <div
              className="status-card"
              key={status}
            >
              <span>
                {status.replaceAll("_", " ")}
              </span>

              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h2>Recent Invoices</h2>

            <p>
              Latest invoice activity
            </p>
          </div>
        </div>

        {dashboard?.recent_invoices?.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Vendor</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {dashboard.recent_invoices.map(
                  (invoice) => (
                    <tr key={invoice.id}>
                      <td>
                        {invoice.invoice_number}
                      </td>

                      <td>
                        Vendor #{invoice.vendor_id}
                      </td>

                      <td>
                        {invoice.invoice_date}
                      </td>

                      <td>
                        {formatMoney(
                          invoice.total_amount
                        )}
                      </td>

                      <td>
                        <span className="table-status">
                          {invoice.status.replaceAll(
                            "_",
                            " "
                          )}
                        </span>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            No invoices found.
          </div>
        )}
      </section>
    </div>
  );
}

export default DashboardPage;