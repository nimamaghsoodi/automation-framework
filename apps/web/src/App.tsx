import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import FlowsPage from "./pages/FlowsPage";
import FlowBuilderPage from "./pages/FlowBuilderPage";
import RunsPage from "./pages/RunsPage";
import ConnectorsPage from "./pages/ConnectorsPage";
import CredentialsPage from "./pages/CredentialsPage";
import ScriptsPage from "./pages/ScriptsPage";
import LoginPage from "./pages/LoginPage";
import UsersPage from "./pages/UsersPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuthStore } from "./store/authStore";
import { cn } from "./lib/utils";

const NAV = [
  { to: "/", label: "Flows", end: true },
  { to: "/scripts", label: "Scripts" },
  { to: "/connectors", label: "Connectors" },
  { to: "/credentials", label: "Credentials" },
  { to: "/runs", label: "Runs" },
];

function Sidebar() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  function handleLogout() {
    clearAuth();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="w-52 shrink-0 border-r border-border flex flex-col py-6 px-4 gap-1">
      <div className="mb-6 px-2">
        <span className="text-base font-semibold tracking-tight text-text-primary">Nexus</span>
        <span className="ml-2 text-xs text-text-muted">v0.1</span>
      </div>

      {NAV.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              "px-3 py-2 rounded-md text-sm font-medium transition-colors",
              isActive
                ? "bg-accent-muted text-accent-hover"
                : "text-text-secondary hover:text-text-primary hover:bg-surface-overlay"
            )
          }
        >
          {label}
        </NavLink>
      ))}

      {user?.role === "admin" && (
        <NavLink
          to="/users"
          className={({ isActive }) =>
            cn(
              "px-3 py-2 rounded-md text-sm font-medium transition-colors",
              isActive
                ? "bg-accent-muted text-accent-hover"
                : "text-text-secondary hover:text-text-primary hover:bg-surface-overlay"
            )
          }
        >
          Users
        </NavLink>
      )}

      {/* User info at bottom */}
      <div className="mt-auto pt-4 border-t border-border">
        <div className="px-2 mb-2">
          <div className="text-xs text-text-primary truncate">{user?.email}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wide mt-0.5">{user?.role}</div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full px-3 py-1.5 text-left text-xs text-text-muted hover:text-status-error transition-colors rounded-md hover:bg-surface-overlay"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<LoginPage />} />

      {/* Protected — all wrapped in the shell */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div className="flex h-screen bg-surface text-text-primary">
              <Sidebar />
              <main className="flex-1 overflow-auto">
                <Routes>
                  <Route path="/" element={<FlowsPage />} />
                  <Route path="/flows/:id" element={<FlowBuilderPage />} />
                  <Route path="/scripts" element={<ScriptsPage />} />
                  <Route path="/runs" element={<RunsPage />} />
                  <Route path="/connectors" element={<ConnectorsPage />} />
                  <Route path="/credentials" element={<CredentialsPage />} />
                  <Route
                    path="/users"
                    element={
                      <ProtectedRoute requireAdmin>
                        <UsersPage />
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </main>
            </div>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
