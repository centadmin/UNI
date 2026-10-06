import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

function StatusBadge({ status }) {
  const map = { open: "b-blue", in_progress: "b-amber", escalated: "b-red", closed: "b-gray" };
  return <span className={`badge ${map[status] || "b-gray"}`}>{status.replace("_", " ")}</span>;
}

export default function CustomerPortal() {
  const [tickets, setTickets] = useState([]);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [err, setErr] = useState("");

  // assistant chat
  const [chat, setChat] = useState([
    { from: "them", text: "Hi! I'm the ABC Financial assistant. Ask me about passwords, cards, transfers, charges and more." },
  ]);
  const [q, setQ] = useState("");

  const load = () => api.myTickets().then(setTickets).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const createTicket = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.createTicket(subject, body);
      setSubject(""); setBody("");
      load();
    } catch (e) { setErr(e.message); }
  };

  const ask = async (e) => {
    e.preventDefault();
    if (!q.trim()) return;
    const question = q;
    setChat((c) => [...c, { from: "me", text: question }]);
    setQ("");
    try {
      const r = await api.ask(question);
      if (r.escalate) {
        setChat((c) => [...c, { from: "them", text: "I couldn't find a confident answer for that. I'd recommend raising a ticket and an agent will help you." }]);
      } else {
        setChat((c) => [...c, { from: "them", text: r.answer, src: r.source?.title }]);
      }
    } catch (e) {
      setChat((c) => [...c, { from: "them", text: "Something went wrong. Please try again." }]);
    }
  };

  return (
    <div className="grid-2">
      {/* left: my tickets + create */}
      <div>
        <div className="card">
          <div className="card-title">Raise a new ticket</div>
          {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}
          <form onSubmit={createTicket}>
            <div className="field">
              <label>Subject</label>
              <input value={subject} onChange={(e) => setSubject(e.target.value)} required placeholder="e.g. Double charge on my card" />
            </div>
            <div className="field">
              <label>Describe your issue</label>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} required rows={3} placeholder="Tell us what happened…" />
            </div>
            <button className="btn btn-primary">Submit ticket</button>
            <p className="muted" style={{ fontSize: 11, marginTop: 8 }}>
              Tickets are automatically categorised and prioritised by AI.
            </p>
          </form>
        </div>

        <div className="card">
          <div className="card-title">My tickets ({tickets.length})</div>
          {tickets.length === 0 ? (
            <p className="muted" style={{ fontSize: 13 }}>No tickets yet.</p>
          ) : (
            <table>
              <thead><tr><th>Subject</th><th>Category</th><th>Status</th></tr></thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.ticket_id}>
                    <td>{t.subject}</td>
                    <td><span className="badge b-gray">{t.category || "—"}</span></td>
                    <td><StatusBadge status={t.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* right: AI assistant */}
      <div className="card" style={{ display: "flex", flexDirection: "column" }}>
        <div className="card-title">AI Assistant</div>
        <div className="chat" style={{ flex: 1 }}>
          {chat.map((m, i) => (
            <div key={i} className={`msg ${m.from}`}>
              {m.text}
              {m.src && <span className="src">Source: {m.src}</span>}
            </div>
          ))}
        </div>
        <form onSubmit={ask} style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask a question…" />
          <button className="btn btn-primary">Send</button>
        </form>
      </div>
    </div>
  );
}
