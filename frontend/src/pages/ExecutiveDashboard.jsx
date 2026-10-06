import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from "recharts";
import { api } from "../lib/api";

const SENTIMENT_COLORS = { positive: "#15803d", neutral: "#9ca3af", negative: "#c00000" };

export default function ExecutiveDashboard() {
  const [kpis, setKpis] = useState(null);
  const [byCat, setByCat] = useState([]);
  const [sentiment, setSentiment] = useState([]);
  const [churn, setChurn] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.kpis(), api.byCategory(), api.sentimentTrend(), api.churnRisk()])
      .then(([k, c, s, ch]) => { setKpis(k); setByCat(c); setSentiment(s); setChurn(ch); })
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="error">{err}</div>;
  if (!kpis) return <p className="muted">Loading analytics…</p>;

  const HIGH = 0.6;

  return (
    <>
      {/* KPI row */}
      <div className="grid-4">
        <div className="stat"><div className="label">CSAT</div><div className="value">{kpis.csat}%</div></div>
        <div className="stat"><div className="label">Avg Resolution</div><div className="value">{kpis.avg_resolution_hours}h</div></div>
        <div className="stat"><div className="label">Open Tickets</div><div className="value">{kpis.open_tickets}</div></div>
        <div className="stat"><div className="label">Churn-Risk Customers</div><div className="value" style={{ color: "var(--red)" }}>{kpis.churn_risk_customers}</div></div>
      </div>

      <div className="grid-2" style={{ marginTop: 16 }}>
        {/* tickets by category */}
        <div className="card">
          <div className="card-title">Tickets by Category</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={byCat} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
              <XAxis dataKey="category" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {byCat.map((_, i) => <Cell key={i} fill="#c00000" />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* sentiment distribution */}
        <div className="card">
          <div className="card-title">Sentiment Distribution</div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={sentiment} dataKey="count" nameKey="label" cx="50%" cy="50%" outerRadius={85} label>
                {sentiment.map((s, i) => <Cell key={i} fill={SENTIMENT_COLORS[s.label] || "#9ca3af"} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* churn risk */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-title">Customer Churn Risk</div>
        <table>
          <thead><tr><th>Customer</th><th>Segment</th><th>Risk Score</th><th>Risk Level</th></tr></thead>
          <tbody>
            {churn.map((c) => (
              <tr key={c.customer_id}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td><span className="badge b-gray">{c.segment}</span></td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 90, height: 6, background: "#eee", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ width: `${c.risk_score * 100}%`, height: "100%", background: c.risk_score >= HIGH ? "var(--red)" : "var(--amber)" }} />
                    </div>
                    <span>{Math.round(c.risk_score * 100)}%</span>
                  </div>
                </td>
                <td>
                  {c.risk_score >= HIGH
                    ? <span className="badge b-red">High</span>
                    : c.risk_score >= 0.35
                      ? <span className="badge b-amber">Medium</span>
                      : <span className="badge b-green">Low</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
