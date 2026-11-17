import {
    useCallback,
    useEffect,
    useState,
  } from "react";
  
  import { apiRequest } from "../services/api";
  
  
  function AuditLogsPage() {
    const [logs, setLogs] = useState([]);
    const [entityType, setEntityType] = useState("");
    const [entityId, setEntityId] = useState("");
  
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
  
  
    const loadLogs = useCallback(async () => {
      setLoading(true);
      setError("");
  
      try {
        const params = new URLSearchParams();
  
        if (entityType) {
          params.append(
            "entity_type",
            entityType
          );
        }
  
        if (entityId.trim()) {
          params.append(
            "entity_id",
            entityId.trim()
          );
        }
  
        const query = params.toString();
  
        const data = await apiRequest(
          `/api/audit-logs${
            query ? `?${query}` : ""
          }`
        );
  
        setLogs(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }, [entityType, entityId]);
  
  
    useEffect(() => {
      loadLogs();
    }, [loadLogs]);
  
  
    const formatDateTime = (value) => {
      if (!value) {
        return "—";
      }
  
      return new Date(
        value
      ).toLocaleString();
    };
  
  
    const clearFilters = () => {
      setEntityType("");
      setEntityId("");
    };
  
  
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <p className="page-eyebrow">
              Transparency
            </p>
  
            <h1>Audit Logs</h1>
  
            <p>
              Review recorded financial
              and workflow actions.
            </p>
          </div>
        </div>
  
  
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
  
  
        <section className="dashboard-section">
          <div className="audit-toolbar">
            <div>
              <h2>Activity History</h2>
  
              <p>
                {logs.length} audit
                {logs.length === 1
                  ? " record"
                  : " records"}
              </p>
            </div>
  
            <div className="audit-filters">
              <select
                value={entityType}
                onChange={(event) =>
                  setEntityType(
                    event.target.value
                  )
                }
              >
                <option value="">
                  All entity types
                </option>
  
                <option value="payment">
                  Payment
                </option>
  
                <option value="invoice">
                  Invoice
                </option>
  
                <option value="vendor">
                  Vendor
                </option>
              </select>
  
              <input
                type="number"
                min="1"
                placeholder="Entity ID"
                value={entityId}
                onChange={(event) =>
                  setEntityId(
                    event.target.value
                  )
                }
              />
  
              <button
                className="secondary-button"
                onClick={clearFilters}
              >
                Clear
              </button>
            </div>
          </div>
  
  
          {loading ? (
            <p>Loading audit logs...</p>
          ) : logs.length === 0 ? (
            <div className="empty-state">
              No audit logs found.
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Entity</th>
                    <th>Action</th>
                    <th>Status Change</th>
                    <th>Description</th>
                    <th>Performed By</th>
                    <th>Date</th>
                  </tr>
                </thead>
  
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td>
                        #{log.id}
                      </td>
  
                      <td>
                        <div className="audit-entity">
                          <strong>
                            {log.entity_type
                              ?.replaceAll(
                                "_",
                                " "
                              )}
                          </strong>
  
                          <span>
                            #{log.entity_id}
                          </span>
                        </div>
                      </td>
  
                      <td>
                        <span className="audit-action">
                          {log.action
                            ?.replaceAll(
                              "_",
                              " "
                            )}
                        </span>
                      </td>
  
                      <td>
                        {log.previous_status ||
                        log.new_status ? (
                          <span className="audit-status-change">
                            {log.previous_status
                              ? log.previous_status.replaceAll(
                                  "_",
                                  " "
                                )
                              : "—"}
  
                            {" → "}
  
                            {log.new_status
                              ? log.new_status.replaceAll(
                                  "_",
                                  " "
                                )
                              : "—"}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
  
                      <td>
                        {log.description ||
                          "—"}
                      </td>
  
                      <td>
                        User #
                        {
                          log.performed_by_user_id
                        }
                      </td>
  
                      <td>
                        {formatDateTime(
                          log.created_at
                        )}
                      </td>
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
  
  export default AuditLogsPage;