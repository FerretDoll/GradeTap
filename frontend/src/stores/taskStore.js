import { defineStore } from "pinia";

import { createTask, listTasks } from "../api/tasks";

const LOCAL_TASKS_KEY = "gradetap.tasks";

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
              progress: 35,
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
  },
});
