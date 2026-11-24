<template>
  <div class="auth-view">
    <template v-if="!submittedEmail">
      <header class="auth-heading">
        <h1>注册教师账号</h1>
        <p>提交后需完成邮箱验证，并由管理员审核通过才能使用批改功能。</p>
      </header>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="form.display_name" maxlength="64" placeholder="张老师" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" autocomplete="username" placeholder="name@school.edu.cn" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            show-password
            placeholder="至少 8 位"
          />
        </el-form-item>
        <el-form-item label="申请说明（选填）" prop="note">
          <el-input
            v-model="form.note"
            type="textarea"
            :rows="3"
            maxlength="500"
            placeholder="所属学院与授课课程，便于管理员审核"
          />
        </el-form-item>
        <el-button class="auth-submit" type="primary" native-type="submit" :loading="submitting">提交注册</el-button>
      </el-form>

      <p class="auth-switch">已有账号？<router-link :to="{ name: 'login' }">返回登录</router-link></p>
    </template>

    <template v-else>
      <el-result icon="success" title="请查收验证邮件" :sub-title="receiptMessage">
        <template #extra>
          <p class="auth-result-hint">验证邮件已发送至 <strong>{{ submittedEmail }}</strong>，点击邮件中的链接完成验证后即可登录查看审核进度。</p>
          <div class="auth-result-actions">
            <el-button :loading="resending" :disabled="cooldown > 0" @click="resend">
              {{ cooldown > 0 ? `${cooldown} 秒后可重新发送` : "重新发送验证邮件" }}
            </el-button>
            <el-button type="primary" @click="router.push({ name: 'login' })">去登录</el-button>
          </div>
        </template>
      </el-result>
    </template>

    <el-alert v-if="mockEnabled && mockMailLink" class="auth-alert" type="info" :closable="false" show-icon>
      <template #title>开发预览：模拟验证邮件</template>
      <router-link :to="mockMailLink">打开验证链接</router-link>
    </el-alert>
  </div>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { register, resendVerification } from "../../api/auth";
import { apiErrorMessage } from "../../api/client";
import { mockEnabled } from "../../api/mock";
import { useMockMail } from "../../composables/useMockMail";

const RESEND_COOLDOWN_SECONDS = 60;

const router = useRouter();
const formRef = ref(null);
const submitting = ref(false);
const resending = ref(false);
const submittedEmail = ref("");
const receiptMessage = ref("");
const cooldown = ref(0);
const { mockMailLink } = useMockMail();
let cooldownTimer = null;

const form = reactive({ display_name: "", email: "", password: "", note: "" });

const rules = {
  display_name: [{ required: true, whitespace: true, message: "请输入姓名", trigger: "blur" }],
  email: [{ required: true, type: "email", message: "请输入有效邮箱", trigger: "blur" }],
  password: [{ required: true, min: 8, message: "密码至少 8 位", trigger: "blur" }],
};

function startCooldown() {
  cooldown.value = RESEND_COOLDOWN_SECONDS;
  window.clearInterval(cooldownTimer);
  cooldownTimer = window.setInterval(() => {
    cooldown.value -= 1;
    if (cooldown.value <= 0) window.clearInterval(cooldownTimer);
  }, 1000);
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return;
  submitting.value = true;
  try {
    const payload = {
      display_name: form.display_name.trim(),
      email: form.email.trim(),
      password: form.password,
    };
    if (form.note.trim()) payload.note = form.note.trim();
    const receipt = await register(payload);
    receiptMessage.value = receipt.message;
    submittedEmail.value = payload.email;
    startCooldown();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "注册失败，请稍后重试"));
  } finally {
    submitting.value = false;
  }
}

async function resend() {
  resending.value = true;
  try {
    const receipt = await resendVerification(submittedEmail.value);
    ElMessage.success(receipt.message);
    startCooldown();
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "发送失败，请稍后重试"));
  } finally {
    resending.value = false;
  }
}

onBeforeUnmount(() => window.clearInterval(cooldownTimer));
</script>
