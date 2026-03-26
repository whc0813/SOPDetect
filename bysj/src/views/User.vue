<template>
  <div class="user-layout">
    <header class="top-nav">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>标准行为识别</span>
      </div>
      <div class="nav-right">
        <div class="user-info">
          <div class="avatar">{{ userInitials }}</div>
          <span class="username">{{ currentUserName }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">退出登录</button>
      </div>
    </header>

    <main class="main-content">
      <div class="content-wrapper">

        <div class="tab-bar" v-if="!currentSop">
          <div class="segmented-control">
            <button :class="['segment', { active: activeTab === 'tasks' }]" type="button" @click="activeTab = 'tasks'">待执行任务</button>
            <button :class="['segment', { active: activeTab === 'jobs' }]" type="button" @click="activeTab = 'jobs'">评测任务</button>
            <button :class="['segment', { active: activeTab === 'history' }]" type="button" @click="activeTab = 'history'">历史记录</button>
          </div>
        </div>

        <!-- 待执行任务 -->
        <div v-if="!currentSop && activeTab === 'tasks'" class="view-transition">
          <div class="page-header">
            <h2>可用任务</h2>
            <p class="subtitle">请选择一个标准操作流程开始执行</p>
          </div>

          <div class="grid-container">
            <div v-for="sop in sopList" :key="sop.id" class="task-card" @click="startSop(sop)">
              <div class="card-content">
                <h3 class="task-title">{{ sop.name }}</h3>
                <div class="task-meta">
                  <span class="meta-item"><el-icon><Location /></el-icon> {{ sop.scene }}</span>
                  <span class="meta-item"><el-icon><List /></el-icon> {{ sop.stepCount }} 步</span>
                </div>
              </div>
              <div class="card-action">
                <span>开始执行</span>
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>
          </div>

          <div v-if="sopList.length === 0" class="empty-state">
            <div class="empty-icon">📋</div>
            <p class="empty-title">暂无可用流程</p>
            <p class="empty-desc">请联系管理员创建标准操作流程</p>
          </div>
        </div>

        <!-- 评测任务 -->
        <div v-if="!currentSop && activeTab === 'jobs'" class="view-transition">
          <div class="page-header">
            <h2>评测任务</h2>
            <p class="subtitle">查看排队、处理中、失败和已完成的评测任务状态</p>
          </div>

          <div class="table-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>SOP 名称</th>
                  <th>提交时间</th>
                  <th style="text-align:center">状态</th>
                  <th>进度</th>
                  <th style="text-align:center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in jobList" :key="row.id">
                  <td>{{ row.taskName }}</td>
                  <td>{{ row.createdAt }}</td>
                  <td style="text-align:center">
                    <span :class="['badge', `badge-${getJobStatusTagType(row.status)}`]">
                      {{ getJobStatusText(row.status) }}
                    </span>
                  </td>
                  <td>
                    <div class="progress-cell">
                      <span class="progress-pct">{{ row.progressPercent }}%</span>
                      <span class="muted-text">{{ getJobStageText(row.stage) }}</span>
                    </div>
                  </td>
                  <td style="text-align:center">
                    <button class="text-btn" @click="openJobDetail(row)">查看详情</button>
                  </td>
                </tr>
                <tr v-if="jobList.length === 0">
                  <td colspan="5" class="empty-row">暂无评测任务</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 历史记录 -->
        <div v-if="!currentSop && activeTab === 'history'" class="view-transition">
          <div class="page-header">
            <h2>执行历史</h2>
            <p class="subtitle">查看你过去完成的流程记录和复核结果</p>
          </div>

          <div class="table-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>SOP 名称</th>
                  <th>完成时间</th>
                  <th style="text-align:center">AI 结论</th>
                  <th style="text-align:center">人工复核</th>
                  <th style="text-align:center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in historyList" :key="row.id">
                  <td>{{ row.taskName }}</td>
                  <td>{{ row.finishTime }}</td>
                  <td style="text-align:center">
                    <span :class="['badge', row.status === 'passed' ? 'badge-success' : 'badge-danger']">
                      {{ getStatusText(row.status) }}
                    </span>
                  </td>
                  <td style="text-align:center">
                    <span class="badge badge-default">{{ getManualReviewText(row.manualReview?.status) }}</span>
                  </td>
                  <td style="text-align:center">
                    <button class="text-btn" @click="openHistoryDetail(row)">查看详情</button>
                  </td>
                </tr>
                <tr v-if="historyList.length === 0">
                  <td colspan="5" class="empty-row">暂无执行记录</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 执行视图 -->
        <div v-else-if="currentSop" class="execution-view">
          <div class="execution-header">
            <button class="back-btn" @click="backToList">
              <el-icon><ArrowLeft /></el-icon>
              返回列表
            </button>
            <div class="header-titles">
              <h2>{{ currentSop.name }}</h2>
              <span class="scene-tag">{{ currentSop.scene }}</span>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-label">共 {{ currentSop.stepCount }} 个步骤</div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :style="{ width: `${currentJob ? currentJob.progressPercent : (evaluationResult ? 100 : 45)}%` }"
              ></div>
            </div>
          </div>

          <div class="step-container">
            <div class="step-section-label">操作流程</div>

            <div v-for="step in currentSop.steps" :key="step.stepNo" class="step-item">
              <div class="step-index">{{ step.stepNo }}</div>
              <div class="step-main">
                <p class="step-desc">{{ step.description }}</p>
                <div class="step-sub">
                  {{ step.referenceMode === 'text' ? '仅按文字规则校验，无示范视频' : (step.referenceSummary || '已生成该步骤的参考信息') }}
                </div>
              </div>
            </div>

            <div class="upload-section" v-if="!currentJob || currentJob.status === 'failed'">
              <el-upload
                class="minimal-upload"
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleVideoChange"
                :show-file-list="false"
                accept="video/*"
              >
                <div class="upload-content">
                  <el-icon class="upload-icon"><VideoCamera /></el-icon>
                  <div class="upload-text">
                    <span class="bold">点击上传</span> 或将文件拖拽到此处
                  </div>
                  <div class="upload-hint">支持 MP4 / MOV / AVI 格式视频</div>
                </div>
              </el-upload>

              <div v-if="currentVideo" class="file-preview">
                <div class="file-info">
                  <el-icon><VideoPlay /></el-icon>
                  <span>{{ currentVideo.name }}</span>
                </div>
                <el-button type="primary" class="submit-action-btn" @click="submitVideo" :loading="isEvaluating">
                  提交评测任务
                </el-button>
              </div>
            </div>
          </div>

          <div v-if="currentJob" class="job-status-card">
            <div class="result-header">
              <el-icon class="result-icon" v-if="currentJob.status === 'succeeded'"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>任务状态：{{ getJobStatusText(currentJob.status) }}</h3>
            </div>
            <div class="job-status-meta">
              <span :class="['badge', `badge-${getJobStatusTagType(currentJob.status)}`]">
                {{ getJobStageText(currentJob.stage) }}
              </span>
              <span>任务编号：{{ currentJob.id }}</span>
              <span>进度：{{ currentJob.progressPercent }}%</span>
            </div>
            <div v-if="currentJob.failureReason" class="job-failure-box">
              <div class="detail-title">失败原因</div>
              <div class="detail-text">{{ currentJob.failureReason }}</div>
            </div>
            <div class="detail-box">
              <div class="detail-title">评测日志</div>
              <div v-if="currentJob.logs?.length" class="job-log-list">
                <div v-for="(log, index) in currentJob.logs" :key="`${currentJob.id}-${index}`" class="job-log-item">
                  <span class="job-log-time">{{ log.time }}</span>
                  <span class="job-log-text">{{ log.message }}</span>
                </div>
              </div>
              <div v-else class="detail-text">暂无任务日志</div>
            </div>
            <div class="result-actions">
              <el-button v-if="currentJob.status === 'failed'" class="action-btn-secondary" @click="retryCurrentJob" :loading="isRetryingJob">
                重试任务
              </el-button>
            </div>
          </div>

          <div class="result-card" v-if="evaluationResult" :class="evaluationResult.passed ? 'success' : 'error'">
            <div class="result-header">
              <el-icon class="result-icon" v-if="evaluationResult.passed"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>{{ evaluationResult.passed ? '验证通过' : '验证未通过' }}</h3>
            </div>
            <div class="result-score">综合得分：{{ formatScore(evaluationResult.score, '-') }}</div>
            <div v-if="currentSopHasNoDemoVideo" class="result-note">
              当前 SOP 没有上传示范视频，本次仅依据步骤文字和你上传的视频进行判断。
            </div>
            <p class="result-feedback">{{ evaluationResult.feedback }}</p>

            <div v-if="evaluationResult.issues?.length" class="issues-list">
              <span v-for="(issue, index) in evaluationResult.issues" :key="index" class="issue-chip">{{ issue }}</span>
            </div>

            <div v-if="evaluationResult.stepResults?.length" class="step-result-list">
              <div v-for="item in evaluationResult.stepResults" :key="item.stepNo" class="step-result-item">
                <div class="step-result-top">
                  <div class="step-result-title">步骤 {{ item.stepNo }}: {{ item.description }}</div>
                  <div class="step-result-status">{{ getStepResultText(item.passed) }}</div>
                </div>
                <div class="step-result-meta">得分 {{ formatScore(item.score, '-') }} / 置信度 {{ formatConfidence(item.confidence) }}</div>
                <div class="detail-text">{{ item.evidence }}</div>
              </div>
            </div>

            <div class="result-actions">
              <el-button v-if="currentJob?.resultRecordId" type="primary" class="action-btn-primary" @click="openHistoryDetailById(currentJob.resultRecordId)">查看评测详情</el-button>
              <el-button v-if="currentJob?.status === 'failed'" class="action-btn-secondary" @click="retryCurrentJob" :loading="isRetryingJob">重试任务</el-button>
              <el-button v-if="currentJob?.status === 'failed'" class="action-btn-secondary" @click="retrySop">重新上传</el-button>
            </div>
          </div>
        </div>

      </div>
    </main>

    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px">
      <div v-if="selectedHistoryRecord" class="detail-wrap">
        <div class="summary">{{ selectedHistoryRecord.taskName }} / {{ selectedHistoryRecord.finishTime }}</div>
        <div class="detail-box">
          <div class="detail-title">综合反馈</div>
          <div class="detail-text">{{ selectedHistoryRecord.detail.feedback || '暂无反馈' }}</div>
        </div>
        <div class="detail-box" v-if="selectedHistoryRecord.detail.tokenUsage">
          <div class="detail-title">评测 Token 消耗</div>
          <div class="detail-text">{{ formatTokenUsage(selectedHistoryRecord.detail.tokenUsage) }}</div>
        </div>
        <div class="detail-box" v-if="selectedHistoryVideoUrl">
          <div class="detail-title">上传视频</div>
          <video :src="selectedHistoryVideoUrl" controls class="video" />
        </div>
        <div class="detail-box" v-if="selectedHistoryRecord.manualReview">
          <div class="detail-title">人工复核</div>
          <div class="detail-text">{{ getManualReviewText(selectedHistoryRecord.manualReview.status) }}</div>
          <div class="detail-text">{{ selectedHistoryRecord.manualReview.note || '暂无复核意见' }}</div>
        </div>
        <div class="detail-box step-results-box" v-if="selectedHistoryRecord.detail.stepResults?.length">
          <div class="detail-title">步骤结果</div>
          <div v-for="item in selectedHistoryRecord.detail.stepResults" :key="item.stepNo" class="step-result-item">
            <div class="step-result-top">
              <div class="step-result-title">步骤 {{ item.stepNo }}: {{ item.description }}</div>
              <div class="step-result-status">{{ getStepResultText(item.passed) }}</div>
            </div>
            <div class="step-result-meta">得分 {{ formatScore(item.score, '-') }}</div>
            <div class="detail-text">{{ item.evidence }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, CircleCheckFilled, List, Location, Monitor, VideoCamera, VideoPlay, WarningFilled } from '@element-plus/icons-vue'
import {
  clearAuthSession,
  createEvaluationJob,
  fileToDataUrl,
  getCurrentUser,
  getEvaluationJobDetail,
  getHistoryDetail,
  listEvaluationJobs,
  listHistory,
  listSops,
  logout,
  retryEvaluationJob,
  fetchAuthorizedMediaBlobUrl
} from '../api/client'

const router = useRouter()
const sopList = ref([])
const jobList = ref([])
const historyList = ref([])
const activeTab = ref('tasks')
const currentSop = ref(null)
const currentVideo = ref(null)
const isEvaluating = ref(false)
const isRetryingJob = ref(false)
const currentJob = ref(null)
const evaluationResult = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const selectedHistoryVideoUrl = ref('')
const currentUser = ref(getCurrentUser())
let jobPollingTimer = null

const currentUserName = computed(() => currentUser.value?.displayName || currentUser.value?.username || '用户')

const userInitials = computed(() => {
  const name = currentUser.value?.displayName || currentUser.value?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const currentSopHasNoDemoVideo = computed(() => {
  const steps = currentSop.value?.steps || []
  return steps.length > 0 && steps.every((step) => step.referenceMode === 'text')
})

function normalizeHistory(record = {}) {
  return {
    ...record,
    detail: {
      feedback: record.detail?.feedback || '',
      issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
      stepResults: Array.isArray(record.detail?.stepResults) ? record.detail.stepResults : [],
      uploadedVideo: record.detail?.uploadedVideo || null,
      tokenUsage: record.detail?.tokenUsage || null,
      payloadPreview: record.detail?.payloadPreview || null,
      rawModelResult: record.detail?.rawModelResult || null,
      sequenceAssessment: record.detail?.sequenceAssessment || '',
      prerequisiteViolated: !!record.detail?.prerequisiteViolated
    },
    manualReview: record.manualReview || null
  }
}

function normalizeJob(record = {}) {
  return {
    ...record,
    progressPercent: Number(record.progressPercent || 0),
    logs: Array.isArray(record.logs) ? record.logs : [],
    uploadedVideo: record.uploadedVideo || null
  }
}

function buildEvaluationResultFromHistory(record = {}) {
  return {
    passed: record.status === 'passed',
    score: record.score,
    feedback: record.detail?.feedback || '',
    issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
    sequenceAssessment: record.detail?.sequenceAssessment || '',
    prerequisiteViolated: !!record.detail?.prerequisiteViolated,
    stepResults: Array.isArray(record.detail?.stepResults) ? record.detail.stepResults : [],
    payloadPreview: record.detail?.payloadPreview || null,
    rawModelResult: record.detail?.rawModelResult || null
  }
}

async function loadSops() {
  sopList.value = (await listSops()).data || []
}

async function loadJobs() {
  jobList.value = ((await listEvaluationJobs()).data || []).map(normalizeJob)
}

async function loadHistory() {
  historyList.value = ((await listHistory()).data || []).map(normalizeHistory)
}

function stopJobPolling() {
  if (jobPollingTimer) {
    clearInterval(jobPollingTimer)
    jobPollingTimer = null
  }
}

function revokeSelectedHistoryVideoUrl() {
  if (selectedHistoryVideoUrl.value) {
    URL.revokeObjectURL(selectedHistoryVideoUrl.value)
    selectedHistoryVideoUrl.value = ''
  }
}

async function refreshCurrentJob(jobId, silent = false) {
  if (!jobId) return
  try {
    const job = normalizeJob((await getEvaluationJobDetail(jobId)).data)
    currentJob.value = job
    jobList.value = jobList.value.some((item) => item.id === job.id)
      ? jobList.value.map((item) => (item.id === job.id ? job : item))
      : [job, ...jobList.value]

    if (job.status === 'succeeded') {
      stopJobPolling()
      await loadHistory()
      if (job.resultRecordId) {
        const historyRecord = normalizeHistory((await getHistoryDetail(job.resultRecordId)).data)
        evaluationResult.value = buildEvaluationResultFromHistory(historyRecord)
      }
    } else if (job.status === 'failed') {
      stopJobPolling()
      evaluationResult.value = null
    }
  } catch (error) {
    if (!silent) {
      ElMessage.error(error.message || '任务状态刷新失败')
    }
    stopJobPolling()
  }
}

function startJobPolling(jobId) {
  stopJobPolling()
  if (!jobId) return
  jobPollingTimer = setInterval(() => {
    refreshCurrentJob(jobId, true)
  }, 3000)
}

async function handleLogout() {
  try {
    await logout()
  } catch (_error) {
    // 即使后端会话已失效，也允许前端本地退出
  } finally {
    clearAuthSession()
    router.push('/login')
  }
}

function startSop(sop) {
  currentSop.value = sop
  currentVideo.value = null
  evaluationResult.value = null
  currentJob.value = null
  stopJobPolling()
}

function backToList() {
  stopJobPolling()
  currentSop.value = null
  currentVideo.value = null
  evaluationResult.value = null
  currentJob.value = null
}

function handleVideoChange(file) {
  currentVideo.value = file?.raw || file
}

async function submitVideo() {
  if (!currentVideo.value) return ElMessage.warning('请先上传视频')
  isEvaluating.value = true
  try {
    const job = normalizeJob((await createEvaluationJob(currentSop.value.id, {
      userVideoDataUrl: await fileToDataUrl(currentVideo.value),
      uploadedVideo: {
        name: currentVideo.value.name || '',
        type: currentVideo.value.type || '',
        size: currentVideo.value.size ?? null,
        lastModified: currentVideo.value.lastModified ?? null
      }
    })).data)
    currentJob.value = job
    evaluationResult.value = null
    await loadJobs()
    startJobPolling(job.id)
    ElMessage.success('评测任务已提交，系统正在后台处理')
  } catch (error) {
    ElMessage.error(error.message || '提交评测任务失败')
  } finally {
    isEvaluating.value = false
  }
}

async function openHistoryDetailById(recordId) {
  if (!recordId) return
  try {
    selectedHistoryRecord.value = normalizeHistory((await getHistoryDetail(recordId)).data)
    revokeSelectedHistoryVideoUrl()
    const mediaPath = selectedHistoryRecord.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      selectedHistoryVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    historyDetailVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载详情失败')
  }
}

function retrySop() {
  currentVideo.value = null
  evaluationResult.value = null
  currentJob.value = null
  stopJobPolling()
}

async function retryCurrentJob() {
  if (!currentJob.value?.id) return
  isRetryingJob.value = true
  try {
    const job = normalizeJob((await retryEvaluationJob(currentJob.value.id)).data)
    currentJob.value = job
    currentVideo.value = null
    evaluationResult.value = null
    await loadJobs()
    startJobPolling(job.id)
    ElMessage.success('已重新提交评测任务')
  } catch (error) {
    ElMessage.error(error.message || '重试任务失败')
  } finally {
    isRetryingJob.value = false
  }
}

async function openJobDetail(row) {
  const job = normalizeJob(row)
  currentJob.value = job
  currentSop.value = sopList.value.find((item) => item.id === job.taskId) || null
  currentVideo.value = null
  evaluationResult.value = null
  if (job.status === 'queued' || job.status === 'processing') {
    startJobPolling(job.id)
    await refreshCurrentJob(job.id, true)
  } else if (job.resultRecordId) {
    stopJobPolling()
    const historyRecord = normalizeHistory((await getHistoryDetail(job.resultRecordId)).data)
    evaluationResult.value = buildEvaluationResultFromHistory(historyRecord)
  }
}

async function openHistoryDetail(row) {
  return openHistoryDetailById(row.id)
}

function formatConfidence(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '-'
}

function formatScore(value, fallback = '-') {
  const num = Number(value)
  return Number.isFinite(num) ? `${num} / 100` : fallback
}

function formatTokenUsage(usage) {
  if (!usage) return '暂无'
  const input = Number.isFinite(Number(usage.inputTokens)) ? Number(usage.inputTokens) : '-'
  const output = Number.isFinite(Number(usage.outputTokens)) ? Number(usage.outputTokens) : '-'
  const total = Number.isFinite(Number(usage.totalTokens)) ? Number(usage.totalTokens) : '-'
  return `输入 ${input} / 输出 ${output} / 总计 ${total}`
}

function getStatusText(status) {
  return status === 'passed' ? '通过' : '异常'
}

function getStepResultText(passed) {
  return passed === true ? '通过' : passed === false ? '异常' : '未知'
}

function getManualReviewText(status) {
  if (status === 'approved') return '复核通过'
  if (status === 'rejected') return '复核不通过'
  if (status === 'needs_attention') return '需要整改'
  return '待复核'
}

function getJobStatusText(status) {
  if (status === 'queued') return '排队中'
  if (status === 'processing') return '处理中'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  return '未知'
}

function getJobStatusTagType(status) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'processing') return 'warning'
  return 'info'
}

function getJobStageText(stage) {
  const stageMap = {
    submitted: '任务已提交',
    waiting: '队列等待中',
    preparing_video: '准备视频资源',
    building_prompt: '构建评测上下文',
    calling_model: '调用多模态模型',
    parsing_result: '解析评测结果',
    saving_result: '保存评测结果',
    done: '任务已完成',
    error: '任务处理失败'
  }
  return stageMap[stage] || '处理中'
}

onMounted(() => {
  Promise.all([loadSops(), loadJobs(), loadHistory()]).catch((error) => {
    ElMessage.error(error.message || '初始化失败')
  })
})

onUnmounted(() => {
  stopJobPolling()
  revokeSelectedHistoryVideoUrl()
})
</script>

<style scoped>
/* ─── Layout ─────────────────────────────────────────────── */
.user-layout {
  min-height: 100vh;
  background-color: var(--bg-base);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
  display: flex;
  flex-direction: column;
}

/* ─── Top Nav ─────────────────────────────────────────────── */
.top-nav {
  height: var(--toolbar-height);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--line-soft);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.brand-logo {
  width: 32px;
  height: 32px;
  background: linear-gradient(150deg, var(--accent), var(--accent-deep));
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 16px;
  flex-shrink: 0;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-main);
}

