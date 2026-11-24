<template>
  <div class="auth-view">
    <header class="auth-heading">
      <h1>登录 GradeTap</h1>
      <p>使用注册邮箱登录教师工作台。</p>
    </header>

    <el-alert
      v-if="notice"
      class="auth-alert"
      :type="notice.type"
      :title="notice.title"
      :description="notice.description"
      :closable="false"
      show-icon
    >
      <template v-if="notice.resend" #default>
        <p class="auth-alert-text">{{ notice.description }}</p>
        <el-button size="small" :loading="resending" @click="resend">重新发送验证邮件</el-button>
      </template>
    </el-alert>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" autocomplete="username" placeholder="name@school.edu.cn" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" autocomplete="current-password" show-password />
      </el-form-item>
      <el-button class="auth-submit" type="primary" native-type="submit" :loading="submitting">登录</el-button>
    </el-form>

    <p class="auth-switch">还没有账号？<router-link :to="{ name: 'register' }">注册教师账号</router-link></p>

    <el-alert v-if="mockEnabled && mockMailLink" class="auth-alert" type="info" :closable="false" show-icon>
      <template #title>开发预览：模拟验证邮件</template>
      <router-link :to="mockMailLink">打开验证链接</router-link>
    </el-alert>

    <section v-if="mockEnabled" class="auth-dev-panel">
      <div class="auth-dev-heading">
        <strong>开发预览 · 模拟身份</strong>
        <el-button size="small" text type="danger" @click="resetMock">重置模拟数据</el-button>
      </div>
      <div class="auth-dev-accounts">
        <el-button v-for="account in mockAccounts" :key="account.email" size="small" @click="quickLogin(account)">
          {{ account.label }}
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { resendVerification } from "../../api/auth";
import { apiErrorCode, apiErrorMessage } from "../../api/client";
import { mockAccounts, mockEnabled, resetMockState } from "../../api/mock";
import { useMockMail } from "../../composables/useMockMail";
import { useAuthStore } from "../../stores/authStore";

const { mockMailLink } = useMockMail();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const formRef = ref(null);
const submitting = ref(false);
const resending = ref(false);
const notice = ref(null);
const form = reactive({ email: "", password: "" });

const rules = {
  email: [{ required: true, type: "email", message: "请输入有效邮箱", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return;
  submitting.value = true;
  notice.value = null;
  try {
    await auth.login({ email: form.email.trim(), password: form.password });
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : null;
    router.replace(redirect && auth.isActive ? redirect : auth.homeRoute);
  } catch (error) {
    notice.value = describeLoginError(error);
  } finally {
    submitting.value = false;
  }
}

function describeLoginError(error) {
  const code = apiErrorCode(error);
  if (code === "email_verification_required") {
    return {
      type: "warning",
      title: "邮箱尚未验证",
      description: "请打开验证邮件中的链接完成验证；没有收到可重新发送。",
      resend: true,
    };
  }
  if (code === "account_disabled") {
    const reason = error.response.data.status_reason;
    return {
      type: "error",
      title: apiErrorMessage(error, "账号已停用，请联系管理员"),
      description: reason ? `停用原因：${reason}` : "",
    };
  }
  if (!error?.response) {
    return { type: "error", title: "无法连接服务器", description: "请确认后端服务已启动后重试。" };
  }
  return { type: "error", title: apiErrorMessage(error, "登录失败，请稍后重试"), description: "" };
}

async function resend() {
  resending.value = true;
  try {
    const receipt = await resendVerification(form.email.trim());
    ElMessage.success(receipt.message);
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "发送失败，请稍后重试"));
  } finally {
    resending.value = false;
  }
}

function quickLogin(account) {
  form.email = account.email;
  form.password = account.password;
  submit();
}

function resetMock() {
  resetMockState();
  notice.value = null;
  ElMessage.success("模拟数据已重置");
}
</script>
