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

export async function deleteTask(taskId) {
  await apiClient.delete(`/tasks/${taskId}`);
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

export async function prepareTaskStudents(taskId) {
  const response = await apiClient.post(`/tasks/${taskId}/prepare-students`);
  return response.data;
}

export async function getTaskAnswerExtraction(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/extract-answers`);
  return response.data;
}

export async function startTaskAnswerExtraction(taskId, maxWorkers = 3, force = false) {
  const response = await apiClient.post(`/tasks/${taskId}/extract-answers`, null, {
    params: { max_workers: maxWorkers, force },
  });
  return response.data;
}

export async function getTaskEvidenceExtraction(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/extract-evidence`);
  return response.data;
}

export async function startTaskEvidenceExtraction(taskId, maxWorkers = 3, force = false) {
  const response = await apiClient.post(`/tasks/${taskId}/extract-evidence`, null, {
    params: { max_workers: maxWorkers, force },
    timeout: LONG_RUNNING_TASK_TIMEOUT,
  });
  return response.data;
}

export async function gradeTaskQuestion(taskId, payload) {
  const response = await apiClient.post(`/tasks/${taskId}/grade-by-question`, payload, {
    timeout: LONG_RUNNING_TASK_TIMEOUT,
  });
  return response.data;
}

export async function getTaskGradingResults(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/grading-results`);
  return response.data;
}

export async function getTaskTeacherRevisions(taskId) {
  const response = await apiClient.get(`/tasks/${taskId}/teacher-revisions`);
  return response.data;
}

export async function reviewTaskGradingResult(taskId, resultId, payload) {
  const response = await apiClient.put(`/tasks/${taskId}/grading-results/${resultId}/review`, payload);
  return response.data;
}

export async function exportTaskResults(taskId, payload) {
  const response = await apiClient.post(`/tasks/${taskId}/export-results`, payload, {
    responseType: "blob",
    timeout: LONG_RUNNING_TASK_TIMEOUT,
  });
  return response;
}