.logout-btn {
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 10px;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.logout-btn:hover {
  background: var(--apple-fill);
  color: var(--text-main);
}

.logout-btn:active {
  transform: scale(0.96);
}

/* ─── Main ─────────────────────────────────────────────── */
.main-content {
  flex: 1;
  padding: 28px 32px;
}

.content-wrapper {
  max-width: 900px;
  margin: 0 auto;
}

/* ─── Tab Bar ─────────────────────────────────────────────── */
.tab-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
}

.segmented-control {
  display: inline-flex;
  padding: 3px;
  background: var(--apple-fill);
  border-radius: 9999px;
}

.segment {
  padding: 9px 28px;
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: 15px;
  font-weight: 500;
  border-radius: 9999px;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.segment.active {
  background: var(--surface-strong);
  color: var(--text-main);
  font-weight: 600;
}

.segment:hover:not(.active) {
  color: var(--text-main);
}

.segment:active {
  transform: scale(0.97);
}

/* ─── Page Header ─────────────────────────────────────────── */
.page-header {
  margin-bottom: 28px;
}

.page-header h2 {
  font-size: 34px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 8px;
  letter-spacing: -0.04em;
  line-height: 1.1;
}

.subtitle {
  font-size: 15px;
  color: var(--text-soft);
  margin: 0;
}

/* ─── Task Cards ─────────────────────────────────────────── */
.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.task-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition:
    transform var(--duration-micro) var(--ease-standard),
    border-color var(--duration-short) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard);
}

