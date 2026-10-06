// Lightweight API client. Token is kept in memory + sessionStorage so a page
// refresh keeps the session, but nothing sensitive is persisted long-term.
const BASE = import.meta.env.VITE_API_BASE || "";

function getToken() {
  return sessionStorage.getItem("token") || "";
}

async function request(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = new URLSearchParams(form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (email, password) =>
    request("/api/auth/login", { method: "POST", form: { username: email, password } }),
  me: () => request("/api/auth/me"),

  // customer portal
  createTicket: (subject, body) =>
    request("/api/tickets", { method: "POST", body: { subject, body } }),
  myTickets: () => request("/api/tickets/mine"),

  // agent workspace
  queue: (status) => request(`/api/tickets/queue${status ? `?status=${status}` : ""}`),
  ticket: (id) => request(`/api/tickets/${id}`),
  reply: (id, body) => request(`/api/tickets/${id}/messages`, { method: "POST", body: { body } }),
  setStatus: (id, status) =>
    request(`/api/tickets/${id}/status?status=${status}`, { method: "PATCH" }),

  // assistant
  ask: (query) => request("/api/assistant/ask", { method: "POST", body: { query } }),

  // analytics
  kpis: () => request("/api/analytics/kpis"),
  byCategory: () => request("/api/analytics/tickets-by-category"),
  sentimentTrend: () => request("/api/analytics/sentiment-trend"),
  churnRisk: () => request("/api/analytics/churn-risk"),

  // admin
  users: () => request("/api/admin/users"),
  createUser: (u) => request("/api/admin/users", { method: "POST", body: u }),
  toggleUser: (id) => request(`/api/admin/users/${id}/toggle`, { method: "PATCH" }),
};

export { getToken };
