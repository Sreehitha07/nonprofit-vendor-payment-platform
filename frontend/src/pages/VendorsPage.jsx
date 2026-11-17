import { useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../services/api";

const emptyForm = {
  name: "",
  contact_name: "",
  email: "",
  status: "pending",
};

function VendorsPage() {
  const { user } = useAuth();

  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingVendor, setEditingVendor] =
    useState(null);

  const [formData, setFormData] =
    useState(emptyForm);

  const canCreate =
    user?.role === "staff" ||
    user?.role === "manager" ||
    user?.role === "admin";

  const canDelete =
    user?.role === "manager" ||
    user?.role === "admin";

  const loadVendors = async () => {
    setLoading(true);
    setError("");

    try {
      const data =
        await apiRequest("/api/vendors");

      setVendors(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVendors();
  }, []);

  const resetForm = () => {
    setFormData(emptyForm);
    setEditingVendor(null);
    setShowForm(false);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;

    setFormData((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleCreateClick = () => {
    setEditingVendor(null);
    setFormData(emptyForm);
    setShowForm(true);
    setError("");
    setSuccess("");
  };

  const handleEditClick = (vendor) => {
    setEditingVendor(vendor);

    setFormData({
      name: vendor.name || "",
      contact_name: vendor.contact_name || "",
      email: vendor.email || "",
      status: vendor.status || "pending",
    });

    setShowForm(true);
    setError("");
    setSuccess("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");

    try {
      if (editingVendor) {
        await apiRequest(
          `/api/vendors/${editingVendor.id}`,
          {
            method: "PATCH",
            body: JSON.stringify({
              name: formData.name,
              contact_name:
                formData.contact_name || null,
              email:
                formData.email || null,
              status: formData.status,
            }),
          }
        );

        setSuccess(
          "Vendor updated successfully."
        );
      } else {
        await apiRequest(
          "/api/vendors",
          {
            method: "POST",
            body: JSON.stringify({
              nonprofit_id:
                user.nonprofit_id,
              name: formData.name,
              contact_name:
                formData.contact_name || null,
              email:
                formData.email || null,
              status: formData.status,
            }),
          }
        );

        setSuccess(
          "Vendor created successfully."
        );
      }

      resetForm();
      await loadVendors();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (vendor) => {
    const confirmed =
      window.confirm(
        `Delete vendor "${vendor.name}"?`
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setSuccess("");

    try {
      await apiRequest(
        `/api/vendors/${vendor.id}`,
        {
          method: "DELETE",
        }
      );

      setSuccess(
        "Vendor deleted successfully."
      );

      await loadVendors();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="page-eyebrow">
            Vendor Management
          </p>

          <h1>Vendors</h1>

          <p>
            Manage vendors associated with
            your nonprofit.
          </p>
        </div>

        {canCreate && (
          <button
            className="primary-button"
            onClick={handleCreateClick}
          >
            + Add Vendor
          </button>
        )}
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
              <h2>
                {editingVendor
                  ? "Edit Vendor"
                  : "Add Vendor"}
              </h2>

              <p>
                Enter the vendor information
                below.
              </p>
            </div>
          </div>

          <form
            className="vendor-form"
            onSubmit={handleSubmit}
          >
            <div className="form-group">
              <label htmlFor="name">
                Vendor Name
              </label>

              <input
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="contact_name">
                Contact Name
              </label>

              <input
                id="contact_name"
                name="contact_name"
                value={
                  formData.contact_name
                }
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">
                Email
              </label>

              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label htmlFor="status">
                Status
              </label>

              <select
                id="status"
                name="status"
                value={formData.status}
                onChange={handleChange}
              >
                <option value="pending">
                  Pending
                </option>

                <option value="active">
                  Active
                </option>

                <option value="inactive">
                  Inactive
                </option>
              </select>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="primary-button"
              >
                {editingVendor
                  ? "Save Changes"
                  : "Create Vendor"}
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
        <div className="section-header">
          <div>
            <h2>Vendor Directory</h2>

            <p>
              {vendors.length} vendor
              {vendors.length === 1
                ? ""
                : "s"}
            </p>
          </div>
        </div>

        {loading ? (
          <p>Loading vendors...</p>
        ) : vendors.length === 0 ? (
          <div className="empty-state">
            No vendors found.
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Vendor</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Status</th>

                  {canCreate && (
                    <th>Actions</th>
                  )}
                </tr>
              </thead>

              <tbody>
                {vendors.map((vendor) => (
                  <tr key={vendor.id}>
                    <td>
                      #{vendor.id}
                    </td>

                    <td>
                      <strong>
                        {vendor.name}
                      </strong>
                    </td>

                    <td>
                      {vendor.contact_name ||
                        "—"}
                    </td>

                    <td>
                      {vendor.email || "—"}
                    </td>

                    <td>
                      <span className="table-status">
                        {vendor.status}
                      </span>
                    </td>

                    {canCreate && (
                      <td>
                        <div className="table-actions">
                          <button
                            className="text-button"
                            onClick={() =>
                              handleEditClick(
                                vendor
                              )
                            }
                          >
                            Edit
                          </button>

                          {canDelete && (
                            <button
                              className="text-button danger"
                              onClick={() =>
                                handleDelete(
                                  vendor
                                )
                              }
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default VendorsPage;