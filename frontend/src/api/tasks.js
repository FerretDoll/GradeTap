import { apiClient } from "./client";

export async function listTasks() {
  const response = await apiClient.get("/tasks");
  return response.data;
}

export async function createTask(payload) {
  const response = await apiClient.post("/tasks", payload);
  return response.data;
}
