import {
  Navigate,
  Route,
  Routes,
} from "react-router";

import AppLayout from "./layouts/AppLayout";
import RoleRoute from "./routes/RoleRoute";

import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import InvoicesPage from "./pages/InvoicesPage";
import VendorsPage from "./pages/VendorsPage";
import PaymentsPage from "./pages/PaymentsPage";
import NotificationsPage from "./pages/NotificationsPage";
import AuditLogsPage from "./pages/AuditLogsPage";
import InvoiceDetailPage from "./pages/InvoiceDetailPage";

import ProtectedRoute from "./routes/ProtectedRoute";

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginPage />}
      />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route
          path="/dashboard"
          element={<DashboardPage />}
        />

        <Route
          path="/vendors"
          element={
            <RoleRoute
              allowedRoles={[
                "staff",
                "manager",
                "admin",
              ]}
            >
              <VendorsPage />
            </RoleRoute>
          }
        />

        <Route
          path="/invoices"
          element={<InvoicesPage />}
        />

        <Route
          path="/invoices/:invoiceId"
          element={<InvoiceDetailPage />}
        />

        <Route
          path="/payments"
          element={<PaymentsPage />}
        />

        <Route
          path="/notifications"
          element={<NotificationsPage />}
        />

        <Route
          path="/audit-logs"
          element={
            <RoleRoute
              allowedRoles={[
                "staff",
                "manager",
                "admin",
              ]}
            >
              <AuditLogsPage />
            </RoleRoute>
          }
        />
      </Route>

      <Route
        path="/"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />

      <Route
        path="*"
        element={
          <Navigate
            to="/dashboard"
            replace
          />
        }
      />
    </Routes>
  );
}

export default App;