.task-card:hover {
  border-color: rgba(0, 122, 255, 0.32);
  background-color: var(--surface-strong);
}

.task-card:active {
  transform: scale(0.98);
}

.task-title {
  font-size: 19px;
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 14px;
  line-height: 1.3;
}

.task-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--text-soft);
}

.card-action {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-main);
  padding-top: 14px;
  border-top: 1px solid var(--line-soft);
}

/* ─── Empty State ─────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-soft);
  margin: 0 0 6px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-faint);
  margin: 0;
}

/* ─── Data Table ─────────────────────────────────────────── */
.table-card {
  background: var(--surface);
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead th {
  text-align: left;
  padding: 13px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--line-soft);
  background: transparent;
  white-space: nowrap;
}

.data-table tbody td {
  padding: 15px 16px;
  font-size: 15px;
  color: var(--text-main);
  border-bottom: 1px solid var(--line-soft);
  vertical-align: middle;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table tbody tr:hover td {
  background: rgba(120, 120, 128, 0.04);
}

.empty-row {
  text-align: center;
  color: var(--text-faint);
  padding: 48px 16px !important;
  font-size: 14px;
}

/* ─── Badges ─────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-success { background: rgba(52, 199, 89, 0.12); color: #2f9b47; }
.badge-danger  { background: rgba(255, 59, 48, 0.10); color: #d9342b; }
.badge-warning { background: rgba(255, 159, 10, 0.12); color: #b26a00; }
.badge-info    { background: rgba(0, 122, 255, 0.10); color: #0066cc; }
.badge-default { background: rgba(120, 120, 128, 0.12); color: var(--text-soft); }

/* ─── Text Button ─────────────────────────────────────────── */
.text-btn {
  border: none;
  background: none;
  color: var(--accent);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  min-height: 44px;
  font-family: inherit;
  transition: background-color var(--duration-short) var(--ease-standard);
}

.text-btn:hover { background: rgba(0, 122, 255, 0.08); }
.text-btn:active { background: rgba(0, 122, 255, 0.14); }

/* Progress Cell */
.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.progress-pct {
  font-size: 14px;
  font-weight: 500;
}

.muted-text {
  font-size: 12px;
  color: var(--text-faint);
}

/* ─── Execution View ─────────────────────────────────────── */
.execution-header {
  margin-bottom: 36px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: none;
  color: var(--accent);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  min-height: 44px;
  padding: 8px 0;
  margin-bottom: 16px;
  transition:
    color var(--duration-short) var(--ease-standard),
    transform var(--duration-micro) var(--ease-standard);
}

.back-btn:hover { color: var(--accent-deep); }
.back-btn:active { transform: scale(0.97); }

.header-titles {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.header-titles h2 {
  font-size: 34px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.scene-tag {
  background: var(--apple-fill);
  color: var(--text-soft);
  padding: 5px 12px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 500;
}

/* ─── Progress Bar ─────────────────────────────────────────── */
.progress-section {
  margin-bottom: 36px;
}

.progress-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}

.progress-track {
  height: 5px;
  background: var(--apple-fill);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 9999px;
  transition: width var(--duration-medium) var(--ease-standard);
}

/* ─── Step Container ─────────────────────────────────────── */
.step-container {
  background: var(--surface);
  border-radius: 20px;
  border: 1px solid var(--line-soft);
  padding: 28px 32px;
  margin-bottom: 20px;
}

.step-section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}

.step-item {
  display: flex;
  gap: 14px;
  margin-top: 18px;
}

.step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-main { flex: 1; }

.step-desc {
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-main);
  margin: 0;
}

