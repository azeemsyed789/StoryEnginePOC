import React, { useState } from "react";
import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);

      const res = await axios.post(`${BASE_URL}/login`, formData);
      const { access_token, role } = res.data;

      localStorage.setItem("token", access_token);
      localStorage.setItem("role", role);

      onLoginSuccess(role);
    } catch (err) {
      console.error(err);
      setError("Invalid email or password");
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white">
      <h2 className="text-2xl font-bold mb-4">Login</h2>
      <form onSubmit={handleLogin} className="flex flex-col gap-3 w-64">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          className="p-2 rounded bg-gray-800 border border-gray-600"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="p-2 rounded bg-gray-800 border border-gray-600"
          required
        />
        <button type="submit" className="py-2 bg-cyan-600 rounded font-bold hover:bg-cyan-500">
          LOGIN
        </button>
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </form>
    </div>
  );
}
