import { apiClient } from "./client";

export async function listOfferings() {
  const response = await apiClient.get("/offerings");
  return response.data;
}

export async function createOffering(payload) {
  const response = await apiClient.post("/offerings", payload);
  return response.data;
}
