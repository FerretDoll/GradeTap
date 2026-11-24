export const taskStatusMap = {
  created: { label: "已创建", type: "info" },
  files_uploaded: { label: "已上传文件", type: "primary" },
  parsed: { label: "文件已解析", type: "primary" },
  questions_analyzed: { label: "题目已分析", type: "primary" },
  rubrics_generated: { label: "量规已生成", type: "warning" },
  waiting_rubric_confirm: { label: "待确认量规", type: "warning" },
  rubrics_confirmed: { label: "量规已确认", type: "success" },
  students_prepared: { label: "学生已解析", type: "primary" },
  answers_extracted: { label: "答案已抽取", type: "primary" },
  evidence_extracted: { label: "证据已提取", type: "primary" },
  grading: { label: "AI评分中", type: "warning" },
  graded: { label: "AI评分完成", type: "success" },
  reflecting: { label: "反思校准中", type: "warning" },
  reflected: { label: "已校准", type: "success" },
  review_routed: { label: "已分流复核", type: "warning" },
  waiting_teacher_review: { label: "待教师复核", type: "warning" },
  teacher_reviewed: { label: "教师已复核", type: "success" },
  exported: { label: "已导出", type: "success" },
  summary_generated: { label: "报告已生成", type: "success" },
  failed: { label: "失败", type: "danger" },
};

export function taskStatusMeta(status) {
  return taskStatusMap[status] ?? { label: status || "已创建", type: "info" };
}

export const accountStatusMap = {
  pending_verification: { label: "待验证邮箱", type: "info" },
  pending_approval: { label: "待审核", type: "warning" },
  active: { label: "已启用", type: "success" },
  rejected: { label: "已驳回", type: "danger" },
  disabled: { label: "已停用", type: "info" },
};

export function accountStatusMeta(status) {
  return accountStatusMap[status] ?? { label: status || "未知", type: "info" };
}

export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}
