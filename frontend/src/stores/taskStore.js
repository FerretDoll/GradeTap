import { defineStore } from "pinia";

import { analyzeTaskQuestions, createTask, listTasks, parseTaskFiles } from "../api/tasks";

const LOCAL_TASKS_KEY = "gradetap.tasks";
const TASK_PROGRESS_STAGES = [
  "prepare_students",
  "extract_answers",
  "extract_evidence",
  "grade_by_question",
  "reflect_grading",
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
  return stageKey;
}

function taskProgressForStage(stageKey) {
  const normalized = normalizeProgressStageKey(stageKey);
  const index = TASK_PROGRESS_STAGES.indexOf(normalized);
  if (index < 0) return 0;
  return Math.round((index / (TASK_PROGRESS_STAGES.length - 1)) * 100);
}

function readLocalTasks() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_TASKS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function writeLocalTasks(tasks) {
  window.localStorage.setItem(LOCAL_TASKS_KEY, JSON.stringify(tasks));
}

function mergeTasks(primaryTasks, secondaryTasks) {
  const seen = new Set();
  return [...primaryTasks, ...secondaryTasks].filter((task) => {
    if (seen.has(task.id)) {
      return false;
    }
    seen.add(task.id);
    return true;
  });
}

export const useTaskStore = defineStore("tasks", {
  state: () => ({
    items: readLocalTasks(),
    loading: false,
  }),
  actions: {
    async fetchTasks() {
      this.loading = true;
      try {
        const remoteTasks = await listTasks();
        this.items = mergeTasks(readLocalTasks(), remoteTasks);
        writeLocalTasks(this.items);
      } catch {
        this.items = readLocalTasks();
      } finally {
        this.loading = false;
      }
    },
    createTask(payload) {
      const now = new Date().toISOString();
      const optimisticTask = {
        id: Date.now(),
        ...payload,
        status: "created",
        progress: 0,
        current_stage: "created",
        created_at: now,
        updated_at: now,
      };

      this.items = [optimisticTask, ...this.items];
      writeLocalTasks(this.items);

      createTask(payload)
        .then((serverTask) => {
          this.items = this.items.map((task) =>
            task.id === optimisticTask.id
              ? {
                  progress: 0,
                  current_stage: "created",
                  ...serverTask,
                }
              : task,
          );
          writeLocalTasks(this.items);
        })
        .catch(() => {
          // Keep the optimistic task visible when the API is not running yet.
        });

      return optimisticTask;
    },
    startTask(taskId) {
      this.items = this.items.map((task) =>
        task.id === taskId
          ? {
              ...task,
              status: "grading",
              progress: taskProgressForStage("extract_answers"),
              current_stage: "extract_answers",
              updated_at: new Date().toISOString(),
            }
          : task,
      );
      writeLocalTasks(this.items);
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
      writeLocalTasks(this.items);
    },
    deleteTask(taskId) {
      this.items = this.items.filter((task) => task.id !== taskId);
      writeLocalTasks(this.items);
    },
    async parseFiles(taskId) {
      const result = await parseTaskFiles(taskId);
      this.items = this.items.map((task) =>
        task.id === taskId
          ? {
              ...task,
              status: result.status ?? "parsed",
              progress: taskProgressForStage("analyze_questions"),
              current_stage: "analyze_questions",
              updated_at: new Date().toISOString(),
            }
          : task,
      );
      writeLocalTasks(this.items);
      return result;
    },
    async analyzeQuestions(taskId) {
      const result = await analyzeTaskQuestions(taskId);
      this.items = this.items.map((task) =>
        task.id === taskId
          ? {
              ...task,
              status: result.status ?? "questions_analyzed",
              progress: taskProgressForStage("build_rubrics"),
              current_stage: "build_rubrics",
              updated_at: new Date().toISOString(),
            }
          : task,
      );
      writeLocalTasks(this.items);
      return result;
    },
  },
});
