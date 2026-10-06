import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

function StatusBadge({ status }) {
  const map = { open: "b-blue", in_progress: "b-amber", escalated: "b-red", closed: "b-gray" };
  return <span className={`badge ${map[status] || "b-gray"}`}>{status.replace("_", " ")}</span>;
}
function SentimentBadge({ s }) {
  if (!s) return <span className="muted">—</span>;
  const map = { positive: "b-green", neutral: "b-gray", negative: "b-red" };
  return <span className={`badge ${map[s]}`}>{s}</span>;
}
function PriorityBadge({ p }) {
  const map = { high: "b-red", medium: "b-amber", low: "b-gray" };
  return <span className={`badge ${map[p] || "b-gray"}`}>{p}</span>;
}

export default function AgentWorkspace() {
  const [tickets, setTickets] = useState([]);
  const [filter, setFilter] = useState("");
  const [active, setActive] = useState(null);     // ticket detail
  const [reply, setReply] = useState("");
  const [suggestion, setSuggestion] = useState(null);
  const [err, setErr] = useState("");

  const loadQueue = () => api.queue(filter || undefined).then(setTickets).catch((e) => setErr(e.message));
  useEffect(() => { loadQueue(); }, [filter]);

  const open = async (id) => {
    setSuggestion(null); setReply("");
    const t = await api.ticket(id);
    setActive(t);
    // fetch an AI suggested reply grounded in the KB (RAG)
    try {
      const r = await api.ask(`${t.subject}. ${t.body}`);
      if (!r.escalate) setSuggestion(r);
    } catch {}
  };

  const sendReply = async (e) => {
    e.preventDefault();
    if (!reply.trim()) return;
    const t = await api.reply(active.ticket_id, reply);
    setActive(t); setReply(""); loadQueue();
  };

  const changeStatus = async (status) => {
    await api.setStatus(active.ticket_id, status);
    const t = await api.ticket(active.ticket_id);
    setActive(t); loadQueue();
  };

  return (
    <div className="grid-2" style={{ gridTemplateColumns: "1.1fr 1fr", alignItems: "start" }}>
      {/* queue */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div className="card-title" style={{ margin: 0 }}>Ticket Queue</div>
          <select style={{ width: 150 }} value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In progress</option>
            <option value="escalated">Escalated</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}
        <table>
          <thead><tr><th>Subject</th><th>Category</th><th>Pri.</th><th>Sentiment</th><th>Status</th></tr></thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.ticket_id} className="clickable" onClick={() => open(t.ticket_id)}>
                <td>
                  <div style={{ fontWeight: 600 }}>{t.subject}</div>
                  <div className="muted" style={{ fontSize: 11 }}>{t.customer_name}</div>
                </td>
                <td><span className="badge b-gray">{t.category || "—"}</span></td>
                <td><PriorityBadge p={t.priority} /></td>
                <td><SentimentBadge s={t.sentiment} /></td>
                <td><StatusBadge status={t.status} /></td>
              </tr>
            ))}
            {tickets.length === 0 && <tr><td colSpan={5} className="muted">No tickets.</td></tr>}
          </tbody>
        </table>
      </div>

      {/* detail */}
      <div className="card">
        {!active ? (
          <p className="muted" style={{ fontSize: 13 }}>Select a ticket from the queue to view details.</p>
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{active.subject}</div>
                <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                  {active.customer_name} · {active.category} · confidence {Math.round((active.classification_confidence || 0) * 100)}%
                </div>
              </div>
              <StatusBadge status={active.status} />
            </div>

            <div style={{ display: "flex", gap: 6, margin: "12px 0" }}>
              <button className="btn btn-sm" onClick={() => changeStatus("in_progress")}>In progress</button>
              <button className="btn btn-sm" onClick={() => changeStatus("escalated")}>Escalate</button>
              <button className="btn btn-sm" onClick={() => changeStatus("closed")}>Close</button>
            </div>

            <div className="chat" style={{ marginTop: 4 }}>
              {active.messages.map((m) => (
                <div key={m.message_id} className={`msg ${m.sender_type === "agent" ? "me" : "them"}`}>
                  {m.body}
                  <span className="src">{m.sender_name || m.sender_type}</span>
                </div>
              ))}
            </div>

            {suggestion && (
              <div className="assistant-box" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 4, color: "var(--red)" }}>
                  ✨ AI suggested reply · source: {suggestion.source?.title}
                </div>
                <div>{suggestion.answer}</div>
                <button className="btn btn-sm" style={{ marginTop: 8 }} onClick={() => setReply(suggestion.answer)}>
                  Use this reply
                </button>
              </div>
            )}

            <form onSubmit={sendReply} style={{ marginTop: 12 }}>
              <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={3} placeholder="Type your reply…" />
              <button className="btn btn-primary" style={{ marginTop: 8 }}>Send reply</button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
