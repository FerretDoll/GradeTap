import axios from "axios";

import { mockAdapter, mockEnabled } from "./mock";

const SAFE_METHODS = new Set(["get", "head", "options"]);
const AUTH_PATHS_WITHOUT_REDIRECT = ["/auth/me", "/auth/login", "/auth/csrf"];

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 15000,
  withCredentials: true,
  ...(mockEnabled ? { adapter: mockAdapter } : {}),
});

let csrfToken = "";
let csrfRequest = null;
const authErrorHandlers = {
  sessionExpired: null,
  approvalRequired: null,
};

export function onAuthError(type, handler) {
  authErrorHandlers[type] = handler;
}

export function resetCsrfToken() {
  csrfToken = "";
  csrfRequest = null;
}

export async function ensureCsrfToken({ force = false } = {}) {
  if (csrfToken && !force) return csrfToken;
  if (!csrfRequest || force) {
    csrfRequest = apiClient
      .get("/auth/csrf", { skipAuthRedirect: true })
      .then((response) => {
        csrfToken = response.data?.csrf_token ?? "";
        return csrfToken;
      })
      .finally(() => {
        csrfRequest = null;
      });
  }
  return csrfRequest;
}

export function apiErrorCode(error) {
  return error?.response?.data?.code ?? "";
}

export function apiErrorMessage(error, fallback = "请求失败，请稍后重试") {
  const data = error?.response?.data;
  if (typeof data?.message === "string" && data.message) return data.message;
  if (typeof data?.detail === "string" && data.detail) return data.detail;
  return fallback;
}

apiClient.interceptors.request.use(async (config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (!SAFE_METHODS.has(method)) {
    const token = await ensureCsrfToken();
    if (token) config.headers.set("X-CSRF-Token", token);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error?.config ?? {};
    const status = error?.response?.status;
    const code = apiErrorCode(error);
    const url = config.url ?? "";

    if (status === 403 && code.startsWith("csrf") && !config.csrfRetried) {
      config.csrfRetried = true;
      await ensureCsrfToken({ force: true });
      return apiClient.request(config);
    }

    const skipRedirect = config.skipAuthRedirect || AUTH_PATHS_WITHOUT_REDIRECT.some((path) => url.startsWith(path));
    if (!skipRedirect) {
      if (status === 401) authErrorHandlers.sessionExpired?.(error);
      if (status === 403 && code === "approval_required") authErrorHandlers.approvalRequired?.(error);
    }
    return Promise.reject(error);
  },
);

export function buildApiUrl(path) {
  const baseURL = apiClient.defaults.baseURL ?? "";
  return `${baseURL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}
