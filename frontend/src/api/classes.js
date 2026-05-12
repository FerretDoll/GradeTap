import { apiClient } from "./client";

export async function listClasses() {
  const response = await apiClient.get("/classes");
  return response.data;
}

export async function createClassGroup(payload) {
  const response = await apiClient.post("/classes", payload);
  return response.data;
}

export async function updateClassGroup(classId, payload) {
  const response = await apiClient.put(`/classes/${classId}`, payload);
  return response.data;
}

export async function deleteClassGroup(classId) {
  await apiClient.delete(`/classes/${classId}`);
}

export async function listClassStudents(classId) {
  const response = await apiClient.get(`/classes/${classId}/students`);
  return response.data;
}

export async function createClassStudent(classId, payload) {
  const response = await apiClient.post(`/classes/${classId}/students`, payload);
  return response.data;
}

export async function updateClassStudent(classId, studentId, payload) {
  const response = await apiClient.put(`/classes/${classId}/students/${studentId}`, payload);
  return response.data;
}

export async function deleteClassStudent(classId, studentId) {
  await apiClient.delete(`/classes/${classId}/students/${studentId}`);
}

export async function importClassStudents(classId, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post(`/classes/${classId}/students/import`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}
