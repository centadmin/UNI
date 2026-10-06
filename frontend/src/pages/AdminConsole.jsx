import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

const ROLE_BADGE = {
  admin: "b-red", manager: "b-blue", executive: "b-amber", agent: "b-green",
};

export default function AdminConsole() {
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent" });
  const [busy, setBusy] = useState(false);

  const load = () => api.users().then(setUsers).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.createUser(form);
      setForm({ name: "", email: "", password: "", role: "agent" });
      load();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  const toggle = async (id) => {
    try { await api.toggleUser(id); load(); }
    catch (e) { setErr(e.message); }
  };

  return (
    <div className="grid-2" style={{ gridTemplateColumns: "1.4fr 1fr", alignItems: "start" }}>
      {/* users table */}
      <div className="card">
        <div className="card-title">Users &amp; Roles ({users.length})</div>
        {err && <div className="error" style={{ marginBottom: 12 }}>{err}</div>}
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.agent_id}>
                <td style={{ fontWeight: 600 }}>{u.name}</td>
                <td className="muted">{u.email}</td>
                <td><span className={`badge ${ROLE_BADGE[u.role] || "b-gray"}`}>{u.role}</span></td>
                <td>{u.is_active
                  ? <span className="badge b-green">Active</span>
                  : <span className="badge b-gray">Disabled</span>}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn btn-sm" onClick={() => toggle(u.agent_id)}>
                    {u.is_active ? "Disable" : "Enable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* create user */}
      <div className="card">
        <div className="card-title">Add a user</div>
        <form onSubmit={create}>
          <div className="field">
            <label>Full name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="field">
            <label>Temporary password</label>
            <input type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="agent">Agent</option>
              <option value="manager">Manager</option>
              <option value="executive">Executive</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Adding…" : "Add user"}</button>
        </form>
      </div>
    </div>
  );
}
