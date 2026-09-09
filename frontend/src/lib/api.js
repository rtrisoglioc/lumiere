import axios from "axios";

export const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

const TOKEN_KEY = "lumiere_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const t = getToken();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// Auto-logout: when a session expires (1h TTL) mid-use, clear it and return to landing.
// Skip the passive /auth/me probe and public routes (landing, login, share) so they never bounce.
api.interceptors.response.use(
  (r) => r,
  (error) => {
    const url = error?.config?.url || "";
    const path = window.location.pathname;
    const publicPath = path === "/" || path.startsWith("/login") || path.startsWith("/share");
    if (error?.response?.status === 401 && !url.includes("/auth/me") && !publicPath) {
      clearToken();
      window.location.href = "/";
    }
    return Promise.reject(error);
  }
);

export const fileUrl = (storagePath) =>
  `${API}/files/${storagePath}?auth=${encodeURIComponent(getToken() || "")}`;
