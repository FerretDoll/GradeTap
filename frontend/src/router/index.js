import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/authStore";

const LegacyWorkspace = () => import("../views/workspace/LegacyWorkspace.vue");

const routes = [
  {
    path: "/",
    component: () => import("../layouts/AuthLayout.vue"),
    children: [
      { path: "login", name: "login", component: () => import("../views/auth/LoginView.vue"), meta: { guestOnly: true } },
      { path: "register", name: "register", component: () => import("../views/auth/RegisterView.vue"), meta: { guestOnly: true } },
      { path: "verify-email", name: "verifyEmail", component: () => import("../views/auth/VerifyEmailView.vue"), meta: { public: true } },
      {
        path: "account-status",
        name: "accountStatus",
        component: () => import("../views/auth/AccountStatusView.vue"),
        meta: { requiresAuth: true, allowInactive: true },
      },
    ],
  },
  {
    path: "/",
    component: () => import("../layouts/ConsoleLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "home", redirect: () => useAuthStore().homeRoute },
      { path: "offerings", name: "offerings", component: () => import("../views/offerings/OfferingListView.vue") },
      {
        path: "offerings/:offeringId",
        name: "offeringTasks",
        component: () => import("../views/offerings/OfferingTasksView.vue"),
        props: true,
      },
      { path: "tasks", name: "tasks", component: LegacyWorkspace, meta: { legacyView: "tasks" } },
      { path: "tasks/:taskId", name: "taskDetail", component: LegacyWorkspace, meta: { legacyView: "taskDetail" } },
      { path: "courses", name: "courses", component: LegacyWorkspace, meta: { legacyView: "courses" } },
      { path: "classes", name: "classes", component: LegacyWorkspace, meta: { legacyView: "classes" } },
      {
        path: "admin/teachers",
        name: "adminTeachers",
        component: () => import("../views/admin/TeacherAccountsView.vue"),
        meta: { requiresAdmin: true },
      },
      {
        path: "admin/llm",
        name: "adminLlm",
        component: LegacyWorkspace,
        meta: { requiresAdmin: true, legacyView: "llmSettings" },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: { name: "home" } },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (to.meta.public) return true;

  try {
    await auth.resolveSession();
  } catch {
    // Network failures leave the user signed out; the login page reports backend errors.
  }

  if (!auth.isAuthenticated) {
    if (to.meta.guestOnly) return true;
    return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : undefined };
  }
  if (to.meta.guestOnly) return auth.homeRoute;
  if (!auth.isActive && !to.meta.allowInactive) return { name: "accountStatus" };
  if (auth.isActive && to.name === "accountStatus") return auth.homeRoute;
  if (to.meta.requiresAdmin && !auth.isAdmin) return { name: "home" };
  return true;
});
