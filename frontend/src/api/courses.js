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

export async function listCourseAssignments(courseId) {
  const response = await apiClient.get(`/courses/${courseId}/assignments`);
  return response.data;
}

export async function createCourseAssignment(courseId, payload) {
  const response = await apiClient.post(`/courses/${courseId}/assignments`, payload);
  return response.data;
}

export async function updateCourseAssignment(courseId, assignmentId, payload) {
  const response = await apiClient.put(`/courses/${courseId}/assignments/${assignmentId}`, payload);
  return response.data;
}

export async function deleteCourseAssignment(courseId, assignmentId) {
  await apiClient.delete(`/courses/${courseId}/assignments/${assignmentId}`);
}

export async function listCourseAssignmentFiles(courseId, assignmentId) {
  const response = await apiClient.get(`/courses/${courseId}/assignments/${assignmentId}/files`);
  return response.data;
}

export async function uploadCourseAssignmentFile(courseId, assignmentId, fileRole, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post(`/courses/${courseId}/assignments/${assignmentId}/files`, formData, {
    params: { file_role: fileRole },
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteCourseAssignmentFile(courseId, assignmentId, fileId) {
  await apiClient.delete(`/courses/${courseId}/assignments/${assignmentId}/files/${fileId}`);
}

export async function parseCourseAssignmentFiles(courseId, assignmentId) {
  const response = await apiClient.post(`/courses/${courseId}/assignments/${assignmentId}/parse-files`);
  return response.data;
}

export async function analyzeCourseAssignmentQuestions(courseId, assignmentId) {
  const response = await apiClient.post(`/courses/${courseId}/assignments/${assignmentId}/analyze-questions`, null, {
    timeout: 180000,
  });
  return response.data;
}

export async function buildCourseAssignmentRubrics(courseId, assignmentId) {
  const response = await apiClient.post(`/courses/${courseId}/assignments/${assignmentId}/build-rubrics`, null, {
    timeout: 180000,
  });
  return response.data;
}

export async function listCourseAssignmentQuestions(courseId, assignmentId) {
  const response = await apiClient.get(`/courses/${courseId}/assignments/${assignmentId}/questions`);
  return response.data;
}

export async function confirmCourseAssignmentRubrics(courseId, assignmentId, payload) {
  const response = await apiClient.put(`/courses/${courseId}/assignments/${assignmentId}/questions`, payload);
  return response.data;
}