.step-sub {
  font-size: 13px;
  color: var(--text-soft);
  margin-top: 5px;
  line-height: 1.5;
}

/* ─── Upload Section ─────────────────────────────────────── */
.upload-section {
  margin-top: 28px;
  padding-top: 28px;
  border-top: 1px solid var(--line-soft);
}

:deep(.minimal-upload .el-upload-dragger) {
  background-color: var(--surface-secondary);
  border: 1.5px dashed var(--line-strong);
  border-radius: 16px;
  transition:
    border-color var(--duration-short) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard);
}

:deep(.minimal-upload .el-upload-dragger:hover) {
  border-color: rgba(0, 122, 255, 0.4);
  background-color: rgba(0, 122, 255, 0.03);
}

.upload-content {
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-icon {
  font-size: 32px;
  color: var(--text-faint);
  margin-bottom: 14px;
}

.upload-text {
  font-size: 15px;
  color: var(--text-soft);
  margin-bottom: 6px;
}

.upload-text .bold {
  font-weight: 600;
  color: var(--text-main);
}

.upload-hint {
  font-size: 13px;
  color: var(--text-faint);
}

.file-preview {
  margin-top: 16px;
  background: var(--surface-secondary);
  border-radius: 12px;
  border: 1px solid var(--line-soft);
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-main);
  font-weight: 500;
  min-width: 0;
}

