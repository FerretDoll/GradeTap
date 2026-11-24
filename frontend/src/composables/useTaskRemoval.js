import { ElMessage, ElMessageBox } from "element-plus";

import { apiErrorCode, apiErrorMessage } from "../api/client";
import { useTaskStore } from "../stores/taskStore";

export function useTaskRemoval() {
  const taskStore = useTaskStore();

  async function confirm(message, title, confirmButtonText) {
    try {
      await ElMessageBox.confirm(message, title, {
        confirmButtonText,
        cancelButtonText: "取消",
        lockScroll: false,
        type: "warning",
      });
      return true;
    } catch {
      return false;
    }
  }

  async function archiveTask(task, { keepVisible = false, skipConfirm = false } = {}) {
    if (
      !skipConfirm
      && !(await confirm(
        `归档后“${task.task_name}”将从默认列表隐藏，原件、证据、师评、发布快照与审计日志完整保留，可通过“显示已归档”回看。`,
        "归档任务",
        "归档",
      ))
    ) {
      return null;
    }
    try {
      const archived = await taskStore.archiveTask(task.id, { keepVisible });
      ElMessage.success("任务已归档");
      return archived;
    } catch (error) {
      ElMessage.error(apiErrorMessage(error, "归档失败，请稍后重试"));
      return null;
    }
  }

  async function deleteTask(task, options = {}) {
    if (!(await confirm(`确定删除批改任务“${task.task_name}”吗？`, "删除确认", "删除"))) {
      return "cancelled";
    }
    try {
      await taskStore.removeTask(task.id);
      ElMessage.success("任务已删除");
      return "deleted";
    } catch (error) {
      if (apiErrorCode(error) === "task_delete_protected") {
        const shouldArchive = await confirm(
          "该任务已有师评或发布记录，不可删除，请改用归档。归档后所有记录完整保留。",
          "无法删除",
          "改为归档",
        );
        if (!shouldArchive) return "cancelled";
        return (await archiveTask(task, { ...options, skipConfirm: true })) ? "archived" : "failed";
      }
      if (error?.response?.status === 404) {
        taskStore.deleteTask(task.id);
        return "deleted";
      }
      ElMessage.error(apiErrorMessage(error, "删除失败，请稍后重试"));
      return "failed";
    }
  }

  return { deleteTask, archiveTask };
}
