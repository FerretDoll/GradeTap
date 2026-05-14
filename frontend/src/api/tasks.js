import { apiClient } from "./client";

const LONG_RUNNING_TASK_TIMEOUT = 180000;

export async function listTasks() {
  const response = await apiClient.get("/tasks");
  return response.data;
}

export async function createTask(payload) {
  const response = await apiClient.post("/tasks", payload);
  return response.data;
}

export async function listTaskFiles(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/files`);
  return response.data;
}

export async function uploadTaskFile(taskId, fileRole, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post(`/tasks/${taskId}/files`, formData, {
    params: { file_role: fileRole },
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteTaskFile(taskId, fileId) {
  await apiClient.delete(`/tasks/${taskId}/files/${fileId}`);
}

export async function parseTaskFiles(taskId) {
  const response = await apiClient.post(`/tasks/${taskId}/parse-files`);
  return response.data;
}

export async function analyzeTaskQuestions(taskId) {
  const response = await apiClient.post(`/tasks/${taskId}/analyze-questions`, null, {
    timeout: LONG_RUNNING_TASK_TIMEOUT,
  });
  return response.data;
}

export async function listTaskQuestions(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/questions`);
  return response.data;
}
