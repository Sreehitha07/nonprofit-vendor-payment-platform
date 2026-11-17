import {
    useCallback,
    useEffect,
    useState,
  } from "react";
  
  import { apiRequest } from "../services/api";
  
  
  function NotificationsPage() {
    const [notifications, setNotifications] =
      useState([]);
  
    const [unreadOnly, setUnreadOnly] =
      useState(false);
  
    const [loading, setLoading] =
      useState(true);
  
    const [error, setError] =
      useState("");
  
    const [success, setSuccess] =
      useState("");
  
  
    const refreshSidebarBadge = () => {
      window.dispatchEvent(
        new Event("notifications-updated")
      );
    };
  
  
    const loadNotifications =
      useCallback(async () => {
        setLoading(true);
        setError("");
  
        try {
          const query = unreadOnly
            ? "?unread_only=true"
            : "";
  
          const data =
            await apiRequest(
              `/api/notifications${query}`
            );
  
          setNotifications(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }, [unreadOnly]);
  
  
    useEffect(() => {
      loadNotifications();
    }, [loadNotifications]);
  
  
    const formatDate = (value) => {
      if (!value) {
        return "—";
      }
  
      return new Date(
        value
      ).toLocaleString();
    };
  
  
    const markAsRead = async (
      notificationId
    ) => {
      setError("");
      setSuccess("");
  
      try {
        await apiRequest(
          `/api/notifications/${notificationId}/read`,
          {
            method: "PATCH",
          }
        );
  
        setSuccess(
          "Notification marked as read."
        );
  
        await loadNotifications();
  
        refreshSidebarBadge();
      } catch (err) {
        setError(err.message);
      }
    };
  
  
    const markAllAsRead = async () => {
      setError("");
      setSuccess("");
  
      try {
        await apiRequest(
          "/api/notifications/read-all",
          {
            method: "PATCH",
          }
        );
  
        setSuccess(
          "All notifications marked as read."
        );
  
        await loadNotifications();
  
        refreshSidebarBadge();
      } catch (err) {
        setError(err.message);
      }
    };
  
  
    const unreadCount =
      notifications.filter(
        (notification) =>
          !notification.is_read
      ).length;
  
  
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <p className="page-eyebrow">
              Activity
            </p>
  
            <h1>Notifications</h1>
  
            <p>
              Review invoice and payment
              workflow updates.
            </p>
          </div>
  
          <button
            className="secondary-button"
            onClick={markAllAsRead}
            disabled={
              notifications.length === 0
            }
          >
            Mark All Read
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
  
  
        <section className="notification-summary">
          <div>
            <strong>
              {notifications.length}
            </strong>
  
            <span>Total</span>
          </div>
  
          <div>
            <strong>
              {unreadCount}
            </strong>
  
            <span>Unread</span>
          </div>
  
          <label className="notification-filter">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(event) =>
                setUnreadOnly(
                  event.target.checked
                )
              }
            />
  
            Show unread only
          </label>
        </section>
  
  
        <section className="dashboard-section">
          {loading ? (
            <p>
              Loading notifications...
            </p>
          ) : notifications.length ===
            0 ? (
            <div className="empty-state">
              No notifications found.
            </div>
          ) : (
            <div className="notification-list">
              {notifications.map(
                (notification) => (
                  <div
                    className={
                      notification.is_read
                        ? "notification-card"
                        : "notification-card unread"
                    }
                    key={notification.id}
                  >
                    <div className="notification-indicator">
                      {!notification.is_read && (
                        <span />
                      )}
                    </div>
  
                    <div className="notification-content">
                      <div className="notification-card-header">
                        <div>
                          <strong>
                            {
                              notification.title
                            }
                          </strong>
  
                          <span className="notification-type">
                            {notification.notification_type.replaceAll(
                              "_",
                              " "
                            )}
                          </span>
                        </div>
  
                        <small>
                          {formatDate(
                            notification.created_at
                          )}
                        </small>
                      </div>
  
                      <p>
                        {
                          notification.message
                        }
                      </p>
  
                      {(notification.entity_type ||
                        notification.entity_id) && (
                        <div className="notification-entity">
                          {notification.entity_type &&
                            notification.entity_type.replaceAll(
                              "_",
                              " "
                            )}
  
                          {notification.entity_id &&
                            ` #${notification.entity_id}`}
                        </div>
                      )}
  
                      {!notification.is_read && (
                        <button
                          className="notification-read-button"
                          onClick={() =>
                            markAsRead(
                              notification.id
                            )
                          }
                        >
                          Mark as read
                        </button>
                      )}
  
                      {notification.is_read &&
                        notification.read_at && (
                          <small className="read-time">
                            Read{" "}
                            {formatDate(
                              notification.read_at
                            )}
                          </small>
                        )}
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </section>
      </div>
    );
  }
  
  export default NotificationsPage;