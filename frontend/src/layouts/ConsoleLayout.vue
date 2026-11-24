<template>
  <el-container class="app-shell grade-console" :class="{ 'app-shell--collapsed': sidebarCollapsed }">
    <el-aside
      class="sidebar"
      :class="{ 'sidebar--collapsed': sidebarCollapsed }"
      :style="{ width: sidebarCollapsed ? '78px' : '264px' }"
    >
      <div class="brand-lockup">
        <img
          class="brand-logo brand-logo--full"
          src="/brand/gradetap-sidebar-logo.svg"
          alt="GradeTap AI 作业批改助手"
        />
        <img class="brand-logo brand-logo--mark" src="/brand/gradetap-mark.svg" alt="" aria-hidden="true" />
        <span class="brand-subtitle">面向编码作业的智能批改助手</span>
      </div>

      <el-menu :default-active="activeMenu" :collapse="sidebarCollapsed" class="side-menu" @select="handleMenuSelect">
        <el-menu-item index="offerings">
          <el-icon><Reading /></el-icon>
          <span>我的授课班</span>
        </el-menu-item>
        <el-menu-item index="tasks">
          <el-icon><DocumentChecked /></el-icon>
          <span>批改任务</span>
        </el-menu-item>
        <el-menu-item index="courses">
          <el-icon><Collection /></el-icon>
          <span>课程管理</span>
        </el-menu-item>
        <el-menu-item index="classes">
          <el-icon><School /></el-icon>
          <span>班级管理</span>
        </el-menu-item>
        <template v-if="auth.isAdmin">
          <div v-if="!sidebarCollapsed" class="side-menu-group">系统管理</div>
          <el-menu-item index="adminTeachers">
            <el-icon><UserFilled /></el-icon>
            <span>教师账号</span>
          </el-menu-item>
          <el-menu-item index="adminLlm">
            <el-icon><Setting /></el-icon>
            <span>模型配置</span>
          </el-menu-item>
        </template>
      </el-menu>

      <div class="sidebar-account" :title="auth.me?.display_name">
        <div class="sidebar-account-avatar">{{ avatarText }}</div>
        <div class="sidebar-account-meta">
          <strong>{{ auth.me?.display_name }}</strong>
          <span>{{ auth.isAdmin ? "管理员" : "教师" }}</span>
        </div>
        <el-button class="sidebar-account-logout" :icon="SwitchButton" circle text title="退出登录" @click="handleLogout" />
      </div>

      <button
        type="button"
        class="sidebar-collapse-button"
        :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="sidebarCollapsed = !sidebarCollapsed"
      >
        <el-icon>
          <Expand v-if="sidebarCollapsed" />
          <Fold v-else />
        </el-icon>
        <span>{{ sidebarCollapsed ? "展开" : "收起" }}</span>
      </button>
    </el-aside>

    <router-view />
  </el-container>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Collection,
  DocumentChecked,
  Expand,
  Fold,
  Reading,
  School,
  Setting,
  SwitchButton,
  UserFilled,
} from "@element-plus/icons-vue";

import { useAuthStore } from "../stores/authStore";

const MENU_BY_ROUTE = {
  offeringTasks: "offerings",
  taskDetail: "tasks",
};

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const sidebarCollapsed = ref(false);

const activeMenu = computed(() => MENU_BY_ROUTE[route.name] ?? route.name);
const avatarText = computed(() => (auth.me?.display_name ?? "?").trim().slice(0, 1));

function handleMenuSelect(name) {
  if (name !== route.name) router.push({ name });
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm("退出后将清空本机上的全部工作数据。", "退出登录", {
      confirmButtonText: "退出",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }
  await auth.logout();
  ElMessage.success("已退出登录");
  router.replace({ name: "login" });
}
</script>
