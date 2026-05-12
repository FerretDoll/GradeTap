import { apiClient } from "./client";

export async function listCourses() {
  const response = await apiClient.get("/courses");
  return response.data;
}

export async function createCourse(payload) {
  const response = await apiClient.post("/courses", payload);
  return response.data;
}

export async function updateCourse(courseId, payload) {
  const response = await apiClient.put(`/courses/${courseId}`, payload);
  return response.data;
}

export async function deleteCourse(courseId) {
  await apiClient.delete(`/courses/${courseId}`);
}