.file-info span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submit-action-btn {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
  border-radius: 9999px !important;
  padding: 8px 20px !important;
  min-height: 44px !important;
  flex-shrink: 0;
}

.submit-action-btn:hover {
  background-color: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

/* ─── Job Status Card ─────────────────────────────────────── */
.job-status-card {
  margin-top: 20px;
  border-radius: 20px;
  padding: 24px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
}

.job-status-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-faint);
  margin-bottom: 16px;
}

.job-failure-box {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--danger-fill);
  border: 1px solid rgba(255, 59, 48, 0.18);
}

.job-log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.job-log-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-soft);
}

.job-log-time {
  min-width: 140px;
  color: var(--text-faint);
  flex-shrink: 0;
}

.job-log-text { flex: 1; }

/* ─── Result Card ─────────────────────────────────────────── */
.result-card {
  margin-top: 20px;
  border-radius: 20px;
  padding: 28px 32px;
  border: 1px solid;
}

.result-card.success {
  background: var(--surface);
  border-color: rgba(0, 122, 255, 0.28);
}

.result-card.error {
  background: var(--surface);
  border-color: var(--line-soft);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.result-icon { font-size: 22px; }

.success .result-icon { color: var(--accent); }
.error .result-icon { color: var(--text-soft); }

.result-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

.result-score {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 12px;
}

.result-note {
  margin-bottom: 14px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--warning-fill);
  color: #9a6700;
  font-size: 14px;
  line-height: 1.7;
}

