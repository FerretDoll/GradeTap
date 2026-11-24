<template>
  <ConsolePage title="教师账号" subtitle="审核教师注册申请，管理账号启用与停用。">
    <template #actions>
      <el-button :icon="Refresh" :loading="loading" @click="fetchTeachers">刷新</el-button>
    </template>

    <el-result v-if="forbidden" icon="warning" title="无权访问" sub-title="教师账号管理仅对平台管理员开放。" />

    <div v-else class="panel console-panel">
      <div class="panel-heading">
        <div class="heading-title-row">
          <h2>账号列表</h2>
          <el-tag effect="plain">{{ teachers.length }} 个账号</el-tag>
        </div>
        <el-radio-group v-model="statusFilter" @change="fetchTeachers">
          <el-radio-button v-for="option in statusOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <el-table :data="teachers" v-loading="loading" class="task-table" empty-text="暂无符合条件的教师账号">
        <el-table-column prop="display_name" label="姓名" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="220" />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="accountStatusMeta(row.account_status).type" effect="light">
              {{ accountStatusMeta(row.account_status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="驳回 / 停用原因" min-width="200">
          <template #default="{ row }">
            <span class="muted-text">{{ row.status_reason || "—" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <div v-if="row.account_status === 'pending_approval'" class="text-actions">
              <el-button size="small" type="primary" :loading="busyId === row.user_id" @click="act(row, 'approve')">批准</el-button>
              <el-button size="small" type="danger" plain :disabled="busyId === row.user_id" @click="act(row, 'reject')">驳回</el-button>
            </div>
            <el-button
              v-else-if="row.account_status === 'active'"
              size="small"
              type="danger"
              plain
              :loading="busyId === row.user_id"
              @click="act(row, 'disable')"
            >
              停用
            </el-button>
            <span v-else class="muted-text">—</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </ConsolePage>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";

import { changeTeacherStatus, listTeachers } from "../../api/admin";
import { apiErrorCode, apiErrorMessage } from "../../api/client";
import ConsolePage from "../../components/ConsolePage.vue";
import { accountStatusMeta } from "../../utils/taskStatus";

const statusOptions = [
  { value: "pending_approval", label: "待审核" },
  { value: "active", label: "已启用" },
  { value: "rejected", label: "已驳回" },
  { value: "disabled", label: "已停用" },
  { value: "", label: "全部" },
];

const ACTION_COPY = {
  approve: { title: "批准账号", success: "已批准" },
  reject: { title: "驳回申请", success: "已驳回", prompt: "请填写驳回原因，教师登录后可见并据此补充材料。" },
  disable: { title: "停用账号", success: "已停用", prompt: "请填写停用原因。停用后该教师的在线会话会立即失效。" },
};

const teachers = ref([]);
const loading = ref(false);
const forbidden = ref(false);
const busyId = ref(null);
const statusFilter = ref("pending_approval");

async function fetchTeachers() {
  loading.value = true;
  try {
    teachers.value = await listTeachers(statusFilter.value || undefined);
    forbidden.value = false;
  } catch (error) {
    if (error?.response?.status === 403) {
      forbidden.value = true;
    } else {
      ElMessage.error(apiErrorMessage(error, "教师列表加载失败"));
    }
  } finally {
    loading.value = false;
  }
}

async function askReason(row, action) {
  const copy = ACTION_COPY[action];
  if (!copy.prompt) {
    await ElMessageBox.confirm(`确定批准“${row.display_name}”（${row.email}）的账号申请吗？`, copy.title, {
      confirmButtonText: "批准",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "info",
    });
    return undefined;
  }
  const { value } = await ElMessageBox.prompt(copy.prompt, `${copy.title} · ${row.display_name}`, {
    confirmButtonText: copy.title.slice(0, 2),
    cancelButtonText: "取消",
    inputType: "textarea",
    inputPlaceholder: "原因（必填）",
    inputValidator: (input) => Boolean(input?.trim()) || "原因不能为空",
    lockScroll: false,
    type: "warning",
  });
  return value.trim();
}

async function act(row, action) {
  let reason;
  try {
    reason = await askReason(row, action);
  } catch {
    return;
  }
  busyId.value = row.user_id;
  try {
    const payload = { action, expected_version: row.version };
    if (reason) payload.reason = reason;
    await changeTeacherStatus(row.user_id, payload);
    ElMessage.success(`${ACTION_COPY[action].success}“${row.display_name}”`);
  } catch (error) {
    if (apiErrorCode(error) === "version_conflict" || error?.response?.status === 409) {
      ElMessage.warning(apiErrorMessage(error, "状态已更新，已为您刷新列表"));
    } else if (error?.response?.status === 403) {
      forbidden.value = true;
    } else {
      ElMessage.error(apiErrorMessage(error, "操作失败，请稍后重试"));
    }
  } finally {
    busyId.value = null;
  }
  await fetchTeachers();
}

onMounted(fetchTeachers);
</script>
