import { useState } from "react";
import { useAuth } from "./AuthContext";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";

export default function App() {
  const { user, loading, logout } = useAuth();
  const [view, setView] = useState("metrics");

  if (loading) {
    return (
      <div className="shell center">
        <p className="muted">Loading session…</p>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="brand">Tenant Analytics</p>
          <p className="muted small">
            {user.full_name} · {user.role}
            {user.is_platform_admin ? " · platform admin" : ""}
          </p>
        </div>
        <nav className="nav">
          <button
            className={view === "metrics" ? "nav-btn active" : "nav-btn"}
            onClick={() => setView("metrics")}
            type="button"
          >
            Metrics
          </button>
          <button
            className={view === "sales" ? "nav-btn active" : "nav-btn"}
            onClick={() => setView("sales")}
            type="button"
          >
            Sales
          </button>
          {user.is_platform_admin && (
            <button
              className={view === "tenants" ? "nav-btn active" : "nav-btn"}
              onClick={() => setView("tenants")}
              type="button"
            >
              Tenants
            </button>
          )}
          <a
            className="nav-btn link"
            href={import.meta.env.VITE_SUPERSET_URL || "http://localhost:8088"}
            target="_blank"
            rel="noreferrer"
          >
            Superset
          </a>
          <button className="nav-btn ghost" onClick={logout} type="button">
            Log out
          </button>
        </nav>
      </header>
      <main className="main">
        <Dashboard view={view} />
      </main>
    </div>
  );
}
