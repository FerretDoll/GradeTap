<template>
  <el-container class="app-shell grade-console">
    <el-aside class="sidebar" width="264px">
      <div class="brand-lockup">
        <div class="brand-mark">GT</div>
        <div>
          <strong>GradeTap</strong>
          <span>AI 作业批改助手</span>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="side-menu" @select="handleMenuSelect">
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
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="page-title">
          <span class="eyebrow">{{ currentPage.eyebrow }}</span>
          <h1>{{ currentPage.title }}</h1>
        </div>
        <div class="topbar-actions">
          <el-button
            v-if="detailViews.includes(activeView)"
            :icon="Back"
            @click="returnToList"
          >
            返回列表
          </el-button>
          <el-button v-if="activeView === 'tasks'" :icon="Refresh" @click="taskStore.fetchTasks">
            刷新
          </el-button>
          <el-button
            v-if="activeView === 'tasks'"
            type="primary"
            :icon="Plus"
            @click="openCreateTask"
          >
            新建任务
          </el-button>
          <el-button
            v-else-if="activeView === 'classes'"
            type="primary"
            :icon="Plus"
            @click="openCreateClass"
          >
            新建班级
          </el-button>
          <el-button
            v-else-if="activeView === 'courses'"
            type="primary"
            :icon="Plus"
            @click="openCreateCourse"
          >
            新建课程
          </el-button>
        </div>
      </el-header>

      <el-main class="workspace">
        <Transition name="view-float" mode="out-in">
          <div :key="activeView" class="view-panel">
            <section v-if="activeView === 'tasks'" class="overview-band">
              <div class="overview-copy">
                <span>本周批改</span>
                <strong>统一评分、保留证据、教师最终确认</strong>
              </div>
              <div class="metric-strip">
                <div v-for="metric in metrics" :key="metric.label" class="metric-item">
                  <span>{{ metric.label }}</span>
                  <strong>{{ metric.value }}</strong>
                </div>
              </div>
            </section>

            <section v-if="activeView === 'tasks'" class="content-grid">
              <div class="panel task-panel">
                <div class="panel-heading">
                  <div>
                    <span class="section-kicker">Tasks</span>
                    <h2>批改任务</h2>
                  </div>
                  <el-tag effect="plain">{{ taskStore.items.length }} 个任务</el-tag>
                </div>

                <el-table
                  :data="taskStore.items"
                  v-loading="taskStore.loading"
                  height="448"
                  class="task-table"
                  empty-text="暂无批改任务"
                >
                  <el-table-column prop="task_name" label="任务名称" min-width="220">
                    <template #default="{ row }">
                      <button class="task-name-cell task-name-button" @click="openTaskDetail(row)">
                        <strong>{{ row.task_name }}</strong>
                        <span>{{ row.grading_instruction || "未填写批改说明" }}</span>
                      </button>
                    </template>
                  </el-table-column>
                  <el-table-column prop="course_name" label="课程" width="160" align="center" />
                  <el-table-column prop="class_name" label="班级" width="140" align="center" />
                  <el-table-column prop="status" label="状态" width="150" align="center">
                    <template #default="{ row }">
                      <el-tag class="status-tag" effect="light">{{ row.status }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="120" fixed="right" align="center">
                    <template #default="{ row }">
                      <div class="icon-actions">
                        <el-button :icon="Edit" circle text title="编辑" @click="editTask(row)" />
                        <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteTask(row)" />
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </section>

            <section v-else-if="activeView === 'taskDetail'" class="task-detail">
              <el-button class="inline-back" :icon="Back" @click="returnToList">
                返回上一页
              </el-button>
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Task Detail</span>
                  <h2>{{ selectedTask?.task_name || "批改任务" }}</h2>
                  <p>{{ selectedTask?.course_name }} / {{ selectedTask?.class_name }}</p>
                </div>
                <el-tag class="status-tag" effect="light">{{ selectedTask?.status || "created" }}</el-tag>
              </div>

              <div class="detail-grid">
                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Progress</span>
                      <h2>批改进度</h2>
                    </div>
                    <strong>{{ selectedTaskProgress }}%</strong>
                  </div>
                  <el-progress :percentage="selectedTaskProgress" :stroke-width="10" />
                  <div class="progress-stages">
                    <div
                      v-for="stage in taskStages"
                      :key="stage.key"
                      class="progress-stage"
                      :class="{ active: stage.key === selectedTask?.current_stage }"
                    >
                      <strong>{{ stage.title }}</strong>
                      <span>{{ stage.caption }}</span>
                    </div>
                  </div>
                </div>

                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Files</span>
                      <h2>任务材料</h2>
                    </div>
                  </div>
                  <div class="material-list">
                    <div v-for="material in taskMaterials" :key="material">
                      <span>{{ material }}</span>
                      <el-tag effect="plain">待上传</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section v-else-if="activeView === 'courses'" class="class-workspace">
              <div class="class-summary">
                <div v-for="item in courseSummary" :key="item.label" class="class-summary-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>

              <div class="panel">
                <div class="panel-heading">
                  <div>
                    <span class="section-kicker">Courses</span>
                    <h2>课程列表</h2>
                  </div>
                  <el-tag effect="plain">{{ courses.length }} 门课程</el-tag>
                </div>

                <el-table :data="courses" height="448" class="task-table" empty-text="暂无课程">
                  <el-table-column prop="course_name" label="课程名称" min-width="260">
                    <template #default="{ row }">
                      <button class="task-name-cell task-name-button" @click="openCourseDetail(row)">
                        <strong>{{ row.course_name }}</strong>
                        <span>{{ row.description || "未填写课程说明" }}</span>
                      </button>
                    </template>
                  </el-table-column>
                  <el-table-column prop="assignment_count" label="作业数量" width="140" align="center" />
                  <el-table-column label="操作" width="120" fixed="right" align="center">
                    <template #default="{ row }">
                      <div class="icon-actions">
                        <el-button :icon="Edit" circle text title="编辑" @click="editCourse(row)" />
                        <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteCourse(row)" />
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </section>

            <section v-else-if="activeView === 'courseDetail'" class="task-detail">
              <el-button class="inline-back" :icon="Back" @click="returnToList">
                返回上一页
              </el-button>
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Course Detail</span>
                  <h2>{{ selectedCourse?.course_name || "课程" }}</h2>
                  <p>{{ selectedCourse?.description || "未填写课程说明" }}</p>
                </div>
                <el-tag effect="plain">{{ selectedCourse?.assignment_count ?? 0 }} 个作业</el-tag>
              </div>

              <div class="detail-grid">
                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Assignments</span>
                      <h2>课程作业</h2>
                    </div>
                  </div>
                  <div class="material-list">
                    <div>
                      <span>已归档作业</span>
                      <el-tag effect="plain">{{ selectedCourse?.assignment_count ?? 0 }}</el-tag>
                    </div>
                    <div>
                      <span>最近批改任务</span>
                      <el-tag effect="plain">暂无</el-tag>
                    </div>
                  </div>
                </div>

                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Classes</span>
                      <h2>关联班级</h2>
                    </div>
                  </div>
                  <div class="material-list">
                    <div v-for="classItem in classes" :key="classItem.id">
                      <span>{{ classItem.class_name }}</span>
                      <el-tag effect="plain">{{ classItem.student_count }} 人</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section v-else-if="activeView === 'classes'" class="class-workspace">
              <div class="class-summary">
                <div v-for="item in classSummary" :key="item.label" class="class-summary-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>

              <div class="panel">
                <div class="panel-heading">
                  <div>
                    <span class="section-kicker">Classes</span>
                    <h2>班级列表</h2>
                  </div>
                  <el-tag effect="plain">{{ classes.length }} 个班级</el-tag>
                </div>

                <el-table :data="classes" height="448" class="task-table" empty-text="暂无班级">
                  <el-table-column prop="class_name" label="班级名称" min-width="180">
                    <template #default="{ row }">
                      <button class="task-name-cell task-name-button" @click="openClassDetail(row)">
                        <strong>{{ row.class_name }}</strong>
                        <span>{{ row.note || "未填写备注" }}</span>
                      </button>
                    </template>
                  </el-table-column>
                  <el-table-column prop="student_count" label="学生数" width="120" align="center" />
                  <el-table-column label="操作" width="120" fixed="right" align="center">
                    <template #default="{ row }">
                      <div class="icon-actions">
                        <el-button :icon="Edit" circle text title="编辑" @click="editClass(row)" />
                        <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteClass(row)" />
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </section>

            <section v-else-if="activeView === 'classDetail'" class="task-detail">
              <el-button class="inline-back" :icon="Back" @click="returnToList">
                返回上一页
              </el-button>
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Class Detail</span>
                  <h2>{{ selectedClass?.class_name || "班级" }}</h2>
                  <p>{{ selectedClass?.note || "未填写备注" }}</p>
                </div>
                <el-tag effect="plain">{{ selectedClass?.student_count ?? 0 }} 名学生</el-tag>
              </div>

              <div class="detail-grid">
                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Students</span>
                      <h2>学生概况</h2>
                    </div>
                  </div>
                  <div class="material-list">
                    <div>
                      <span>学生总数</span>
                      <el-tag effect="plain">{{ selectedClass?.student_count ?? 0 }}</el-tag>
                    </div>
                    <div>
                      <span>待复核作业</span>
                      <el-tag effect="plain">暂无</el-tag>
                    </div>
                  </div>
                </div>

                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Tasks</span>
                      <h2>班级任务</h2>
                    </div>
                  </div>
                  <div class="material-list">
                    <div>
                      <span>批改任务</span>
                      <el-tag effect="plain">0</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </Transition>
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="taskDialogVisible" :title="editingTaskId ? '编辑批改任务' : '新建批改任务'" width="600px" class="task-dialog">
    <el-form :model="form" label-position="top">
      <div class="form-grid">
        <el-form-item label="作业名称">
          <el-input v-model="form.task_name" placeholder="SQL 数据库第 13 周作业" />
        </el-form-item>
        <el-form-item label="课程名称">
          <el-select v-model="form.course_name" placeholder="请选择课程" class="form-control">
            <el-option
              v-for="course in courses"
              :key="course.id"
              :label="course.course_name"
              :value="course.course_name"
            />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="班级名称">
        <el-select v-model="form.class_name" placeholder="请选择班级" class="form-control">
          <el-option
            v-for="classItem in classes"
            :key="classItem.id"
            :label="classItem.class_name"
            :value="classItem.class_name"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="批改说明">
        <el-input
          v-model="form.grading_instruction"
          type="textarea"
          :rows="4"
          placeholder="重点考查 SQL 语法、结果正确性和代码规范。"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="taskDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingTaskId ? Check : Plus" :loading="submitting" @click="submitTask">
        {{ editingTaskId ? "保存任务" : "创建任务" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="classDialogVisible" :title="editingClassId ? '编辑班级' : '新建班级'" width="560px">
    <el-form :model="classForm" label-position="top">
      <el-form-item label="班级名称">
        <el-input v-model="classForm.class_name" placeholder="软件 2301" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input
          v-model="classForm.note"
          type="textarea"
          :rows="3"
          placeholder="例如：高职软件技术专业，SQL 作业较多。"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="classDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingClassId ? Check : Plus" @click="submitClass">
        {{ editingClassId ? "保存班级" : "创建班级" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="courseDialogVisible" :title="editingCourseId ? '编辑课程' : '新建课程'" width="600px">
    <el-form :model="courseForm" label-position="top">
      <el-form-item label="课程名称">
        <el-input v-model="courseForm.course_name" placeholder="数据库应用技术" />
      </el-form-item>
      <el-form-item label="课程说明">
        <el-input
          v-model="courseForm.description"
          type="textarea"
          :rows="3"
          placeholder="保存本课程相关作业和历史批改资料。"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="courseDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingCourseId ? Check : Plus" @click="submitCourse">
        {{ editingCourseId ? "保存课程" : "创建课程" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Back,
  Check,
  Collection,
  Delete,
  DocumentChecked,
  Edit,
  Plus,
  Refresh,
  School,
} from "@element-plus/icons-vue";

import { useTaskStore } from "./stores/taskStore";

const taskStore = useTaskStore();
const activeView = ref("tasks");
const selectedTaskId = ref(null);
const selectedCourseId = ref(null);
const selectedClassId = ref(null);
const editingTaskId = ref(null);
const editingCourseId = ref(null);
const editingClassId = ref(null);
const taskDialogVisible = ref(false);
const classDialogVisible = ref(false);
const courseDialogVisible = ref(false);
const submitting = ref(false);

const form = reactive({
  task_name: "",
  course_name: "",
  class_name: "",
  grading_instruction: "",
});

const classForm = reactive({
  class_name: "",
  note: "",
});

const courseForm = reactive({
  course_name: "",
  description: "",
});

const courses = ref([
  {
    id: 1,
    course_name: "数据库应用技术",
    assignment_count: 8,
    description: "SQL 作业、实验报告和课程项目批改资料",
  },
  {
    id: 2,
    course_name: "Python 程序设计",
    assignment_count: 6,
    description: "代码作业、函数练习和综合项目资料",
  },
]);

const classes = ref([
  {
    id: 1,
    class_name: "软件 2301",
    student_count: 45,
    note: "SQL 作业与实验报告批改班级",
  },
  {
    id: 2,
    class_name: "软件 2302",
    student_count: 42,
    note: "代码作业批改班级",
  },
]);

const pageMeta = {
  tasks: {
    eyebrow: "Teacher Review Console",
    title: "批改任务工作台",
  },
  classes: {
    eyebrow: "Class Operations",
    title: "班级管理",
  },
  courses: {
    eyebrow: "Course Management",
    title: "课程管理",
  },
  taskDetail: {
    eyebrow: "Task Progress",
    title: "任务进度",
  },
  courseDetail: {
    eyebrow: "Course Detail",
    title: "课程明细",
  },
  classDetail: {
    eyebrow: "Class Detail",
    title: "班级明细",
  },
};

const detailViews = ["taskDetail", "courseDetail", "classDetail"];
const currentPage = computed(() => pageMeta[activeView.value]);
const activeMenu = computed(() => {
  if (activeView.value === "taskDetail") {
    return "tasks";
  }
  if (activeView.value === "courseDetail") {
    return "courses";
  }
  if (activeView.value === "classDetail") {
    return "classes";
  }
  return activeView.value;
});
const selectedTask = computed(() =>
  taskStore.items.find((task) => task.id === selectedTaskId.value),
);
const selectedCourse = computed(() =>
  courses.value.find((course) => course.id === selectedCourseId.value),
);
const selectedClass = computed(() =>
  classes.value.find((classItem) => classItem.id === selectedClassId.value),
);
const selectedTaskProgress = computed(() => selectedTask.value?.progress ?? 0);

const metrics = [
  { label: "待确认标准", value: "0" },
  { label: "批改中", value: "0" },
  { label: "需复核", value: "0" },
  { label: "可导出", value: "0" },
];

const classSummary = computed(() => [
  { label: "班级总数", value: classes.value.length },
  {
    label: "学生总数",
    value: classes.value.reduce((sum, item) => sum + item.student_count, 0),
  },
]);

const courseSummary = computed(() => [
  { label: "课程总数", value: courses.value.length },
  {
    label: "作业数量",
    value: courses.value.reduce((sum, item) => sum + item.assignment_count, 0),
  },
]);

const taskStages = [
  { key: "created", title: "创建任务", caption: "等待上传材料" },
  { key: "parse_files", title: "解析文件", caption: "读取要求与参考答案" },
  { key: "extract_answers", title: "抽取答案", caption: "按题匹配学生作答" },
  { key: "grade_by_question", title: "按题批改", caption: "统一评分标准" },
  { key: "teacher_review", title: "教师复核", caption: "确认最终分数" },
  { key: "summary", title: "汇总导出", caption: "生成成绩与报告" },
];

const taskMaterials = ["作业要求", "参考答案", "学生作业"];

onMounted(() => {
  taskStore.fetchTasks();
});

function submitTask() {
  if (!form.task_name.trim()) {
    ElMessage.warning("请填写作业名称");
    return;
  }
  if (!form.course_name) {
    ElMessage.warning("请选择课程");
    return;
  }
  if (!form.class_name) {
    ElMessage.warning("请选择班级");
    return;
  }

  submitting.value = true;
  const wasEditing = Boolean(editingTaskId.value);
  let task;
  if (wasEditing) {
    taskStore.updateTask(editingTaskId.value, { ...form });
    task = taskStore.items.find((item) => item.id === editingTaskId.value);
  } else {
    task = taskStore.createTask({ ...form });
  }
  Object.assign(form, {
    task_name: "",
    course_name: "",
    class_name: "",
    grading_instruction: "",
  });
  editingTaskId.value = null;
  taskDialogVisible.value = false;
  selectedTaskId.value = task?.id ?? null;
  activeView.value = "tasks";
  submitting.value = false;
  ElMessage.success(wasEditing ? "任务已保存" : "任务已创建");
}

function handleMenuSelect(view) {
  activeView.value = view;
}

function openCreateTask() {
  editingTaskId.value = null;
  Object.assign(form, {
    task_name: "",
    course_name: "",
    class_name: "",
    grading_instruction: "",
  });
  taskDialogVisible.value = true;
}

function returnToList() {
  if (activeView.value === "taskDetail") {
    activeView.value = "tasks";
    return;
  }
  if (activeView.value === "courseDetail") {
    activeView.value = "courses";
    return;
  }
  activeView.value = "classes";
}

function openTaskDetail(task) {
  selectedTaskId.value = task.id;
  activeView.value = "taskDetail";
}

function startTask(task) {
  taskStore.startTask(task.id);
  openTaskDetail(task);
  ElMessage.success("批改已开始");
}

function editTask(task) {
  editingTaskId.value = task.id;
  Object.assign(form, {
    task_name: task.task_name,
    course_name: task.course_name,
    class_name: task.class_name,
    grading_instruction: task.grading_instruction,
  });
  taskDialogVisible.value = true;
}

async function deleteTask(task) {
  try {
    await ElMessageBox.confirm(
      `确定删除批改任务「${task.task_name}」吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  taskStore.deleteTask(task.id);
  if (selectedTaskId.value === task.id) {
    selectedTaskId.value = null;
    activeView.value = "tasks";
  }
  ElMessage.success("任务已删除");
}

function openCourseDetail(course) {
  selectedCourseId.value = course.id;
  activeView.value = "courseDetail";
}

function openClassDetail(classItem) {
  selectedClassId.value = classItem.id;
  activeView.value = "classDetail";
}

function openCreateClass() {
  editingClassId.value = null;
  Object.assign(classForm, {
    class_name: "",
    note: "",
  });
  classDialogVisible.value = true;
}

function openCreateCourse() {
  editingCourseId.value = null;
  Object.assign(courseForm, {
    course_name: "",
    description: "",
  });
  courseDialogVisible.value = true;
}

function editClass(classItem) {
  editingClassId.value = classItem.id;
  Object.assign(classForm, {
    class_name: classItem.class_name,
    note: classItem.note,
  });
  classDialogVisible.value = true;
}

async function deleteClass(classItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除班级「${classItem.class_name}」吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  classes.value = classes.value.filter((item) => item.id !== classItem.id);
  if (selectedClassId.value === classItem.id) {
    selectedClassId.value = null;
    activeView.value = "classes";
  }
  ElMessage.success("班级已删除");
}

function editCourse(course) {
  editingCourseId.value = course.id;
  Object.assign(courseForm, {
    course_name: course.course_name,
    description: course.description,
  });
  courseDialogVisible.value = true;
}

async function deleteCourse(course) {
  try {
    await ElMessageBox.confirm(
      `确定删除课程「${course.course_name}」吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  courses.value = courses.value.filter((item) => item.id !== course.id);
  if (selectedCourseId.value === course.id) {
    selectedCourseId.value = null;
    activeView.value = "courses";
  }
  ElMessage.success("课程已删除");
}

function submitClass() {
  if (!classForm.class_name.trim()) {
    ElMessage.warning("请填写班级名称");
    return;
  }

  const wasEditing = Boolean(editingClassId.value);
  if (wasEditing) {
    classes.value = classes.value.map((item) =>
      item.id === editingClassId.value
        ? {
            ...item,
            class_name: classForm.class_name,
            note: classForm.note,
          }
        : item,
    );
  } else {
    classes.value = [
      {
        id: Date.now(),
        class_name: classForm.class_name,
        student_count: 0,
        note: classForm.note,
      },
      ...classes.value,
    ];
  }

  Object.assign(classForm, {
    class_name: "",
    note: "",
  });
  editingClassId.value = null;
  classDialogVisible.value = false;
  ElMessage.success(wasEditing ? "班级已保存" : "班级已创建");
}

function submitCourse() {
  if (!courseForm.course_name.trim()) {
    ElMessage.warning("请填写课程名称");
    return;
  }

  const wasEditing = Boolean(editingCourseId.value);
  if (wasEditing) {
    courses.value = courses.value.map((item) =>
      item.id === editingCourseId.value
        ? {
            ...item,
            course_name: courseForm.course_name,
            description: courseForm.description,
          }
        : item,
    );
  } else {
    courses.value = [
      {
        id: Date.now(),
        course_name: courseForm.course_name,
        assignment_count: 0,
        description: courseForm.description,
      },
      ...courses.value,
    ];
  }

  Object.assign(courseForm, {
    course_name: "",
    description: "",
  });
  editingCourseId.value = null;
  courseDialogVisible.value = false;
  ElMessage.success(wasEditing ? "课程已保存" : "课程已创建");
}
</script>
