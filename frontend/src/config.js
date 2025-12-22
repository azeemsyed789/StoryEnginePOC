// Centralized API configuration
// Vite exposes env vars prefixed with VITE_
// Define VITE_API_BASE_URL in your .env (e.g. VITE_API_BASE_URL=http://127.0.0.1:8000)

export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
