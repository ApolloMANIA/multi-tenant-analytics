const API_BASE = import.meta.env.VITE_API_URL || "";

function authHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request("/api/auth/me"),
  tenants: () => request("/api/auth/tenants"),
  sales: (limit = 50) => request(`/api/sales?limit=${limit}`),
  createSale: (payload) =>
    request("/api/sales", { method: "POST", body: JSON.stringify(payload) }),
  dailyRevenue: (days = 30) => request(`/api/analytics/daily-revenue?days=${days}`),
  productRanks: () => request("/api/analytics/product-ranks"),
  tenantComparison: () => request("/api/analytics/tenant-comparison"),
  refreshMv: () => request("/api/analytics/refresh-materialized-view", { method: "POST" }),
};
