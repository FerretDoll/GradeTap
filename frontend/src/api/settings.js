import { apiClient } from "./client";

export async function getLlmSettings() {
  const response = await apiClient.get("/settings/llm");
  return response.data;
}

export async function updateLlmSettings(payload) {
  const response = await apiClient.put("/settings/llm", payload);
  return response.data;
}

export async function clearLlmApiKey() {
  const response = await apiClient.delete("/settings/llm/api-key");
  return response.data;
}

export async function testLlmSettings() {
  const response = await apiClient.post("/settings/llm/test");
  return response.data;
}
