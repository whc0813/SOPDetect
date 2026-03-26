<template>
  <el-container class="user-layout">
    <el-header class="top-nav">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>视觉巡检</span>
      </div>
      <div class="nav-right">
        <div class="user-info">
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          <span class="username">{{ currentUserName }}</span>
        </div>
        <el-button text class="logout-btn" @click="handleLogout">
          退出登录
        </el-button>
      </div>
    </el-header>

    <el-main class="main-content">
      <div class="content-wrapper">
        <div class="user-tabs" v-if="!currentSop">
          <el-radio-group v-model="activeTab" class="minimal-radio-group">
            <el-radio-button label="tasks">待执行任务</el-radio-button>
            <el-radio-button label="jobs">评测任务</el-radio-button>
            <el-radio-button label="history">历史记录</el-radio-button>
          </el-radio-group>
        </div>

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

          <el-empty v-if="sopList.length === 0" description="暂无可用流程，请联系管理员创建" class="minimal-empty" />
        </div>

        <div v-if="!currentSop && activeTab === 'jobs'" class="view-transition">
          <div class="page-header">
            <h2>评测任务</h2>
            <p class="subtitle">查看排队、处理中、失败和已完成的评测任务状态</p>
          </div>

          <div class="table-card">
            <el-table :data="jobList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无评测任务">
              <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
              <el-table-column prop="createdAt" label="提交时间" width="180" />
              <el-table-column label="状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getJobStatusTagType(row.status)" effect="plain">{{ getJobStatusText(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="180">
                <template #default="{ row }">
                  <div class="job-progress-cell">
                    <span>{{ row.progressPercent }}%</span>
                    <span class="muted-text">{{ getJobStageText(row.stage) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center">
                <template #default="{ row }">
                  <el-button text @click="openJobDetail(row)">查看详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-if="!currentSop && activeTab === 'history'" class="view-transition">
          <div class="page-header">
            <h2>执行历史</h2>
            <p class="subtitle">查看你过去完成的流程记录和复核结果</p>
          </div>

          <div class="table-card">
            <el-table :data="historyList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无执行记录">
              <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
              <el-table-column prop="finishTime" label="完成时间" width="180" />
              <el-table-column label="AI 结论" width="100" align="center">
                <template #default="{ row }">
                  <el-tag :class="['minimal-status-tag', row.status === 'passed' ? 'is-passed' : 'is-failed']">
                    {{ getStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="人工复核" width="120" align="center">
                <template #default="{ row }">
                  <el-tag class="minimal-status-tag is-review">{{ getManualReviewText(row.manualReview?.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center">
                <template #default="{ row }">
                  <el-button text @click="openHistoryDetail(row)">查看详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-else-if="currentSop" class="execution-view">
          <div class="execution-header">
            <el-button text @click="backToList" class="back-btn">
              <el-icon><ArrowLeft /></el-icon> 返回列表
            </el-button>
            <div class="header-titles">
              <h2>{{ currentSop.name }}</h2>
              <span class="scene-tag">{{ currentSop.scene }}</span>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-text">共 {{ currentSop.stepCount }} 个步骤</div>
            <el-progress :percentage="currentJob ? currentJob.progressPercent : (evaluationResult ? 100 : 45)" :show-text="false" color="#000000" class="minimal-progress" />
          </div>

          <div class="step-container">
            <div class="step-label">操作流程</div>

            <div v-for="step in currentSop.steps" :key="step.stepNo" class="step-item">
              <div class="step-index">{{ step.stepNo }}</div>
              <div class="step-main">
                <p class="step-desc">{{ step.description }}</p>
                <div class="step-sub">{{ step.referenceMode === 'text' ? '仅按文字规则校验，无示范视频' : (step.referenceSummary || '已生成该步骤的参考信息') }}</div>
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
              <el-tag :type="getJobStatusTagType(currentJob.status)" effect="plain">{{ getJobStageText(currentJob.stage) }}</el-tag>
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
    </el-main>

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
        <div class="detail-box" v-if="selectedHistoryRecord.detail.stepResults?.length">
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
  </el-container>
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
.user-layout {
  min-height: 100vh;
  background-color: #fafafa;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.top-nav {
  height: 64px;
  background-color: #ffffff;
  border-bottom: 1px solid #e5e5ea;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.brand {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.brand-logo {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #000000 0%, #434343 100%);
  border-radius: 8px;
  margin-right: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #ffffff;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.user-info {
  display: flex;
  align-items: center;
}

.username {
  margin-left: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

.logout-btn {
  color: #86868b;
  font-weight: 500;
}

.logout-btn:hover {
  color: #1d1d1f;
}

.main-content {
  padding: 40px 32px;
}

.content-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.user-tabs {
  margin-bottom: 32px;
  display: flex;
  justify-content: center;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.subtitle {
  font-size: 15px;
  color: #86868b;
  margin: 0;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.task-card {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 16px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.task-card:hover {
  border-color: #000000;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.task-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 16px 0;
}

.task-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #86868b;
}

.card-action {
  margin-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  padding-top: 16px;
  border-top: 1px solid #f5f5f7;
}

:deep(.minimal-radio-group) {
  background-color: #e5e5ea;
  padding: 4px;
  border-radius: 12px;
  display: inline-flex;
  --el-fill-color-blank: transparent;
  --el-border-color: transparent;
  --el-border-color-hover: transparent;
  --el-color-primary: #000000;
  --el-text-color-primary: #1d1d1f;
}

:deep(.minimal-radio-group .el-radio-button__inner) {
  border: none !important;
  background: transparent !important;
  background-color: transparent !important;
  color: #515154 !important;
  font-weight: 500;
  box-shadow: none !important;
  border-radius: 8px !important;
  padding: 8px 32px;
  font-size: 15px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

:deep(.minimal-radio-group .el-radio-button:hover .el-radio-button__inner) {
  color: #1d1d1f !important;
}

:deep(.minimal-radio-group .el-radio-button.is-active .el-radio-button__inner),
:deep(.minimal-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #000000 !important;
  background-color: #000000 !important;
  border-color: #000000 !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  font-weight: 600;
}

:deep(.minimal-radio-group .el-radio-button:first-child .el-radio-button__inner) {
  border-left: none;
}

:deep(.minimal-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner::before) {
  display: none !important;
}

.table-card {
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  padding: 8px;
  overflow: hidden;
}

:deep(.minimal-status-tag) {
  border-radius: 6px;
  padding: 0 12px;
  font-weight: 500;
  border: 1px solid;
}

:deep(.minimal-status-tag.is-passed) {
  background-color: #ffffff;
  color: #1d1d1f;
  border-color: #1d1d1f;
}

:deep(.minimal-status-tag.is-failed),
:deep(.minimal-status-tag.is-review) {
  background-color: #f5f5f7;
  color: #86868b;
  border-color: #e5e5ea;
}

:deep(.el-table) {
  --el-table-border-color: #f5f5f7;
  --el-table-header-bg-color: #fafafa;
  color: #1d1d1f;
}

:deep(.el-table th.el-table__cell) {
  font-weight: 500;
  font-size: 13px;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.el-table td.el-table__cell) {
  padding: 16px 0;
  font-size: 14px;
}

.execution-header {
  margin-bottom: 40px;
}

.back-btn {
  margin-bottom: 24px;
  padding: 0;
  color: #86868b;
  font-size: 14px;
}

.back-btn:hover {
  color: #1d1d1f;
}

.header-titles {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-titles h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
}

.scene-tag {
  background: #f5f5f7;
  color: #515154;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.progress-section {
  margin-bottom: 40px;
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

:deep(.minimal-progress .el-progress-bar__outer) {
  background-color: #e5e5ea;
  border-radius: 4px;
  height: 4px !important;
}

:deep(.minimal-progress .el-progress-bar__inner) {
  border-radius: 4px;
  transition: width 0.6s ease;
}

.step-container {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e5e5ea;
  padding: 32px;
  margin-bottom: 24px;
}

.step-label {
  font-size: 13px;
  font-weight: 600;
  color: #000000;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.step-item {
  display: flex;
  gap: 16px;
  margin-top: 18px;
}

.step-main {
  flex: 1;
}

.step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #000000;
  color: #ffffff;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-desc {
  font-size: 16px;
  line-height: 1.6;
  color: #1d1d1f;
  margin: 0;
}

.step-sub {
  font-size: 13px;
  color: #86868b;
  margin-top: 6px;
}

.upload-section {
  margin-top: 32px;
  padding-top: 32px;
  border-top: 1px solid #f5f5f7;
}

:deep(.minimal-upload .el-upload-dragger) {
  background-color: #fafafa;
  border: 1px dashed #d2d2d7;
  border-radius: 12px;
  transition: all 0.3s ease;
}

:deep(.minimal-upload .el-upload-dragger:hover) {
  border-color: #000000;
  background-color: #f5f5f7;
}

.upload-content {
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-icon {
  font-size: 32px;
  color: #86868b;
  margin-bottom: 16px;
}

.upload-text {
  font-size: 15px;
  color: #515154;
  margin-bottom: 8px;
}

.upload-text .bold {
  font-weight: 600;
  color: #1d1d1f;
}

.upload-hint {
  font-size: 13px;
  color: #86868b;
}

.file-preview {
  margin-top: 24px;
  background: #f5f5f7;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
}

.submit-action-btn {
  background-color: #000000;
  border-color: #000000;
  border-radius: 8px;
  padding: 8px 24px;
}

.submit-action-btn:hover {
  background-color: #333333;
  border-color: #333333;
}

.result-card {
  margin-top: 24px;
  border-radius: 16px;
  padding: 32px;
  border: 1px solid;
}

.job-status-card {
  margin-top: 24px;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #e5e5ea;
  background: #ffffff;
}

.job-status-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #86868b;
  margin-bottom: 16px;
}

.job-failure-box {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #fff4f4;
  border: 1px solid #f3d6d6;
}

.job-log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.job-log-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.6;
  color: #515154;
}

.job-log-time {
  min-width: 140px;
  color: #86868b;
}

.job-log-text {
  flex: 1;
}

.job-progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.muted-text {
  color: #86868b;
  font-size: 12px;
}

.result-card.success {
  background-color: #ffffff;
  border-color: #000000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.result-card.error {
  background-color: #fcfcfc;
  border-color: #e5e5ea;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.result-icon {
  font-size: 24px;
}

.success .result-icon {
  color: #1d1d1f;
}

.error .result-icon {
  color: #86868b;
}

.result-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.result-score {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
}

.result-note {
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 8px;
  background: #fff8e8;
  color: #9a6700;
  line-height: 1.7;
}

.result-feedback {
  font-size: 15px;
  line-height: 1.5;
  margin: 0 0 24px 0;
  color: #515154;
}

.issues-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.issue-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  background: #f5f5f7;
  border-radius: 20px;
  font-size: 13px;
  color: #515154;
}

.step-result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.step-result-item,
.detail-box {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 12px;
  padding: 16px;
}

.step-result-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 6px;
}

.step-result-title,
.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.step-result-status,
.step-result-meta {
  font-size: 13px;
  color: #86868b;
}

.detail-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.detail-text {
  color: #515154;
  line-height: 1.7;
}

.video {
  width: 100%;
  max-height: 360px;
  background: #000;
  border-radius: 18px;
}

.result-actions,
.form-row {
  display: flex;
  gap: 12px;
}

.action-btn-primary {
  background-color: #000000;
  border-color: #000000;
  border-radius: 8px;
}

.action-btn-primary:hover {
  background-color: #333333;
  border-color: #333333;
}

.action-btn-secondary {
  border-radius: 8px;
  border-color: #d2d2d7;
  color: #1d1d1f;
}

.action-btn-secondary:hover {
  border-color: #86868b;
  color: #000000;
  background-color: transparent;
}

.grow {
  flex: 1;
}

:deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e5e5ea;
}

:deep(.el-dialog__header) {
  padding: 24px 24px 16px;
  margin-right: 0;
  border-bottom: 1px solid #e5e5ea;
}

:deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 0 24px 24px;
}

:deep(.el-button) {
  border-radius: 8px;
  font-weight: 500;
}

:deep(.el-button--primary) {
  background: #000000;
  border-color: #000000;
}

:deep(.el-button--primary:hover) {
  background: #333333;
  border-color: #333333;
}

@media (max-width: 768px) {
  .main-content {
    padding: 24px 16px;
  }

  .top-nav {
    padding: 16px;
    height: auto;
    align-items: flex-start;
  }

  .nav-right,
  .header-titles,
  .file-preview,
  .step-result-top,
  .result-actions,
  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .grid-container {
    grid-template-columns: 1fr;
  }
}
</style>
