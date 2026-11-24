<template>
  <el-container class="main-shell">
    <el-header class="topbar">
      <div class="page-title" :class="{ 'page-title--detail': parentLabel }">
        <div v-if="parentLabel" class="topbar-detail-path">
          <button type="button" class="topbar-detail-path-button" @click="$emit('parent')">{{ parentLabel }}</button>
          <span class="topbar-detail-path-arrow">›</span>
          <h1>{{ title }}</h1>
          <slot name="title-extra" />
        </div>
        <h1 v-else>{{ title }}</h1>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <div class="topbar-actions">
        <el-button v-if="showBack" :icon="Back" @click="goBack">返回上一页</el-button>
        <slot name="actions" />
      </div>
    </el-header>

    <el-main class="workspace">
      <div class="view-panel console-view">
        <slot />
      </div>
    </el-main>
    <el-footer class="app-footer">© 2026 武汉软件工程职业学院 信息学院</el-footer>
  </el-container>
</template>

<script setup>
import { useRouter } from "vue-router";
import { Back } from "@element-plus/icons-vue";

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  parentLabel: { type: String, default: "" },
  showBack: { type: Boolean, default: false },
  fallbackRoute: { type: Object, default: () => ({ name: "home" }) },
});

defineEmits(["parent"]);

const router = useRouter();

function goBack() {
  if (window.history.state?.back) {
    router.back();
  } else {
    router.push(props.fallbackRoute);
  }
}
</script>
