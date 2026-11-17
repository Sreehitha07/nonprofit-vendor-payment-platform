import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../services/api";
import { Link } from "react-router";

const emptyLineItem = () => ({
  description: "",
  quantity: "1",
  unit_price: "",
  category: "",
});

function InvoicesPage() {
  const { user } = useAuth();

  const [invoices, setInvoices] = useState([]);
  const [vendors, setVendors] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);

  const [vendorFilter, setVendorFilter] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("");

  const [formData, setFormData] = useState({
    vendor_id: "",
    invoice_number: "",
    invoice_date: "",
    due_date: "",
    currency: "USD",
    line_items: [emptyLineItem()],
  });

  const vendorMap = useMemo(() => {
    const map = {};

    vendors.forEach((vendor) => {
      map[vendor.id] = vendor.name;
    });

    return map;
  }, [vendors]);

  const estimatedTotal = useMemo(() => {
    return formData.line_items.reduce(
      (total, item) => {
        const quantity =
          Number(item.quantity) || 0;

        const price =
          Number(item.unit_price) || 0;

        return total + quantity * price;
      },
      0
    );
  }, [formData.line_items]);

  const loadVendors = async () => {
    try {
      const data =
        await apiRequest("/api/vendors");

      setVendors(data);
    } catch (err) {
      console.error(
        "Failed to load vendors:",
        err
      );
    }
  };

  const loadInvoices = async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();

      if (vendorFilter) {
        params.append(
          "vendor_id",
          vendorFilter
        );
      }

      if (statusFilter) {
        params.append(
          "invoice_status",
          statusFilter
        );
      }

      const query = params.toString();

      const data = await apiRequest(
        `/api/invoices${
          query ? `?${query}` : ""
        }`
      );

      setInvoices(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVendors();
  }, []);

  useEffect(() => {
    loadInvoices();
  }, [vendorFilter, statusFilter]);

  const resetForm = () => {
    setFormData({
      vendor_id:
        user?.role === "vendor"
          ? String(user.vendor_id || "")
          : "",
      invoice_number: "",
      invoice_date: "",
      due_date: "",
      currency: "USD",
      line_items: [emptyLineItem()],
    });

    setShowForm(false);
  };

  const handleCreateClick = () => {
    setError("");
    setSuccess("");

    setFormData({
      vendor_id:
        user?.role === "vendor"
          ? String(user.vendor_id || "")
          : "",
      invoice_number: "",
      invoice_date: "",
      due_date: "",
      currency: "USD",
      line_items: [emptyLineItem()],
    });

    setShowForm(true);
  };

  const handleFieldChange = (event) => {
    const { name, value } = event.target;

    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleLineItemChange = (
    index,
    event
  ) => {
    const { name, value } = event.target;

    setFormData((current) => {
      const updatedItems = [
        ...current.line_items,
      ];

      updatedItems[index] = {
        ...updatedItems[index],
        [name]: value,
      };

      return {
        ...current,
        line_items: updatedItems,
      };
    });
  };

  const addLineItem = () => {
    setFormData((current) => ({
      ...current,
      line_items: [
        ...current.line_items,
        emptyLineItem(),
      ],
    }));
  };

  const removeLineItem = (index) => {
    setFormData((current) => {
      if (current.line_items.length === 1) {
        return current;
      }

      return {
        ...current,
        line_items:
          current.line_items.filter(
            (_, itemIndex) =>
              itemIndex !== index
          ),
      };
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    const vendorId =
      user?.role === "vendor"
        ? user.vendor_id
        : Number(formData.vendor_id);

    if (!vendorId) {
      setError(
        "Please select a vendor."
      );
      return;
    }

    try {
      await apiRequest(
        "/api/invoices",
        {
          method: "POST",

          body: JSON.stringify({
            nonprofit_id:
              user.nonprofit_id,

            vendor_id: vendorId,

            invoice_number:
              formData.invoice_number,

            invoice_date:
              formData.invoice_date,

            due_date:
              formData.due_date || null,

            currency:
              formData.currency,

            line_items:
              formData.line_items.map(
                (item) => ({
                  description:
                    item.description,

                  quantity:
                    Number(item.quantity),

                  unit_price:
                    Number(
                      item.unit_price
                    ),

                  category:
                    item.category || null,
                })
              ),
          }),
        }
      );

      setSuccess(
        "Invoice submitted successfully."
      );

      resetForm();
      await loadInvoices();
    } catch (err) {
      setError(err.message);
    }
  };

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

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="page-eyebrow">
            Invoice Management
          </p>

          <h1>Invoices</h1>

          <p>
            Submit, review and track vendor
            invoices.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={handleCreateClick}
        >
          + New Invoice
        </button>
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

      {showForm && (
        <section className="form-card">
          <div className="section-header">
            <div>
              <h2>Submit Invoice</h2>

              <p>
                Enter invoice details and
                line items.
              </p>
            </div>
          </div>

          <form
            className="invoice-form"
            onSubmit={handleSubmit}
          >
            {user?.role !== "vendor" && (
              <div className="form-group">
                <label htmlFor="vendor_id">
                  Vendor
                </label>

                <select
                  id="vendor_id"
                  name="vendor_id"
                  value={
                    formData.vendor_id
                  }
                  onChange={
                    handleFieldChange
                  }
                  required
                >
                  <option value="">
                    Select vendor
                  </option>

                  {vendors.map(
                    (vendor) => (
                      <option
                        key={vendor.id}
                        value={vendor.id}
                      >
                        {vendor.name}
                      </option>
                    )
                  )}
                </select>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="invoice_number">
                Invoice Number
              </label>

              <input
                id="invoice_number"
                name="invoice_number"
                value={
                  formData.invoice_number
                }
                onChange={
                  handleFieldChange
                }
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="invoice_date">
                Invoice Date
              </label>

              <input
                id="invoice_date"
                name="invoice_date"
                type="date"
                value={
                  formData.invoice_date
                }
                onChange={
                  handleFieldChange
                }
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="due_date">
                Due Date
              </label>

              <input
                id="due_date"
                name="due_date"
                type="date"
                value={
                  formData.due_date
                }
                onChange={
                  handleFieldChange
                }
              />
            </div>

            <div className="form-group">
              <label htmlFor="currency">
                Currency
              </label>

              <input
                id="currency"
                name="currency"
                value={
                  formData.currency
                }
                onChange={
                  handleFieldChange
                }
                maxLength={3}
                required
              />
            </div>

            <div className="line-items-section">
              <div className="line-items-header">
                <div>
                  <h3>Line Items</h3>

                  <p>
                    Add at least one invoice
                    item.
                  </p>
                </div>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={addLineItem}
                >
                  + Add Item
                </button>
              </div>

              {formData.line_items.map(
                (item, index) => (
                  <div
                    className="line-item-row"
                    key={index}
                  >
                    <div className="form-group line-description">
                      <label>
                        Description
                      </label>

                      <input
                        name="description"
                        value={
                          item.description
                        }
                        onChange={(event) =>
                          handleLineItemChange(
                            index,
                            event
                          )
                        }
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>
                        Quantity
                      </label>

                      <input
                        name="quantity"
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={
                          item.quantity
                        }
                        onChange={(event) =>
                          handleLineItemChange(
                            index,
                            event
                          )
                        }
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>
                        Unit Price
                      </label>

                      <input
                        name="unit_price"
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={
                          item.unit_price
                        }
                        onChange={(event) =>
                          handleLineItemChange(
                            index,
                            event
                          )
                        }
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>
                        Category
                      </label>

                      <input
                        name="category"
                        value={
                          item.category
                        }
                        onChange={(event) =>
                          handleLineItemChange(
                            index,
                            event
                          )
                        }
                      />
                    </div>

                    <div className="line-total">
                      <span>Line Total</span>

                      <strong>
                        {formatMoney(
                          (Number(
                            item.quantity
                          ) || 0) *
                            (Number(
                              item.unit_price
                            ) || 0),
                          formData.currency
                        )}
                      </strong>
                    </div>

                    {formData.line_items
                      .length > 1 && (
                      <button
                        type="button"
                        className="remove-item-button"
                        onClick={() =>
                          removeLineItem(
                            index
                          )
                        }
                      >
                        Remove
                      </button>
                    )}
                  </div>
                )
              )}

              <div className="invoice-total-preview">
                <span>
                  Estimated Total
                </span>

                <strong>
                  {formatMoney(
                    estimatedTotal,
                    formData.currency
                  )}
                </strong>
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="primary-button"
              >
                Submit Invoice
              </button>

              <button
                type="button"
                className="secondary-button"
                onClick={resetForm}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="dashboard-section">
        <div className="section-header invoice-list-header">
          <div>
            <h2>Invoice Directory</h2>

            <p>
              {invoices.length} invoice
              {invoices.length === 1
                ? ""
                : "s"}{" "}
              found
            </p>
          </div>

          <div className="invoice-filters">
            {user?.role !== "vendor" && (
              <select
                value={vendorFilter}
                onChange={(event) =>
                  setVendorFilter(
                    event.target.value
                  )
                }
              >
                <option value="">
                  All vendors
                </option>

                {vendors.map(
                  (vendor) => (
                    <option
                      key={vendor.id}
                      value={vendor.id}
                    >
                      {vendor.name}
                    </option>
                  )
                )}
              </select>
            )}

            <select
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

              <option value="submitted">
                Submitted
              </option>

              <option value="under_review">
                Under Review
              </option>

              <option value="needs_documents">
                Needs Documents
              </option>

              <option value="approved">
                Approved
              </option>

              <option value="rejected">
                Rejected
              </option>
            </select>
          </div>
        </div>

        {loading ? (
          <p>Loading invoices...</p>
        ) : invoices.length === 0 ? (
          <div className="empty-state">
            No invoices found.
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Vendor</th>
                  <th>Invoice Date</th>
                  <th>Due Date</th>
                  <th>Items</th>
                  <th>Total</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {invoices.map(
                  (invoice) => (
                    <tr key={invoice.id}>
                      <td>
                        <Link
                          className= "invoice-link"
                          to={`/invoices/${invoice.id}`}
                        >
                            {invoice.invoice_number}
                        </Link>
                      </td>

                      <td>
                        {vendorMap[
                          invoice.vendor_id
                        ] ||
                          `Vendor #${invoice.vendor_id}`}
                      </td>

                      <td>
                        {invoice.invoice_date}
                      </td>

                      <td>
                        {invoice.due_date ||
                          "—"}
                      </td>

                      <td>
                        {
                          invoice.line_items
                            ?.length
                        }
                      </td>

                      <td>
                        {formatMoney(
                          invoice.total_amount,
                          invoice.currency
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
        )}
      </section>
    </div>
  );
}

export default InvoicesPage;