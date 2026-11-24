<template>
  <ConsolePage
    :title="offering ? `${offering.course_name} · ${offering.class_name}` : '授课班'"
    :subtitle="offering ? `学期 ${offering.term} · 授课班 #${offering.id}` : ''"
    parent-label="我的授课班"
    show-back
    :fallback-route="{ name: 'offerings' }"
    @parent="router.push({ name: 'offerings' })"
  >
    <template #actions>
      <el-button :icon="Refresh" :loading="taskStore.loading" @click="fetchTasks">刷新</el-button>
      <el-button v-if="canCreateTask" type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
    </template>

    <el-result
      v-if="notFound"
      icon="warning"
      title="授课班不存在或无权访问"
      sub-title="请从“我的授课班”重新选择。"
    >
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'offerings' })">返回授课班列表</el-button>
      </template>
    </el-result>

    <div v-else class="panel console-panel">
      <div class="panel-heading">
        <div class="heading-title-row">
          <h2>批改任务</h2>
          <el-tag effect="plain">{{ taskStore.items.length }} 个任务</el-tag>
        </div>
        <el-switch v-model="includeArchived" active-text="显示已归档" @change="fetchTasks" />
      </div>

      <el-table :data="taskStore.items" v-loading="taskStore.loading" class="task-table" :row-class-name="rowClassName">
        <el-table-column label="任务名称" min-width="240">
          <template #default="{ row }">
            <button class="task-name-cell task-name-button" @click="openTask(row)">
              <strong>{{ row.task_name }}</strong>
              <span>{{ row.grading_instruction || "未填写批改说明" }}</span>
            </button>
          </template>
        </el-table-column>
        <el-table-column label="课程作业" min-width="160" align="center">
          <template #default="{ row }">{{ row.assignment_name || "—" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="150" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_archived" type="info" effect="plain">已归档</el-tag>
            <el-tag v-else class="status-tag" :type="taskStatusMeta(row.status).type" effect="light">
              {{ taskStatusMeta(row.status).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180" align="center">
          <template #default="{ row }">{{ formatDateTime(row.archived_at || row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <div v-if="!row.is_archived" class="icon-actions">
              <el-button :icon="FolderChecked" circle text title="归档" @click="archiveTask(row, { keepVisible: includeArchived })" />
              <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteTask(row, { keepVisible: includeArchived })" />
            </div>
            <span v-else class="muted-text">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="includeArchived ? '该授课班暂无任务' : '该授课班暂无进行中的任务'">
            <el-button v-if="canCreateTask" type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
          </el-empty>
        </template>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新建批改任务" width="600px" :lock-scroll="false" class="task-dialog">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="授课班">
          <el-input :model-value="offering ? `${offering.course_name} / ${offering.class_name}（${offering.term}）` : ''" disabled />
        </el-form-item>
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" maxlength="255" placeholder="第4周-异常处理练习" />
        </el-form-item>
        <el-form-item label="课程作业（选填）">
          <el-select
            v-model="form.assignment_id"
            class="form-control"
            clearable
            filterable
            placeholder="关联课程下的作业，可复用作业要求与评分量规"
            :loading="assignmentsLoading"
          >
            <el-option v-for="item in assignments" :key="item.id" :label="item.assignment_name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="批改说明">
          <el-input v-model="form.grading_instruction" type="textarea" :rows="4" placeholder="重点核对边界用例。" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Plus" :loading="submitting" @click="submit">创建任务</el-button>
      </template>
    </el-dialog>
  </ConsolePage>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Delete, FolderChecked, Plus, Refresh } from "@element-plus/icons-vue";

import { apiErrorMessage } from "../../api/client";
import { listCourseAssignments } from "../../api/courses";
import ConsolePage from "../../components/ConsolePage.vue";
import { useTaskRemoval } from "../../composables/useTaskRemoval";
import { useOfferingStore } from "../../stores/offeringStore";
import { useTaskStore } from "../../stores/taskStore";
import { formatDateTime, taskStatusMeta } from "../../utils/taskStatus";

const props = defineProps({
  offeringId: { type: String, required: true },
});

const router = useRouter();
const offeringStore = useOfferingStore();
const taskStore = useTaskStore();
const { deleteTask, archiveTask } = useTaskRemoval();
const formRef = ref(null);
const includeArchived = ref(false);
const notFound = ref(false);
const dialogVisible = ref(false);
const submitting = ref(false);
const assignments = ref([]);
const assignmentsLoading = ref(false);
const form = reactive({ task_name: "", assignment_id: null, grading_instruction: "" });

const rules = {
  task_name: [{ required: true, whitespace: true, message: "请填写任务名称", trigger: "blur" }],
};

const offering = computed(() => offeringStore.byId(props.offeringId));
const canCreateTask = computed(() => Boolean(offering.value?.allowed_actions?.includes("create_task")));

function rowClassName({ row }) {
  return row.is_archived ? "task-row--archived" : "";
}

async function fetchTasks() {
  await taskStore.fetchTasks({ offeringId: Number(props.offeringId), includeArchived: includeArchived.value });
  const status = taskStore.error?.response?.status;
  if (status === 403 || status === 404) notFound.value = true;
}

async function load() {
  notFound.value = false;
  taskStore.$reset();
  try {
    await offeringStore.fetchOfferings();
  } catch {
    // The task request below reports access problems.
  }
  if (!offering.value) {
    notFound.value = true;
    return;
  }
  await fetchTasks();
}

async function openCreate() {
  Object.assign(form, { task_name: "", assignment_id: null, grading_instruction: "" });
  dialogVisible.value = true;
  formRef.value?.clearValidate();
  assignmentsLoading.value = true;
  try {
    assignments.value = await listCourseAssignments(offering.value.course_id);
  } catch {
    assignments.value = [];
  } finally {
    assignmentsLoading.value = false;
  }
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return;
  const assignment = assignments.value.find((item) => item.id === form.assignment_id);
  submitting.value = true;
  try {
    const task = await taskStore.createTask({
      offering_id: offering.value.id,
      task_name: form.task_name.trim(),
      assignment_id: assignment?.id ?? null,
      assignment_name: assignment?.assignment_name ?? "",
      grading_instruction: form.grading_instruction.trim(),
    });
    dialogVisible.value = false;
    ElMessage.success(`任务“${task.task_name}”已创建`);
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, "创建失败，请稍后重试"));
  } finally {
    submitting.value = false;
  }
}

function openTask(task) {
  router.push({ name: "taskDetail", params: { taskId: task.id } });
}

watch(() => props.offeringId, load, { immediate: true });
</script>
