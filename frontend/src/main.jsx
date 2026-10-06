import React, { createContext, useContext, useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { api } from "./lib/api";
import "./styles.css";

import Login from "./pages/Login";
import Shell from "./components/Shell";
import CustomerPortal from "./pages/CustomerPortal";
import AgentWorkspace from "./pages/AgentWorkspace";
import ExecutiveDashboard from "./pages/ExecutiveDashboard";
import AdminConsole from "./pages/AdminConsole";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem("token");
    if (!token) { setReady(true); return; }
    api.me().then(setUser).catch(() => sessionStorage.removeItem("token")).finally(() => setReady(true));
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    sessionStorage.setItem("token", res.access_token);
    setUser(res.user);
    return res.user;
  };
  const logout = () => { sessionStorage.removeItem("token"); setUser(null); };

  return (
    <AuthCtx.Provider value={{ user, login, logout, ready }}>
      {ready ? children : null}
    </AuthCtx.Provider>
  );
}

// Landing route per role (mirrors the wireframe each user class starts on).
function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (user.role === "customer") return <Navigate to="/portal" />;
  if (user.role === "executive" || user.role === "manager") return <Navigate to="/dashboard" />;
  if (user.role === "admin") return <Navigate to="/admin" />;
  return <Navigate to="/workspace" />;
}

function Protected({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" />;
  return <Shell>{children}</Shell>;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Home />} />
          <Route path="/portal" element={<Protected roles={["customer"]}><CustomerPortal /></Protected>} />
          <Route path="/workspace" element={<Protected roles={["agent","manager","admin"]}><AgentWorkspace /></Protected>} />
          <Route path="/dashboard" element={<Protected roles={["manager","executive","admin"]}><ExecutiveDashboard /></Protected>} />
          <Route path="/admin" element={<Protected roles={["admin"]}><AdminConsole /></Protected>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
