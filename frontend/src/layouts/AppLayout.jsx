import { useEffect, useState } from "react";
import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../services/api";

function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const loadUnreadCount = async () => {
      try {
        const data = await apiRequest(
          "/api/notifications/unread-count"
        );
  
        setUnreadCount(
          data.unread_count ?? 0
        );
      } catch (error) {
        console.error(
          "Failed to load notification count:",
          error
        );
      }
    };
  
    loadUnreadCount();
  
    window.addEventListener(
      "notifications-updated",
      loadUnreadCount
    );
  
    const interval = setInterval(
      loadUnreadCount,
      30000
    );
  
    return () => {
      window.removeEventListener(
        "notifications-updated",
        loadUnreadCount
      );
  
      clearInterval(interval);
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    {
      label: "Dashboard",
      path: "/dashboard",
      roles: ["vendor", "staff", "manager", "admin"],
    },
    {
      label: "Vendors",
      path: "/vendors",
      roles: ["staff", "manager", "admin"],
    },
    {
      label: "Invoices",
      path: "/invoices",
      roles: ["vendor", "staff", "manager", "admin"],
    },
    {
      label: "Payments",
      path: "/payments",
      roles: ["vendor", "staff", "manager", "admin"],
    },
    {
      label: "Notifications",
      path: "/notifications",
      roles: ["vendor", "staff", "manager", "admin"],
    },
    {
      label: "Audit Logs",
      path: "/audit-logs",
      roles: ["staff", "manager", "admin"],
    },
  ];

  const visibleItems = navItems.filter((item) =>
    item.roles.includes(user?.role)
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">
            <div className="brand-mark">
              NP
            </div>

            <div>
              <h2>Nonprofit Pay</h2>
              <p>Vendor Platform</p>
            </div>
          </div>

          <nav className="sidebar-nav">
            {visibleItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  isActive
                    ? "nav-link active"
                    : "nav-link"
                }
              >
                <span>{item.label}</span>

                {item.label === "Notifications" &&
                  unreadCount > 0 && (
                    <span className="notification-badge">
                      {unreadCount}
                    </span>
                  )}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="sidebar-user">
          <div>
            <strong>
              {user?.full_name || user?.email}
            </strong>

            <span className="role-badge">
              {user?.role}
            </span>
          </div>

          <button
            className="logout-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;