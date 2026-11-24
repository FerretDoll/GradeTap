import { apiClient } from "./client";

export async function listTeachers(status) {
  const response = await apiClient.get("/admin/teachers", {
    params: status ? { status } : undefined,
  });
  return response.data;
}

export async function changeTeacherStatus(userId, payload) {
  const response = await apiClient.post(`/admin/teachers/${userId}/actions`, payload);
  return response.data;
}
