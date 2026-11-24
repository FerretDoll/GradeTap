import { defineStore } from "pinia";

import {
  analyzeTaskQuestions,
  archiveTask,
  createTask,
  deleteTask,
  listTasks,
  parseTaskFiles,
} from "../api/tasks";

const TASK_PROGRESS_STAGES = [
  "prepare_students",
  "extract_answers",
  "plagiarism_check",
  "extract_evidence",
  "grade_by_question",
  "teacher_review",
  "export_results",
];

function normalizeProgressStageKey(stageKey) {
  if (
    stageKey === "parse_files"
    || stageKey === "analyze_questions"
    || stageKey === "build_rubrics"
    || stageKey === "teacher_confirm_rubrics"
  ) {
    return "prepare_students";
  }
  if (stageKey === "reflect_grading" || stageKey === "route_review") {
    return "teacher_review";
  }
  return stageKey;
}

function taskProgressForStage(stageKey) {
  const normalized = normalizeProgressStageKey(stageKey);
  const index = TASK_PROGRESS_STAGES.indexOf(normalized);
  if (index < 0) return 0;
  return Math.round((index / (TASK_PROGRESS_STAGES.length - 1)) * 100);
}

function withLocalProgress(task, previous) {
  return {
    progress: previous?.progress ?? 0,
    current_stage: previous?.current_stage ?? "created",
    ...task,
  };
}

export const useTaskStore = defineStore("tasks", {
  state: () => ({
    items: [],
    loading: false,
    error: null,
  }),
  actions: {
    async fetchTasks(query = {}) {
      this.loading = true;
      this.error = null;
      try {
        const remoteTasks = await listTasks(query);
        const previousById = new Map(this.items.map((task) => [task.id, task]));
        this.items = remoteTasks.map((task) => withLocalProgress(task, previousById.get(task.id)));
      } catch (error) {
        this.items = [];
        this.error = error;
      } finally {
        this.loading = false;
      }
      return this.items;
    },
    async createTask(payload) {
      const task = withLocalProgress(await createTask(payload));
      this.items = [task, ...this.items];
      return task;
    },
    async removeTask(taskId) {
      await deleteTask(taskId);
      this.items = this.items.filter((task) => task.id !== taskId);
    },
    async archiveTask(taskId, { keepVisible = false } = {}) {
      const archived = await archiveTask(taskId);
      this.items = keepVisible
        ? this.items.map((task) => (task.id === taskId ? withLocalProgress(archived, task) : task))
        : this.items.filter((task) => task.id !== taskId);
      return archived;
    },
    startTask(taskId) {
      this.updateTask(taskId, {
        status: "grading",
        progress: taskProgressForStage("extract_answers"),
        current_stage: "extract_answers",
      });
    },
    updateTask(taskId, payload) {
      this.items = this.items.map((task) =>
        task.id === taskId
          ? {
              ...task,
              ...payload,
              updated_at: new Date().toISOString(),
            }
          : task,
      );
    },
    deleteTask(taskId) {
      this.items = this.items.filter((task) => task.id !== taskId);
    },
    async parseFiles(taskId) {
      const result = await parseTaskFiles(taskId);
      this.updateTask(taskId, {
        status: result.status ?? "parsed",
        progress: taskProgressForStage("analyze_questions"),
        current_stage: "analyze_questions",
      });
      return result;
    },
    async analyzeQuestions(taskId) {
      const result = await analyzeTaskQuestions(taskId);
      this.updateTask(taskId, {
        status: result.status ?? "questions_analyzed",
        progress: taskProgressForStage("build_rubrics"),
        current_stage: "build_rubrics",
      });
      return result;
    },
  },
});
