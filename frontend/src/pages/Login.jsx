import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../main";

const DEMOS = [
  ["Customer", "rahul@example.com", "customer123"],
  ["Agent", "agent@abcfin.com", "agent123"],
  ["Manager", "manager@abcfin.com", "manager123"],
  ["Executive", "exec@abcfin.com", "exec123"],
  ["Admin", "admin@abcfin.com", "admin123"],
];

export default function Login() {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("rahul@example.com");
  const [password, setPassword] = useState("customer123");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) { nav("/"); return null; }

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { await login(email.trim(), password); nav("/"); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <div className="logo" style={{ width: 34, height: 34, borderRadius: 8, background: "var(--red)", color: "#fff", display: "grid", placeItems: "center", fontWeight: 700 }}>ABC</div>
            <div>
              <div style={{ fontWeight: 700 }}>ABC Financial Services</div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>AI Customer Support &amp; Analytics</div>
            </div>
          </div>
          <h2 style={{ fontSize: 18, margin: "16px 0 4px" }}>Sign in</h2>
          <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>Use a demo account below or enter credentials.</p>
          {err && <div className="error" style={{ marginBottom: 14 }}>{err}</div>}
          <form onSubmit={submit}>
            <div className="field">
              <label>Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
            </div>
            <div className="field">
              <label>Password</label>
              <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
            </div>
            <button className="btn btn-primary" style={{ width: "100%" }} disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <div className="demo">
            <strong>Demo accounts</strong> (click to fill):
            <div className="chips" style={{ marginTop: 8 }}>
              {DEMOS.map(([label, e, p]) => (
                <span key={e} className="chip" onClick={() => { setEmail(e); setPassword(p); }}>{label}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
