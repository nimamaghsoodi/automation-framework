import { Routes, Route, NavLink } from "react-router-dom";
import FlowsPage from "./pages/FlowsPage";
import FlowBuilderPage from "./pages/FlowBuilderPage";
import RunsPage from "./pages/RunsPage";
import ConnectorsPage from "./pages/ConnectorsPage";
import CredentialsPage from "./pages/CredentialsPage";
import ScriptsPage from "./pages/ScriptsPage";
import { cn } from "./lib/utils";

const NAV = [
  { to: "/", label: "Flows", end: true },
  { to: "/scripts", label: "Scripts" },
  { to: "/connectors", label: "Connectors" },
  { to: "/credentials", label: "Credentials" },
  { to: "/runs", label: "Runs" },
];

export default function App() {
  return (
    <div className="flex h-screen bg-surface text-text-primary">
      {/* Sidebar */}
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
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<FlowsPage />} />
          <Route path="/flows/:id" element={<FlowBuilderPage />} />
          <Route path="/scripts" element={<ScriptsPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/credentials" element={<CredentialsPage />} />
        </Routes>
      </main>
    </div>
  );
}
