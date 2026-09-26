import { useState } from "react";
import { useAuth } from "../AuthContext";

const DEMOS = [
  { email: "admin@platform.local", label: "Platform Admin" },
  { email: "editor@acme.local", label: "Acme Editor" },
  { email: "viewer@acme.local", label: "Acme Viewer" },
  { email: "viewer@globex.local", label: "Globex Viewer" },
];

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("editor@acme.local");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell login-shell">
      <div className="login-panel">
        <p className="brand hero-brand">Tenant Analytics</p>
        <h1>Sign in to your workspace</h1>
        <p className="muted">
          Multi-tenant sales metrics with JWT roles and PostgreSQL row-level security.
        </p>
        <form className="login-form" onSubmit={onSubmit}>
          <label>
            Email
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              autoComplete="username"
              required
            />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="demo-users">
          <p className="muted small">Demo accounts (password: password123)</p>
          <div className="chip-row">
            {DEMOS.map((d) => (
              <button
                key={d.email}
                type="button"
                className="chip"
                onClick={() => setEmail(d.email)}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="login-visual" aria-hidden="true" />
    </div>
  );
}