.result-feedback {
  font-size: 15px;
  line-height: 1.6;
  margin: 0 0 20px;
  color: var(--text-soft);
}

.issues-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}

.issue-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  background: var(--apple-fill);
  border-radius: 9999px;
  font-size: 13px;
  color: var(--text-soft);
}

/* ─── Step Results ─────────────────────────────────────────── */
.step-result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.step-result-item,
.detail-box {
  background: var(--surface-strong);
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  padding: 16px 20px;
}

.step-results-box {
  padding: 18px 20px 16px;
}

.step-results-box .detail-title {
  margin-bottom: 14px;
}

.step-results-box .step-result-item {
  background: var(--surface-secondary);
}

.step-results-box .step-result-item + .step-result-item {
  margin-top: 10px;
}

.step-result-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.step-result-title,
.detail-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.5;
}

.step-result-title {
  max-width: calc(100% - 80px);
}

.step-result-status {
  flex-shrink: 0;
  min-height: 22px;
  padding: 2px 10px;
  border-radius: 9999px;
  background: rgba(120, 120, 128, 0.1);
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

.step-result-meta {
  display: block;
  font-size: 12px;
  margin-bottom: 8px;
  color: var(--text-faint);
  line-height: 1.5;
}

.step-result-item .detail-text {
  line-height: 1.8;
}

/* ─── Detail Dialog Content ───────────────────────────────── */
.detail-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

.detail-text {
  color: var(--text-soft);
  font-size: 14px;
  line-height: 1.7;
}

.video {
  width: 100%;
  max-height: 360px;
  background: #000;
  border-radius: 16px;
  display: block;
}

/* ─── Action Buttons ─────────────────────────────────────── */
.result-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.action-btn-primary {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
  border-radius: 9999px !important;
  min-height: 44px !important;
}

.action-btn-primary:hover {
  background-color: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

.action-btn-secondary {
  border-radius: 9999px !important;
  border-color: var(--line-soft) !important;
  color: var(--text-main) !important;
  background: var(--apple-fill) !important;
  min-height: 44px !important;
}

.action-btn-secondary:hover {
  background: rgba(120, 120, 128, 0.18) !important;
  border-color: var(--line-strong) !important;
}

/* ─── Dialog Overrides ─────────────────────────────────────── */
:deep(.el-dialog) {
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--line-soft);
  background: var(--surface-strong);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

:deep(.el-dialog__header) {
  padding: 22px 24px 16px;
  margin-right: 0;
  border-bottom: 1px solid var(--line-soft);
}

:deep(.el-dialog__title) {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

:deep(.el-dialog__body) { padding: 20px 24px; }
:deep(.el-dialog__footer) { padding: 0 24px 22px; }

/* ─── Dark Mode ─────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  .task-card,
  .step-container,
  .job-status-card,
  .result-card,
  .table-card {
    background: var(--surface);
  }
}

/* ─── Reduced Motion ─────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .logout-btn,
  .task-card,
  .back-btn,
  .segment,
  .progress-fill,
  :deep(.minimal-upload .el-upload-dragger) {
    transition: none;
  }
}

/* ─── Responsive ─────────────────────────────────────────── */
@media (max-width: 768px) {
  .main-content { padding: 20px 16px; }

  .top-nav {
    padding: 0 16px;
    height: auto;
    min-height: var(--toolbar-height);
  }

  .header-titles { flex-direction: column; align-items: flex-start; gap: 8px; }
  .header-titles h2 { font-size: 26px; }
  .grid-container { grid-template-columns: 1fr; }
  .result-actions { flex-direction: column; }
  .file-preview { flex-direction: column; align-items: flex-start; }
  .step-result-top { flex-direction: column; }

  .segment { padding: 8px 18px; font-size: 14px; }
}
</style>
