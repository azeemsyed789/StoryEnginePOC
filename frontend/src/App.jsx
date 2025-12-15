import React, { useState } from "react";
import Login from "./Login";
import BuilderAndUserPanel from "./BuilderAndUserPanel";

export default function App() {
  const [role, setRole] = useState(localStorage.getItem("role") || null);

  if (!role) {
    return <Login onLoginSuccess={(role) => setRole(role)} />;
  }
  const handleLogout = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  setRole(null);
};


  return <BuilderAndUserPanel role={role} onLogout={handleLogout} />
;
}
