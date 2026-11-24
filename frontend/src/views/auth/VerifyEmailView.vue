<template>
  <div class="auth-view">
    <div v-if="state === 'verifying'" class="auth-verifying" v-loading="true" element-loading-text="正在验证邮箱…" />

    <el-result v-else-if="state === 'success'" icon="success" title="邮箱验证成功" :sub-title="message">
      <template #extra>
        <el-button type="primary" @click="router.replace({ name: 'login' })">登录查看审核进度</el-button>
      </template>
    </el-result>

    <template v-else>
      <el-result icon="warning" title="验证链接无效" :sub-title="message">
        <template #extra>
          <el-form class="auth-inline-form" :model="resendForm" @submit.prevent="resend">
            <el-input v-model="resendForm.email" placeholder="输入注册邮箱重新获取验证邮件" />
            <el-button type="primary" native-type="submit" :loading="resending">重新发送</el-button>
          </el-form>
          <el-button text @click="router.replace({ name: 'login' })">返回登录</el-button>
        </template>
      </el-result>
      <el-alert v-if="mockEnabled && mockMailLink" class="auth-alert" type="info" :closable="false" show-icon>
        <template #title>开发预览：模拟验证邮件</template>
        <router-link :to="mockMailLink">打开新的验证链接</router-link>
      </el-alert>
    </template>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { resendVerification, verifyEmail } from "../../api/auth";
import { apiErrorMessage } from "../../api/client";
import { mockEnabled } from "../../api/mock";
import { useMockMail } from "../../composables/useMockMail";

const route = useRoute();
const router = useRouter();
const state = ref("verifying");
const message = ref("");
const resending = ref(false);
const resendForm = reactive({ email: "" });
const { mockMailLink } = useMockMail();

async function verify(token) {
  if (!token) {
    state.value = "failed";
    message.value = "链接缺少验证令牌，请从邮件中重新打开或重新发送验证邮件。";
    return;
  }
  state.value = "verifying";
  try {
    const receipt = await verifyEmail(token);
    message.value = receipt.message;
    state.value = "success";
  } catch (error) {
    message.value = apiErrorMessage(error, "验证链接无效或已过期，请重新发送验证邮件。");
    state.value = "failed";
  }
}

async function resend() {
  const email = resendForm.email.trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) {
    ElMessage.warning("请输入有效邮箱");
    return;
  }
  resending.value = true;
  try {
    const receipt = await resendVerification(email);
    ElMessage.success(receipt.message);
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "发送失败，请稍后重试"));
  } finally {
    resending.value = false;
  }
}

watch(
  () => route.query.token,
  (token) => verify(typeof token === "string" ? token : ""),
  { immediate: true },
);
</script>
