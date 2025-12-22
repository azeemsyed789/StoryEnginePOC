import React, { useState } from "react";
import axios from "axios";
import { BASE_URL } from "./config";

export default function Login({ onLoginSuccess }) {
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);

      const res = await axios.post(`${BASE_URL}/login`, formData);
      console.log("login response", res.data);
      const { access_token, role } = res.data;

      localStorage.setItem("token", access_token);
      localStorage.setItem("role", role);

      onLoginSuccess(role);
    } catch (err) {
      console.error(err);
      setError("Invalid email or password");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("email", email);
      formData.append("password", password);
      formData.append("role", "user");

      const res = await axios.post(`${BASE_URL}/register`, formData);
      const { access_token, role } = res.data;

      localStorage.setItem("token", access_token);
      localStorage.setItem("role", role);

      onLoginSuccess(role);
    } catch (err) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Registration failed. Please try again.");
      }
    }
  };

  const toggleMode = () => {
    setIsRegisterMode(!isRegisterMode);
    setError("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white">
      <h2 className="text-2xl font-bold mb-4">
        {isRegisterMode ? "Create Account" : "Login"}
      </h2>
      <form
        onSubmit={isRegisterMode ? handleRegister : handleLogin}
        className="flex flex-col gap-3 w-64"
      >
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
        {isRegisterMode && (
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm Password"
            className="p-2 rounded bg-gray-800 border border-gray-600"
            required
          />
        )}
        <button
          type="submit"
          className="py-2 bg-cyan-600 rounded font-bold hover:bg-cyan-500"
        >
          {isRegisterMode ? "REGISTER" : "LOGIN"}
        </button>
        {error && <p className="text-red-500 text-sm">{error}</p>}
      </form>
      <button
        onClick={toggleMode}
        className="mt-4 text-cyan-400 hover:text-cyan-300 underline"
      >
        {isRegisterMode
          ? "Already have an account? Login"
          : "Don't have an account? Register"}
      </button>
    </div>
  );
}
