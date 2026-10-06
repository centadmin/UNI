import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../main";

const NAV = [
  { to: "/portal", label: "Support Portal", roles: ["customer"] },
  { to: "/workspace", label: "Agent Workspace", roles: ["agent", "manager", "admin"] },
  { to: "/dashboard", label: "Executive Dashboard", roles: ["manager", "executive", "admin"] },
  { to: "/admin", label: "Admin Console", roles: ["admin"] },
];

export default function Shell({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const items = NAV.filter((n) => n.roles.includes(user.role));

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">ABC</div>
          <div className="name">ABC Financial</div>
          <div className="sub">AI Support &amp; Analytics</div>
        </div>
        <nav className="nav">
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="foot">Powered by Centium Technologies</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{items.find((i) => location.pathname.startsWith(i.to))?.label || "Dashboard"}</h1>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{user.name}</div>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "capitalize" }}>{user.role}</div>
          </div>
          <button className="btn btn-sm" onClick={() => { logout(); nav("/login"); }}>Log out</button>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
