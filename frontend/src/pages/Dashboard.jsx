import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useAuth } from "../AuthContext";

function money(n) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n || 0);
}

export default function Dashboard({ view }) {
  const { user } = useAuth();
  const canWrite = user?.role === "admin" || user?.role === "editor" || user?.is_platform_admin;

  if (view === "sales") return <SalesPanel canWrite={canWrite} />;
  if (view === "tenants") return <TenantPanel />;
  return <MetricsPanel />;
}

function MetricsPanel() {
  const [daily, setDaily] = useState([]);
  const [ranks, setRanks] = useState([]);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  async function load() {
    setError("");
    try {
      const [d, r] = await Promise.all([api.dailyRevenue(30), api.productRanks()]);
      setDaily(d);
      setRanks(r);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    try {
      await api.refreshMv();
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }

  const totalRevenue = daily.reduce((s, d) => s + (d.revenue || 0), 0);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Revenue metrics</h2>
          <p className="muted">
            Materialized daily sales with LAG deltas and running totals (SQL window functions).
          </p>
        </div>
        <button className="secondary" type="button" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh MV"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="stat-row">
        <div className="stat">
          <span className="muted small">30-day revenue</span>
          <strong>{money(totalRevenue)}</strong>
        </div>
        <div className="stat">
          <span className="muted small">Days with sales</span>
          <strong>{daily.length}</strong>
        </div>
        <div className="stat">
          <span className="muted small">Top products</span>
          <strong>{ranks.length}</strong>
        </div>
      </div>
      <div className="chart-card">
        <h3>Daily revenue & running total</h3>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={daily}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7c5cff" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#7c5cff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(18,18,18,0.06)" vertical={false} />
              <XAxis dataKey="sale_date" tick={{ fontSize: 11 }} minTickGap={24} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => money(v)} />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#7c5cff"
                fill="url(#rev)"
                name="Revenue"
              />
              <Area
                type="monotone"
                dataKey="running_revenue"
                stroke="#ff6b4a"
                fill="transparent"
                strokeDasharray="4 4"
                name="Running total"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="chart-card">
        <h3>Product rank (within tenant)</h3>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={ranks} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid stroke="rgba(18,18,18,0.06)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="product_name" tick={{ fontSize: 11 }} width={80} />
              <Tooltip formatter={(v) => money(v)} />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function SalesPanel({ canWrite }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    product_name: "Widget A",
    category: "Hardware",
    quantity: 1,
    unit_price: 29.99,
  });

  async function load() {
    try {
      setRows(await api.sales(40));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createSale({
        ...form,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
      });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Sales ledger</h2>
          <p className="muted">RLS scopes every row to your tenant. Viewers cannot write.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {canWrite && (
        <form className="sale-form" onSubmit={onCreate}>
          <input
            value={form.product_name}
            onChange={(e) => setForm({ ...form, product_name: e.target.value })}
            placeholder="Product"
            required
          />
          <input
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            placeholder="Category"
            required
          />
          <input
            type="number"
            min="1"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            required
          />
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.unit_price}
            onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
            required
          />
          <button className="primary" type="submit">
            Add sale
          </button>
        </form>
      )}
      {!canWrite && (
        <p className="notice">Your role is viewer — create/update/delete are blocked by API and RLS.</p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Category</th>
              <th>Qty</th>
              <th>Price</th>
              <th>Sold at</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.product_name}</td>
                <td>{r.category}</td>
                <td>{r.quantity}</td>
                <td>{money(r.unit_price)}</td>
                <td className="mono">{new Date(r.sold_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TenantPanel() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .tenantComparison()
      .then(setRows)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Tenant comparison</h2>
          <p className="muted">Platform-admin only. Tenant users receive 403.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tenant</th>
              <th>Revenue</th>
              <th>Units</th>
              <th>Orders</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.tenant_id}>
                <td>{r.tenant_name}</td>
                <td>{money(r.revenue)}</td>
                <td>{r.units_sold}</td>
                <td>{r.order_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
