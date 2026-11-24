import { apiClient, ensureCsrfToken, resetCsrfToken } from "./client";

export async function getMe() {
  const response = await apiClient.get("/auth/me");
  return response.data;
}

export async function login(payload) {
  await ensureCsrfToken({ force: true });
  const response = await apiClient.post("/auth/login", payload);
  resetCsrfToken();
  return response.data;
}

export async function logout() {
  try {
    await apiClient.post("/auth/logout", null, { skipAuthRedirect: true });
  } finally {
    resetCsrfToken();
  }
}

export async function register(payload) {
  const response = await apiClient.post("/auth/register", payload);
  return response.data;
}

export async function verifyEmail(token) {
  const response = await apiClient.post("/auth/verify-email", { token });
  return response.data;
}

export async function resendVerification(email) {
  const response = await apiClient.post("/auth/resend-verification", { email });
  return response.data;
}

export async function resubmitApplication(payload) {
  const response = await apiClient.post("/auth/resubmit", payload);
  return response.data;
}
