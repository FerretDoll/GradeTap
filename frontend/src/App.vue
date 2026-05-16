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
        <img
          class="brand-logo brand-logo--mark"
          src="/brand/gradetap-mark.svg"
          alt=""
          aria-hidden="true"
        />
        <span class="brand-subtitle">证据驱动的教师批改工作台</span>
      </div>

      <el-menu :default-active="activeMenu" :collapse="sidebarCollapsed" class="side-menu" @select="handleMenuSelect">
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
        <el-menu-item index="llmSettings">
          <el-icon><Setting /></el-icon>
          <span>模型设置</span>
        </el-menu-item>
      </el-menu>
      <button
        type="button"
        class="sidebar-collapse-button"
        :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
        @click="toggleSidebar"
      >
        <el-icon>
          <Expand v-if="sidebarCollapsed" />
          <Fold v-else />
        </el-icon>
        <span>{{ sidebarCollapsed ? "展开" : "收起" }}</span>
      </button>
    </el-aside>

    <el-container class="main-shell">
      <el-header class="topbar">
        <div class="page-title">
          <span class="eyebrow">{{ currentPage.eyebrow }}</span>
          <h1>{{ currentPage.title }}</h1>
        </div>
        <div class="topbar-actions">
          <el-button v-if="detailViews.includes(activeView)" :icon="Back" @click="returnToList">
            返回列表
          </el-button>
          <el-button v-if="activeView === 'tasks'" :icon="Refresh" @click="taskStore.fetchTasks">
            刷新
          </el-button>
          <el-button v-if="activeView === 'tasks'" type="primary" :icon="Plus" @click="openCreateTask">
            新建任务
          </el-button>
          <el-button v-else-if="activeView === 'classes'" type="primary" :icon="Plus" @click="openCreateClass">
            新建班级
          </el-button>
          <el-button v-else-if="activeView === 'courses'" type="primary" :icon="Plus" @click="openCreateCourse">
            新建课程
          </el-button>
          <el-button
            v-else-if="activeView === 'llmSettings'"
            type="primary"
            :icon="Check"
            :loading="llmSettingsLoading"
            @click="saveLlmSettings"
          >
            保存设置
          </el-button>
        </div>
      </el-header>

      <el-main
        class="workspace"
        :class="{
          'workspace--tasks': activeView === 'tasks',
          'workspace--task-detail': activeView === 'taskDetail',
          'workspace--course-detail': activeView === 'courseDetail',
        }"
      >
        <Transition name="view-float" mode="out-in">
          <div
            :key="activeView"
            class="view-panel"
            :class="{
              'tasks-view': activeView === 'tasks',
              'task-detail-view': activeView === 'taskDetail',
            }"
          >
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
                    <div class="heading-title-row">
                      <h2>批改任务</h2>
                      <el-tag effect="plain">{{ taskStore.items.length }} 个任务</el-tag>
                    </div>
                  </div>
                </div>

                <el-table
                  :data="taskStore.items"
                  v-loading="taskStore.loading"
                  height="100%"
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
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Task Detail</span>
                  <h2>{{ selectedTask?.task_name || "批改任务" }}</h2>
                  <p>{{ selectedTask?.course_name }} / {{ selectedTask?.class_name }}</p>
                </div>
                <div class="detail-header-actions">
                  <el-tag class="status-tag" effect="light">{{ selectedTask?.status || "created" }}</el-tag>
                </div>
              </div>

              <div class="detail-grid">
                <div class="panel progress-panel" :class="{ 'runtime-flow': questionAnalysisLoading }">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Progress</span>
                      <h2>批改进度</h2>
                    </div>
                  </div>
                  <el-progress
                    :percentage="selectedTaskProgress"
                    :stroke-width="10"
                    :class="{ 'progress-bar--running': questionAnalysisLoading }"
                  />
                  <div class="progress-stages" :style="{ '--stage-count': visibleTaskStages.length }">
                    <button
                      v-for="stage in visibleTaskStages"
                      :key="stage.key"
                      type="button"
                      class="progress-stage"
                      :class="{
                        active: stage.key === activeProgressStage.key,
                        current: stage.key === normalizedTaskProgressStageKey,
                        running: questionAnalysisLoading && stage.key === 'analyze_questions',
                      }"
                      @click="selectProgressStage(stage.key)"
                    >
                      <strong>
                        {{ stage.title }}
                        <span
                          v-if="questionAnalysisLoading && stage.key === 'analyze_questions'"
                          class="stage-loading-dot"
                          aria-hidden="true"
                        />
                      </strong>
                      <span>{{ stage.caption }}</span>
                    </button>
                  </div>
                  <div
                    class="progress-stage-detail"
                    :class="{
                      'progress-stage-detail--analysis': activeProgressStage.key === 'analyze_questions',
                      'progress-stage-detail--student-parse': activeProgressStage.key === 'prepare_students',
                      'progress-stage-detail--answer-extract': activeProgressStage.key === 'extract_answers',
                      'progress-stage-detail--evidence-extract': activeProgressStage.key === 'extract_evidence',
                    }"
                  >
                    <div class="stage-detail-title">
                      <div v-if="activeProgressStage.key === 'prepare_students'">
                        <span class="section-kicker">Match Summary</span>
                        <h3>{{ studentParseMatchedCount }}/{{ studentParseTotalCount }} 名学生已匹配</h3>
                      </div>
                      <div v-else-if="activeProgressStage.key === 'extract_answers'">
                        <span class="section-kicker">Answer Extract</span>
                        <h3>{{ answerExtractionCompletedCount }}/{{ answerExtractionEligibleCount }} 名学生已抽取</h3>
                      </div>
                      <div v-else-if="activeProgressStage.key === 'extract_evidence'">
                        <span class="section-kicker">Evidence Extract</span>
                        <h3>{{ evidenceExtractionCompletedCount }}/{{ evidenceExtractionEligibleCount }} 名学生已提取证据</h3>
                      </div>
                      <div v-else-if="activeProgressStage.key === 'analyze_questions'">
                        <span class="section-kicker">{{ activeProgressStage.eyebrow }}</span>
                        <h3>{{ activeProgressStage.title }}</h3>
                      </div>
                      <div class="stage-detail-actions">
                        <el-tag effect="plain">{{ activeProgressStageStatus }}</el-tag>
                        <el-tag v-if="activeProgressStage.key === 'prepare_students'" effect="plain">
                          {{ uploadedStudentSubmissionFileCount }} 个学生作业文件
                        </el-tag>
                        <el-tag v-if="activeProgressStage.key === 'extract_answers'" effect="plain">
                          {{ taskQuestions.length }} 道题
                        </el-tag>
                        <el-tag v-if="activeProgressStage.key === 'extract_evidence'" effect="plain">
                          {{ evidenceLowConfidenceCount }} 个低置信度维度
                        </el-tag>
                        <template v-if="activeProgressStage.key === 'analyze_questions'">
                          <el-button
                            size="small"
                            :type="taskQuestions.length ? 'warning' : 'primary'"
                            :loading="questionAnalysisLoading"
                            @click="runQuestionAnalysis"
                          >
                            {{ taskQuestions.length ? "重新分析题目" : "开始题目分析" }}
                          </el-button>
                        </template>
                        <template v-else-if="activeProgressStage.key === 'prepare_students'">
                          <el-button
                            size="small"
                            :type="selectedTaskStudentMatches.length ? 'warning' : 'primary'"
                            :loading="studentPrepareLoading"
                            @click="runStudentPrepare"
                          >
                            {{ selectedTaskStudentMatches.length ? "重新解析学生" : "开始学生解析" }}
                          </el-button>
                        </template>
                        <template v-else-if="activeProgressStage.key === 'extract_answers'">
                          <el-button
                            size="small"
                            type="primary"
                            :disabled="!uploadedStudentSubmissionFileCount"
                            :loading="answerExtractionLoading"
                            @click="runAnswerExtraction(false)"
                          >
                            {{ answerExtractionHasAnswers ? "继续抽取答案" : "开始答案抽取" }}
                          </el-button>
                          <el-button
                            v-if="answerExtractionHasAnswers"
                            size="small"
                            type="warning"
                            :disabled="!uploadedStudentSubmissionFileCount"
                            :loading="answerExtractionLoading"
                            @click="runAnswerExtraction(true)"
                          >
                            重新抽取答案
                          </el-button>
                        </template>
                        <template v-else-if="activeProgressStage.key === 'extract_evidence'">
                          <el-button
                            size="small"
                            type="primary"
                            :disabled="!answerExtractionHasAnswers"
                            :loading="evidenceExtractionLoading"
                            @click="runEvidenceExtraction(false)"
                          >
                            {{ evidenceExtractionHasEvidence ? "继续提取证据" : "开始证据提取" }}
                          </el-button>
                          <el-button
                            v-if="evidenceExtractionHasEvidence"
                            size="small"
                            type="warning"
                            :disabled="!answerExtractionHasAnswers"
                            :loading="evidenceExtractionLoading"
                            @click="runEvidenceExtraction(true)"
                          >
                            重新提取证据
                          </el-button>
                          <el-switch
                            v-model="evidenceLowConfidenceOnly"
                            size="small"
                            active-text="只看低置信度"
                          />
                        </template>
                      </div>
                    </div>
                    <div v-if="activeProgressStage.key === 'analyze_questions'" class="question-analysis-panel">
                      <div
                        v-if="questionAnalysisLoading"
                        class="llm-stream-panel running"
                      >
                        <div class="llm-stream-heading">
                          <strong>模型实时进度</strong>
                          <el-tag effect="plain">{{ taskLlmStream.status }}</el-tag>
                        </div>
                        <pre>{{ taskLlmStream.text || "等待模型开始分析题目..." }}</pre>
                      </div>
                      <div class="question-analysis-heading">
                        <strong>题目分析结果</strong>
                        <el-tag effect="plain">{{ taskQuestions.length }} 道题</el-tag>
                      </div>
                      <el-table
                        v-if="taskQuestions.length"
                        :data="taskQuestions"
                        size="small"
                        height="100%"
                        class="task-table question-analysis-table"
                      >
                        <el-table-column prop="question_number" label="题号" width="80" align="center" />
                        <el-table-column prop="content" label="题干" min-width="220" show-overflow-tooltip />
                        <el-table-column prop="question_type" label="题型" width="120" align="center" />
                        <el-table-column label="知识点" min-width="160" show-overflow-tooltip>
                          <template #default="{ row }">
                            {{ formatKnowledgePoints(row.knowledge_points) }}
                          </template>
                        </el-table-column>
                        <el-table-column label="难度" width="100" align="center">
                          <template #default="{ row }">
                            <el-tag :type="difficultyMeta(row.difficulty).type" effect="light">
                              {{ difficultyMeta(row.difficulty).label }}
                            </el-tag>
                          </template>
                        </el-table-column>
                        <el-table-column prop="total_score" label="分值" width="90" align="center" />
                      </el-table>
                      <el-empty
                        v-else
                        class="question-analysis-empty"
                        description="尚未生成题目分析结果"
                        :image-size="72"
                      />
                    </div>
                    <div v-else-if="activeProgressStage.key === 'prepare_students'" class="student-parse-panel">
                      <div
                        v-if="taskClassStudents.length && selectedTaskStudentMatches.length"
                        v-loading="studentPrepareLoading"
                        class="student-match-list"
                      >
                        <div class="student-match-head">
                          <span>学生</span>
                          <span>匹配文件</span>
                        </div>
                        <div
                          v-for="match in selectedTaskStudentMatches"
                          :key="match.student_id"
                          class="student-match-row"
                        >
                          <div class="student-match-student">
                            <strong>{{ match.student_name }}</strong>
                            <span>{{ match.student_no || "未填写学号" }}</span>
                          </div>
                          <div class="student-match-file">
                            <div>
                              <strong>{{ match.matched_file_name || "未匹配到文件" }}</strong>
                              <span>{{ match.reason }}</span>
                              <small v-if="match.match_status === 'ambiguous' && match.candidate_files?.length">
                                候选：{{ match.candidate_files.join("、") }}
                              </small>
                            </div>
                            <el-tag :type="studentMatchStatusMeta(match.match_status).type" effect="light">
                              {{ studentMatchStatusMeta(match.match_status).label }}
                            </el-tag>
                          </div>
                        </div>
                      </div>
                      <el-empty
                        v-else
                        class="student-parse-empty"
                        description="请先维护班级学生并上传学生作业文件"
                        :image-size="72"
                      />
                    </div>
                    <div v-else-if="activeProgressStage.key === 'extract_answers'" class="answer-extract-panel">
                      <div v-if="answerExtractionEligibleCount" class="answer-extract-grid">
                        <div class="answer-student-list">
                          <button
                            v-for="student in answerExtractionStudents"
                            :key="student.submission_id"
                            type="button"
                            class="answer-student-card"
                            :class="{
                              active: student.submission_id === selectedAnswerSubmissionId,
                              done: studentAnswerExtractionCompleted(student),
                              running: student.status === 'processing',
                            }"
                            @click="selectAnswerStudent(student.submission_id)"
                          >
                            <div>
                              <strong>{{ student.student_name }}</strong>
                              <span>{{ student.student_no || "未填写学号" }}</span>
                            </div>
                            <div v-if="studentAnswerExtractionFinalized(student)" class="answer-student-counts">
                              <span class="matched">已匹配 {{ studentAnswerCounts(student).matched }} 题</span>
                              <span v-if="studentAnswerCounts(student).unmatched > 0" class="unmatched">
                                未匹配 {{ studentAnswerCounts(student).unmatched }} 题
                              </span>
                            </div>
                            <el-progress
                              :percentage="studentAnswerProgress(student)"
                              :stroke-width="6"
                              :show-text="false"
                              :class="{ 'progress-bar--running': student.status === 'processing' }"
                            />
                            <small>{{ student.completed_questions }}/{{ student.total_questions }} 题</small>
                          </button>
                        </div>
                        <div
                          class="answer-list-view"
                          @mouseenter="setAnswerInteractionArea('question-list')"
                          @mouseleave="clearAnswerInteractionArea('question-list')"
                        >
                          <div class="answer-column-heading">
                            <strong>作业题目</strong>
                            <el-tag effect="plain">{{ selectedAnswerStudentAnswers.length }} 题</el-tag>
                          </div>
                          <div ref="answerQuestionListRef" class="answer-card-list">
                            <article
                              v-for="question in taskQuestions"
                              :key="question.id"
                              class="answer-card"
                              :data-answer-question-id="question.id"
                              :class="{
                                active: question.id === activeAnswerQuestionId,
                                matched: answerQuestionFinalized(question.id) && answerForQuestion(question.id)?.extraction_status === 'matched',
                                unmatched: answerQuestionFinalized(question.id) && answerForQuestion(question.id)?.extraction_status !== 'matched',
                              }"
                              @click="focusAnswerQuestion(question.id, 'question-list')"
                              @mouseenter="hoveredAnswerQuestionId = question.id"
                              @mouseleave="hoveredAnswerQuestionId = null"
                            >
                              <div>
                                <strong>{{ question.question_number }}. {{ question.content }}</strong>
                              </div>
                            </article>
                          </div>
                        </div>
                        <div
                          ref="answerSourceViewRef"
                          class="answer-source-view"
                          @mouseenter="setAnswerInteractionArea('source')"
                          @mouseleave="clearAnswerInteractionArea('source')"
                        >
                          <div class="answer-column-heading">
                            <strong>{{ selectedAnswerStudent?.source_file_name || "学生作业原文" }}</strong>
                            <el-tag effect="plain">{{ selectedAnswerStudent?.content?.length ?? 0 }} 字</el-tag>
                          </div>
                          <div class="answer-source-text">
                            <template v-for="part in highlightedSubmissionParts" :key="part.key">
                              <mark
                                v-if="part.questionId"
                                class="answer-highlight"
                                :data-source-question-id="part.questionId"
                                :class="{
                                  active: part.questionId === activeAnswerQuestionId,
                                }"
                                role="button"
                                tabindex="0"
                                @click="focusAnswerQuestion(part.questionId, 'source')"
                                @keydown.enter.prevent="focusAnswerQuestion(part.questionId, 'source')"
                                @mouseenter="hoveredAnswerQuestionId = part.questionId"
                                @mouseleave="hoveredAnswerQuestionId = null"
                              >
                                {{ part.text }}
                              </mark>
                              <span v-else>{{ part.text }}</span>
                            </template>
                          </div>
                        </div>
                      </div>
                      <el-empty
                        v-else
                        class="student-parse-empty"
                        description="只有学生解析中已匹配作业的学生才能进入答案抽取"
                        :image-size="72"
                      />
                    </div>
                    <div v-else-if="activeProgressStage.key === 'extract_evidence'" class="evidence-extract-panel">
                      <div v-if="evidenceExtractionEligibleCount" class="evidence-extract-grid">
                        <div class="evidence-student-list">
                          <button
                            v-for="student in evidenceExtractionStudents"
                            :key="student.submission_id"
                            type="button"
                            class="evidence-student-card"
                            :class="{
                              active: student.submission_id === selectedEvidenceSubmissionId,
                              done: studentEvidenceCompleted(student),
                              review: studentEvidenceLowConfidenceCount(student) > 0,
                              running: studentEvidenceRunning(student),
                            }"
                            @click="selectEvidenceStudent(student.submission_id)"
                          >
                            <div class="evidence-student-card-head">
                              <div>
                                <strong>{{ student.student_name }}</strong>
                                <span>{{ student.student_no || "未填写学号" }}</span>
                              </div>
                              <el-tag
                                :type="studentEvidenceLowConfidenceCount(student) ? 'warning' : 'success'"
                                effect="light"
                              >
                                {{ studentEvidenceLowConfidenceCount(student) ? "需关注" : "稳定" }}
                              </el-tag>
                            </div>
                            <div class="evidence-student-counts">
                              <span>已提取 {{ studentEvidenceCompletedQuestionCount(student) }} 题</span>
                              <span>低置信度 {{ studentEvidenceLowConfidenceCount(student) }}</span>
                            </div>
                            <el-progress
                              :percentage="studentEvidenceProgress(student)"
                              :stroke-width="6"
                              :show-text="false"
                              :class="{ 'progress-bar--running': student.status === 'processing' }"
                            />
                            <small>{{ studentEvidenceCompletedQuestionCount(student) }}/{{ taskQuestions.length }} 题</small>
                          </button>
                        </div>

                        <div class="evidence-question-view">
                          <div class="answer-column-heading">
                            <strong>题目与学生答案</strong>
                            <el-tag effect="plain">{{ filteredEvidenceQuestions.length }} 题</el-tag>
                          </div>
                          <div class="evidence-question-list">
                            <article
                              v-for="questionItem in filteredEvidenceQuestions"
                              :key="questionItem.question_id"
                              class="evidence-question-card"
                              :class="{
                                active: questionItem.question_id === selectedEvidenceQuestionId,
                                warning: questionEvidenceLowConfidenceCount(questionItem) > 0,
                              }"
                              @click="selectEvidenceQuestion(questionItem.question_id)"
                            >
                              <div class="evidence-question-card-head">
                                <strong>{{ questionLabel(questionItem.question_id) }}</strong>
                                <el-tag :type="answerStatusMeta(questionItem.extraction_status).type" effect="light">
                                  {{ answerStatusMeta(questionItem.extraction_status).label }}
                                </el-tag>
                              </div>
                              <p>{{ questionItem.answer_text || "未抽取到学生答案，后续评分应进入复核。" }}</p>
                              <div class="evidence-question-meta">
                                <span>答案置信度 {{ formatPercent(questionItem.answer_confidence) }}</span>
                                <span>低置信度 {{ questionEvidenceLowConfidenceCount(questionItem) }}</span>
                              </div>
                            </article>
                          </div>
                        </div>

                        <div class="evidence-detail-view">
                          <div class="answer-column-heading">
                            <strong>{{ selectedEvidenceQuestionTitle }}</strong>
                            <el-tag effect="plain">{{ selectedEvidenceDimensionRows.length }} 个维度</el-tag>
                          </div>
                          <div v-if="selectedEvidenceQuestion" class="evidence-detail-body">
                            <article
                              v-for="row in selectedEvidenceDimensionRows"
                              :key="row.rubric.id"
                              class="evidence-dimension-card"
                              :class="{
                                warning: row.confidence < 0.8,
                                skipped: row.skipped,
                                empty: !row.hasEvidence && !row.skipped,
                              }"
                            >
                              <div class="evidence-dimension-head">
                                <div>
                                  <strong>{{ row.rubric.dimension_name }}</strong>
                                  <span>{{ row.rubric.max_score }} 分 · {{ row.rubric.evidence_requirement }}</span>
                                </div>
                                <el-tag :type="evidenceConfidenceMeta(row.confidence, row.skipped).type" effect="light">
                                  {{ evidenceConfidenceMeta(row.confidence, row.skipped).label }}
                                </el-tag>
                              </div>
                              <div class="evidence-pill-grid">
                                <div>
                                  <span>正向证据</span>
                                  <ul v-if="row.positive_evidence.length">
                                    <li v-for="item in row.positive_evidence" :key="item">{{ item }}</li>
                                  </ul>
                                  <p v-else-if="row.skipped">缺失答案，无需提取</p>
                                  <p v-else>暂无正向证据</p>
                                </div>
                                <div>
                                  <span>负向证据</span>
                                  <ul v-if="row.negative_evidence.length">
                                    <li v-for="item in row.negative_evidence" :key="item">{{ item }}</li>
                                  </ul>
                                  <p v-else-if="row.skipped">缺失答案，无需提取</p>
                                  <p v-else>暂无负向证据</p>
                                </div>
                              </div>
                            </article>
                          </div>
                          <el-empty
                            v-else
                            class="student-parse-empty"
                            description="请选择需要查看证据的题目"
                            :image-size="72"
                          />
                        </div>
                      </div>
                      <el-empty
                        v-else
                        class="student-parse-empty"
                        description="请先完成答案抽取，再进入证据提取"
                        :image-size="72"
                      />
                    </div>
                  </div>
                </div>

                <div class="panel material-panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Files</span>
                      <div class="heading-title-row">
                        <h2>任务材料</h2>
                      </div>
                    </div>
                    <div class="material-heading-actions">
                      <el-button size="small" :loading="parseFilesLoading" @click="parseSelectedTaskFiles">
                        解析文件
                      </el-button>
                    </div>
                  </div>
                  <div v-loading="taskFilesLoading" class="material-upload-list">
                    <div
                      v-for="material in taskMaterials"
                      :key="material.role"
                      class="material-upload-card"
                      :class="{
                        'material-upload-card--student': material.role === 'student_submission',
                        'material-upload-card--readonly': material.readOnly,
                      }"
                    >
                      <template v-if="material.readOnly">
                        <div class="task-material-readonly-row">
                          <span class="task-material-readonly-label">{{ material.title }}</span>
                          <template v-if="taskFilesForRole(material.role).length">
                            <span class="task-material-readonly-sep" aria-hidden="true">·</span>
                            <div class="task-material-readonly-files">
                              <button
                                v-for="file in taskFilesForRole(material.role)"
                                :key="file.id"
                                type="button"
                                class="task-material-filename-link"
                                :title="file.file_name"
                                @click="openParsedTextPreview(file)"
                              >
                                {{ file.file_name }}
                              </button>
                            </div>
                          </template>
                          <span v-else class="task-material-readonly-missing">暂无</span>
                        </div>
                      </template>
                      <template v-else>
                        <div class="material-upload-header">
                          <div>
                            <div class="material-student-heading">
                              <strong>{{ material.title }}</strong>
                              <el-tag effect="plain">{{ uploadedStudentSubmissionFileCount }} 个文件</el-tag>
                            </div>
                            <span v-if="material.description">{{ material.description }}</span>
                          </div>
                          <el-tag :type="taskFilesForRole(material.role).length ? 'success' : 'info'" effect="plain">
                            {{ taskFilesForRole(material.role).length ? "已上传" : "待上传" }}
                          </el-tag>
                        </div>
                        <el-upload
                          :accept="material.accept"
                          :auto-upload="false"
                          :multiple="material.multiple"
                          :show-file-list="false"
                          :on-change="(uploadFile) => handleTaskMaterialChange(material, uploadFile)"
                        >
                          <el-button
                            class="material-upload-button"
                            :icon="Upload"
                            :loading="taskFileUploading[material.role]"
                          >
                            {{ material.multiple ? "添加文件" : "上传文件" }}
                          </el-button>
                        </el-upload>
                        <div
                          class="uploaded-file-list"
                          :class="{
                            'uploaded-file-list--scrollable':
                              material.role === 'student_submission'
                              && taskFilesForRole(material.role).length > 0,
                          }"
                        >
                          <div
                            v-for="file in taskFilesForRole(material.role)"
                            :key="file.id"
                            class="uploaded-file-item"
                          >
                            <div class="uploaded-file-main">
                              <span :title="file.file_name">{{ file.file_name }}</span>
                              <small v-if="file.parsed_text">解析文本 {{ file.parsed_text.length }} 字</small>
                              <small v-else>尚未解析</small>
                            </div>
                            <el-button
                              v-if="file.parsed_text"
                              text
                              size="small"
                              @click="openParsedTextPreview(file)"
                            >
                              查看
                            </el-button>
                            <el-button
                              :icon="Delete"
                              circle
                              text
                              type="danger"
                              title="移除"
                              :loading="taskFileDeletingId === file.id"
                              @click="removeTaskMaterialFile(file)"
                            />
                          </div>
                          <p v-if="!taskFilesForRole(material.role).length">尚未选择文件</p>
                        </div>
                      </template>
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
                    <div class="heading-title-row">
                      <h2>课程列表</h2>
                      <el-tag effect="plain">{{ courses.length }} 门课程</el-tag>
                    </div>
                  </div>
                </div>

                <el-table :data="courses" height="100%" class="task-table" empty-text="暂无课程">
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
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Course Detail</span>
                  <div class="heading-title-row">
                    <h2>{{ selectedCourse?.course_name || "课程" }}</h2>
                    <el-tag effect="plain">{{ selectedCourse?.assignment_count ?? 0 }} 个作业</el-tag>
                  </div>
                  <p>{{ selectedCourse?.description || "未填写课程说明" }}</p>
                </div>
              </div>

              <div
                class="detail-grid course-assignment-grid"
                :class="{ 'course-assignment-grid--selected': courseAssignmentLayoutExpanded }"
              >
                <div class="panel student-roster-panel course-assignment-list-panel">
                  <div class="panel-heading">
                    <div class="course-assignment-heading">
                      <span class="section-kicker">Assignments</span>
                      <div class="course-assignment-path">
                        <button
                          type="button"
                          class="course-assignment-path-button"
                          @click="clearCourseAssignmentSelection"
                        >
                          课程作业管理
                        </button>
                        <template v-if="selectedCourseAssignment">
                          <span class="course-assignment-path-arrow">›</span>
                          <strong>{{ selectedCourseAssignment.assignment_name }}</strong>
                        </template>
                      </div>
                    </div>
                    <el-button v-if="!selectedCourseAssignment" type="primary" :icon="Plus" @click="openCreateAssignment">
                      新建作业
                    </el-button>
                    <div v-else class="assignment-heading-status">
                      <el-tag :type="selectedAssignmentRubricConfirmed ? 'success' : 'warning'" effect="light">
                        {{ selectedAssignmentRubricConfirmed ? "量规已绑定" : "待确认量规" }}
                      </el-tag>
                    </div>
                  </div>
                  <el-table
                    v-if="!selectedCourseAssignment"
                    :data="courseAssignments"
                    v-loading="assignmentLoading"
                    height="100%"
                    class="task-table"
                    empty-text="暂无课程作业，请先新建作业"
                  >
                    <el-table-column prop="assignment_name" label="作业名称" min-width="180">
                      <template #default="{ row }">
                        <button
                          class="task-name-cell task-name-button"
                          :class="{ active: row.id === selectedCourseAssignmentId }"
                          @click="selectCourseAssignment(row)"
                        >
                          <strong>{{ row.assignment_name }}</strong>
                          <span>{{ row.description || "未填写作业说明" }}</span>
                        </button>
                      </template>
                    </el-table-column>
                    <el-table-column prop="total_score" label="总分" width="90" align="center" />
                    <el-table-column prop="file_count" label="材料" width="90" align="center">
                      <template #default="{ row }">
                        <el-tag effect="plain">{{ row.file_count ?? 0 }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="量规" width="90" align="center">
                      <template #default="{ row }">
                        <el-tooltip
                          :content="assignmentRubricBound(row) ? '评分量规已确认绑定' : '评分量规尚未绑定'"
                          placement="top"
                        >
                          <span
                            class="rubric-bind-icon"
                            :class="{ bound: assignmentRubricBound(row) }"
                            :aria-label="assignmentRubricBound(row) ? '量规已绑定' : '量规未绑定'"
                          >
                            <el-icon v-if="assignmentRubricBound(row)"><Check /></el-icon>
                            <span v-else class="rubric-bind-icon-dot">!</span>
                          </span>
                        </el-tooltip>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="120" fixed="right" align="center">
                      <template #default="{ row }">
                        <div class="icon-actions">
                          <el-button :icon="Edit" circle text title="编辑" @click="editAssignment(row)" />
                          <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteAssignment(row)" />
                        </div>
                      </template>
                    </el-table-column>
                  </el-table>
                  <Transition name="assignment-material">
                    <div
                      v-if="selectedCourseAssignment"
                      class="assignment-workflow-panel"
                      :class="{ 'runtime-flow': assignmentQuestionAnalysisLoading || assignmentRubricBuildLoading }"
                    >
                      <el-progress
                        :percentage="selectedAssignmentRubricProgress"
                        :stroke-width="10"
                        :class="{ 'progress-bar--running': assignmentQuestionAnalysisLoading || assignmentRubricBuildLoading }"
                      />
                      <div class="progress-stages" :style="{ '--stage-count': assignmentRubricStages.length }">
                        <button
                          v-for="stage in assignmentRubricStages"
                          :key="stage.key"
                          type="button"
                          class="progress-stage"
                          :class="{
                            active: stage.key === activeAssignmentRubricStage.key,
                            current: stage.key === currentAssignmentRubricStageKey,
                            running:
                              (assignmentQuestionAnalysisLoading && stage.key === 'analyze_questions')
                              || (assignmentRubricBuildLoading && stage.key === 'build_rubrics'),
                          }"
                          @click="selectAssignmentRubricStage(stage.key)"
                        >
                          <strong>
                            {{ stage.title }}
                            <span
                              v-if="
                                (assignmentQuestionAnalysisLoading && stage.key === 'analyze_questions')
                                || (assignmentRubricBuildLoading && stage.key === 'build_rubrics')
                              "
                              class="stage-loading-dot"
                              aria-hidden="true"
                            />
                          </strong>
                          <span>{{ stage.caption }}</span>
                        </button>
                      </div>
                      <div
                        class="progress-stage-detail"
                      >
                          <div class="assignment-rubric-step-panel">
                            <div class="stage-detail-title">
                              <div>
                                <span class="section-kicker">{{ activeAssignmentRubricStage.eyebrow }}</span>
                                <h3>{{ activeAssignmentRubricStage.title }}</h3>
                              </div>
                              <div class="stage-detail-actions">
                                <el-tag effect="plain">{{ activeAssignmentRubricStageStatus }}</el-tag>
                                <el-button
                                  v-if="activeAssignmentRubricStage.key === 'analyze_questions'"
                                  size="small"
                                  :type="selectedAssignmentQuestions.length ? 'warning' : 'primary'"
                                  :loading="assignmentQuestionAnalysisLoading"
                                  @click="runAssignmentQuestionAnalysis"
                                >
                                  {{ selectedAssignmentQuestions.length ? "重新分析题目" : "开始题目分析" }}
                                </el-button>
                                <el-button
                                  v-else-if="activeAssignmentRubricStage.key === 'build_rubrics'"
                                  size="small"
                                  :type="selectedAssignmentHasRubrics ? 'warning' : 'primary'"
                                  :disabled="!selectedAssignmentQuestions.length"
                                  :loading="assignmentRubricBuildLoading"
                                  @click="runAssignmentRubricBuild"
                                >
                                  {{ selectedAssignmentHasRubrics ? "重新生成评分量规" : "生成评分量规" }}
                                </el-button>
                                <el-button
                                  v-else-if="activeAssignmentRubricStage.key === 'teacher_confirm_rubrics'"
                                  size="small"
                                  type="success"
                                  :disabled="!selectedAssignmentHasRubrics"
                                  :loading="assignmentRubricConfirmLoading"
                                  @click="confirmSelectedAssignmentRubrics"
                                >
                                  确认并绑定
                                </el-button>
                              </div>
                            </div>
                            <p>{{ activeAssignmentRubricStage.detail }}</p>
                            <div
                              v-if="assignmentQuestionAnalysisLoading || assignmentRubricBuildLoading"
                              class="llm-stream-panel running"
                            >
                              <div class="llm-stream-heading">
                                <strong>模型实时进度</strong>
                                <el-tag effect="plain">{{ assignmentLlmStream.status }}</el-tag>
                              </div>
                              <pre>{{ assignmentLlmStream.text || llmProgressPlaceholder(assignmentLlmStream.stage) }}</pre>
                            </div>
                            <div class="progress-stage-result">
                              <el-table
                                v-if="activeAssignmentRubricStage.key === 'analyze_questions' && selectedAssignmentQuestions.length"
                                :data="selectedAssignmentQuestions"
                                size="small"
                                height="100%"
                                class="task-table question-analysis-table"
                              >
                                <el-table-column prop="question_number" label="题号" width="80" align="center" />
                                <el-table-column prop="content" label="题干" min-width="220" show-overflow-tooltip />
                                <el-table-column prop="question_type" label="题型" width="120" align="center" />
                                <el-table-column label="知识点" min-width="160" show-overflow-tooltip>
                                  <template #default="{ row }">
                                    {{ formatKnowledgePoints(row.knowledge_points) }}
                                  </template>
                                </el-table-column>
                                <el-table-column label="难度" width="100" align="center">
                                  <template #default="{ row }">
                                    <el-tag :type="difficultyMeta(row.difficulty).type" effect="light">
                                      {{ difficultyMeta(row.difficulty).label }}
                                    </el-tag>
                                  </template>
                                </el-table-column>
                                <el-table-column prop="total_score" label="分值" width="90" align="center" />
                              </el-table>
                              <div
                                v-else-if="activeAssignmentRubricStage.key !== 'analyze_questions' && selectedAssignmentQuestions.length"
                                class="assignment-rubric-list"
                              >
                                <div
                                  v-for="question in selectedAssignmentQuestions"
                                  :key="question.question_number"
                                  class="assignment-rubric-item"
                                >
                                  <div class="assignment-rubric-title">
                                    <strong>{{ question.question_number }}. {{ question.content }}</strong>
                                    <el-tag effect="plain">{{ question.total_score }} 分</el-tag>
                                  </div>
                                  <el-table
                                    :data="question.rubrics ?? []"
                                    size="small"
                                    class="task-table"
                                    empty-text="尚未生成评分量规"
                                  >
                                    <el-table-column prop="dimension_name" label="评分维度" min-width="130" />
                                    <el-table-column prop="max_score" label="分值" width="80" align="center" />
                                    <el-table-column prop="scoring_criteria" label="得分条件" min-width="180" show-overflow-tooltip />
                                    <el-table-column prop="deduction_criteria" label="扣分条件" min-width="180" show-overflow-tooltip />
                                    <el-table-column prop="evidence_requirement" label="证据要求" min-width="180" show-overflow-tooltip />
                                  </el-table>
                                </div>
                              </div>
                              <el-empty
                                v-else
                                description="点击当前步骤按钮后，将在这里查看作业题目、量规和确认状态"
                                :image-size="72"
                              />
                            </div>
                          </div>
                      </div>
                    </div>
                  </Transition>
                </div>

                <Transition name="assignment-material">
                  <div v-if="selectedCourseAssignment" class="panel course-assignment-material-panel">
                    <div class="panel-heading">
                      <div>
                        <span class="section-kicker">Materials</span>
                        <div class="heading-title-row">
                          <h2>作业文件与答案</h2>
                          <el-tag effect="plain">{{ uploadedAssignmentFileCount }} 个文件</el-tag>
                        </div>
                      </div>
                      <div class="material-heading-actions">
                        <el-button
                          size="small"
                          :disabled="!selectedCourseAssignmentId"
                          :loading="parseAssignmentFilesLoading"
                          @click="parseSelectedAssignmentFiles"
                        >
                          解析材料
                        </el-button>
                      </div>
                    </div>
                    <div class="assignment-material-title">
                      <strong>{{ selectedCourseAssignment.assignment_name }}</strong>
                      <span>{{ selectedCourseAssignment.description || "可先上传作业文件和答案文件，后续批改任务从这里引用。" }}</span>
                    </div>
                    <div v-loading="assignmentFilesLoading" class="material-upload-list">
                      <div v-for="material in assignmentMaterials" :key="material.role" class="material-upload-card">
                        <div class="material-upload-header">
                          <div>
                            <strong>{{ material.title }}</strong>
                            <span>{{ material.description }}</span>
                          </div>
                          <el-tag :type="assignmentFilesForRole(material.role).length ? 'success' : 'info'" effect="plain">
                            {{ assignmentFilesForRole(material.role).length ? "已上传" : "待上传" }}
                          </el-tag>
                        </div>
                        <el-upload
                          :auto-upload="false"
                          :show-file-list="false"
                          :accept="material.accept"
                          :on-change="(uploadFile) => handleAssignmentMaterialChange(material, uploadFile)"
                        >
                          <el-button
                            class="material-upload-button"
                            :icon="Upload"
                            :loading="assignmentFileUploading[material.role]"
                          >
                            上传文件
                          </el-button>
                        </el-upload>
                        <div class="uploaded-file-list">
                          <div v-for="file in assignmentFilesForRole(material.role)" :key="file.id" class="uploaded-file-item">
                            <div class="uploaded-file-main">
                              <span :title="file.file_name">{{ file.file_name }}</span>
                              <small v-if="file.parsed_text">解析文本 {{ file.parsed_text.length }} 字</small>
                              <small v-else>尚未解析</small>
                            </div>
                            <el-button
                              v-if="file.parsed_text"
                              text
                              size="small"
                              @click="openParsedTextPreview(file)"
                            >
                              查看
                            </el-button>
                            <el-button
                              :icon="Delete"
                              circle
                              text
                              type="danger"
                              :loading="assignmentFileDeletingId === file.id"
                              @click="removeAssignmentMaterialFile(file)"
                            />
                          </div>
                          <p v-if="!assignmentFilesForRole(material.role).length">尚未选择文件</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Transition>
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
                    <div class="heading-title-row">
                      <h2>班级列表</h2>
                      <el-tag effect="plain">{{ classes.length }} 个班级</el-tag>
                    </div>
                  </div>
                </div>

                <el-table :data="classes" height="100%" class="task-table" empty-text="暂无班级">
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
              <div class="panel detail-header">
                <div>
                  <span class="section-kicker">Class Detail</span>
                  <div class="heading-title-row">
                    <h2>{{ selectedClass?.class_name || "班级" }}</h2>
                    <el-tag effect="plain">{{ classStudents.length }} 名学生</el-tag>
                  </div>
                  <p>{{ selectedClass?.note || "未填写备注" }}</p>
                </div>
              </div>

              <div class="detail-grid">
                <div class="panel student-roster-panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Students</span>
                      <h2>学生名单</h2>
                    </div>
                    <div class="student-actions">
                      <el-upload
                        ref="studentImportUploadRef"
                        accept=".xlsx"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleStudentImportChange"
                      >
                        <el-button :icon="Upload" :loading="importingStudents">导入 Excel</el-button>
                      </el-upload>
                      <el-button type="primary" :icon="Plus" @click="openCreateStudent">
                        手动添加
                      </el-button>
                    </div>
                  </div>
                  <el-table
                    :data="classStudents"
                    v-loading="studentLoading"
                    height="100%"
                    class="task-table"
                    empty-text="暂无学生，请导入 Excel 或手动添加"
                  >
                    <el-table-column prop="student_name" label="姓名" min-width="160" />
                    <el-table-column prop="student_no" label="学号" min-width="160" align="center">
                      <template #default="{ row }">
                        <span>{{ row.student_no || "未填写" }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="120" fixed="right" align="center">
                      <template #default="{ row }">
                        <div class="icon-actions">
                          <el-button :icon="Edit" circle text title="编辑" @click="editStudent(row)" />
                          <el-button :icon="Delete" circle text type="danger" title="删除" @click="deleteStudent(row)" />
                        </div>
                      </template>
                    </el-table-column>
                  </el-table>
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
                      <span>学生总数</span>
                      <el-tag effect="plain">{{ classStudents.length }}</el-tag>
                    </div>
                    <div>
                      <span>批改任务</span>
                      <el-tag effect="plain">0</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section v-else-if="activeView === 'llmSettings'" class="settings-workspace">
              <div class="class-summary">
                <div class="class-summary-item">
                  <span>当前服务商</span>
                  <strong>{{ llmProviderLabel }}</strong>
                </div>
                <div class="class-summary-item">
                  <span>默认模型</span>
                  <strong>{{ llmForm.model || "未设置" }}</strong>
                </div>
                <div class="class-summary-item">
                  <span>密钥状态</span>
                  <strong class="llm-health" :class="`is-${llmHealth.status}`">{{ llmHealthLabel }}</strong>
                </div>
              </div>

              <div class="settings-grid">
                <div class="panel" v-loading="llmSettingsLoading">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Provider</span>
                      <h2>大模型连接</h2>
                    </div>
                    <el-tag :type="llmForm.enabled ? 'success' : 'info'" effect="plain">
                      {{ llmForm.enabled ? "已启用" : "未启用" }}
                    </el-tag>
                  </div>

                  <el-form :model="llmForm" label-position="top">
                    <div class="form-grid">
                      <el-form-item label="启用大模型">
                        <el-switch v-model="llmForm.enabled" active-text="启用" inactive-text="停用" />
                      </el-form-item>
                      <el-form-item label="服务商">
                        <el-select v-model="llmForm.provider" class="form-control" @change="handleLlmProviderChange">
                          <el-option
                            v-for="provider in llmProviders"
                            :key="provider.value"
                            :label="provider.label"
                            :value="provider.value"
                          />
                        </el-select>
                      </el-form-item>
                    </div>

                    <el-form-item label="API Key">
                      <el-input
                        :model-value="apiKeyDisplayValue"
                        type="password"
                        :placeholder="apiKeyPlaceholder"
                        autocomplete="off"
                        @focus="prepareApiKeyEdit"
                        @blur="finishApiKeyEdit"
                        @input="handleApiKeyInput"
                      />
                    </el-form-item>

                    <el-form-item label="Base URL">
                      <el-input v-model="llmForm.baseUrl" placeholder="https://api.openai.com/v1" />
                    </el-form-item>

                    <div class="form-grid">
                      <el-form-item label="默认模型">
                        <el-select
                          v-model="llmForm.model"
                          class="form-control"
                          filterable
                          allow-create
                          default-first-option
                          placeholder="请选择或输入模型名"
                        >
                          <el-option
                            v-for="model in activeModelOptions"
                            :key="model"
                            :label="model"
                            :value="model"
                          />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="JSON 重试次数">
                        <el-input-number v-model="llmForm.maxRetries" :min="1" :max="5" class="form-control" />
                      </el-form-item>
                    </div>

                    <el-form-item label="Temperature">
                      <el-slider v-model="llmForm.temperature" :min="0" :max="1" :step="0.1" show-input />
                    </el-form-item>
                  </el-form>
                </div>

                <div class="panel">
                  <div class="panel-heading">
                    <div>
                      <span class="section-kicker">Runtime</span>
                      <h2>批改调用策略</h2>
                    </div>
                  </div>
                  <div class="material-list settings-list">
                    <div>
                      <span>题目分析</span>
                      <el-tag effect="plain">{{ llmForm.enabled ? llmForm.model || "待选择" : "停用" }}</el-tag>
                    </div>
                    <div>
                      <span>量规生成</span>
                      <el-tag effect="plain">{{ llmForm.enabled ? llmForm.model || "待选择" : "停用" }}</el-tag>
                    </div>
                    <div>
                      <span>证据提取</span>
                      <el-tag effect="plain">JSON 优先</el-tag>
                    </div>
                    <div>
                      <span>失败处理</span>
                      <el-tag effect="plain">{{ llmForm.maxRetries }} 次重试</el-tag>
                    </div>
                  </div>

                  <div class="settings-actions">
                    <el-button type="primary" :icon="Check" :loading="llmSettingsLoading" @click="saveLlmSettings">
                      保存设置
                    </el-button>
                    <el-button :icon="Delete" :loading="llmSettingsLoading" @click="clearLlmApiKey">
                      清除密钥
                    </el-button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </Transition>
      </el-main>
      <el-footer class="app-footer">
        © 2026 武汉软件工程职业学院 信息学院
      </el-footer>
    </el-container>
  </el-container>

  <el-dialog v-model="taskDialogVisible" :title="editingTaskId ? '编辑批改任务' : '新建批改任务'" width="600px" :lock-scroll="false" class="task-dialog">
    <el-form :model="form" label-position="top">
      <el-form-item label="任务名称">
        <el-input v-model="form.task_name" placeholder="SQL 数据库第 13 周作业批改" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="课程名称">
          <el-select v-model="form.course_name" placeholder="请选择课程" class="form-control" @change="handleTaskCourseChange">
            <el-option v-for="course in courses" :key="course.id" :label="course.course_name" :value="course.course_name" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.course_name" label="作业名称">
          <el-select
            v-model="form.assignment_name"
            placeholder="请选择作业"
            class="form-control"
            :loading="taskAssignmentLoading"
          >
            <el-option
              v-for="assignment in taskAssignmentOptions"
              :key="assignment.id"
              :label="assignment.assignment_name"
              :value="assignment.assignment_name"
            />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="班级名称">
        <el-select v-model="form.class_name" placeholder="请选择班级" class="form-control">
          <el-option v-for="classItem in classes" :key="classItem.id" :label="classItem.class_name" :value="classItem.class_name" />
        </el-select>
      </el-form-item>
      <el-form-item label="批改说明">
        <el-input v-model="form.grading_instruction" type="textarea" :rows="4" placeholder="重点考查 SQL 语法、结果正确性和代码规范。" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="taskDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingTaskId ? Check : Plus" :loading="submitting" @click="submitTask">
        {{ editingTaskId ? "保存任务" : "创建任务" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="classDialogVisible" :title="editingClassId ? '编辑班级' : '新建班级'" width="560px" :lock-scroll="false">
    <el-form :model="classForm" label-position="top">
      <el-form-item label="班级名称">
        <el-input v-model="classForm.class_name" placeholder="软件 2301" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="classForm.note" type="textarea" :rows="3" placeholder="例如：高职软件技术专业，SQL 作业较多。" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="classDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingClassId ? Check : Plus" @click="submitClass">
        {{ editingClassId ? "保存班级" : "创建班级" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="studentDialogVisible" :title="editingStudentId ? '编辑学生' : '手动添加学生'" width="460px" :lock-scroll="false">
    <el-form :model="studentForm" label-position="top">
      <el-form-item label="姓名">
        <el-input v-model="studentForm.student_name" placeholder="学生姓名" />
      </el-form-item>
      <el-form-item label="学号">
        <el-input v-model="studentForm.student_no" placeholder="可留空，后续再补" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="studentDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingStudentId ? Check : Plus" @click="submitStudent">
        {{ editingStudentId ? "保存学生" : "添加学生" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="courseDialogVisible" :title="editingCourseId ? '编辑课程' : '新建课程'" width="600px" :lock-scroll="false">
    <el-form :model="courseForm" label-position="top">
      <el-form-item label="课程名称">
        <el-input v-model="courseForm.course_name" placeholder="数据库应用技术" />
      </el-form-item>
      <el-form-item label="课程说明">
        <el-input v-model="courseForm.description" type="textarea" :rows="3" placeholder="保存本课程相关作业和历史批改资料。" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="courseDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingCourseId ? Check : Plus" @click="submitCourse">
        {{ editingCourseId ? "保存课程" : "创建课程" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="assignmentDialogVisible" :title="editingAssignmentId ? '编辑课程作业' : '新建课程作业'" width="600px" :lock-scroll="false">
    <el-form :model="assignmentForm" label-position="top">
      <div class="form-grid">
        <el-form-item label="作业名称">
          <el-input v-model="assignmentForm.assignment_name" placeholder="第 3 次 SQL 查询作业" />
        </el-form-item>
        <el-form-item label="总分">
          <el-input-number v-model="assignmentForm.total_score" :min="0" :max="1000" class="form-control" />
        </el-form-item>
      </div>
      <el-form-item label="作业说明">
        <el-input
          v-model="assignmentForm.description"
          type="textarea"
          :rows="3"
          placeholder="记录作业范围、提交要求或后续批改注意事项。"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="assignmentDialogVisible = false">取消</el-button>
      <el-button type="primary" :icon="editingAssignmentId ? Check : Plus" @click="submitAssignment">
        {{ editingAssignmentId ? "保存作业" : "创建作业" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="parsedPreviewVisible"
    :title="parsedPreviewFile ? `${parsedPreviewFile.file_name} · 解析文本` : '解析文本'"
    width="min(1080px, 92vw)"
    :lock-scroll="false"
    class="parsed-preview-dialog"
  >
    <el-input
      :model-value="parsedPreviewFile?.parsed_text || '暂无解析文本'"
      type="textarea"
      :rows="26"
      readonly
    />
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Back,
  Check,
  Collection,
  Delete,
  DocumentChecked,
  Edit,
  Expand,
  Fold,
  Plus,
  Refresh,
  School,
  Setting,
  Upload,
} from "@element-plus/icons-vue";

import { useTaskStore } from "./stores/taskStore";
import { buildApiUrl } from "./api/client";
import {
  createClassGroup,
  createClassStudent,
  deleteClassGroup,
  deleteClassStudent,
  importClassStudents,
  listClasses,
  listClassStudents,
  updateClassGroup,
  updateClassStudent,
} from "./api/classes";
import {
  analyzeCourseAssignmentQuestions,
  buildCourseAssignmentRubrics,
  confirmCourseAssignmentRubrics,
  createCourseAssignment,
  createCourse,
  deleteCourseAssignment,
  deleteCourseAssignmentFile,
  deleteCourse as deleteCourseApi,
  listCourseAssignmentQuestions,
  listCourses,
  listCourseAssignments,
  listCourseAssignmentFiles,
  parseCourseAssignmentFiles,
  updateCourse,
  updateCourseAssignment,
  uploadCourseAssignmentFile,
} from "./api/courses";
import {
  deleteTask as deleteTaskApi,
  deleteTaskFile,
  getTaskAnswerExtraction,
  getTaskEvidenceExtraction,
  listTaskQuestions,
  listTaskFiles,
  prepareTaskStudents,
  startTaskAnswerExtraction,
  startTaskEvidenceExtraction,
  uploadTaskFile,
} from "./api/tasks";
import {
  clearLlmApiKey as clearLlmApiKeyApi,
  getLlmSettings,
  testLlmSettings,
  updateLlmSettings,
} from "./api/settings";

const taskStore = useTaskStore();
const activeView = ref("tasks");
const sidebarCollapsed = ref(false);
const selectedTaskId = ref(null);
const selectedCourseId = ref(null);
const selectedCourseAssignmentId = ref(null);
const courseAssignmentLayoutExpanded = ref(false);
const selectedClassId = ref(null);
const selectedProgressStageKey = ref("");
const selectedAssignmentRubricStageKey = ref("");
const editingTaskId = ref(null);
const editingCourseId = ref(null);
const editingAssignmentId = ref(null);
const editingClassId = ref(null);
const editingStudentId = ref(null);
const taskDialogVisible = ref(false);
const classDialogVisible = ref(false);
const courseDialogVisible = ref(false);
const assignmentDialogVisible = ref(false);
const studentDialogVisible = ref(false);
const parsedPreviewVisible = ref(false);
const parsedPreviewFile = ref(null);
const answerQuestionListRef = ref(null);
const answerSourceViewRef = ref(null);
const submitting = ref(false);
const assignmentLoading = ref(false);
const taskAssignmentLoading = ref(false);
const studentLoading = ref(false);
const importingStudents = ref(false);
const studentImportUploadRef = ref(null);
const taskFilesLoading = ref(false);
const assignmentFilesLoading = ref(false);
const taskFileDeletingId = ref(null);
const assignmentFileDeletingId = ref(null);
const parseFilesLoading = ref(false);
const studentPrepareLoading = ref(false);
const answerExtractionLoading = ref(false);
const evidenceExtractionLoading = ref(false);
const parseAssignmentFilesLoading = ref(false);
const questionAnalysisLoading = ref(false);
const assignmentQuestionAnalysisLoading = ref(false);
const assignmentRubricBuildLoading = ref(false);
const assignmentRubricConfirmLoading = ref(false);
const llmSettingsLoading = ref(false);
const apiKeyEditing = ref(false);
const taskFileUploading = reactive({
  student_submission: false,
});
const assignmentFileUploading = reactive({
  requirement: false,
  reference_answer: false,
});
const llmSecretState = reactive({
  hasApiKey: false,
  apiKeyMask: "",
});
const llmHealth = reactive({
  status: "unknown",
  message: "尚未检测",
});

const form = reactive({
  task_name: "",
  course_name: "",
  assignment_name: "",
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

const assignmentForm = reactive({
  assignment_name: "",
  description: "",
  total_score: 100,
});

const studentForm = reactive({
  student_name: "",
  student_no: "",
});

const llmForm = reactive({
  enabled: false,
  provider: "deepseek",
  apiKey: "",
  baseUrl: "https://api.deepseek.com",
  model: "deepseek-v4-pro",
  temperature: 0.2,
  maxRetries: 3,
});

const courses = ref([]);
const courseAssignments = ref([]);
const taskAssignmentOptions = ref([]);
const classes = ref([]);
const classStudents = ref([]);
const taskClassStudents = ref([]);
const taskQuestions = ref([]);
const taskAnswerExtraction = ref(null);
const taskEvidenceExtraction = ref(null);
const selectedAnswerSubmissionId = ref(null);
const hoveredAnswerQuestionId = ref(null);
const answerInteractionArea = ref(null);
const selectedEvidenceSubmissionId = ref(null);
const selectedEvidenceQuestionId = ref(null);
const evidenceLowConfidenceOnly = ref(false);
const activeEvidenceSubmissionIds = ref(new Set());
const activeEventSources = new Set();
const taskLlmStream = reactive({
  stage: "",
  status: "等待开始",
  text: "",
});
const assignmentLlmStream = reactive({
  stage: "",
  status: "等待开始",
  text: "",
});

const pageMeta = {
  tasks: { eyebrow: "Teacher Review Console", title: "批改任务工作台" },
  classes: { eyebrow: "Class Operations", title: "班级管理" },
  courses: { eyebrow: "Course Management", title: "课程管理" },
  taskDetail: { eyebrow: "Task Progress", title: "任务进度" },
  courseDetail: { eyebrow: "Course Detail", title: "课程明细" },
  classDetail: { eyebrow: "Class Detail", title: "班级明细" },
  llmSettings: { eyebrow: "LLM Runtime", title: "模型设置" },
};

const detailViews = ["taskDetail", "courseDetail", "classDetail"];
const currentPage = computed(() => pageMeta[activeView.value]);
const activeMenu = computed(() => {
  if (activeView.value === "taskDetail") return "tasks";
  if (activeView.value === "courseDetail") return "courses";
  if (activeView.value === "classDetail") return "classes";
  return activeView.value;
});
const selectedTask = computed(() => taskStore.items.find((task) => task.id === selectedTaskId.value));
const selectedCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value));
const selectedCourseAssignment = computed(() =>
  courseAssignments.value.find((assignment) => assignment.id === selectedCourseAssignmentId.value),
);
const selectedClass = computed(() => classes.value.find((classItem) => classItem.id === selectedClassId.value));
const selectedTaskProgress = computed(() => selectedTask.value?.progress ?? 0);
const selectedAssignmentFileGroup = computed(() => getAssignmentFileGroup(selectedCourseAssignmentId.value));
const selectedAssignmentRubricState = computed(() => getAssignmentRubricState(selectedCourseAssignmentId.value));
const selectedAssignmentQuestions = computed(() => selectedAssignmentRubricState.value.questions ?? []);
const selectedAssignmentRubricConfirmed = computed(() => Boolean(selectedAssignmentRubricState.value.rubric_confirmed));
const selectedAssignmentHasRubrics = computed(() =>
  selectedAssignmentQuestions.value.some((question) => Array.isArray(question.rubrics) && question.rubrics.length),
);
const selectedAssignmentRubricStep = computed(() => {
  if (selectedAssignmentRubricConfirmed.value) return 3;
  if (selectedAssignmentHasRubrics.value) return 2;
  if (selectedAssignmentQuestions.value.length) return 1;
  return 0;
});
const selectedAssignmentRubricProgress = computed(() => Math.round((selectedAssignmentRubricStep.value / 3) * 100));
const selectedTaskFileGroup = computed(() => getTaskFileGroup(selectedTaskId.value));
const uploadedAssignmentFileCount = computed(() =>
  Object.values(selectedAssignmentFileGroup.value).reduce((sum, files) => sum + files.length, 0),
);
const uploadedStudentSubmissionFileCount = computed(
  () => selectedTaskFileGroup.value.student_submission?.length ?? 0,
);
const selectedTaskStudentMatches = computed(() => {
  const storedMatches = taskStudentMatchMap.value[String(selectedTaskId.value)] ?? [];
  if (storedMatches.length) return storedMatches;
  return buildLocalStudentMatches(taskClassStudents.value, selectedTaskFileGroup.value.student_submission ?? []);
});
const studentParseMatchedCount = computed(
  () => selectedTaskStudentMatches.value.filter((item) => item.match_status === "matched").length,
);
const studentParseTotalCount = computed(() => taskClassStudents.value.length);
const answerExtractionStudents = computed(() => {
  const currentFileIds = new Set(
    (selectedTaskFileGroup.value.student_submission ?? []).map((file) => String(file.id)),
  );
  const persistedStudents = (taskAnswerExtraction.value?.students ?? []).filter(
    (student) => !student.source_file_id || currentFileIds.has(String(student.source_file_id)),
  );
  const previewStudents = buildPreviewAnswerExtractionStudents();
  const seenKeys = new Set(persistedStudents.map((student) => answerStudentKey(student)));
  const mergedPreviewStudents = previewStudents.filter((student) => {
    const key = answerStudentKey(student);
    if (seenKeys.has(key)) return false;
    seenKeys.add(key);
    return true;
  });
  return [...persistedStudents, ...mergedPreviewStudents];
});
const answerExtractionEligibleCount = computed(() => answerExtractionStudents.value.length);
const answerExtractionCompletedCount = computed(
  () => answerExtractionStudents.value.filter((student) => student.status === "done").length,
);
const answerExtractionHasAnswers = computed(() =>
  answerExtractionStudents.value.some((student) => (student.answers ?? []).length > 0),
);
const selectedAnswerStudent = computed(() => {
  if (!answerExtractionStudents.value.length) return null;
  return (
    answerExtractionStudents.value.find((student) => student.submission_id === selectedAnswerSubmissionId.value)
    ?? answerExtractionStudents.value[0]
  );
});
const selectedAnswerStudentAnswers = computed(() => selectedAnswerStudent.value?.answers ?? []);
const highlightedSubmissionParts = computed(() =>
  buildHighlightedSubmissionParts(
    selectedAnswerStudent.value,
    selectedAnswerStudentAnswers.value,
  ),
);
const activeAnswerQuestionId = computed(() => hoveredAnswerQuestionId.value);
const evidenceExtractionStudents = computed(() => {
  const snapshotStudents = taskEvidenceExtraction.value?.students ?? [];
  if (snapshotStudents.length) {
    return snapshotStudents.filter((student) => studentEvidenceEligible(student));
  }
  return buildPreviewEvidenceExtractionStudents();
});
const evidenceExtractionEligibleCount = computed(() => evidenceExtractionStudents.value.length);
const evidenceExtractionCompletedCount = computed(
  () => evidenceExtractionStudents.value.filter((student) => studentEvidenceCompleted(student)).length,
);
const evidenceExtractionHasEvidence = computed(() =>
  evidenceExtractionStudents.value.some((student) =>
    (student.questions ?? []).some((question) => (question.evidence_items ?? []).length > 0),
  ),
);
const evidenceLowConfidenceCount = computed(() =>
  evidenceExtractionStudents.value.reduce(
    (sum, student) => sum + studentEvidenceLowConfidenceCount(student),
    0,
  ),
);
const selectedEvidenceStudent = computed(() => {
  if (!evidenceExtractionStudents.value.length) return null;
  return (
    evidenceExtractionStudents.value.find((student) => student.submission_id === selectedEvidenceSubmissionId.value)
    ?? evidenceExtractionStudents.value[0]
  );
});
const selectedEvidenceQuestions = computed(() => selectedEvidenceStudent.value?.questions ?? []);
const filteredEvidenceQuestions = computed(() => {
  if (!evidenceLowConfidenceOnly.value) return selectedEvidenceQuestions.value;
  return selectedEvidenceQuestions.value.filter((question) => questionEvidenceLowConfidenceCount(question) > 0);
});
const selectedEvidenceQuestion = computed(() => {
  if (!filteredEvidenceQuestions.value.length) return null;
  return (
    filteredEvidenceQuestions.value.find((question) => question.question_id === selectedEvidenceQuestionId.value)
    ?? filteredEvidenceQuestions.value[0]
  );
});
const selectedEvidenceQuestionTitle = computed(() =>
  selectedEvidenceQuestion.value ? questionLabel(selectedEvidenceQuestion.value.question_id) : "评分证据",
);
const selectedEvidenceQuestionRubrics = computed(() =>
  taskQuestions.value.find((question) => question.id === selectedEvidenceQuestion.value?.question_id)?.rubrics ?? [],
);
const selectedEvidenceDimensionRows = computed(() =>
  selectedEvidenceQuestionRubrics.value.map((rubric) => {
    const evidence = evidenceForRubric(selectedEvidenceQuestion.value, rubric.id);
    const positiveEvidence = evidence?.positive_evidence ?? [];
    const negativeEvidence = evidence?.negative_evidence ?? [];
    const skipped = evidenceQuestionSkipsExtraction(selectedEvidenceQuestion.value);
    return {
      rubric,
      positive_evidence: positiveEvidence,
      negative_evidence: negativeEvidence,
      confidence: Number(evidence?.confidence ?? 0),
      hasEvidence: positiveEvidence.length > 0 || negativeEvidence.length > 0,
      skipped,
    };
  }),
);
const llmProviders = [
  {
    label: "DeepSeek",
    value: "deepseek",
    baseUrl: "https://api.deepseek.com",
    models: ["deepseek-v4-pro", "deepseek-v4-flash"],
  },
  {
    label: "OpenAI Compatible",
    value: "openai-compatible",
    baseUrl: "https://api.openai.com/v1",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
  },
  {
    label: "通义千问",
    value: "qwen",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    models: ["qwen-plus", "qwen-turbo", "qwen-max"],
  },
  {
    label: "豆包",
    value: "doubao",
    baseUrl: "https://ark.cn-beijing.volces.com/api/v3",
    models: ["doubao-1-5-pro-32k", "doubao-1-5-lite-32k"],
  },
  {
    label: "自定义",
    value: "custom",
    baseUrl: "",
    models: [],
  },
];

const activeLlmProvider = computed(() =>
  llmProviders.find((provider) => provider.value === llmForm.provider) ?? llmProviders[0],
);
const activeModelOptions = computed(() => activeLlmProvider.value.models);
const llmProviderLabel = computed(() => activeLlmProvider.value.label);
const apiKeyDisplayValue = computed(() => {
  if (apiKeyEditing.value) return llmForm.apiKey;
  if (llmForm.apiKey) return llmForm.apiKey;
  if (llmSecretState.hasApiKey) return "已保存 API Key";
  return "";
});
const apiKeyPlaceholder = computed(() =>
  llmSecretState.hasApiKey ? "已保存 API Key，输入新值可替换" : "sk-...",
);
const llmHealthLabel = computed(() => {
  const labels = {
    unknown: "未检测",
    checking: "检测中",
    available: "可用",
    unavailable: "不可用",
    disabled: "未启用",
    missing_key: "未设置",
    unconfigured: "未配置",
  };
  return labels[llmHealth.status] ?? llmHealth.message;
});

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
    value: classes.value.reduce((sum, item) => sum + Number(item.student_count ?? 0), 0),
  },
]);

const courseSummary = computed(() => [
  { label: "课程总数", value: courses.value.length },
  {
    label: "作业数量",
    value: courses.value.reduce((sum, item) => sum + Number(item.assignment_count ?? 0), 0),
  },
]);

const taskStages = [
  {
    key: "analyze_questions",
    eyebrow: "Question Analysis",
    title: "题目分析",
    caption: "识别题目结构",
    detail: "识别题号、题型、知识点、难度和期望答案类型，为量规生成提供结构化基础。",
  },
  {
    key: "build_rubrics",
    eyebrow: "Rubric Build",
    title: "量规生成",
    caption: "生成评分维度",
    detail: "为每道题生成评分维度、维度分值、得分条件、扣分条件和证据要求。",
  },
  {
    key: "teacher_confirm_rubrics",
    eyebrow: "Rubric Confirm",
    title: "量规确认",
    caption: "教师确认标准",
    detail: "教师检查并修改评分量规，确认后才进入正式批改，保证评分标准可控。",
  },
  {
    key: "prepare_students",
    eyebrow: "Student Parse",
    title: "学生解析",
    caption: "整理学生作业",
    detail: "从学生提交文件中识别姓名、学号和正文内容，建立学生作业记录。",
  },
  {
    key: "extract_answers",
    eyebrow: "Answer Extract",
    title: "答案抽取",
    caption: "按题匹配答案",
    detail: "从每份学生作业中按题抽取答案，并标记 matched、missing、ambiguous 或 manual_check 等状态。",
  },
  {
    key: "extract_evidence",
    eyebrow: "Evidence Extract",
    title: "证据提取",
    caption: "抽取评分依据",
    detail: "围绕每个评分维度提取正向证据、负向证据和置信度，此阶段只找证据，不直接给分。",
  },
  {
    key: "grade_by_question",
    eyebrow: "AI Grading",
    title: "AI评分",
    caption: "按题统一评分",
    detail: "同一道题批量批改所有学生答案，主要依据结构化证据和已确认量规评分。",
  },
  {
    key: "reflect_grading",
    eyebrow: "Reflection",
    title: "反思校准",
    caption: "检查评分一致性",
    detail: "检查总分求和、证据冲突、空答案给分、超分和理由不匹配等异常情况。",
  },
  {
    key: "teacher_review",
    eyebrow: "Teacher Review",
    title: "教师复核",
    caption: "确认最终成绩",
    detail: "教师查看证据、修改单题得分和评语，系统保存最终成绩与修订记录。",
  },
  {
    key: "export_results",
    eyebrow: "Export",
    title: "结果导出",
    caption: "生成成绩表",
    detail: "基于最终分数生成成绩表、详细评分记录和后续报告导出数据。",
  },
];

function normalizeProgressStageKey(backendKey) {
  if (
    backendKey === "parse_files"
    || backendKey === "analyze_questions"
    || backendKey === "build_rubrics"
    || backendKey === "teacher_confirm_rubrics"
  ) {
    return "prepare_students";
  }
  return backendKey;
}

const assignmentStageKeys = new Set(["analyze_questions", "build_rubrics", "teacher_confirm_rubrics"]);
const visibleTaskStages = computed(() => taskStages.filter((stage) => !assignmentStageKeys.has(stage.key)));
const assignmentRubricStages = computed(() => taskStages.filter((stage) => assignmentStageKeys.has(stage.key)));

const normalizedTaskProgressStageKey = computed(() =>
  normalizeProgressStageKey(selectedTask.value?.current_stage),
);

const activeProgressStage = computed(() => {
  const rawKey = selectedProgressStageKey.value || selectedTask.value?.current_stage;
  const selectedKey = normalizeProgressStageKey(rawKey) || taskStages[0].key;
  return visibleTaskStages.value.find((stage) => stage.key === selectedKey) ?? visibleTaskStages.value[0];
});

const currentProgressStageIndex = computed(() =>
  visibleTaskStages.value.findIndex((stage) => stage.key === normalizedTaskProgressStageKey.value),
);

const activeProgressStageStatus = computed(() => {
  const activeIndex = visibleTaskStages.value.findIndex((stage) => stage.key === activeProgressStage.value.key);
  if (activeIndex === currentProgressStageIndex.value) return "进行中";
  if (currentProgressStageIndex.value >= 0 && activeIndex < currentProgressStageIndex.value) return "已完成";
  return "待开始";
});

const currentAssignmentRubricStageKey = computed(() => {
  if (selectedAssignmentRubricConfirmed.value) return "teacher_confirm_rubrics";
  if (selectedAssignmentHasRubrics.value) return "teacher_confirm_rubrics";
  if (selectedAssignmentQuestions.value.length) return "build_rubrics";
  return "analyze_questions";
});

const activeAssignmentRubricStage = computed(() => {
  const selectedKey = selectedAssignmentRubricStageKey.value || currentAssignmentRubricStageKey.value;
  return assignmentRubricStages.value.find((stage) => stage.key === selectedKey) ?? assignmentRubricStages.value[0];
});

const activeAssignmentRubricStageStatus = computed(() => {
  const activeIndex = assignmentRubricStages.value.findIndex(
    (stage) => stage.key === activeAssignmentRubricStage.value.key,
  );
  const currentIndex = assignmentRubricStages.value.findIndex(
    (stage) => stage.key === currentAssignmentRubricStageKey.value,
  );
  if (activeIndex === currentIndex) return selectedAssignmentRubricConfirmed.value ? "已完成" : "进行中";
  if (activeIndex < currentIndex || selectedAssignmentRubricConfirmed.value) return "已完成";
  return "待开始";
});

const taskMaterials = [
  {
    role: "requirement",
    title: "作业文件",
    description: "",
    multiple: false,
    accept: ".doc,.docx,.pdf,.txt,.md",
    readOnly: true,
  },
  {
    role: "reference_answer",
    title: "答案文件",
    description: "",
    multiple: false,
    accept: ".doc,.docx,.pdf,.txt,.md",
    readOnly: true,
  },
  {
    role: "student_submission",
    title: "学生作业",
    description: "支持连续添加多份学生作业文件",
    multiple: true,
    accept: ".doc,.docx,.pdf,.txt,.md,.zip",
    readOnly: false,
  },
];

const assignmentMaterials = [
  {
    role: "requirement",
    title: "作业文件",
    description: "保存作业要求、题目或说明文件，后续批改任务可直接引用",
    multiple: false,
    accept: ".doc,.docx,.pdf,.txt,.md",
  },
  {
    role: "reference_answer",
    title: "答案文件",
    description: "保存参考答案或评分说明，后续用于题目分析和量规生成",
    multiple: false,
    accept: ".doc,.docx,.pdf,.txt,.md",
  },
];

const LOCAL_COURSES_KEY = "gradetap.courses";
const LOCAL_COURSE_ASSIGNMENTS_KEY = "gradetap.courseAssignments";
const LOCAL_COURSE_ASSIGNMENT_FILES_KEY = "gradetap.courseAssignmentFiles";
const LOCAL_COURSE_ASSIGNMENT_RUBRICS_KEY = "gradetap.courseAssignmentRubrics";
const LOCAL_CLASSES_KEY = "gradetap.classes";
const LOCAL_CLASS_STUDENTS_KEY = "gradetap.classStudents";
const LOCAL_LLM_SETTINGS_KEY = "gradetap.llmSettings";
const LOCAL_TASK_FILES_KEY = "gradetap.taskFiles";
const LOCAL_TASK_STUDENT_MATCHES_KEY = "gradetap.taskStudentMatches";

const assignmentFileMap = ref(readLocalAssignmentFileMap());
const taskFileMap = ref(readLocalTaskFileMap());
const taskStudentMatchMap = ref(readLocalTaskStudentMatchMap());
const assignmentRubricMap = ref(readLocalAssignmentRubricMap());

function readLocalList(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) ?? "[]");
  } catch {
    return [];
  }
}

function writeLocalList(key, items) {
  window.localStorage.setItem(key, JSON.stringify(items));
}

function readLocalStudentMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_CLASS_STUDENTS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function readLocalTaskFileMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_TASK_FILES_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function readLocalTaskStudentMatchMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_TASK_STUDENT_MATCHES_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function readLocalAssignmentMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_COURSE_ASSIGNMENTS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function writeLocalAssignments(courseId, assignments) {
  const map = readLocalAssignmentMap();
  map[courseId] = assignments;
  window.localStorage.setItem(LOCAL_COURSE_ASSIGNMENTS_KEY, JSON.stringify(map));
}

function readLocalAssignments(courseId) {
  return readLocalAssignmentMap()[courseId] ?? [];
}

function readLocalAssignmentFileMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_COURSE_ASSIGNMENT_FILES_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function writeLocalAssignmentFileMap(map) {
  window.localStorage.setItem(LOCAL_COURSE_ASSIGNMENT_FILES_KEY, JSON.stringify(map));
}

function readLocalAssignmentRubricMap() {
  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_COURSE_ASSIGNMENT_RUBRICS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function writeLocalAssignmentRubricMap(map) {
  window.localStorage.setItem(LOCAL_COURSE_ASSIGNMENT_RUBRICS_KEY, JSON.stringify(map));
}

function writeLocalTaskFileMap(map) {
  window.localStorage.setItem(LOCAL_TASK_FILES_KEY, JSON.stringify(map));
}

function writeLocalTaskStudentMatchMap(map) {
  window.localStorage.setItem(LOCAL_TASK_STUDENT_MATCHES_KEY, JSON.stringify(map));
}

function createEmptyAssignmentFileGroup() {
  return {
    requirement: [],
    reference_answer: [],
  };
}

function createEmptyTaskFileGroup() {
  return {
    requirement: [],
    reference_answer: [],
    student_submission: [],
  };
}

function normalizeAssignmentFile(file, fileRole) {
  const now = new Date().toISOString();
  return {
    id: file.id ?? `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    assignment_id: file.assignment_id ?? selectedCourseAssignmentId.value,
    file_name: file.file_name ?? file.name ?? "未命名文件",
    file_role: file.file_role ?? fileRole,
    content_type: file.content_type ?? file.raw?.type ?? "",
    storage_path: file.storage_path ?? "",
    parsed_text: file.parsed_text ?? "",
    created_at: file.created_at ?? now,
    updated_at: file.updated_at ?? now,
    local_only: file.local_only ?? false,
  };
}

function normalizeTaskFile(file, fileRole) {
  const now = new Date().toISOString();
  return {
    id: file.id ?? `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    task_id: file.task_id ?? selectedTaskId.value,
    file_name: file.file_name ?? file.name ?? "未命名文件",
    file_role: file.file_role ?? fileRole,
    content_type: file.content_type ?? file.raw?.type ?? "",
    storage_path: file.storage_path ?? "",
    parsed_text: file.parsed_text ?? "",
    created_at: file.created_at ?? now,
    updated_at: file.updated_at ?? now,
    local_only: file.local_only ?? false,
  };
}

function groupAssignmentFiles(files) {
  const groupedFiles = createEmptyAssignmentFileGroup();
  files.forEach((file) => {
    const fileRole = file.file_role;
    if (!groupedFiles[fileRole]) return;
    groupedFiles[fileRole].push(normalizeAssignmentFile(file, fileRole));
  });
  return groupedFiles;
}

function groupTaskFiles(files) {
  const groupedFiles = createEmptyTaskFileGroup();
  files.forEach((file) => {
    const fileRole = file.file_role;
    if (!groupedFiles[fileRole]) return;
    groupedFiles[fileRole].push(normalizeTaskFile(file, fileRole));
  });
  return groupedFiles;
}

function getAssignmentFileGroup(assignmentId) {
  if (!assignmentId) return createEmptyAssignmentFileGroup();
  return assignmentFileMap.value[String(assignmentId)] ?? createEmptyAssignmentFileGroup();
}

function setAssignmentFileGroup(assignmentId, group) {
  if (!assignmentId) return;
  assignmentFileMap.value = {
    ...assignmentFileMap.value,
    [String(assignmentId)]: group,
  };
  writeLocalAssignmentFileMap(assignmentFileMap.value);
}

function assignmentFilesForRole(fileRole) {
  return selectedAssignmentFileGroup.value[fileRole] ?? [];
}

function createEmptyAssignmentRubricState() {
  return {
    questions: [],
    rubrics: [],
    rubric_confirmed: false,
    rubric_confirmed_at: null,
  };
}

function getAssignmentRubricState(assignmentId) {
  if (!assignmentId) return createEmptyAssignmentRubricState();
  const assignment = courseAssignments.value.find((item) => item.id === assignmentId);
  const localState = assignmentRubricMap.value[String(assignmentId)] ?? {};
  return {
    ...createEmptyAssignmentRubricState(),
    ...localState,
    questions: assignment?.questions?.length ? assignment.questions : localState.questions ?? [],
    rubrics: assignment?.rubrics?.length ? assignment.rubrics : localState.rubrics ?? [],
    rubric_confirmed: assignment?.rubric_confirmed ?? localState.rubric_confirmed ?? false,
    rubric_confirmed_at: assignment?.rubric_confirmed_at ?? localState.rubric_confirmed_at ?? null,
  };
}

function assignmentRubricBound(assignment) {
  if (!assignment?.id) return false;
  const localState = assignmentRubricMap.value[String(assignment.id)] ?? {};
  return Boolean(assignment.rubric_confirmed ?? localState.rubric_confirmed);
}

function setAssignmentRubricState(assignmentId, state) {
  if (!assignmentId) return;
  const normalizedState = {
    ...createEmptyAssignmentRubricState(),
    ...state,
    questions: state.questions ?? state.rubrics ?? [],
    rubrics: state.rubrics ?? state.questions ?? [],
    rubric_confirmed: Boolean(state.rubric_confirmed),
  };
  assignmentRubricMap.value = {
    ...assignmentRubricMap.value,
    [String(assignmentId)]: normalizedState,
  };
  writeLocalAssignmentRubricMap(assignmentRubricMap.value);
  courseAssignments.value = courseAssignments.value.map((item) =>
    item.id === assignmentId
      ? {
          ...item,
          questions: normalizedState.questions,
          rubrics: normalizedState.rubrics,
          rubric_confirmed: normalizedState.rubric_confirmed,
          rubric_confirmed_at: normalizedState.rubric_confirmed_at,
        }
      : item,
  );
  if (selectedCourseId.value) {
    writeLocalAssignments(selectedCourseId.value, courseAssignments.value);
  }
}

function getTaskFileGroup(taskId) {
  if (!taskId) return createEmptyTaskFileGroup();
  return taskFileMap.value[String(taskId)] ?? createEmptyTaskFileGroup();
}

function setTaskFileGroup(taskId, group) {
  if (!taskId) return;
  taskFileMap.value = {
    ...taskFileMap.value,
    [String(taskId)]: group,
  };
  writeLocalTaskFileMap(taskFileMap.value);
}

function taskFilesForRole(fileRole) {
  return selectedTaskFileGroup.value[fileRole] ?? [];
}

function setTaskStudentMatches(taskId, matches) {
  if (!taskId) return;
  taskStudentMatchMap.value = {
    ...taskStudentMatchMap.value,
    [String(taskId)]: matches,
  };
  writeLocalTaskStudentMatchMap(taskStudentMatchMap.value);
}

function clearTaskStudentMatches(taskId) {
  setTaskStudentMatches(taskId, []);
}

function openParsedTextPreview(file) {
  parsedPreviewFile.value = file;
  parsedPreviewVisible.value = true;
}

function writeLocalStudents(classId, students) {
  const map = readLocalStudentMap();
  map[classId] = students;
  window.localStorage.setItem(LOCAL_CLASS_STUDENTS_KEY, JSON.stringify(map));
}

function readLocalStudents(classId) {
  return readLocalStudentMap()[classId] ?? [];
}

function mergeById(primaryItems, secondaryItems) {
  const seen = new Set();
  return [...primaryItems, ...secondaryItems].filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

function updateClassStudentCount(classId, count) {
  classes.value = classes.value.map((item) =>
    item.id === classId ? { ...item, student_count: count } : item,
  );
  writeLocalList(LOCAL_CLASSES_KEY, classes.value);
}

function updateCourseAssignmentCount(courseId, count) {
  courses.value = courses.value.map((item) =>
    item.id === courseId ? { ...item, assignment_count: count } : item,
  );
  writeLocalList(LOCAL_COURSES_KEY, courses.value);
}

async function fetchCourses() {
  try {
    const remoteCourses = await listCourses();
    courses.value = mergeById(remoteCourses, readLocalList(LOCAL_COURSES_KEY));
  } catch {
    courses.value = mergeById(readLocalList(LOCAL_COURSES_KEY), courses.value);
  }
  writeLocalList(LOCAL_COURSES_KEY, courses.value);
}

async function fetchCourseAssignments(courseId) {
  if (!courseId) {
    courseAssignments.value = [];
    return;
  }
  assignmentLoading.value = true;
  try {
    const remoteAssignments = await listCourseAssignments(courseId);
    courseAssignments.value = mergeById(remoteAssignments, readLocalAssignments(courseId));
  } catch {
    courseAssignments.value = readLocalAssignments(courseId);
  } finally {
    assignmentLoading.value = false;
  }
  writeLocalAssignments(courseId, courseAssignments.value);
  updateCourseAssignmentCount(courseId, courseAssignments.value.length);
}

async function fetchTaskAssignmentOptions(courseName) {
  taskAssignmentOptions.value = [];
  const course = courses.value.find((item) => item.course_name === courseName);
  if (!course?.id) return;

  taskAssignmentLoading.value = true;
  try {
    const remoteAssignments = await listCourseAssignments(course.id);
    taskAssignmentOptions.value = mergeById(remoteAssignments, readLocalAssignments(course.id));
  } catch {
    taskAssignmentOptions.value = readLocalAssignments(course.id);
  } finally {
    taskAssignmentLoading.value = false;
  }
}

async function fetchClasses() {
  try {
    const remoteClasses = await listClasses();
    classes.value = mergeById(remoteClasses, readLocalList(LOCAL_CLASSES_KEY));
  } catch {
    classes.value = mergeById(readLocalList(LOCAL_CLASSES_KEY), classes.value);
  }
  writeLocalList(LOCAL_CLASSES_KEY, classes.value);
}

async function fetchClassStudents(classId) {
  studentLoading.value = true;
  try {
    const remoteStudents = await listClassStudents(classId);
    classStudents.value = mergeById(remoteStudents, readLocalStudents(classId));
  } catch {
    classStudents.value = readLocalStudents(classId);
  } finally {
    studentLoading.value = false;
  }
  writeLocalStudents(classId, classStudents.value);
  updateClassStudentCount(classId, classStudents.value.length);
}

async function fetchTaskClassStudents(task) {
  taskClassStudents.value = [];
  if (!task?.class_name) return;

  let classItem = classes.value.find((item) => item.class_name === task.class_name);
  if (!classItem) {
    await fetchClasses();
    classItem = classes.value.find((item) => item.class_name === task.class_name);
  }
  if (!classItem?.id) return;

  try {
    taskClassStudents.value = mergeById(
      await listClassStudents(classItem.id),
      readLocalStudents(classItem.id),
    );
  } catch {
    taskClassStudents.value = readLocalStudents(classItem.id);
  }
  writeLocalStudents(classItem.id, taskClassStudents.value);
  updateClassStudentCount(classItem.id, taskClassStudents.value.length);
}

onMounted(() => {
  loadLlmSettings();
  taskStore.fetchTasks();
  fetchCourses();
  fetchClasses();
});

onBeforeUnmount(() => {
  for (const eventSource of activeEventSources) {
    eventSource.close();
  }
  activeEventSources.clear();
});

function handleMenuSelect(view) {
  activeView.value = view;
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
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

function openCreateTask() {
  editingTaskId.value = null;
  Object.assign(form, {
    task_name: "",
    course_name: "",
    assignment_name: "",
    class_name: "",
    grading_instruction: "",
  });
  taskAssignmentOptions.value = [];
  taskDialogVisible.value = true;
}

function handleTaskCourseChange() {
  form.assignment_name = "";
  fetchTaskAssignmentOptions(form.course_name);
}

function openTaskDetail(task) {
  selectedTaskId.value = task.id;
  const normalized = normalizeProgressStageKey(task.current_stage);
  selectedProgressStageKey.value = taskStages.some((stage) => stage.key === normalized)
    ? normalized
    : taskStages[0].key;
  activeView.value = "taskDetail";
  fetchTaskFiles(task.id);
  fetchTaskQuestions(task.id);
  fetchTaskClassStudents(task);
  fetchTaskAnswerExtraction(task.id);
  fetchTaskEvidenceExtraction(task.id);
}

function selectProgressStage(stageKey) {
  selectedProgressStageKey.value = stageKey;
  if (stageKey === "extract_evidence") {
    ensureEvidenceSelection();
  }
}

function selectAssignmentRubricStage(stageKey) {
  selectedAssignmentRubricStageKey.value = stageKey;
}

function editTask(task) {
  editingTaskId.value = task.id;
  Object.assign(form, {
    task_name: task.task_name,
    course_name: task.course_name,
    assignment_name: task.assignment_name ?? "",
    class_name: task.class_name,
    grading_instruction: task.grading_instruction,
  });
  fetchTaskAssignmentOptions(task.course_name);
  taskDialogVisible.value = true;
}

function submitTask() {
  if (!form.task_name.trim()) {
    ElMessage.warning("请填写任务名称");
    return;
  }
  if (!form.course_name) {
    ElMessage.warning("请选择课程");
    return;
  }
  if (!form.assignment_name) {
    ElMessage.warning("请选择作业");
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
    assignment_name: "",
    class_name: "",
    grading_instruction: "",
  });
  taskAssignmentOptions.value = [];
  editingTaskId.value = null;
  taskDialogVisible.value = false;
  selectedTaskId.value = task?.id ?? null;
  activeView.value = "tasks";
  submitting.value = false;
  ElMessage.success(wasEditing ? "任务已保存" : "任务已创建");
}

async function deleteTask(task) {
  try {
    await ElMessageBox.confirm(`确定删除批改任务“${task.task_name}”吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteTaskApi(task.id);
  } catch (err) {
    const status = err?.response?.status;
    if (status !== 404) {
      const detail = err?.response?.data?.detail;
      ElMessage.error(typeof detail === "string" ? detail : "删除失败，请稍后重试");
      return;
    }
  }
  taskStore.deleteTask(task.id);
  if (selectedTaskId.value === task.id) {
    selectedTaskId.value = null;
    activeView.value = "tasks";
  }
  ElMessage.success("任务已删除");
}

function openCreateCourse() {
  editingCourseId.value = null;
  Object.assign(courseForm, { course_name: "", description: "" });
  courseDialogVisible.value = true;
}

async function openCourseDetail(course) {
  selectedCourseId.value = course.id;
  selectedCourseAssignmentId.value = null;
  courseAssignmentLayoutExpanded.value = false;
  courseAssignments.value = [];
  activeView.value = "courseDetail";
  await fetchCourseAssignments(course.id);
}

function editCourse(course) {
  editingCourseId.value = course.id;
  Object.assign(courseForm, {
    course_name: course.course_name,
    description: course.description,
  });
  courseDialogVisible.value = true;
}

async function submitCourse() {
  if (!courseForm.course_name.trim()) {
    ElMessage.warning("请填写课程名称");
    return;
  }

  const wasEditing = Boolean(editingCourseId.value);
  const courseId = editingCourseId.value;
  const payload = { ...courseForm };
  if (wasEditing) {
    courses.value = courses.value.map((item) => (item.id === courseId ? { ...item, ...payload } : item));
  } else {
    courses.value = [{ id: Date.now(), ...payload, assignment_count: 0 }, ...courses.value];
  }
  writeLocalList(LOCAL_COURSES_KEY, courses.value);

  let courseBackendSynced = false;
  try {
    const serverCourse = wasEditing ? await updateCourse(courseId, payload) : await createCourse(payload);
    courses.value = wasEditing
      ? courses.value.map((item) => (item.id === courseId ? serverCourse : item))
      : [serverCourse, ...courses.value.filter((item) => item.id !== serverCourse.id && item.course_name !== payload.course_name)];
    writeLocalList(LOCAL_COURSES_KEY, courses.value);
    courseBackendSynced = true;
  } catch {
    ElMessage.warning("课程已保存在本地，后端同步失败");
  }

  Object.assign(courseForm, { course_name: "", description: "" });
  editingCourseId.value = null;
  courseDialogVisible.value = false;
  if (courseBackendSynced) {
    ElMessage.success(wasEditing ? "课程已保存" : "课程已创建");
  }
}

async function deleteCourse(course) {
  try {
    await ElMessageBox.confirm(`确定删除课程“${course.course_name}”吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }

  courses.value = courses.value.filter((item) => item.id !== course.id);
  writeLocalList(LOCAL_COURSES_KEY, courses.value);
  let courseBackendDeleted = false;
  try {
    await deleteCourseApi(course.id);
    courseBackendDeleted = true;
  } catch {
    ElMessage.warning("课程已从本地移除，但后端删除失败");
  }
  if (selectedCourseId.value === course.id) {
    selectedCourseId.value = null;
    activeView.value = "courses";
  }
  if (courseBackendDeleted) {
    ElMessage.success("课程已删除");
  }
}

function openCreateAssignment() {
  if (!selectedCourseId.value) return;
  editingAssignmentId.value = null;
  Object.assign(assignmentForm, { assignment_name: "", description: "", total_score: 100 });
  assignmentDialogVisible.value = true;
}

function editAssignment(assignment) {
  editingAssignmentId.value = assignment.id;
  Object.assign(assignmentForm, {
    assignment_name: assignment.assignment_name,
    description: assignment.description,
    total_score: Number(assignment.total_score ?? 100),
  });
  assignmentDialogVisible.value = true;
}

async function selectCourseAssignment(assignment) {
  if (!selectedCourseId.value) return;
  courseAssignmentLayoutExpanded.value = true;
  selectedCourseAssignmentId.value = assignment.id;
  selectedAssignmentRubricStageKey.value = "";
  await Promise.all([
    fetchCourseAssignmentFiles(selectedCourseId.value, assignment.id),
    fetchCourseAssignmentQuestions(selectedCourseId.value, assignment.id),
  ]);
}

function clearCourseAssignmentSelection() {
  courseAssignmentLayoutExpanded.value = false;
  if (selectedCourseAssignmentId.value) {
    selectedCourseAssignmentId.value = null;
  }
  selectedAssignmentRubricStageKey.value = "";
}

async function submitAssignment() {
  if (!selectedCourseId.value) return;
  if (!assignmentForm.assignment_name.trim()) {
    ElMessage.warning("请填写作业名称");
    return;
  }

  const courseId = selectedCourseId.value;
  const wasEditing = Boolean(editingAssignmentId.value);
  const assignmentId = editingAssignmentId.value;
  const payload = {
    assignment_name: assignmentForm.assignment_name.trim(),
    description: assignmentForm.description.trim(),
    total_score: Number(assignmentForm.total_score ?? 100),
  };

  if (wasEditing) {
    courseAssignments.value = courseAssignments.value.map((item) =>
      item.id === assignmentId ? { ...item, ...payload } : item,
    );
  } else {
    const localAssignment = {
      id: Date.now(),
      course_id: courseId,
      ...payload,
      file_count: 0,
    };
    courseAssignments.value = [localAssignment, ...courseAssignments.value];
  }
  writeLocalAssignments(courseId, courseAssignments.value);
  updateCourseAssignmentCount(courseId, courseAssignments.value.length);

  try {
    const serverAssignment = wasEditing
      ? await updateCourseAssignment(courseId, assignmentId, payload)
      : await createCourseAssignment(courseId, payload);
    courseAssignments.value = wasEditing
      ? courseAssignments.value.map((item) => (item.id === assignmentId ? serverAssignment : item))
      : [
          serverAssignment,
          ...courseAssignments.value.filter(
            (item) => item.id !== serverAssignment.id && item.assignment_name !== payload.assignment_name,
          ),
        ];
    writeLocalAssignments(courseId, courseAssignments.value);
    updateCourseAssignmentCount(courseId, courseAssignments.value.length);
    ElMessage.success(wasEditing ? "作业已保存" : "作业已创建");
  } catch {
    ElMessage.warning("课程作业已保存在本地，后端同步失败");
  }

  Object.assign(assignmentForm, { assignment_name: "", description: "", total_score: 100 });
  editingAssignmentId.value = null;
  assignmentDialogVisible.value = false;
}

async function deleteAssignment(assignment) {
  if (!selectedCourseId.value) return;
  try {
    await ElMessageBox.confirm(`确定删除课程作业“${assignment.assignment_name}”吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }

  const courseId = selectedCourseId.value;
  courseAssignments.value = courseAssignments.value.filter((item) => item.id !== assignment.id);
  writeLocalAssignments(courseId, courseAssignments.value);
  updateCourseAssignmentCount(courseId, courseAssignments.value.length);
  if (selectedCourseAssignmentId.value === assignment.id) {
    selectedCourseAssignmentId.value = null;
    courseAssignmentLayoutExpanded.value = false;
  }

  try {
    await deleteCourseAssignment(courseId, assignment.id);
    ElMessage.success("作业已删除");
  } catch {
    ElMessage.warning("作业已从本地移除，但后端删除失败");
  }
}

function openCreateClass() {
  editingClassId.value = null;
  Object.assign(classForm, { class_name: "", note: "" });
  classDialogVisible.value = true;
}

async function openClassDetail(classItem) {
  selectedClassId.value = classItem.id;
  activeView.value = "classDetail";
  await fetchClassStudents(classItem.id);
}

function editClass(classItem) {
  editingClassId.value = classItem.id;
  Object.assign(classForm, {
    class_name: classItem.class_name,
    note: classItem.note,
  });
  classDialogVisible.value = true;
}

async function submitClass() {
  if (!classForm.class_name.trim()) {
    ElMessage.warning("请填写班级名称");
    return;
  }

  const wasEditing = Boolean(editingClassId.value);
  const classId = editingClassId.value;
  const payload = { ...classForm };
  if (wasEditing) {
    classes.value = classes.value.map((item) => (item.id === classId ? { ...item, ...payload } : item));
  } else {
    classes.value = [{ id: Date.now(), ...payload, student_count: 0 }, ...classes.value];
  }
  writeLocalList(LOCAL_CLASSES_KEY, classes.value);

  let classBackendSynced = false;
  try {
    const serverClass = wasEditing ? await updateClassGroup(classId, payload) : await createClassGroup(payload);
    classes.value = wasEditing
      ? classes.value.map((item) => (item.id === classId ? serverClass : item))
      : [serverClass, ...classes.value.filter((item) => item.id !== serverClass.id && item.class_name !== payload.class_name)];
    writeLocalList(LOCAL_CLASSES_KEY, classes.value);
    classBackendSynced = true;
  } catch {
    ElMessage.warning("班级已保存在本地，后端同步失败");
  }

  Object.assign(classForm, { class_name: "", note: "" });
  editingClassId.value = null;
  classDialogVisible.value = false;
  if (classBackendSynced) {
    ElMessage.success(wasEditing ? "班级已保存" : "班级已创建");
  }
}

async function deleteClass(classItem) {
  try {
    await ElMessageBox.confirm(`确定删除班级“${classItem.class_name}”吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }

  classes.value = classes.value.filter((item) => item.id !== classItem.id);
  writeLocalList(LOCAL_CLASSES_KEY, classes.value);
  let classBackendDeleted = false;
  try {
    await deleteClassGroup(classItem.id);
    classBackendDeleted = true;
  } catch {
    ElMessage.warning("班级已从本地移除，但后端删除失败");
  }
  if (selectedClassId.value === classItem.id) {
    selectedClassId.value = null;
    activeView.value = "classes";
  }
  if (classBackendDeleted) {
    ElMessage.success("班级已删除");
  }
}

function openCreateStudent() {
  editingStudentId.value = null;
  Object.assign(studentForm, { student_name: "", student_no: "" });
  studentDialogVisible.value = true;
}

function editStudent(student) {
  editingStudentId.value = student.id;
  Object.assign(studentForm, {
    student_name: student.student_name,
    student_no: student.student_no,
  });
  studentDialogVisible.value = true;
}

async function submitStudent() {
  if (!selectedClassId.value) return;
  if (!studentForm.student_name.trim()) {
    ElMessage.warning("请填写学生姓名");
    return;
  }

  const classId = selectedClassId.value;
  const wasEditing = Boolean(editingStudentId.value);
  const studentId = editingStudentId.value;
  const payload = {
    student_name: studentForm.student_name.trim(),
    student_no: studentForm.student_no.trim(),
  };

  if (wasEditing) {
    classStudents.value = classStudents.value.map((item) => (item.id === studentId ? { ...item, ...payload } : item));
  } else {
    classStudents.value = [{ id: Date.now(), class_group_id: classId, ...payload }, ...classStudents.value];
  }
  writeLocalStudents(classId, classStudents.value);
  updateClassStudentCount(classId, classStudents.value.length);

  try {
    const serverStudent = wasEditing
      ? await updateClassStudent(classId, studentId, payload)
      : await createClassStudent(classId, payload);
    classStudents.value = wasEditing
      ? classStudents.value.map((item) => (item.id === studentId ? serverStudent : item))
      : [serverStudent, ...classStudents.value.filter((item) => item.id !== serverStudent.id && item.id !== studentId)];
    writeLocalStudents(classId, classStudents.value);
    updateClassStudentCount(classId, classStudents.value.length);
  } catch {
    ElMessage.warning("学生已保存在本地，后端同步失败");
  }

  Object.assign(studentForm, { student_name: "", student_no: "" });
  editingStudentId.value = null;
  studentDialogVisible.value = false;
  ElMessage.success(wasEditing ? "学生已保存" : "学生已添加");
}

async function deleteStudent(student) {
  if (!selectedClassId.value) return;
  try {
    await ElMessageBox.confirm(`确定删除学生“${student.student_name}”吗？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      lockScroll: false,
      type: "warning",
    });
  } catch {
    return;
  }

  const classId = selectedClassId.value;
  classStudents.value = classStudents.value.filter((item) => item.id !== student.id);
  writeLocalStudents(classId, classStudents.value);
  updateClassStudentCount(classId, classStudents.value.length);

  try {
    await deleteClassStudent(classId, student.id);
  } catch {
    ElMessage.warning("学生已从本地移除，但后端删除失败");
  }
  ElMessage.success("学生已删除");
}

async function fetchCourseAssignmentFiles(courseId, assignmentId) {
  if (!courseId || !assignmentId) return;
  assignmentFilesLoading.value = true;
  try {
    const remoteFiles = await listCourseAssignmentFiles(courseId, assignmentId);
    const localGroup = getAssignmentFileGroup(assignmentId);
    const remoteGroup = groupAssignmentFiles(remoteFiles);
    setAssignmentFileGroup(assignmentId, {
      requirement: remoteGroup.requirement.length ? remoteGroup.requirement : localGroup.requirement,
      reference_answer: remoteGroup.reference_answer.length
        ? remoteGroup.reference_answer
        : localGroup.reference_answer,
    });
  } catch {
    setAssignmentFileGroup(assignmentId, getAssignmentFileGroup(assignmentId));
  } finally {
    assignmentFilesLoading.value = false;
  }
}

async function fetchCourseAssignmentQuestions(courseId, assignmentId) {
  if (!courseId || !assignmentId) return;
  try {
    const result = await listCourseAssignmentQuestions(courseId, assignmentId);
    setAssignmentRubricState(assignmentId, {
      questions: result.questions ?? [],
      rubrics: result.rubrics ?? result.questions ?? [],
      rubric_confirmed: result.rubric_confirmed ?? false,
      rubric_confirmed_at: result.rubric_confirmed_at ?? null,
    });
  } catch {
    setAssignmentRubricState(assignmentId, getAssignmentRubricState(assignmentId));
  }
}

async function parseSelectedAssignmentFiles() {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) return;
  if (selectedAssignmentQuestions.value.length || selectedAssignmentRubricConfirmed.value) {
    const confirmed = await confirmRestartStep({
      title: "重新解析作业材料",
      message:
        "重新解析成功后，将清空该作业当前的题目分析结果、评分量规和量规确认状态。解析失败时，当前记录会保留。",
      confirmText: "确认重新解析",
    });
    if (!confirmed) return;
  }
  parseAssignmentFilesLoading.value = true;
  try {
    const result = await parseCourseAssignmentFiles(selectedCourseId.value, selectedCourseAssignmentId.value);
    await fetchCourseAssignmentFiles(selectedCourseId.value, selectedCourseAssignmentId.value);
    setAssignmentRubricState(selectedCourseAssignmentId.value, createEmptyRubricState());
    selectedAssignmentRubricStageKey.value = "analyze_questions";
    ElMessage.success(`作业材料解析完成，成功 ${result.parsed_count ?? 0} 个`);
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail ?? "作业材料解析失败，请检查上传文件");
  } finally {
    parseAssignmentFilesLoading.value = false;
  }
}

function resetLlmStream(streamState, stage) {
  streamState.stage = stage;
  streamState.status = "连接中";
  streamState.text = "";
}

function clearLlmStream(streamState) {
  streamState.stage = "";
  streamState.status = "等待开始";
  streamState.text = "";
}

function openLlmEventStream(url, streamState, expectedStage) {
  const eventSource = new EventSource(url);
  activeEventSources.add(eventSource);

  eventSource.addEventListener("stage_started", (event) => {
    const data = parseSseData(event);
    if (data.stage !== expectedStage) return;
    streamState.status = "生成中";
    streamState.text = llmProgressPlaceholder(expectedStage);
  });
  eventSource.addEventListener("llm_progress", (event) => {
    const data = parseSseData(event);
    if (data.stage !== expectedStage) return;
    streamState.status = "生成中";
    streamState.text = formatLlmProgress(data);
  });
  eventSource.addEventListener("stage_done", (event) => {
    const data = parseSseData(event);
    if (data.stage !== expectedStage) return;
    streamState.status = "校验完成";
    streamState.text = formatLlmProgressDone(expectedStage, data, streamState.text);
    closeLlmEventStream(eventSource);
  });
  eventSource.addEventListener("stage_failed", (event) => {
    const data = parseSseData(event);
    if (data.stage !== expectedStage) return;
    streamState.status = "生成失败";
    if (data.message) {
      streamState.text += `\n\n[系统] ${data.message}`;
    }
    closeLlmEventStream(eventSource);
  });
  eventSource.onerror = () => {
    streamState.status = streamState.text ? "连接中断" : "等待响应";
  };
  return eventSource;
}

function openAnswerExtractionEventStream(url) {
  const eventSource = new EventSource(url);
  activeEventSources.add(eventSource);

  eventSource.addEventListener("stage_started", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    answerExtractionLoading.value = true;
    ensureAnswerExtractionSnapshot(data.total_questions ?? taskQuestions.value.length);
  });
  eventSource.addEventListener("student_started", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    updateAnswerStudentProgress(data, { status: "processing" });
  });
  eventSource.addEventListener("student_question_progress", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    updateAnswerStudentProgress(data, { status: "processing" });
  });
  eventSource.addEventListener("student_done", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    updateAnswerStudentProgress(data, {
      status: "done",
      completed_questions: data.total_questions ?? taskQuestions.value.length,
    });
  });
  eventSource.addEventListener("student_failed", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    updateAnswerStudentProgress(data, { status: "failed", error_message: data.message ?? "抽取失败" });
  });
  eventSource.addEventListener("stage_done", async (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    await fetchTaskQuestions(selectedTaskId.value);
    await fetchTaskAnswerExtraction(selectedTaskId.value);
    await fetchTaskEvidenceExtraction(selectedTaskId.value);
    taskStore.updateTask(selectedTaskId.value, {
      status: "answers_extracted",
      current_stage: "extract_evidence",
      progress: Math.max(selectedTask.value?.progress ?? 0, 58),
    });
    answerExtractionLoading.value = false;
    closeLlmEventStream(eventSource);
    ElMessage.success("答案抽取完成");
  });
  eventSource.addEventListener("stage_failed", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_answers") return;
    answerExtractionLoading.value = false;
    closeLlmEventStream(eventSource);
    ElMessage.error(data.message || "答案抽取失败");
  });
  eventSource.onerror = () => {
    if (answerExtractionLoading.value) return;
    closeLlmEventStream(eventSource);
  };
  return eventSource;
}

function openEvidenceExtractionEventStream(url) {
  const eventSource = new EventSource(url);
  activeEventSources.add(eventSource);

  eventSource.addEventListener("stage_started", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    evidenceExtractionLoading.value = true;
    activeEvidenceSubmissionIds.value = new Set();
    selectedProgressStageKey.value = "extract_evidence";
    taskEvidenceExtraction.value = {
      ...(taskEvidenceExtraction.value ?? buildInitialEvidenceSnapshot("queued")),
      status: "processing",
      total_answers: data.total_answers ?? taskEvidenceExtraction.value?.total_answers ?? 0,
      completed_answers: data.completed_answers ?? taskEvidenceExtraction.value?.completed_answers ?? 0,
    };
  });
  eventSource.addEventListener("answer_started", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    if (data.submission_id != null) {
      activeEvidenceSubmissionIds.value = new Set([
        ...activeEvidenceSubmissionIds.value,
        data.submission_id,
      ]);
    }
    updateEvidenceQuestionRuntime(data, "processing");
  });
  eventSource.addEventListener("answer_done", async (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    updateEvidenceQuestionRuntime(data, "done");
    await fetchTaskQuestions(selectedTaskId.value);
    await fetchTaskEvidenceExtraction(selectedTaskId.value);
  });
  eventSource.addEventListener("answer_failed", async (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    updateEvidenceQuestionRuntime(data, "failed");
    await fetchTaskEvidenceExtraction(selectedTaskId.value);
  });
  eventSource.addEventListener("answer_progress", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    taskEvidenceExtraction.value = {
      ...(taskEvidenceExtraction.value ?? buildInitialEvidenceSnapshot("queued")),
      status: "processing",
      total_answers: data.total_answers ?? taskEvidenceExtraction.value?.total_answers ?? 0,
      completed_answers: data.completed_answers ?? taskEvidenceExtraction.value?.completed_answers ?? 0,
    };
  });
  eventSource.addEventListener("stage_done", async (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    await fetchTaskQuestions(selectedTaskId.value);
    await fetchTaskEvidenceExtraction(selectedTaskId.value);
    taskStore.updateTask(selectedTaskId.value, {
      status: "evidence_extracted",
      current_stage: "grade_by_question",
      progress: Math.max(selectedTask.value?.progress ?? 0, 68),
    });
    evidenceExtractionLoading.value = false;
    activeEvidenceSubmissionIds.value = new Set();
    closeLlmEventStream(eventSource);
    ElMessage.success("证据提取完成");
  });
  eventSource.addEventListener("stage_failed", (event) => {
    const data = parseSseData(event);
    if (data.stage !== "extract_evidence") return;
    evidenceExtractionLoading.value = false;
    activeEvidenceSubmissionIds.value = new Set();
    closeLlmEventStream(eventSource);
    ElMessage.error(data.message || "证据提取失败");
  });
  eventSource.onerror = () => {
    if (evidenceExtractionLoading.value) return;
    closeLlmEventStream(eventSource);
  };
  return eventSource;
}

function closeLlmEventStream(eventSource) {
  eventSource.close();
  activeEventSources.delete(eventSource);
}

function parseSseData(event) {
  try {
    return JSON.parse(event.data || "{}");
  } catch {
    return {};
  }
}

function llmProgressPlaceholder(stage) {
  if (stage === "build_rubrics") {
    return "模型正在生成评分量规，系统会按题号更新进度...";
  }
  return "模型正在分析题目，系统会按题号更新识别进度...";
}

function formatLlmProgress(data) {
  const numbers = Array.isArray(data.question_numbers) ? data.question_numbers : [];
  const count = data.recognized_count ?? numbers.length;
  const action = data.stage === "build_rubrics" ? "已开始生成量规" : "已识别题目";
  const numberText = numbers.length ? `\n题号：${numbers.join("、")}` : "";
  return `${action} ${count} 道${numberText}`;
}

function formatLlmProgressDone(stage, data, fallbackText) {
  const count = data.question_count;
  if (typeof count === "number") {
    return stage === "build_rubrics"
      ? `评分量规生成完成，共 ${count} 道题，正在渲染结构化结果。`
      : `题目分析完成，共识别 ${count} 道题，正在渲染结构化结果。`;
  }
  return fallbackText || "模型生成完成，正在渲染结构化结果。";
}

async function runAssignmentQuestionAnalysis() {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) return;
  if (selectedAssignmentQuestions.value.length) {
    const confirmed = await confirmRestartStep({
      title: "重新分析题目",
      message:
        "重新分析成功后，将替换当前题目分析结果，并清空已生成的评分量规与量规确认状态。模型失败或结果校验失败时，当前记录会保留。",
      confirmText: "确认重新分析",
    });
    if (!confirmed) return;
  }
  assignmentQuestionAnalysisLoading.value = true;
  resetLlmStream(assignmentLlmStream, "analyze_questions");
  const eventSource = openLlmEventStream(
    buildApiUrl(`/courses/${selectedCourseId.value}/assignments/${selectedCourseAssignmentId.value}/events`),
    assignmentLlmStream,
    "analyze_questions",
  );
  try {
    const result = await analyzeCourseAssignmentQuestions(selectedCourseId.value, selectedCourseAssignmentId.value);
    setAssignmentRubricState(selectedCourseAssignmentId.value, {
      questions: result.questions ?? [],
      rubrics: [],
      rubric_confirmed: false,
      rubric_confirmed_at: null,
    });
    selectedAssignmentRubricStageKey.value = "build_rubrics";
    ElMessage.success(`题目分析完成，识别 ${result.question_count ?? result.questions?.length ?? 0} 道题`);
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail ?? "题目分析失败，请确认作业材料已解析且模型设置可用");
  } finally {
    closeLlmEventStream(eventSource);
    assignmentQuestionAnalysisLoading.value = false;
    clearLlmStream(assignmentLlmStream);
  }
}

async function runAssignmentRubricBuild() {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) return;
  if (selectedAssignmentHasRubrics.value) {
    const confirmed = await confirmRestartStep({
      title: "重新生成评分量规",
      message:
        "重新生成成功后，将替换当前评分量规，并清空量规确认状态。模型失败或结果校验失败时，当前量规会保留。",
      confirmText: "确认重新生成",
    });
    if (!confirmed) return;
  }
  assignmentRubricBuildLoading.value = true;
  resetLlmStream(assignmentLlmStream, "build_rubrics");
  const eventSource = openLlmEventStream(
    buildApiUrl(`/courses/${selectedCourseId.value}/assignments/${selectedCourseAssignmentId.value}/events`),
    assignmentLlmStream,
    "build_rubrics",
  );
  try {
    const result = await buildCourseAssignmentRubrics(selectedCourseId.value, selectedCourseAssignmentId.value);
    setAssignmentRubricState(selectedCourseAssignmentId.value, {
      questions: result.questions ?? result.rubrics ?? [],
      rubrics: result.rubrics ?? result.questions ?? [],
      rubric_confirmed: false,
      rubric_confirmed_at: null,
    });
    selectedAssignmentRubricStageKey.value = "teacher_confirm_rubrics";
    ElMessage.success("评分量规已生成，请检查后确认");
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail ?? "量规生成失败，请先完成题目分析");
  } finally {
    closeLlmEventStream(eventSource);
    assignmentRubricBuildLoading.value = false;
    clearLlmStream(assignmentLlmStream);
  }
}

async function confirmSelectedAssignmentRubrics() {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) return;
  if (!selectedAssignmentHasRubrics.value) {
    ElMessage.warning("请先生成评分量规");
    return;
  }
  assignmentRubricConfirmLoading.value = true;
  const confirmedAt = new Date().toISOString();
  const payload = {
    questions: selectedAssignmentQuestions.value,
    rubric_confirmed: true,
  };
  setAssignmentRubricState(selectedCourseAssignmentId.value, {
    questions: payload.questions,
    rubrics: payload.questions,
    rubric_confirmed: true,
    rubric_confirmed_at: confirmedAt,
  });
  try {
    const result = await confirmCourseAssignmentRubrics(
      selectedCourseId.value,
      selectedCourseAssignmentId.value,
      payload,
    );
    setAssignmentRubricState(selectedCourseAssignmentId.value, {
      questions: result.questions ?? payload.questions,
      rubrics: result.rubrics ?? result.questions ?? payload.questions,
      rubric_confirmed: result.rubric_confirmed ?? true,
      rubric_confirmed_at: result.rubric_confirmed_at ?? confirmedAt,
    });
    ElMessage.success("评分量规已与该作业绑定，后续批改可直接复用");
  } catch (error) {
    ElMessage.warning(error?.response?.data?.detail ?? "量规已保存在本地，后端同步失败");
  } finally {
    assignmentRubricConfirmLoading.value = false;
  }
}

async function handleAssignmentMaterialChange(material, uploadFile) {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) {
    ElMessage.warning("请先选择课程作业");
    return;
  }
  const rawFile = uploadFile.raw;
  if (!rawFile) return;

  assignmentFileUploading[material.role] = true;
  const courseId = selectedCourseId.value;
  const assignmentId = selectedCourseAssignmentId.value;
  const currentGroup = getAssignmentFileGroup(assignmentId);
  const localFile = normalizeAssignmentFile(
    {
      id: `local-${Date.now()}-${rawFile.name}`,
      name: rawFile.name,
      content_type: rawFile.type,
      local_only: true,
    },
    material.role,
  );

  setAssignmentFileGroup(assignmentId, {
    ...currentGroup,
    [material.role]: [localFile],
  });

  try {
    const serverFile = await uploadCourseAssignmentFile(courseId, assignmentId, material.role, rawFile);
    const latestGroup = getAssignmentFileGroup(assignmentId);
    setAssignmentFileGroup(assignmentId, {
      ...latestGroup,
      [material.role]: [normalizeAssignmentFile(serverFile, material.role)],
    });
    courseAssignments.value = courseAssignments.value.map((item) =>
      item.id === assignmentId ? { ...item, file_count: uploadedAssignmentFileCount.value } : item,
    );
    writeLocalAssignments(courseId, courseAssignments.value);
    ElMessage.success(`${material.title}已上传`);
  } catch {
    ElMessage.warning(`${material.title}已暂存在本地，后端上传失败`);
  } finally {
    assignmentFileUploading[material.role] = false;
  }
}

async function removeAssignmentMaterialFile(file) {
  if (!selectedCourseId.value || !selectedCourseAssignmentId.value) return;
  const courseId = selectedCourseId.value;
  const assignmentId = selectedCourseAssignmentId.value;
  const currentGroup = getAssignmentFileGroup(assignmentId);
  setAssignmentFileGroup(assignmentId, {
    ...currentGroup,
    [file.file_role]: currentGroup[file.file_role].filter((item) => item.id !== file.id),
  });
  courseAssignments.value = courseAssignments.value.map((item) =>
    item.id === assignmentId ? { ...item, file_count: uploadedAssignmentFileCount.value } : item,
  );
  writeLocalAssignments(courseId, courseAssignments.value);

  if (typeof file.id === "string" && file.id.startsWith("local-")) {
    ElMessage.success("文件已移除");
    return;
  }

  assignmentFileDeletingId.value = file.id;
  try {
    await deleteCourseAssignmentFile(courseId, assignmentId, file.id);
    ElMessage.success("文件已移除");
  } catch {
    ElMessage.warning("文件已从本地列表移除，但后端删除失败");
  } finally {
    assignmentFileDeletingId.value = null;
  }
}

async function fetchTaskFiles(taskId) {
  if (!taskId) return;
  taskFilesLoading.value = true;
  try {
    const remoteFiles = await listTaskFiles(taskId);
    const localGroup = getTaskFileGroup(taskId);
    const remoteGroup = groupTaskFiles(remoteFiles);
    setTaskFileGroup(taskId, {
      requirement: remoteGroup.requirement.length ? remoteGroup.requirement : localGroup.requirement,
      reference_answer: remoteGroup.reference_answer.length
        ? remoteGroup.reference_answer
        : localGroup.reference_answer,
      student_submission: mergeTaskFiles(remoteGroup.student_submission, localGroup.student_submission),
    });
  } catch {
    setTaskFileGroup(taskId, getTaskFileGroup(taskId));
  } finally {
    taskFilesLoading.value = false;
  }
}

async function fetchTaskQuestions(taskId) {
  if (!taskId) {
    taskQuestions.value = [];
    return;
  }
  try {
    taskQuestions.value = await listTaskQuestions(taskId);
  } catch {
    taskQuestions.value = [];
  }
}

async function fetchTaskAnswerExtraction(taskId) {
  if (!taskId) {
    taskAnswerExtraction.value = null;
    selectedAnswerSubmissionId.value = null;
    return;
  }
  try {
    const snapshot = await getTaskAnswerExtraction(taskId);
    taskAnswerExtraction.value = snapshot;
    if (!selectedAnswerSubmissionId.value && snapshot.students?.length) {
      selectedAnswerSubmissionId.value = snapshot.students[0].submission_id;
    } else if (!selectedAnswerSubmissionId.value && answerExtractionStudents.value.length) {
      selectedAnswerSubmissionId.value = answerExtractionStudents.value[0].submission_id;
    }
  } catch {
    taskAnswerExtraction.value = null;
    selectedAnswerSubmissionId.value = answerExtractionStudents.value[0]?.submission_id ?? null;
  }
}

async function fetchTaskEvidenceExtraction(taskId) {
  if (!taskId) {
    taskEvidenceExtraction.value = null;
    selectedEvidenceSubmissionId.value = null;
    selectedEvidenceQuestionId.value = null;
    return;
  }
  try {
    const snapshot = await getTaskEvidenceExtraction(taskId);
    taskEvidenceExtraction.value = snapshot;
  } catch {
    taskEvidenceExtraction.value = null;
  }
  ensureEvidenceSelection();
}

async function parseSelectedTaskFiles() {
  if (!selectedTaskId.value) return;
  if (taskQuestions.value.length || selectedTask.value?.status !== "created") {
    const confirmed = await confirmRestartStep({
      title: "重新解析任务材料",
      message:
        "重新解析成功后，将清空题目分析、评分量规、学生解析、答案抽取、证据、AI评分、反思校准、教师复核与修订记录。解析失败时，当前记录会保留。",
      confirmText: "确认重新解析",
    });
    if (!confirmed) return;
  }
  parseFilesLoading.value = true;
  try {
    const result = await taskStore.parseFiles(selectedTaskId.value);
    await fetchTaskFiles(selectedTaskId.value);
    taskQuestions.value = [];
    clearTaskStudentMatches(selectedTaskId.value);
    taskAnswerExtraction.value = null;
    taskEvidenceExtraction.value = null;
    selectedAnswerSubmissionId.value = null;
    selectedEvidenceSubmissionId.value = null;
    selectedEvidenceQuestionId.value = null;
    selectedProgressStageKey.value = "prepare_students";
    ElMessage.success(`文件解析完成，成功 ${result.parsed_count ?? 0} 个`);
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail ?? "文件解析失败，请检查上传材料");
  } finally {
    parseFilesLoading.value = false;
  }
}

async function runStudentPrepare() {
  if (!selectedTaskId.value) return;
  if (!taskClassStudents.value.length) {
    await fetchTaskClassStudents(selectedTask.value);
  }
  if (!taskClassStudents.value.length) {
    ElMessage.warning("该任务班级暂无学生，请先在班级管理中维护学生名单");
    return;
  }
  if (!uploadedStudentSubmissionFileCount.value) {
    ElMessage.warning("请先上传学生作业文件");
    return;
  }

  studentPrepareLoading.value = true;
  try {
    const result = await prepareTaskStudents(selectedTaskId.value);
    setTaskStudentMatches(selectedTaskId.value, result.matches ?? []);
    taskAnswerExtraction.value = null;
    taskEvidenceExtraction.value = null;
    selectedAnswerSubmissionId.value = null;
    selectedEvidenceSubmissionId.value = null;
    selectedEvidenceQuestionId.value = null;
    taskStore.updateTask(selectedTaskId.value, {
      status: result.status ?? "students_prepared",
      current_stage: "extract_answers",
      progress: Math.max(selectedTask.value?.progress ?? 0, 42),
    });
    ElMessage.success(`学生解析完成，匹配 ${result.matched_count ?? studentParseMatchedCount.value}/${result.total_students ?? studentParseTotalCount.value}`);
  } catch (error) {
    const localMatches = buildLocalStudentMatches(
      taskClassStudents.value,
      selectedTaskFileGroup.value.student_submission ?? [],
    );
    setTaskStudentMatches(selectedTaskId.value, localMatches);
    taskAnswerExtraction.value = null;
    taskEvidenceExtraction.value = null;
    selectedAnswerSubmissionId.value = null;
    selectedEvidenceSubmissionId.value = null;
    selectedEvidenceQuestionId.value = null;
    taskStore.updateTask(selectedTaskId.value, {
      status: "students_prepared",
      current_stage: "extract_answers",
      progress: Math.max(selectedTask.value?.progress ?? 0, 42),
    });
    ElMessage.warning(error?.response?.data?.detail ?? "后端学生解析失败，已先按本地文件名和解析文本完成匹配预览");
  } finally {
    studentPrepareLoading.value = false;
  }
}

async function runAnswerExtraction(force = false) {
  if (!selectedTaskId.value) return;
  if (!uploadedStudentSubmissionFileCount.value) {
    ElMessage.warning("请先上传学生作业文件");
    return;
  }

  const hasMatchedSubmissions = await ensureAnswerExtractionSubmissions();
  if (!hasMatchedSubmissions) {
    ElMessage.warning("当前没有匹配成功的学生作业，无法进入答案抽取");
    return;
  }
  if (force && answerExtractionHasAnswers.value) {
    const confirmed = await confirmRestartStep({
      title: "重新抽取答案",
      message: "重新抽取会替换当前学生答案，并清空后续证据、AI评分、反思校准和教师复核记录。",
      confirmText: "确认重新抽取",
    });
    if (!confirmed) return;
  }

  answerExtractionLoading.value = true;
  const eventSource = openAnswerExtractionEventStream(
    buildApiUrl(`/tasks/${selectedTaskId.value}/events`),
  );
  try {
    const started = await startTaskAnswerExtraction(selectedTaskId.value, 3, force);
    if (!taskQuestions.value.length) {
      await fetchTaskQuestions(selectedTaskId.value);
    }
    taskAnswerExtraction.value = {
      task_id: selectedTaskId.value,
      status: "students_prepared",
      stage: "extract_answers",
      total_questions: started.total_questions,
      total_students: started.total_students,
      completed_students: 0,
      students: force
        ? buildInitialAnswerExtractionStudents(started.total_questions)
        : answerExtractionStudents.value,
    };
    selectedAnswerSubmissionId.value = taskAnswerExtraction.value.students[0]?.submission_id ?? null;
    if (force) {
      taskEvidenceExtraction.value = null;
      selectedEvidenceSubmissionId.value = null;
      selectedEvidenceQuestionId.value = null;
    }
    selectedProgressStageKey.value = "extract_answers";
    taskStore.updateTask(selectedTaskId.value, {
      current_stage: "extract_answers",
      progress: Math.max(selectedTask.value?.progress ?? 0, 48),
    });
  } catch (error) {
    answerExtractionLoading.value = false;
    closeLlmEventStream(eventSource);
    ElMessage.error(error?.response?.data?.detail ?? "答案抽取启动失败，请确认前一步已有匹配成功的学生作业");
  }
}

async function runEvidenceExtraction(force = false) {
  if (!selectedTaskId.value) return;
  if (!answerExtractionHasAnswers.value) {
    ElMessage.warning("请先完成答案抽取，再提取评分证据");
    return;
  }
  if (force && evidenceExtractionHasEvidence.value) {
    const confirmed = await confirmRestartStep({
      title: "重新提取证据",
      message: "重新提取会替换当前评分证据，并清空后续 AI评分、反思校准和教师复核记录。",
      confirmText: "确认重新提取",
    });
    if (!confirmed) return;
  }

  evidenceExtractionLoading.value = true;
  const eventSource = openEvidenceExtractionEventStream(
    buildApiUrl(`/tasks/${selectedTaskId.value}/events`),
  );
  try {
    const started = await startTaskEvidenceExtraction(selectedTaskId.value, 3, force);
    markEvidenceExtractionStarted(started);
    selectedProgressStageKey.value = "extract_evidence";
    taskStore.updateTask(selectedTaskId.value, {
      status: selectedTask.value?.status ?? "answers_extracted",
      current_stage: "extract_evidence",
      progress: Math.max(selectedTask.value?.progress ?? 0, 62),
    });
    ensureEvidenceSelection();
    ElMessage.success("证据提取已开始");
  } catch (error) {
    evidenceExtractionLoading.value = false;
    closeLlmEventStream(eventSource);
    ElMessage.error(error?.response?.data?.detail ?? "证据提取启动失败，请确认已完成答案抽取和量规生成");
  }
}

async function ensureAnswerExtractionSubmissions() {
  await fetchTaskAnswerExtraction(selectedTaskId.value);
  if (answerExtractionStudents.value.length) return true;

  if (!taskClassStudents.value.length) {
    await fetchTaskClassStudents(selectedTask.value);
  }
  if (!taskClassStudents.value.length) return false;

  try {
    const result = await prepareTaskStudents(selectedTaskId.value);
    setTaskStudentMatches(selectedTaskId.value, result.matches ?? []);
    taskStore.updateTask(selectedTaskId.value, {
      status: result.status ?? "students_prepared",
      current_stage: "extract_answers",
      progress: Math.max(selectedTask.value?.progress ?? 0, 42),
    });
    await fetchTaskAnswerExtraction(selectedTaskId.value);
    return answerExtractionStudents.value.length > 0;
  } catch (error) {
    ElMessage.warning(error?.response?.data?.detail ?? "学生解析未完成，暂时没有可抽取答案的学生作业");
    return false;
  }
}

async function runQuestionAnalysis() {
  if (!selectedTaskId.value) return;
  if (taskQuestions.value.length) {
    const confirmed = await confirmRestartStep({
      title: "重新分析题目",
      message:
        "重新分析成功后，将替换当前题目，并清空后续步骤生成的评分量规、学生解析、答案抽取、证据、AI评分、反思校准、教师复核与修订记录。模型失败或结果校验失败时，当前记录会保留。",
      confirmText: "确认重新分析",
    });
    if (!confirmed) return;
  }
  questionAnalysisLoading.value = true;
  resetLlmStream(taskLlmStream, "analyze_questions");
  const eventSource = openLlmEventStream(
    buildApiUrl(`/tasks/${selectedTaskId.value}/events`),
    taskLlmStream,
    "analyze_questions",
  );
  try {
    const result = await taskStore.analyzeQuestions(selectedTaskId.value);
    taskQuestions.value = result.questions ?? [];
    selectedProgressStageKey.value = "analyze_questions";
    ElMessage.success(`题目分析完成，识别 ${result.question_count ?? taskQuestions.value.length} 道题`);
  } catch (error) {
    if (error?.code === "ECONNABORTED") {
      ElMessage.error("题目分析超时，模型响应时间较长，请稍后重试");
    } else {
      ElMessage.error(error?.response?.data?.detail ?? "题目分析失败，请确认模型设置和已解析文件");
    }
  } finally {
    closeLlmEventStream(eventSource);
    questionAnalysisLoading.value = false;
    clearLlmStream(taskLlmStream);
  }
}

async function confirmRestartStep({ title, message, confirmText }) {
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: confirmText,
      cancelButtonText: "取消",
      type: "warning",
      distinguishCancelAndClose: true,
    });
    return true;
  } catch {
    return false;
  }
}

function formatKnowledgePoints(points) {
  if (Array.isArray(points)) return points.join("、") || "未识别";
  return points || "未识别";
}

function difficultyMeta(difficulty) {
  const metaMap = {
    easy: { label: "简单", type: "success" },
    medium: { label: "中等", type: "warning" },
    hard: { label: "困难", type: "danger" },
    unknown: { label: "未知", type: "info" },
  };
  return metaMap[difficulty] || { label: difficulty || "未知", type: "info" };
}

function mergeTaskFiles(primaryFiles, secondaryFiles) {
  const seen = new Set();
  return [...primaryFiles, ...secondaryFiles].filter((file) => {
    const fileKey = file.id ?? file.file_name;
    if (seen.has(fileKey)) return false;
    seen.add(fileKey);
    return true;
  });
}

function normalizeMatchText(value) {
  return String(value ?? "").replace(/\s+/g, "").toLowerCase();
}

function scoreStudentFile(student, file) {
  const filenameText = normalizeMatchText(file.file_name);
  const fullText = normalizeMatchText(`${file.file_name}\n${file.parsed_text ?? ""}`);
  const studentName = normalizeMatchText(student.student_name);
  const studentNo = normalizeMatchText(student.student_no);
  let confidence = 0;
  const reasons = [];

  if (studentNo) {
    if (filenameText.includes(studentNo)) {
      confidence = Math.max(confidence, 0.96);
      reasons.push("文件名包含学号");
    } else if (fullText.includes(studentNo)) {
      confidence = Math.max(confidence, 0.9);
      reasons.push("内容包含学号");
    }
  }
  if (studentName) {
    if (filenameText.includes(studentName)) {
      confidence = Math.max(confidence, 0.88);
      reasons.push("文件名包含姓名");
    } else if (fullText.includes(studentName)) {
      confidence = Math.max(confidence, 0.78);
      reasons.push("内容包含姓名");
    }
  }
  if (studentNo && studentName && fullText.includes(studentNo) && fullText.includes(studentName)) {
    confidence = Math.max(confidence, 0.98);
    reasons.push("姓名与学号均匹配");
  }
  if (confidence < 0.75) return null;
  return {
    file,
    confidence: Number(confidence.toFixed(2)),
    reason: reasons.join("、"),
  };
}

function buildLocalStudentMatches(students, files) {
  return students.map((student) => {
    const candidates = files
      .map((file) => scoreStudentFile(student, file))
      .filter(Boolean)
      .sort((left, right) => right.confidence - left.confidence);
    const topCandidate = candidates[0] ?? null;
    const matchStatus = !topCandidate
      ? "missing"
      : candidates[1] && topCandidate.confidence - candidates[1].confidence < 0.08
        ? "ambiguous"
        : "matched";

    return {
      student_id: student.id,
      student_name: student.student_name,
      student_no: student.student_no ?? "",
      match_status: matchStatus,
      matched_file_id: topCandidate?.file.id ?? null,
      matched_file_name: topCandidate?.file.file_name ?? "",
      confidence: topCandidate?.confidence ?? 0,
      reason: topCandidate?.reason || "未在文件名或解析文本中找到学生姓名/学号",
      candidate_files: candidates.slice(0, 3).map((candidate) => candidate.file.file_name),
      submission_id: null,
    };
  });
}

function studentMatchStatusMeta(status) {
  const metaMap = {
    matched: { label: "已匹配", type: "success" },
    ambiguous: { label: "需确认", type: "warning" },
    missing: { label: "未匹配", type: "danger" },
  };
  return metaMap[status] ?? { label: "未匹配", type: "info" };
}

function answerStatusMeta(status) {
  const metaMap = {
    matched: { label: "已匹配", type: "success" },
    missing: { label: "缺失", type: "warning" },
    ambiguous: { label: "不确定", type: "warning" },
    manual_check: { label: "需检查", type: "danger" },
    extract_error: { label: "失败", type: "danger" },
  };
  return metaMap[status] ?? { label: "待抽取", type: "info" };
}

function selectAnswerStudent(submissionId) {
  selectedAnswerSubmissionId.value = submissionId;
  hoveredAnswerQuestionId.value = null;
  scrollSelectedAnswerToFirstHighlight();
}

function setAnswerInteractionArea(area) {
  answerInteractionArea.value = area;
}

function clearAnswerInteractionArea(area) {
  if (answerInteractionArea.value === area) {
    answerInteractionArea.value = null;
  }
}

function shouldSkipAnswerAutoScroll(area, origin) {
  return origin === area || answerInteractionArea.value === area;
}

async function focusAnswerQuestion(questionId, origin = "auto") {
  hoveredAnswerQuestionId.value = questionId;
  await nextTick();
  if (!shouldSkipAnswerAutoScroll("question-list", origin)) {
    scrollAnswerQuestionListToQuestion(questionId);
  }
  if (!shouldSkipAnswerAutoScroll("source", origin)) {
    scrollAnswerSourceToQuestion(questionId);
  }
}

async function scrollSelectedAnswerToFirstHighlight() {
  await nextTick();
  const firstQuestionId = highlightedSubmissionParts.value.find((part) => part.questionId)?.questionId;
  if (!shouldSkipAnswerAutoScroll("source", "student-list")) {
    scrollAnswerSourceToQuestion(firstQuestionId, { fallbackToTop: true });
  }
}

function scrollAnswerQuestionListToQuestion(questionId) {
  const container = answerQuestionListRef.value;
  if (!container || !questionId) return;

  const target = Array.from(container.querySelectorAll("[data-answer-question-id]")).find(
    (element) => String(element.dataset.answerQuestionId) === String(questionId),
  );
  target?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
}

function scrollAnswerSourceToQuestion(questionId, options = {}) {
  const container = answerSourceViewRef.value;
  if (!container) return;

  const target = questionId
    ? Array.from(container.querySelectorAll("[data-source-question-id]")).find(
        (element) => String(element.dataset.sourceQuestionId) === String(questionId),
      )
    : null;

  if (!target) {
    if (options.fallbackToTop) {
      container.scrollTo({ top: 0, behavior: "smooth" });
    }
    return;
  }

  const containerRect = container.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const stickyHeading = container.querySelector(".answer-column-heading");
  const headingOffset = stickyHeading?.getBoundingClientRect().height ?? 0;
  const top = container.scrollTop + targetRect.top - containerRect.top - headingOffset - 8;
  container.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

function studentAnswerProgress(student) {
  const total = Number(student.total_questions || taskQuestions.value.length || 0);
  if (!total) return 0;
  return Math.min(100, Math.round((Number(student.completed_questions || 0) / total) * 100));
}

function studentAnswerExtractionFinalized(student) {
  const total = Number(student?.total_questions || taskQuestions.value.length || 0);
  return Boolean(
    total
    && !student?.preview_only
    && student?.status === "done"
    && (student?.answers ?? []).length >= total,
  );
}

function studentAnswerExtractionCompleted(student) {
  const total = Number(student?.total_questions || taskQuestions.value.length || 0);
  return Boolean(
    total
    && !student?.preview_only
    && student?.status === "done"
    && Number(student?.completed_questions || 0) >= total,
  );
}

function studentAnswerCounts(student) {
  const answers = student?.answers ?? [];
  const total = Number(student?.total_questions || taskQuestions.value.length || 0);
  const matched = answers.filter((answer) => answer.extraction_status === "matched").length;
  return {
    matched,
    unmatched: Math.max(0, total - matched),
  };
}

function answerForQuestion(questionId) {
  return selectedAnswerStudentAnswers.value.find((answer) => answer.question_id === questionId);
}

function answerQuestionFinalized(questionId) {
  return Boolean(studentAnswerExtractionFinalized(selectedAnswerStudent.value) && answerForQuestion(questionId));
}

function buildPreviewEvidenceExtractionStudents() {
  return answerExtractionStudents.value
    .filter((student) => studentEvidenceEligible(student))
    .map((student) => ({
      submission_id: student.submission_id,
      student_name: student.student_name,
      student_no: student.student_no,
      source_file_id: student.source_file_id,
      source_file_name: student.source_file_name,
      status: student.status === "done" ? "pending" : student.status,
      questions: (student.answers ?? []).map((answer) => ({
        question_id: answer.question_id,
        student_answer_id: answer.id,
        answer_text: answer.answer_text ?? "",
        extraction_status: answer.extraction_status,
        answer_confidence: answer.confidence ?? 0,
        evidence_items: [],
      })),
    }));
}

function studentEvidenceEligible(student) {
  const total = Number(student?.total_questions || taskQuestions.value.length || 0);
  const answers = student?.answers ?? student?.questions ?? [];
  if (!total || answers.length < total) return false;
  return true;
}

function buildInitialEvidenceSnapshot(status = "queued") {
  const isCompleted = status === "done" || status === "evidence_extracted";
  const students = buildPreviewEvidenceExtractionStudents().map((student) => ({
    ...student,
    status: isCompleted ? "done" : "pending",
  }));
  const totalAnswers = students.reduce((sum, student) => sum + (student.questions ?? []).length, 0);
  return {
    task_id: selectedTaskId.value,
    status,
    stage: "extract_evidence",
    total_answers: totalAnswers,
    completed_answers: isCompleted ? totalAnswers : 0,
    students,
  };
}

function markEvidenceExtractionStarted(started = {}) {
  const currentSnapshot = taskEvidenceExtraction.value;
  const nextSnapshot = currentSnapshot?.students?.length
    ? currentSnapshot
    : buildInitialEvidenceSnapshot(started.status ?? "queued");
  taskEvidenceExtraction.value = {
    ...nextSnapshot,
    status: "processing",
    stage: "extract_evidence",
    total_answers: started.total_answers ?? nextSnapshot.total_answers ?? 0,
    completed_answers: started.completed_answers ?? nextSnapshot.completed_answers ?? 0,
    students: (nextSnapshot.students ?? []).map((student) => ({
      ...student,
      status: student.status === "done" ? "done" : "pending",
    })),
  };
}

function ensureEvidenceSelection() {
  const firstStudent = evidenceExtractionStudents.value[0];
  if (!firstStudent) {
    selectedEvidenceSubmissionId.value = null;
    selectedEvidenceQuestionId.value = null;
    return;
  }
  if (!evidenceExtractionStudents.value.some((student) => student.submission_id === selectedEvidenceSubmissionId.value)) {
    selectedEvidenceSubmissionId.value = firstStudent.submission_id;
  }
  const firstQuestion = selectedEvidenceQuestions.value[0];
  if (!firstQuestion) {
    selectedEvidenceQuestionId.value = null;
    return;
  }
  if (!selectedEvidenceQuestions.value.some((question) => question.question_id === selectedEvidenceQuestionId.value)) {
    selectedEvidenceQuestionId.value = firstQuestion.question_id;
  }
}

function updateEvidenceQuestionRuntime(data, status) {
  const baseSnapshot = taskEvidenceExtraction.value ?? buildInitialEvidenceSnapshot("queued");
  const nextStudents = (baseSnapshot.students ?? []).map((student) => {
    if (String(student.submission_id) !== String(data.submission_id)) return student;
    return {
      ...student,
      status: status === "processing" ? "processing" : student.status,
      questions: (student.questions ?? []).map((question) => {
        const sameAnswer = String(question.student_answer_id) === String(data.student_answer_id);
        const sameQuestion = String(question.question_id) === String(data.question_id);
        if (!sameAnswer && !sameQuestion) return question;
        return {
          ...question,
          processing_status: status,
        };
      }),
    };
  });
  taskEvidenceExtraction.value = {
    ...baseSnapshot,
    status: "processing",
    students: nextStudents,
  };
  ensureEvidenceSelection();
}

function selectEvidenceStudent(submissionId) {
  selectedEvidenceSubmissionId.value = submissionId;
  selectedEvidenceQuestionId.value = selectedEvidenceQuestions.value[0]?.question_id ?? null;
}

function selectEvidenceQuestion(questionId) {
  selectedEvidenceQuestionId.value = questionId;
}

function questionLabel(questionId) {
  const question = taskQuestions.value.find((item) => item.id === questionId);
  if (!question) return `题目 ${questionId}`;
  return `${question.question_number}. ${question.content}`;
}

function evidenceForRubric(question, rubricId) {
  return (question?.evidence_items ?? []).find((item) => item.rubric_id === rubricId) ?? null;
}

function studentEvidenceCompleted(student) {
  if (student?.status === "done") return true;
  const questions = student?.questions ?? [];
  return Boolean(
    questions.length
    && questions.every((question) =>
      (question.evidence_items ?? []).length > 0
      || evidenceQuestionSkipsExtraction(question)
      || question.processing_status === "done"
      || question.processing_status === "failed",
    ),
  );
}

function studentEvidenceCompletedQuestionCount(student) {
  return (student?.questions ?? []).filter((question) =>
    (question.evidence_items ?? []).length > 0
    || evidenceQuestionSkipsExtraction(question)
    || question.processing_status === "done"
    || question.processing_status === "failed",
  ).length;
}

function studentEvidenceRunning(student) {
  return activeEvidenceSubmissionIds.value.has(student?.submission_id);
}

function studentEvidenceLowConfidenceCount(student) {
  return (student?.questions ?? []).reduce(
    (sum, question) => sum + questionEvidenceLowConfidenceCount(question),
    0,
  );
}

function studentEvidenceProgress(student) {
  const total = Number(taskQuestions.value.length || student?.questions?.length || 0);
  if (!total) return 0;
  return Math.min(100, Math.round((studentEvidenceCompletedQuestionCount(student) / total) * 100));
}

function questionEvidenceLowConfidenceCount(question) {
  return (question?.evidence_items ?? []).filter((item) => Number(item.confidence ?? 0) < 0.8).length;
}

function evidenceQuestionSkipsExtraction(question) {
  return question?.extraction_status === "missing" || !String(question?.answer_text ?? "").trim();
}

function evidenceConfidenceMeta(confidence, skipped = false) {
  if (skipped) return { label: "无需提取", type: "info" };
  if (confidence >= 0.9) return { label: `${formatPercent(confidence)} 高`, type: "success" };
  if (confidence >= 0.8) return { label: `${formatPercent(confidence)} 可用`, type: "primary" };
  if (confidence > 0) return { label: `${formatPercent(confidence)} 需复核`, type: "warning" };
  return { label: "待提取", type: "info" };
}

function formatPercent(value) {
  const normalized = Number(value ?? 0);
  return `${Math.round(Math.max(0, Math.min(1, normalized)) * 100)}%`;
}

function answerStudentKey(student) {
  if (student?.source_file_id) return `file:${student.source_file_id}`;
  if (student?.student_no) return `no:${student.student_no}`;
  return `name:${student?.student_name ?? ""}`;
}

function buildPreviewAnswerExtractionStudents() {
  const matchedItems = selectedTaskStudentMatches.value.filter((item) => item.match_status === "matched");
  return matchedItems
    .map((item) => {
      const sourceFile = selectedTaskFileGroup.value.student_submission?.find(
        (file) => file.id === item.matched_file_id,
      );
      if (!sourceFile?.parsed_text) return null;
      return {
        submission_id: item.submission_id ?? `preview-${item.student_id}-${item.matched_file_id}`,
        student_name: item.student_name,
        student_no: item.student_no,
        source_file_id: item.matched_file_id,
        source_file_name: item.matched_file_name,
        content: sourceFile.parsed_text,
        total_questions: taskQuestions.value.length,
        completed_questions: 0,
        status: "pending",
        error_message: "",
        answers: [],
        streaming_question_numbers: [],
        preview_only: true,
      };
    })
    .filter(Boolean);
}

function buildInitialAnswerExtractionStudents(totalQuestions) {
  const matchedItems = selectedTaskStudentMatches.value.filter((item) => item.match_status === "matched");
  return matchedItems
    .filter((item) => item.submission_id)
    .map((item) => {
      const sourceFile = selectedTaskFileGroup.value.student_submission?.find(
        (file) => file.id === item.matched_file_id,
      );
      return {
        submission_id: item.submission_id,
        student_name: item.student_name,
        student_no: item.student_no,
        source_file_id: item.matched_file_id,
        source_file_name: item.matched_file_name,
        content: sourceFile?.parsed_text ?? "",
        total_questions: totalQuestions,
        completed_questions: 0,
        status: "pending",
        error_message: "",
        answers: [],
        streaming_question_numbers: [],
      };
    });
}

function ensureAnswerExtractionSnapshot(totalQuestions) {
  if (taskAnswerExtraction.value?.students?.length) return;
  taskAnswerExtraction.value = {
    task_id: selectedTaskId.value,
    status: selectedTask.value?.status ?? "students_prepared",
    stage: "extract_answers",
    total_questions: totalQuestions,
    total_students: studentParseMatchedCount.value,
    completed_students: 0,
    students: buildInitialAnswerExtractionStudents(totalQuestions),
  };
  selectedAnswerSubmissionId.value = taskAnswerExtraction.value.students[0]?.submission_id ?? null;
}

function updateAnswerStudentProgress(data, patch) {
  ensureAnswerExtractionSnapshot(data.total_questions ?? taskQuestions.value.length);
  taskAnswerExtraction.value = {
    ...taskAnswerExtraction.value,
    students: taskAnswerExtraction.value.students.map((student) =>
      student.submission_id === data.submission_id
        ? {
            ...student,
            status: patch.status ?? student.status,
            completed_questions:
              patch.completed_questions ?? data.completed_questions ?? student.completed_questions,
            total_questions: data.total_questions ?? student.total_questions,
            error_message: patch.error_message ?? student.error_message,
            streaming_question_numbers: Array.isArray(data.question_numbers)
              ? data.question_numbers
              : student.streaming_question_numbers,
          }
        : student,
    ),
  };
  taskAnswerExtraction.value.completed_students = taskAnswerExtraction.value.students.filter(
    (student) => student.status === "done",
  ).length;
}

function buildHighlightedSubmissionParts(student, answers) {
  const content = student?.content ?? "";
  if (!content) return [{ key: "empty", text: "暂无学生作业原文", questionId: null }];

  const ranges = [];
  answers.forEach((answer) => {
    const answerText = String(answer.answer_text ?? "").trim();
    if (!answerText) return;
    const range = findAnswerTextRange(content, answerText);
    if (!range) return;
    ranges.push({
      start: range.start,
      end: range.end,
      questionId: answer.question_id,
      streaming: false,
    });
  });
  ranges.sort((left, right) => left.start - right.start);

  const parts = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start < cursor) return;
    if (range.start > cursor) {
      parts.push({ key: `text-${index}-${cursor}`, text: content.slice(cursor, range.start), questionId: null });
    }
    parts.push({
      key: `answer-${range.questionId}-${range.start}`,
      text: content.slice(range.start, range.end),
      questionId: range.questionId,
    });
    cursor = range.end;
  });
  if (cursor < content.length) {
    parts.push({ key: `text-tail-${cursor}`, text: content.slice(cursor), questionId: null });
  }
  return parts.length ? parts : [{ key: "all", text: content, questionId: null }];
}

function findAnswerTextRange(content, answerText) {
  const exactIndex = content.indexOf(answerText);
  if (exactIndex >= 0) {
    return { start: exactIndex, end: exactIndex + answerText.length };
  }

  const normalizedNeedle = normalizeTextForRangeMatch(answerText);
  if (!normalizedNeedle) return null;

  let normalizedContent = "";
  const indexMap = [];
  Array.from(content).forEach((char, originalIndex) => {
    if (/\s/.test(char)) return;
    normalizedContent += char;
    indexMap.push(originalIndex);
  });

  const normalizedIndex = normalizedContent.indexOf(normalizedNeedle);
  if (normalizedIndex < 0) return null;

  const start = indexMap[normalizedIndex];
  const end = indexMap[normalizedIndex + normalizedNeedle.length - 1] + 1;
  return { start, end };
}

function normalizeTextForRangeMatch(value) {
  return Array.from(String(value ?? ""))
    .filter((char) => !/\s/.test(char))
    .join("");
}

async function handleTaskMaterialChange(material, uploadFile) {
  if (material.readOnly) return;
  if (!selectedTaskId.value) {
    ElMessage.warning("请先进入任务详情页");
    return;
  }
  const rawFile = uploadFile.raw;
  if (!rawFile) return;

  taskFileUploading[material.role] = true;
  const taskId = selectedTaskId.value;
  const currentGroup = getTaskFileGroup(taskId);
  const localFile = normalizeTaskFile(
    {
      id: `local-${Date.now()}-${rawFile.name}`,
      name: rawFile.name,
      content_type: rawFile.type,
      local_only: true,
    },
    material.role,
  );

  if (material.multiple) {
    setTaskFileGroup(taskId, {
      ...currentGroup,
      [material.role]: [localFile, ...currentGroup[material.role]],
    });
  } else {
    setTaskFileGroup(taskId, {
      ...currentGroup,
      [material.role]: [localFile],
    });
  }

  try {
    const serverFile = await uploadTaskFile(taskId, material.role, rawFile);
    const latestGroup = getTaskFileGroup(taskId);
    const normalizedServerFile = normalizeTaskFile(serverFile, material.role);
    if (material.multiple) {
      setTaskFileGroup(taskId, {
        ...latestGroup,
        [material.role]: [
          normalizedServerFile,
          ...latestGroup[material.role].filter((file) => file.id !== localFile.id),
        ],
      });
    } else {
      setTaskFileGroup(taskId, {
        ...latestGroup,
        [material.role]: [normalizedServerFile],
      });
    }
    taskStore.updateTask(taskId, {
      status: "files_uploaded",
      current_stage: "analyze_questions",
      progress: Math.max(selectedTask.value?.progress ?? 0, 8),
    });
    clearTaskStudentMatches(taskId);
    ElMessage.success(`${material.title}已上传`);
  } catch {
    ElMessage.warning(`${material.title}已暂存在本地，后端上传失败`);
  } finally {
    taskFileUploading[material.role] = false;
  }
}

async function removeTaskMaterialFile(file) {
  if (!selectedTaskId.value) return;
  if (file.file_role === "requirement" || file.file_role === "reference_answer") return;
  const taskId = selectedTaskId.value;
  const currentGroup = getTaskFileGroup(taskId);
  const nextRoleFiles = currentGroup[file.file_role].filter((item) => item.id !== file.id);
  setTaskFileGroup(taskId, {
    ...currentGroup,
    [file.file_role]: nextRoleFiles,
  });
  clearTaskStudentMatches(taskId);

  if (typeof file.id === "string" && file.id.startsWith("local-")) {
    ElMessage.success("文件已移除");
    return;
  }

  taskFileDeletingId.value = file.id;
  try {
    await deleteTaskFile(taskId, file.id);
    ElMessage.success("文件已移除");
  } catch {
    ElMessage.warning("文件已从本地列表移除，后端删除失败");
  } finally {
    taskFileDeletingId.value = null;
  }
}

async function importStudentsFromFile(file) {
  if (!selectedClassId.value) {
    ElMessage.warning("请先进入班级明细页");
    return false;
  }
  if (!file?.name?.toLowerCase().endsWith(".xlsx")) {
    ElMessage.warning("请上传 .xlsx 格式的学生名单");
    return false;
  }
  importingStudents.value = true;
  try {
    const result = await importClassStudents(selectedClassId.value, file);
    await fetchClassStudents(selectedClassId.value);
    await fetchClasses();
    ElMessage.success(`导入 ${result.imported_count} 名学生，跳过 ${result.skipped_count} 条重复记录`);
  } catch {
    ElMessage.error("导入失败，请确认 Excel 为 .xlsx，表头包含“姓名”，可选“学号”");
  } finally {
    importingStudents.value = false;
  }
  return false;
}

async function handleStudentImportChange(uploadFile) {
  await importStudentsFromFile(uploadFile.raw);
  studentImportUploadRef.value?.clearFiles();
}

async function loadLlmSettings() {
  try {
    const savedSettings = JSON.parse(window.localStorage.getItem(LOCAL_LLM_SETTINGS_KEY) ?? "{}");
    applyLlmSettings(savedSettings, { keepTypedApiKey: true });
  } catch {
    window.localStorage.removeItem(LOCAL_LLM_SETTINGS_KEY);
  }

  llmSettingsLoading.value = true;
  try {
    const remoteSettings = await getLlmSettings();
    applyLlmSettings(remoteSettings, { keepTypedApiKey: false });
    writeLlmSettingsToLocal(remoteSettings);
    await refreshLlmHealth({ silent: true });
  } catch {
    ElMessage.warning("模型设置暂时只保存在本地，后端设置接口不可用");
  } finally {
    llmSettingsLoading.value = false;
  }
}

async function saveLlmSettings() {
  if (llmForm.enabled && !llmForm.apiKey.trim() && !llmSecretState.hasApiKey) {
    ElMessage.warning("请填写 API Key");
    return;
  }
  if (llmForm.enabled && !llmForm.baseUrl.trim()) {
    ElMessage.warning("请填写 Base URL");
    return;
  }
  if (llmForm.enabled && !llmForm.model.trim()) {
    ElMessage.warning("请填写默认模型");
    return;
  }

  llmSettingsLoading.value = true;
  try {
    const remoteSettings = await updateLlmSettings(buildLlmSettingsPayload());
    applyLlmSettings(remoteSettings, { keepTypedApiKey: false });
    writeLlmSettingsToLocal(remoteSettings);
    await refreshLlmHealth({ silent: true });
    ElMessage.success("模型设置已同步到后端");
  } catch {
    writeLlmSettingsToLocal({ ...llmForm, hasApiKey: Boolean(llmForm.apiKey || llmSecretState.hasApiKey), apiKeyMask: "" });
    llmHealth.status = "unknown";
    llmHealth.message = "后端不可用，暂未检测";
    ElMessage.warning("后端同步失败，模型设置已暂存本地");
  } finally {
    llmSettingsLoading.value = false;
  }
}

async function clearLlmApiKey() {
  llmSettingsLoading.value = true;
  try {
    const remoteSettings = await clearLlmApiKeyApi();
    applyLlmSettings(remoteSettings, { keepTypedApiKey: false });
    writeLlmSettingsToLocal(remoteSettings);
    llmHealth.status = remoteSettings.enabled ? "missing_key" : "disabled";
    llmHealth.message = remoteSettings.enabled ? "未配置 API Key" : "大模型未启用";
    ElMessage.success("API Key 已从后端清除");
  } catch {
    llmForm.apiKey = "";
    llmForm.enabled = false;
    llmSecretState.hasApiKey = false;
    llmSecretState.apiKeyMask = "";
    llmHealth.status = "disabled";
    llmHealth.message = "大模型未启用";
    writeLlmSettingsToLocal({ ...llmForm, hasApiKey: false, apiKeyMask: "" });
    ElMessage.warning("后端清除失败，已清除本地密钥");
  } finally {
    llmSettingsLoading.value = false;
  }
}

function handleLlmProviderChange() {
  const provider = activeLlmProvider.value;
  llmForm.baseUrl = provider.baseUrl;
  llmForm.model = provider.models[0] ?? "";
}

function prepareApiKeyEdit() {
  apiKeyEditing.value = true;
  if (llmSecretState.hasApiKey) {
    llmForm.apiKey = "";
  }
}

function finishApiKeyEdit() {
  if (!llmForm.apiKey.trim()) {
    apiKeyEditing.value = false;
  }
}

function handleApiKeyInput(value) {
  llmForm.apiKey = value;
}

function applyLlmSettings(settings, options = {}) {
  const keepTypedApiKey = options.keepTypedApiKey ?? false;
  Object.assign(llmForm, {
    enabled: Boolean(settings.enabled ?? llmForm.enabled),
    provider: settings.provider ?? llmForm.provider,
    apiKey: keepTypedApiKey ? (settings.apiKey ?? llmForm.apiKey) : "",
    baseUrl: settings.baseUrl ?? settings.base_url ?? llmForm.baseUrl,
    model: settings.model ?? llmForm.model,
    temperature: Number(settings.temperature ?? llmForm.temperature),
    maxRetries: Number(settings.maxRetries ?? settings.max_retries ?? llmForm.maxRetries),
  });
  llmSecretState.hasApiKey = Boolean(settings.hasApiKey ?? settings.has_api_key ?? llmForm.apiKey);
  llmSecretState.apiKeyMask = settings.apiKeyMask ?? settings.api_key_mask ?? "";
  if (!llmForm.enabled) {
    llmHealth.status = "disabled";
    llmHealth.message = "大模型未启用";
  } else if (!llmSecretState.hasApiKey && !llmForm.apiKey) {
    llmHealth.status = "missing_key";
    llmHealth.message = "未配置 API Key";
  }
}

function buildLlmSettingsPayload() {
  const typedApiKey = llmForm.apiKey.trim();
  const payload = {
    enabled: llmForm.enabled,
    provider: llmForm.provider,
    baseUrl: llmForm.baseUrl.trim(),
    model: llmForm.model.trim(),
    temperature: llmForm.temperature,
    maxRetries: llmForm.maxRetries,
  };
  if (typedApiKey && typedApiKey !== llmSecretState.apiKeyMask) {
    payload.apiKey = typedApiKey;
  }
  return payload;
}

function writeLlmSettingsToLocal(settings) {
  window.localStorage.setItem(LOCAL_LLM_SETTINGS_KEY, JSON.stringify({
    enabled: settings.enabled ?? llmForm.enabled,
    provider: settings.provider ?? llmForm.provider,
    baseUrl: settings.baseUrl ?? settings.base_url ?? llmForm.baseUrl,
    model: settings.model ?? llmForm.model,
    temperature: settings.temperature ?? llmForm.temperature,
    maxRetries: settings.maxRetries ?? settings.max_retries ?? llmForm.maxRetries,
    hasApiKey: settings.hasApiKey ?? settings.has_api_key ?? llmSecretState.hasApiKey,
    apiKeyMask: settings.hasApiKey ?? settings.has_api_key ?? llmSecretState.hasApiKey ? "已保存 API Key" : "",
  }));
}

async function refreshLlmHealth(options = {}) {
  if (!llmForm.enabled) {
    llmHealth.status = "disabled";
    llmHealth.message = "大模型未启用";
    return;
  }
  if (!llmSecretState.hasApiKey && !llmForm.apiKey) {
    llmHealth.status = "missing_key";
    llmHealth.message = "未配置 API Key";
    return;
  }

  llmHealth.status = "checking";
  llmHealth.message = "正在检测模型连接";
  try {
    const result = await testLlmSettings();
    llmHealth.status = result.status;
    llmHealth.message = result.message;
    if (!options.silent && result.status === "available") {
      ElMessage.success("模型密钥检测通过");
    }
  } catch {
    llmHealth.status = "unknown";
    llmHealth.message = "后端检测接口不可用";
    if (!options.silent) {
      ElMessage.warning("模型密钥暂时无法检测");
    }
  }
}
</script>
