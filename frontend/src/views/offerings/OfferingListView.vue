<template>
  <ConsolePage title="我的授课班" subtitle="按课程、班级与学期组织批改任务，不同授课班的数据彼此隔离。">
    <template #actions>
      <el-button :icon="Refresh" :loading="offeringStore.loading" @click="reload">刷新</el-button>
      <el-button type="primary" :icon="Plus" @click="openCreate">新建授课班</el-button>
    </template>

    <div class="panel console-panel">
      <div class="panel-heading">
        <div class="heading-title-row">
          <h2>授课班</h2>
          <el-tag effect="plain">{{ offeringStore.items.length }} 个授课班</el-tag>
        </div>
      </div>

      <el-table :data="offeringStore.items" v-loading="offeringStore.loading" class="task-table">
        <el-table-column label="课程" min-width="200">
          <template #default="{ row }">
            <button class="task-name-cell task-name-button" @click="openOffering(row)">
              <strong>{{ row.course_name }}</strong>
              <span>授课班 #{{ row.id }}</span>
            </button>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" min-width="160" align="center" />
        <el-table-column prop="term" label="学期" width="140" align="center" />
        <el-table-column label="我的角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.teaching_role === 'owner' ? 'success' : 'info'" effect="light">
              {{ row.teaching_role === "owner" ? "负责教师" : "协作教师" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button :icon="Right" circle text title="查看任务" @click="openOffering(row)" />
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="尚未建立授课班，新建后即可在授课班下创建批改任务">
            <el-button type="primary" :icon="Plus" @click="openCreate">新建授课班</el-button>
          </el-empty>
        </template>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新建授课班" width="560px" :lock-scroll="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="课程" prop="course">
          <el-radio-group v-model="form.courseMode" class="offering-mode">
            <el-radio-button value="existing" :disabled="!courses.length">选择已有课程</el-radio-button>
            <el-radio-button value="new">新建课程</el-radio-button>
          </el-radio-group>
          <el-select
            v-if="form.courseMode === 'existing'"
            v-model="form.course_id"
            class="form-control"
            filterable
            placeholder="选择课程"
            :loading="optionsLoading"
          >
            <el-option v-for="course in courses" :key="course.id" :label="course.course_name" :value="course.id" />
          </el-select>
          <el-input v-else v-model="form.course_name" maxlength="255" placeholder="例如：Python 编程基础" />
        </el-form-item>
        <el-form-item label="班级" prop="classGroup">
          <el-radio-group v-model="form.classMode" class="offering-mode">
            <el-radio-button value="existing" :disabled="!classes.length">选择已有班级</el-radio-button>
            <el-radio-button value="new">新建班级</el-radio-button>
          </el-radio-group>
          <el-select
            v-if="form.classMode === 'existing'"
            v-model="form.class_group_id"
            class="form-control"
            filterable
            placeholder="选择班级"
            :loading="optionsLoading"
          >
            <el-option v-for="item in classes" :key="item.id" :label="item.class_name" :value="item.id" />
          </el-select>
          <el-input v-else v-model="form.class_name" maxlength="255" placeholder="例如：软件试点班" />
        </el-form-item>
        <el-form-item label="学期" prop="term">
          <el-select v-model="form.term" class="form-control" filterable allow-create default-first-option>
            <el-option v-for="term in termOptions" :key="term" :label="term" :value="term" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Plus" :loading="submitting" @click="submit">创建授课班</el-button>
      </template>
    </el-dialog>
  </ConsolePage>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Plus, Refresh, Right } from "@element-plus/icons-vue";

import { listClasses } from "../../api/classes";
import { apiErrorCode, apiErrorMessage } from "../../api/client";
import { listCourses } from "../../api/courses";
import ConsolePage from "../../components/ConsolePage.vue";
import { useOfferingStore } from "../../stores/offeringStore";

const offeringStore = useOfferingStore();
const router = useRouter();
const formRef = ref(null);
const dialogVisible = ref(false);
const submitting = ref(false);
const optionsLoading = ref(false);
const courses = ref([]);
const classes = ref([]);
const termOptions = buildTermOptions();

const form = reactive({
  courseMode: "new",
  course_id: null,
  course_name: "",
  classMode: "new",
  class_group_id: null,
  class_name: "",
  term: termOptions[1],
});

const rules = {
  course: [{ validator: (_rule, _value, callback) => callback(hasCourse() ? undefined : new Error("请选择或填写课程")) }],
  classGroup: [{ validator: (_rule, _value, callback) => callback(hasClass() ? undefined : new Error("请选择或填写班级")) }],
  term: [{ required: true, message: "请选择学期", trigger: "change" }],
};

function buildTermOptions(today = new Date()) {
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const startYear = month >= 8 ? year : year - 1;
  const term = (from, semester) => `${from}-${from + 1}-${semester}`;
  if (month >= 8 || month < 2) {
    return [term(startYear - 1, 2), term(startYear, 1), term(startYear, 2)];
  }
  return [term(startYear, 1), term(startYear, 2), term(startYear + 1, 1)];
}

function hasCourse() {
  return form.courseMode === "existing" ? Boolean(form.course_id) : Boolean(form.course_name.trim());
}

function hasClass() {
  return form.classMode === "existing" ? Boolean(form.class_group_id) : Boolean(form.class_name.trim());
}

async function reload() {
  try {
    await offeringStore.fetchOfferings({ force: true });
  } catch (error) {
    if (error?.response?.status !== 403) ElMessage.error(apiErrorMessage(error, "授课班加载失败"));
  }
}

async function loadOptions() {
  optionsLoading.value = true;
  const [courseResult, classResult] = await Promise.allSettled([listCourses(), listClasses()]);
  courses.value = courseResult.status === "fulfilled" ? courseResult.value : [];
  classes.value = classResult.status === "fulfilled" ? classResult.value : [];
  optionsLoading.value = false;
}

async function openCreate() {
  Object.assign(form, {
    courseMode: "new",
    course_id: null,
    course_name: "",
    classMode: "new",
    class_group_id: null,
    class_name: "",
    term: termOptions[1],
  });
  dialogVisible.value = true;
  formRef.value?.clearValidate();
  await loadOptions();
  if (courses.value.length) form.courseMode = "existing";
  if (classes.value.length) form.classMode = "existing";
}

function buildPayload() {
  const payload = { term: String(form.term).trim() };
  if (form.courseMode === "existing") payload.course_id = form.course_id;
  else payload.course_name = form.course_name.trim();
  if (form.classMode === "existing") payload.class_group_id = form.class_group_id;
  else payload.class_name = form.class_name.trim();
  return payload;
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return;
  submitting.value = true;
  try {
    const offering = await offeringStore.createOffering(buildPayload());
    dialogVisible.value = false;
    ElMessage.success(`已创建授课班：${offering.course_name} / ${offering.class_name}`);
  } catch (error) {
    if (apiErrorCode(error) === "offering_already_exists") {
      ElMessage.warning(apiErrorMessage(error, "本学期已存在相同的课程与班级授课班"));
    } else {
      ElMessage.error(apiErrorMessage(error, "创建失败，请稍后重试"));
    }
  } finally {
    submitting.value = false;
  }
}

function openOffering(offering) {
  router.push({ name: "offeringTasks", params: { offeringId: offering.id } });
}

onMounted(reload);
</script>
