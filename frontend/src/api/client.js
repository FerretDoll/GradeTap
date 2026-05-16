import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api",
  timeout: 15000,
});

export function buildApiUrl(path) {
  const baseURL = apiClient.defaults.baseURL ?? "";
  return `${baseURL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}
