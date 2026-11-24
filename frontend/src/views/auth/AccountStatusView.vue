<template>
  <div class="auth-view">
    <header class="auth-heading">
      <h1>{{ auth.me?.display_name }}，{{ heading }}</h1>
      <p>账号启用前只能查看审核状态，不能访问授课班与批改数据。</p>
    </header>

    <el-steps class="account-steps" :active="activeStep" :process-status="isRejected ? 'error' : 'process'" finish-status="success" align-center>
      <el-step title="提交注册" />
      <el-step title="邮箱验证" />
      <el-step :title="isRejected ? '审核驳回' : '管理员审核'" />
      <el-step title="账号启用" />
    </el-steps>

    <template v-if="isRejected">
      <el-alert class="auth-alert" type="error" title="申请已被驳回" :closable="false" show-icon>
        <p class="auth-alert-text">驳回原因：{{ auth.me?.status_reason || "管理员未填写原因" }}</p>
      </el-alert>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="resubmit">
        <el-form-item label="姓名（可修改）" prop="display_name">
          <el-input v-model="form.display_name" maxlength="64" />
        </el-form-item>
        <el-form-item label="补充说明" prop="note">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="针对驳回原因补充所属学院、授课课程等信息"
          />
        </el-form-item>
        <el-button class="auth-submit" type="primary" native-type="submit" :loading="submitting">重新提交审核</el-button>
      </el-form>
    </template>

    <el-alert v-else class="auth-alert" type="info" title="已提交审核" :closable="false" show-icon>
      <p class="auth-alert-text">管理员审核通过后，点击“刷新状态”即可进入授课班工作台。</p>
    </el-alert>

    <div class="auth-result-actions">
      <el-button v-if="!isRejected" type="primary" :icon="Refresh" :loading="refreshing" @click="refresh">刷新状态</el-button>
      <el-button :icon="SwitchButton" @click="logout">退出登录</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Refresh, SwitchButton } from "@element-plus/icons-vue";

import { apiErrorCode, apiErrorMessage } from "../../api/client";
import { useAuthStore } from "../../stores/authStore";

const auth = useAuthStore();
const router = useRouter();
const formRef = ref(null);
const refreshing = ref(false);
const submitting = ref(false);
const form = reactive({ display_name: "", note: "" });

const isRejected = computed(() => auth.me?.account_status === "rejected");
const heading = computed(() => (isRejected.value ? "您的申请需要补充信息" : "您的账号正在等待审核"));
const activeStep = computed(() => (auth.me?.account_status === "pending_verification" ? 1 : 2));

const rules = {
  display_name: [{ required: true, whitespace: true, message: "请输入姓名", trigger: "blur" }],
  note: [{ required: true, whitespace: true, message: "请填写补充说明", trigger: "blur" }],
};

watch(
  () => auth.me?.display_name,
  (name) => {
    form.display_name = name ?? "";
  },
  { immediate: true },
);

async function refresh() {
  refreshing.value = true;
  try {
    await auth.refreshMe();
    if (!auth.isAuthenticated) {
      router.replace({ name: "login" });
    } else if (auth.isActive) {
      ElMessage.success("账号已启用");
      router.replace(auth.homeRoute);
    } else if (!isRejected.value) {
      ElMessage.info("仍在等待管理员审核");
    }
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "刷新失败，请稍后重试"));
  } finally {
    refreshing.value = false;
  }
}

async function resubmit() {
  if (!(await formRef.value.validate().catch(() => false))) return;
  submitting.value = true;
  try {
    await auth.resubmit({ display_name: form.display_name.trim(), note: form.note.trim() });
    form.note = "";
    ElMessage.success("已重新提交审核");
  } catch (error) {
    if (apiErrorCode(error) === "invalid_state" || error?.response?.status === 409) {
      ElMessage.warning("账号状态已变化，已为您刷新");
      await refresh();
    } else {
      ElMessage.error(apiErrorMessage(error, "提交失败，请稍后重试"));
    }
  } finally {
    submitting.value = false;
  }
}

async function logout() {
  await auth.logout();
  router.replace({ name: "login" });
}
</script>
