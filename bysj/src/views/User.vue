<template>
  <div class="user-layout">
    <AppBlobs />

    <header class="top-nav">
      <div class="nav-left"></div>
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

        <!-- Tab content with slide transition -->
        <template v-if="!currentSop">
          <transition :name="tabTransition" mode="out-in">

            <!-- 待执行任务 -->
            <div v-if="activeTab === 'tasks'" key="tasks">
              <GlassCard class="hero-section">
                <p class="hero-greeting">{{ greetingText }}，</p>
                <h1 class="hero-name">{{ currentUserName }}</h1>
                <p class="hero-meta">
                  <span v-if="sopList.length > 0" class="hero-count">{{ sopList.length }} 个流程可执行</span>
                  <span v-else class="hero-count">暂无待执行流程</span>
                </p>
              </GlassCard>

              <div class="section-label">可用任务</div>

              <GroupedList :data="sopList">
                <template #item="{ row }">
                  <div class="task-item" @click="startSop(row)">
                    <div class="task-item-info">
                      <h3 class="task-item-name">{{ row.name }}</h3>
                      <div class="task-item-meta">
                        <span class="meta-item"><el-icon><Location /></el-icon> {{ row.scene }}</span>
                        <span class="meta-item"><el-icon><List /></el-icon> {{ row.stepCount }} 步</span>
                      </div>
                    </div>
                    <div class="task-item-action">
                      <span>开始执行</span>
                      <el-icon><ArrowRight /></el-icon>
                    </div>
                  </div>
                </template>
                <template #empty>
                  <div class="empty-state">
                    <svg class="empty-icon" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <rect x="8" y="6" width="32" height="36" rx="4" stroke="currentColor" stroke-width="2"/>
                      <line x1="14" y1="16" x2="34" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                      <line x1="14" y1="22" x2="28" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                      <line x1="14" y1="28" x2="24" y2="28" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                    <p class="empty-title">暂无可用流程</p>
                    <p class="empty-desc">请联系管理员创建标准操作流程</p>
                  </div>
                </template>
              </GroupedList>
            </div>

            <!-- 评测任务 (list view) -->
            <div v-else-if="activeTab === 'jobs'" key="jobs">
              <GlassCard class="page-header">
                <h2>评测任务</h2>
                <p class="subtitle">查看排队、处理中、失败和已完成的评测任务状态</p>
              </GlassCard>

              <GroupedList :data="jobList" empty-text="暂无评测任务">
                <template #item="{ row }">
                  <div class="list-item" @click="openJobDetail(row)">
                    <div class="list-item-main">
                      <span class="list-item-name">{{ row.taskName }}</span>
                      <StatusBadge :type="getJobStatusTagType(row.status)">
                        {{ getJobStatusText(row.status) }}
                      </StatusBadge>
                    </div>
                    <div class="list-item-sub">
                      <span class="list-item-time">{{ row.createdAt }}</span>
                      <span class="list-item-detail">{{ row.progressPercent }}% · {{ getJobStageText(row.stage) }}</span>
                    </div>
                  </div>
                </template>
              </GroupedList>
            </div>

            <!-- 历史记录 (list view) -->
            <div v-else key="history">
              <GlassCard class="page-header">
                <h2>执行历史</h2>
                <p class="subtitle">查看你过去完成的流程记录和复核结果</p>
              </GlassCard>

              <GroupedList :data="historyList" empty-text="暂无执行记录">
                <template #item="{ row }">
                  <div class="list-item history-item" @click="openHistoryDetail(row)">
                    <div class="history-item-main">
                      <span class="list-item-name">{{ row.taskName }}</span>
                      <span class="list-item-time">{{ row.finishTime }}</span>
                      <span v-if="row.detail?.tokenUsage" class="history-item-token">
                        Token：{{ formatTokenUsage(row.detail.tokenUsage) }}
                      </span>
                    </div>
                    <div class="history-item-badges">
                      <StatusBadge :type="row.status === 'passed' ? 'success' : 'danger'">
                        {{ getStatusText(row.status) }}
                      </StatusBadge>
                      <StatusBadge type="default">
                        {{ getManualReviewText(row.manualReview?.status) }}
                      </StatusBadge>
                    </div>
                    <div class="history-item-action">
                      <span class="history-item-link">查看详情</span>
                      <el-icon><ArrowRight /></el-icon>
                    </div>
                  </div>
                </template>
              </GroupedList>
            </div>

          </transition>
        </template>

        <!-- 执行视图 -->
        <div v-else class="execution-view">
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

          <GlassCard class="progress-card">
            <div class="progress-card-top">
              <div class="progress-copy">
                <div class="progress-label">执行进度</div>
                <div class="progress-headline">{{ progressState.title }}</div>
                <div class="progress-caption">{{ progressState.description }}</div>
              </div>
              <div class="progress-side">
                <StatusBadge :type="progressState.type">{{ progressState.label }}</StatusBadge>
                <div class="progress-value">{{ executionProgress }}%</div>
              </div>
            </div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :style="{ width: `${executionProgress}%` }"
              ></div>
            </div>
            <div class="progress-meta">
              <span>{{ progressState.meta }}</span>
              <span>{{ executionProgress }}%</span>
            </div>
          </GlassCard>

          <GlassCard class="step-container">
            <div class="step-layout">
              <div class="step-flow">
                <SectionHeader
                  title="操作流程"
                  subtitle="根据下方步骤完成本次 SOP 操作，并上传完整录制视频"
                />
                <div class="step-list">
                  <div v-for="step in currentSop.steps" :key="step.stepNo" class="step-card">
                    <div class="step-badge">{{ step.stepNo }}</div>
                    <div class="step-card-content">
                      <p class="step-desc">{{ step.description }}</p>
                      <div class="step-sub">
                        {{ step.referenceMode === 'text' ? '仅按文字规则校验，无示范视频' : (step.referenceSummary || '已生成该步骤的参考信息') }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="upload-panel" v-if="!currentJob || currentJob.status === 'failed'">
                <div class="upload-section">
                  <SectionHeader
                    title="上传操作视频"
                    subtitle="选择完整录制视频后提交评测，支持重新选择文件。"
                  >
                    <span class="upload-section-tip">{{ currentVideo ? '已选择视频' : '等待上传' }}</span>
                  </SectionHeader>

                  <div class="upload-checklist">
                    <div class="upload-check-item" :class="{ done: !!currentVideo }">1. 选择本次 SOP 的完整操作视频</div>
                    <div class="upload-check-item" :class="{ done: !!currentVideo }">2. 确认画面清晰、步骤完整</div>
                    <div class="upload-check-item" :class="{ done: !!currentVideo }">3. 提交后开始评测并刷新进度</div>
                  </div>

                  <el-upload
                    class="apple-upload"
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
                      <div class="upload-hint-text">支持 MP4 / MOV / AVI 格式视频</div>
                    </div>
                  </el-upload>

                  <div v-if="currentVideo" class="file-preview">
                    <div class="file-info">
                      <el-icon><VideoPlay /></el-icon>
                      <span>{{ currentVideo.name }}</span>
                    </div>
                    <div class="file-actions">
                      <span class="file-status">已选择完成，提交后开始评测</span>
                      <el-button type="primary" class="submit-action-btn" @click="submitVideo" :loading="isEvaluating">
                        提交评测任务
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>

          <GlassCard v-if="currentJob" class="job-status-card">
            <div class="result-header">
              <el-icon class="result-icon" v-if="currentJob.status === 'succeeded'"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>任务状态：{{ getJobStatusText(currentJob.status) }}</h3>
            </div>
            <div class="job-status-meta">
              <StatusBadge :type="getJobStatusTagType(currentJob.status)">
                {{ getJobStageText(currentJob.stage) }}
              </StatusBadge>
              <span class="job-meta-pill">任务编号：{{ currentJob.id }}</span>
              <span class="job-meta-pill">进度：{{ currentJob.progressPercent }}%</span>
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
          </GlassCard>

          <GlassCard class="result-card" v-if="evaluationResult" :class="evaluationResult.passed ? 'success' : 'error'">
            <div class="result-header">
              <el-icon class="result-icon" v-if="evaluationResult.passed"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>{{ evaluationResult.passed ? '验证通过' : '验证未通过' }}</h3>
            </div>
            <div class="result-score">综合得分：{{ formatScore(evaluationResult.score, '-') }}</div>
            <div v-if="currentSopHasNoDemoVideo" class="result-note">
              当前 SOP 没有上传示范视频，本次仅依据步骤文字和你上传的视频进行判断。
            </div>
            <div v-if="evaluationResult.tokenUsage" class="result-token">
              Token：{{ formatTokenUsage(evaluationResult.tokenUsage) }}
            </div>
            <p class="result-feedback">{{ evaluationResult.feedback }}</p>

            <div v-if="evaluationResult.issues?.length" class="issues-list">
              <span v-for="(issue, index) in evaluationResult.issues" :key="index" class="issue-chip">{{ issue }}</span>
            </div>

            <!-- Timeline visualization (Phase 5) -->
            <EvalTimeline
              v-if="evaluationResult.stepResults?.length"
              :step-results="evaluationResult.stepResults"
              :video-duration-sec="evaluationResult.overviewPreview?.durationSec || 0"
            />

            <!-- Score radar chart (Phase 5) -->
            <div class="viz-row" v-if="evaluationResult.stepResults?.length >= 3">
              <ScoreRadar :step-results="evaluationResult.stepResults" :size="220" />
            </div>

            <div v-if="evaluationResult.stepResults?.length" class="step-result-list">
              <div v-for="item in evaluationResult.stepResults" :key="item.stepNo" class="step-result-item">
                <div class="step-result-top">
                  <div class="step-result-title">步骤 {{ item.stepNo }}: {{ item.description }}</div>
                  <StatusBadge :type="item.includedInScore === false ? 'default' : (item.passed ? 'success' : 'danger')">{{ item.includedInScore === false ? '未计分' : getStepResultText(item.passed) }}</StatusBadge>
                </div>
                <div class="step-result-meta">得分 {{ formatScore(item.score, '-') }} / 置信度 {{ formatConfidence(item.confidence) }}</div>
                <div class="step-result-meta">类型 {{ formatStepType(item.stepType) }} / 权重 {{ formatStepWeight(item.stepWeight) }}</div>
                <div class="step-result-meta">适用 {{ item.applicable === false ? '否' : '是' }} / 前置依赖 {{ item.prerequisiteViolated ? '违反' : '正常' }}</div>
                <div class="step-result-meta">检测区间 {{ formatDetectedRange(item.detectedStartSec, item.detectedEndSec) }}</div>
                <div class="detail-text">{{ item.evidence }}</div>
              </div>
            </div>

            <div class="result-actions">
              <el-button v-if="currentJob?.resultRecordId" type="primary" class="action-btn-primary" @click="openHistoryDetailById(currentJob.resultRecordId)">查看评测详情</el-button>
              <el-button v-if="currentJob?.status === 'failed'" class="action-btn-secondary" @click="retryCurrentJob" :loading="isRetryingJob">重试任务</el-button>
              <el-button v-if="currentJob?.status === 'failed'" class="action-btn-secondary" @click="retrySop">重新上传</el-button>
            </div>
          </GlassCard>
        </div>

      </div>
    </main>

    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px" class="apple-dialog">
      <div v-if="selectedHistoryRecord" class="detail-wrap">
        <div class="summary">{{ selectedHistoryRecord.taskName }} / {{ selectedHistoryRecord.finishTime }}</div>
        <div
          v-if="selectedHistoryRecord.detail.evaluationProcess?.stages?.length"
          class="detail-actions"
        >
          <el-button class="action-btn-secondary" @click="toggleHistoryProcess">
            {{ historyProcessVisible ? '收起评测过程' : '评测过程' }}
          </el-button>
        </div>
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
        <div
          v-if="historyProcessVisible && selectedHistoryRecord.detail.evaluationProcess?.stages?.length"
          class="detail-box process-box"
        >
          <div class="detail-title">评测过程</div>
          <el-collapse v-model="historyProcessActiveNames" class="process-collapse">
            <el-collapse-item
              v-for="stage in selectedHistoryRecord.detail.evaluationProcess.stages"
              :key="stage.key"
              :name="stage.key"
            >
              <template #title>
                <div class="process-stage-header">
                  <div class="process-stage-title">{{ stage.label }}</div>
                  <div class="process-stage-header-meta">
                    <span v-if="stage.tokenUsage" class="process-stage-token">
                      Token：{{ formatTokenUsage(stage.tokenUsage) }}
                    </span>
                    <span v-if="stage.media.images.length" class="process-stage-chip">
                      图片 {{ stage.media.images.length }}
                    </span>
                    <span v-if="stage.media.videos.length" class="process-stage-chip">
                      视频 {{ stage.media.videos.length }}
                    </span>
                  </div>
                </div>
              </template>

              <div class="process-stage-body">
                <div
                  v-if="stage.media.images.length || stage.media.videos.length"
                  class="process-block"
                >
                  <div class="process-block-title">发送给 AI 的媒体</div>
                  <div v-if="stage.media.images.length" class="process-image-grid">
                    <div
                      v-for="(image, index) in stage.media.images"
                      :key="`${stage.key}-image-${index}`"
                      class="process-image-card"
                    >
                      <img
                        v-if="canRenderProcessImage(image.url)"
                        :src="image.url"
                        :alt="`${stage.label} 图片 ${index + 1}`"
                        class="process-image"
                      />
                      <div v-else class="process-media-placeholder">
                        图片 {{ index + 1 }}
                        <span>历史记录未保留原图，仅保留发送痕迹</span>
                      </div>
                    </div>
                  </div>
                  <div v-if="stage.media.videos.length" class="process-video-list">
                    <div
                      v-for="(_video, index) in stage.media.videos"
                      :key="`${stage.key}-video-${index}`"
                      class="process-video-item"
                    >
                      <span class="process-stage-chip">{{ _video.label || `视频 ${index + 1}` }}</span>
                      <span class="detail-text">
                        该阶段向 AI 发送了整段用户视频，详情视频可在上方“上传视频”中查看。
                      </span>
                    </div>
                  </div>
                </div>

                <div v-if="stage.promptText" class="process-block">
                  <div class="process-block-title">提示词</div>
                  <pre class="process-text">{{ stage.promptText }}</pre>
                </div>

                <div v-if="stage.responseText" class="process-block">
                  <div class="process-block-title">AI 回复</div>
                  <pre class="process-text process-response">{{ stage.responseText }}</pre>
                </div>

                <div v-if="!stage.promptText && !stage.responseText" class="detail-text">
                  该阶段未记录可展示的过程内容。
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div class="detail-box step-results-box" v-if="selectedHistoryRecord.detail.stepResults?.length">
          <div class="detail-title">步骤结果</div>
          <EvalTimeline
            :step-results="selectedHistoryRecord.detail.stepResults"
            :video-duration-sec="selectedHistoryRecord.detail.overviewPreview?.durationSec || 0"
          />
          <div v-if="selectedHistoryRecord.detail.stepResults.length >= 3" class="viz-row">
            <ScoreRadar :step-results="selectedHistoryRecord.detail.stepResults" :size="200" />
          </div>
          <div v-for="item in selectedHistoryRecord.detail.stepResults" :key="item.stepNo" class="step-result-item">
            <div class="step-result-top">
              <div class="step-result-title">步骤 {{ item.stepNo }}: {{ item.description }}</div>
              <StatusBadge :type="item.includedInScore === false ? 'default' : (item.passed ? 'success' : 'danger')">{{ item.includedInScore === false ? '未计分' : getStepResultText(item.passed) }}</StatusBadge>
            </div>
            <div class="step-result-meta">得分 {{ formatScore(item.score, '-') }}</div>
            <div class="step-result-meta">类型 {{ formatStepType(item.stepType) }} / 权重 {{ formatStepWeight(item.stepWeight) }}</div>
            <div class="step-result-meta">适用 {{ item.applicable === false ? '否' : '是' }} / 前置依赖 {{ item.prerequisiteViolated ? '违反' : '正常' }}</div>
            <div class="step-result-meta">检测区间 {{ formatDetectedRange(item.detectedStartSec, item.detectedEndSec) }}</div>
            <div class="detail-text">{{ item.evidence }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
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
  isAuthSessionError,
  listEvaluationJobs,
  listHistory,
  listSops,
  logout,
  retryEvaluationJob,
  fetchAuthorizedMediaBlobUrl
} from '../api/client'
import AppBlobs from '../components/AppBlobs.vue'
import GroupedList from '../components/GroupedList.vue'
import StatusBadge from '../components/StatusBadge.vue'
import GlassCard from '../components/GlassCard.vue'
import SectionHeader from '../components/SectionHeader.vue'
import EvalTimeline from '../components/EvalTimeline.vue'
import ScoreRadar from '../components/ScoreRadar.vue'
import {
  buildEvaluationResultFromHistory,
  formatTokenUsage,
  normalizeHistory,
} from '../utils/user-history.mjs'

const router = useRouter()
const sopList = ref([])
const jobList = ref([])
const historyList = ref([])
const activeTab = ref('tasks')
const tabTransition = ref('tab-slide-left')
const tabOrder = ['tasks', 'jobs', 'history']
watch(activeTab, (newTab, oldTab) => {
  tabTransition.value = tabOrder.indexOf(newTab) > tabOrder.indexOf(oldTab) ? 'tab-slide-left' : 'tab-slide-right'
})
const currentSop = ref(null)
const currentVideo = ref(null)
const isEvaluating = ref(false)
const isRetryingJob = ref(false)
const currentJob = ref(null)
const evaluationResult = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const selectedHistoryVideoUrl = ref('')
const historyProcessVisible = ref(false)
const historyProcessActiveNames = ref([])
const currentUser = ref(getCurrentUser())
let jobPollingTimer = null

watch(historyDetailVisible, (visible) => {
  if (!visible) {
    historyProcessVisible.value = false
    historyProcessActiveNames.value = []
  }
})

const currentUserName = computed(() => currentUser.value?.displayName || currentUser.value?.username || '用户')

const userInitials = computed(() => {
  const name = currentUser.value?.displayName || currentUser.value?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 11) return '早上好'
  if (hour >= 11 && hour < 14) return '中午好'
  if (hour >= 14 && hour < 18) return '下午好'
  return '晚上好'
})

const executionProgress = computed(() => {
  if (currentJob.value) return Number(currentJob.value.progressPercent || 0)
  return evaluationResult.value ? 100 : 0
})

const progressState = computed(() => {
  if (evaluationResult.value) {
    return {
      type: evaluationResult.value.passed ? 'success' : 'danger',
      label: evaluationResult.value.passed ? '已完成' : '已结束',
      title: evaluationResult.value.passed ? '评测已完成' : '评测已结束',
      description: '可以查看评测结果、问题明细和步骤得分。',
      meta: '结果已生成'
    }
  }

  if (currentJob.value) {
    const stage = currentJob.value.stage
    const stepCount = currentSop.value?.stepCount || 3
    const timeHint = getEstimatedTimeHint(stage, stepCount)
    return {
      type: currentJob.value.status === 'failed' ? 'danger' : 'info',
      label: currentJob.value.status === 'failed' ? '异常' : '进行中',
      title: currentJob.value.status === 'failed' ? '评测任务异常中断' : '评测任务处理中',
      description: currentJob.value.status === 'failed'
        ? '请检查失败原因，必要时重新上传视频后再试。'
        : '系统正在分析上传视频，进度会随任务状态自动刷新。',
      meta: timeHint ? `${getJobStageText(stage)} · ${timeHint}` : getJobStageText(stage),
    }
  }

  if (currentVideo.value) {
    return {
      type: 'warning',
      label: '待提交',
      title: '视频已就绪，等待提交',
      description: '确认文件无误后点击提交评测任务，系统才会开始计算进度。',
      meta: '尚未开始评测'
    }
  }

  return {
    type: 'default',
    label: '未开始',
    title: '等待上传操作视频',
    description: `共 ${currentSop.value?.stepCount || 0} 个步骤，上传并提交后才会开始评测。`,
    meta: '尚未开始评测'
  }
})

function showErrorMessage(error, fallback) {
  if (isAuthSessionError(error)) return
  ElMessage.error(error.message || fallback)
}

const currentSopHasNoDemoVideo = computed(() => {
  const steps = currentSop.value?.steps || []
  return steps.length > 0 && steps.every((step) => step.referenceMode === 'text')
})

function normalizeJob(record = {}) {
  return {
    ...record,
    progressPercent: Number(record.progressPercent || 0),
    logs: Array.isArray(record.logs) ? record.logs : [],
    uploadedVideo: record.uploadedVideo || null
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

function getEvaluationProcessStages(record = selectedHistoryRecord.value) {
  return Array.isArray(record?.detail?.evaluationProcess?.stages)
    ? record.detail.evaluationProcess.stages
    : []
}

function getEvaluationProcessPanelNames(record = selectedHistoryRecord.value) {
  return getEvaluationProcessStages(record).map((stage) => stage.key)
}

function toggleHistoryProcess() {
  historyProcessVisible.value = !historyProcessVisible.value
  if (historyProcessVisible.value) {
    historyProcessActiveNames.value = getEvaluationProcessPanelNames()
  }
}

function canRenderProcessImage(url) {
  return typeof url === 'string' && url.startsWith('data:image/') && !url.includes('<base64 omitted>')
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
      showErrorMessage(error, '任务状态刷新失败')
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
    showErrorMessage(error, '提交评测任务失败')
  } finally {
    isEvaluating.value = false
  }
}

async function openHistoryDetailById(recordId) {
  if (!recordId) return
  try {
    selectedHistoryRecord.value = normalizeHistory((await getHistoryDetail(recordId)).data)
    historyProcessVisible.value = false
    historyProcessActiveNames.value = getEvaluationProcessPanelNames(selectedHistoryRecord.value)
    revokeSelectedHistoryVideoUrl()
    const mediaPath = selectedHistoryRecord.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      selectedHistoryVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    historyDetailVisible.value = true
  } catch (error) {
    showErrorMessage(error, '加载详情失败')
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
    showErrorMessage(error, '重试任务失败')
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

function formatStepType(stepType) {
  const mapping = {
    required: '必做',
    optional: '可选',
    conditional: '条件触发'
  }
  return mapping[stepType] || stepType || '-'
}

function formatStepWeight(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(1) : '1.0'
}

function formatDetectedRange(startSec, endSec) {
  const start = Number(startSec)
  const end = Number(endSec)
  if (!Number.isFinite(start) && !Number.isFinite(end)) return '-'
  const startText = Number.isFinite(start) ? `${start.toFixed(1)}s` : '-'
  const endText = Number.isFinite(end) ? `${end.toFixed(1)}s` : '-'
  return `${startText} ~ ${endText}`
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
    stage1_segmentation: '分析视频时序结构',
    stage2_step_eval: '逐步精细评估中',
    stage3_validation: '全局顺序校验',
    parsing_result: '解析评测结果',
    saving_result: '保存评测结果',
    done: '任务已完成',
    error: '任务处理失败',
  }
  return stageMap[stage] || '处理中'
}

function getEstimatedTimeHint(stage, stepCount) {
  if (stage === 'stage1_segmentation') return '预计 30–60 秒'
  if (stage === 'stage2_step_eval') {
    const remaining = Math.max(1, stepCount || 3)
    return `预计 ${remaining * 15}–${remaining * 25} 秒`
  }
  if (stage === 'stage3_validation') return '预计 10–20 秒'
  return ''
}

onMounted(() => {
  Promise.all([loadSops(), loadJobs(), loadHistory()]).catch((error) => {
    showErrorMessage(error, '初始化失败')
  })
})

onUnmounted(() => {
  stopJobPolling()
  revokeSelectedHistoryVideoUrl()
})
</script>

<style scoped>
/* ── Layout ──────────────────────────────────────────────── */

.user-layout {
  position: relative;
  min-height: 100vh;
  background-color: var(--bg-base);
  font-family: var(--font-family);
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

/* ── Top Nav ─────────────────────────────────────────────── */

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--toolbar-height);
  background: var(--material-regular);
  border-bottom: 1px solid var(--separator);
  backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 var(--sp-8);
}

.nav-left {
  display: flex;
  justify-content: flex-start;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}

.brand-logo {
  width: 32px;
  height: 32px;
  background: linear-gradient(150deg, var(--accent), var(--accent-deep));
  border-radius: var(--radius-sm);
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
  justify-content: flex-end;
  gap: var(--sp-5);
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
  min-height: var(--touch-target);
  padding: var(--sp-2) 14px;
  border-radius: 10px;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.logout-btn:hover {
  background: var(--fill-quaternary);
  color: var(--text-main);
}

.logout-btn:active {
  transform: scale(0.96);
}

/* ── Main Content ────────────────────────────────────────── */

.main-content {
  position: relative;
  z-index: 1;
  flex: 1;
  padding: var(--sp-8) var(--sp-8);
}

.content-wrapper {
  max-width: 1040px;
  margin: 0 auto;
}

/* ── Tab Bar ─────────────────────────────────────────────── */

.tab-bar {
  display: flex;
  justify-content: center;
  margin-bottom: var(--sp-8);
}

.segmented-control {
  display: inline-flex;
  padding: 3px;
  background: var(--apple-fill);
  border-radius: var(--radius-full);
}

.segment {
  padding: 9px var(--sp-7);
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: var(--fs-subheadline);
  font-weight: 500;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard),
    box-shadow var(--duration-short) var(--ease-standard);
}

.segment.active {
  background: var(--surface);
  color: var(--text-main);
  font-weight: 600;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.08), 0 0 0 0.5px rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .segment.active {
    background: var(--fill-secondary);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  }
}

.segment:hover:not(.active) {
  color: var(--text-main);
}

.segment:active {
  transform: scale(0.97);
}

/* ── Hero Section ────────────────────────────────────────── */

.hero-section {
  padding: var(--sp-8) var(--sp-7);
  margin-bottom: var(--sp-6);
}

.hero-greeting {
  font-size: var(--fs-headline);
  color: var(--text-soft);
  margin: 0 0 var(--sp-1);
  font-weight: 500;
}

.hero-name {
  font-size: var(--fs-large-title);
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--text-main);
  margin: 0 0 var(--sp-3);
  line-height: 1;
}

.hero-meta {
  margin: 0;
}

.hero-count {
  display: inline-block;
  font-size: 14px;
  color: var(--text-faint);
  background: var(--fill-quaternary);
  padding: var(--sp-1) var(--sp-3);
  border-radius: var(--radius-full);
  font-weight: 500;
}

.section-label {
  font-size: var(--fs-caption1);
  font-weight: 700;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin-bottom: 14px;
}

/* ── Page Header ─────────────────────────────────────────── */

.page-header {
  margin-bottom: var(--sp-7);
  padding: var(--sp-6) var(--sp-7);
}

.page-header h2 {
  font-size: var(--fs-large-title);
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 var(--sp-2);
  letter-spacing: -0.04em;
  line-height: 1.1;
}

.subtitle {
  font-size: var(--fs-subheadline);
  color: var(--text-soft);
  margin: 0;
}

/* ── Task Cards ──────────────────────────────────────────── */

/* ── Task List Items ─────────────────────────────────────── */

.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-4) var(--sp-5);
  cursor: pointer;
  transition: background var(--duration-micro);
}

.task-item:hover {
  background: var(--fill-quaternary);
}

.task-item:active {
  background: var(--fill-tertiary);
}

.task-item-info {
  flex: 1;
  min-width: 0;
}

.task-item-name {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--text-main);
  margin: 0 0 6px;
}

.task-item-meta {
  display: flex;
  gap: var(--sp-4);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-footnote);
  color: var(--text-soft);
}

.task-item-action {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--accent);
  flex-shrink: 0;
  margin-left: var(--sp-4);
}

/* ── List Items (Jobs / History) ─────────────────────────── */

.list-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--sp-4) var(--sp-5);
  cursor: pointer;
  transition: background var(--duration-micro);
}

.list-item:hover {
  background: var(--fill-quaternary);
}

.list-item:active {
  background: var(--fill-tertiary);
}

.list-item-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.list-item-name {
  font-size: var(--fs-body);
  font-weight: 600;
  color: var(--text-main);
  flex: 1;
  min-width: 0;
}

.list-item-badges {
  display: flex;
  gap: var(--sp-2);
  flex-shrink: 0;
}

.list-item-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.list-item-time {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
}

.list-item-detail {
  font-size: var(--fs-footnote);
  color: var(--accent);
  font-weight: 500;
}

.history-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: var(--sp-5);
}

.history-item-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item-token {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  line-height: 1.6;
}

.history-item-badges {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}

.history-item-action {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-width: 88px;
  color: var(--accent);
}

.history-item-link {
  font-size: var(--fs-footnote);
  font-weight: 600;
}

/* ── Tab Slide Transitions ───────────────────────────────── */

.tab-slide-left-enter-active,
.tab-slide-left-leave-active,
.tab-slide-right-enter-active,
.tab-slide-right-leave-active {
  transition:
    transform var(--duration-medium) var(--ease-standard),
    opacity var(--duration-medium) var(--ease-standard);
}

.tab-slide-left-enter-from {
  transform: translateX(30px);
  opacity: 0;
}

.tab-slide-left-leave-to {
  transform: translateX(-30px);
  opacity: 0;
}

.tab-slide-right-enter-from {
  transform: translateX(-30px);
  opacity: 0;
}

.tab-slide-right-leave-to {
  transform: translateX(30px);
  opacity: 0;
}

.progress-pct {
  font-size: 14px;
  font-weight: 500;
}

.muted-text {
  font-size: var(--fs-caption1);
  color: var(--text-faint);
}

/* ── Execution View ──────────────────────────────────────── */

.execution-header {
  margin-bottom: var(--sp-8);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: none;
  color: var(--accent);
  font-size: var(--fs-subheadline);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  min-height: var(--touch-target);
  padding: var(--sp-2) 0;
  margin-bottom: var(--sp-4);
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
  font-size: var(--fs-large-title);
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.scene-tag {
  background: var(--fill-quaternary);
  color: var(--text-soft);
  padding: 5px var(--sp-3);
  border-radius: var(--radius-full);
  font-size: var(--fs-footnote);
  font-weight: 500;
}

/* ── Progress Bar ────────────────────────────────────────── */

.progress-card {
  margin-bottom: var(--sp-8);
  padding: var(--sp-6) var(--sp-7);
}

.progress-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  margin-bottom: var(--sp-4);
}

.progress-copy {
  min-width: 0;
  flex: 1;
}

.progress-label {
  font-size: var(--fs-caption1);
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 10px;
}

.progress-card > .progress-label {
  display: none;
}

.progress-headline {
  font-size: clamp(24px, 3vw, 30px);
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-main);
  margin-bottom: var(--sp-2);
}

.progress-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--sp-3);
  flex-shrink: 0;
}

.progress-value {
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.04em;
}

.progress-caption {
  font-size: var(--fs-footnote);
  line-height: 1.7;
  color: var(--text-soft);
  margin-bottom: var(--sp-4);
}

.progress-track {
  height: 5px;
  background: var(--fill-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--sp-3);
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: var(--radius-full);
  transition: width var(--duration-medium) var(--ease-standard);
}

.progress-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  font-size: var(--fs-footnote);
  color: var(--text-soft);
}

/* ── Step Container ──────────────────────────────────────── */

.step-container {
  background: var(--material-chrome);
  backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  border-radius: var(--radius-xl);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05), 0 8px 32px rgba(0, 0, 0, 0.04);
  padding: var(--sp-7) var(--sp-8);
  margin-bottom: var(--sp-5);
}

.step-container > .step-section-label {
  display: none;
}

.step-container :deep(.section-header) {
  align-items: flex-start;
  margin-bottom: var(--sp-7);
}

.step-container :deep(.section-header-text) {
  gap: var(--sp-2);
  max-width: 56ch;
}

.step-container :deep(.section-header-subtitle) {
  line-height: 1.75;
}

.step-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--sp-6);
  align-items: start;
}

.step-flow {
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: var(--sp-6);
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.58) 0%, rgba(255, 255, 255, 0.36) 100%);
  border: 1px solid rgba(255, 255, 255, 0.56);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}

.step-flow :deep(.section-header),
.upload-section :deep(.section-header) {
  align-items: flex-start;
  margin-bottom: var(--sp-6);
}

.step-flow :deep(.section-header-text),
.upload-section :deep(.section-header-text) {
  gap: var(--sp-2);
  max-width: 34rem;
}

.step-flow :deep(.section-header-subtitle),
.upload-section :deep(.section-header-subtitle) {
  line-height: 1.7;
}

.upload-section :deep(.section-header-trailing) {
  align-self: flex-start;
}

@media (prefers-color-scheme: dark) {
  .step-flow {
    background: rgba(44, 44, 46, 0.32);
    border-color: rgba(84, 84, 88, 0.28);
  }
}

@media (prefers-color-scheme: dark) {
  .step-container {
    border-color: rgba(84, 84, 88, 0.4);
  }
}

.step-section-label {
  font-size: var(--fs-caption1);
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--sp-4);
}

/* ── Timeline ────────────────────────────────────────────── */

.step-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}

.step-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: var(--sp-4);
  padding: var(--sp-5);
  border-radius: var(--radius-lg);
  background: var(--surface-secondary);
  border: 1px solid var(--line-soft);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.step-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 30px;
  padding: 0 10px;
  border-radius: 10px;
  background: var(--fill-quaternary);
  border: 1px solid var(--line-soft);
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-mono);
  line-height: 1;
}

.step-card-content {
  min-width: 0;
}

.step-desc {
  font-size: var(--fs-callout);
  line-height: 1.6;
  color: var(--text-main);
  margin: 0;
  font-weight: 650;
}

.step-sub {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  margin-top: var(--sp-2);
  line-height: 1.5;
}

/* ── Upload Section ──────────────────────────────────────── */

.upload-panel {
  min-width: 0;
  display: block;
}

.upload-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  padding: var(--sp-6);
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.58) 0%, rgba(255, 255, 255, 0.36) 100%);
  border: 1px solid rgba(255, 255, 255, 0.56);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

@media (prefers-color-scheme: dark) {
  .upload-section {
    background: rgba(44, 44, 46, 0.42);
    border-color: rgba(84, 84, 88, 0.35);
    box-shadow: none;
  }
}

.upload-section-tip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: var(--radius-full);
  background: var(--fill-quaternary);
  color: var(--text-soft);
  font-size: var(--fs-caption1);
  font-weight: 600;
  white-space: nowrap;
}

.upload-checklist {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.upload-check-item {
  position: relative;
  padding-left: 18px;
  font-size: var(--fs-footnote);
  line-height: 1.5;
  color: var(--text-soft);
}

.upload-check-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--fill-secondary);
}

.upload-check-item.done::before {
  background: var(--system-green);
}

:deep(.apple-upload .el-upload-dragger) {
  background-color: var(--surface-secondary);
  border: 1.5px dashed var(--line-strong);
  border-radius: var(--radius-lg);
  transition:
    border-color var(--duration-short) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard);
}

:deep(.apple-upload .el-upload-dragger:hover) {
  border-color: rgba(0, 122, 255, 0.4);
  background-color: var(--info-fill);
}

.upload-content {
  min-height: 164px;
  padding: var(--sp-6) var(--sp-5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-icon {
  font-size: 32px;
  color: var(--text-faint);
  margin-bottom: 14px;
}

.upload-text {
  font-size: var(--fs-subheadline);
  color: var(--text-soft);
  margin-bottom: 6px;
}

.upload-text .bold {
  font-weight: 600;
  color: var(--text-main);
}

.upload-hint-text {
  font-size: var(--fs-footnote);
  color: var(--text-faint);
}

.file-preview {
  background: var(--surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--line-soft);
  padding: 14px var(--sp-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-3);
}

.file-actions {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-left: auto;
}

.file-status {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  white-space: nowrap;
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
  border-radius: var(--radius-full) !important;
  padding: var(--sp-2) var(--sp-5) !important;
  min-height: var(--touch-target) !important;
  flex-shrink: 0;
}

.submit-action-btn:hover {
  background-color: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

/* ── Job Status Card ─────────────────────────────────────── */

.job-status-card {
  margin-top: var(--sp-5);
  border-radius: var(--radius-xl);
  padding: var(--sp-6);
  background: var(--material-chrome);
  backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05), 0 8px 32px rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .job-status-card {
    border-color: rgba(84, 84, 88, 0.4);
  }
}

.job-status-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  font-size: var(--fs-footnote);
  color: var(--text-faint);
  margin-bottom: var(--sp-4);
}

.job-meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--fill-quaternary);
  color: var(--text-soft);
}

.job-failure-box {
  margin-bottom: var(--sp-4);
  padding: 14px var(--sp-4);
  border-radius: var(--radius-md);
  background: var(--danger-fill);
  border: 1px solid rgba(255, 59, 48, 0.18);
}

.job-log-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.job-log-item {
  display: flex;
  gap: var(--sp-3);
  align-items: flex-start;
  font-size: var(--fs-footnote);
  line-height: 1.6;
  color: var(--text-soft);
}

.job-log-time {
  min-width: 140px;
  color: var(--text-faint);
  flex-shrink: 0;
}

.job-log-text { flex: 1; }

/* ── Result Card ─────────────────────────────────────────── */

.result-card {
  margin-top: var(--sp-5);
  border-radius: var(--radius-xl);
  padding: var(--sp-7) var(--sp-8);
  border: 1px solid transparent;
}

.result-card.success {
  background: linear-gradient(135deg, rgba(52, 199, 89, 0.07) 0%, rgba(0, 122, 255, 0.05) 100%);
  border-color: rgba(52, 199, 89, 0.22);
}

.result-card.error {
  background: linear-gradient(135deg, rgba(255, 59, 48, 0.06) 0%, rgba(255, 159, 10, 0.04) 100%);
  border-color: rgba(255, 59, 48, 0.18);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin-bottom: 14px;
}

.result-icon { font-size: 24px; }

.success .result-icon { color: var(--system-green); }
.error .result-icon { color: var(--system-red); }

.result-header h3 {
  margin: 0;
  font-size: var(--fs-title3);
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

.result-score {
  font-size: var(--fs-subheadline);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: var(--sp-3);
}

.result-note {
  margin-bottom: 14px;
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-md);
  background: var(--warning-fill);
  color: var(--badge-warning-color);
  font-size: 14px;
  line-height: 1.7;
}

.result-token {
  margin-bottom: var(--sp-4);
  font-size: var(--fs-footnote);
  color: var(--text-soft);
}

.result-feedback {
  font-size: var(--fs-subheadline);
  line-height: 1.6;
  margin: 0 0 var(--sp-5);
  color: var(--text-soft);
}

.issues-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-bottom: var(--sp-5);
}

.issue-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px var(--sp-3);
  background: var(--fill-quaternary);
  border-radius: var(--radius-full);
  font-size: var(--fs-footnote);
  color: var(--text-soft);
}

.viz-row {
  display: flex;
  justify-content: center;
  margin: 8px 0 12px;
}

/* ── Step Results ────────────────────────────────────────── */

.step-result-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin-bottom: var(--sp-5);
}

.step-result-item {
  background: var(--fill-quaternary);
  border: 1px solid rgba(255, 255, 255, 0.60);
  border-radius: var(--radius-lg);
  padding: var(--sp-4) var(--sp-5);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .step-result-item {
    border-color: rgba(84, 84, 88, 0.3);
  }
}

.step-results-box {
  padding: 18px var(--sp-5) var(--sp-4);
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
  gap: var(--sp-4);
  align-items: flex-start;
  margin-bottom: 10px;
}

.step-result-title {
  font-size: var(--fs-subheadline);
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.5;
  max-width: calc(100% - 80px);
}

.step-result-meta {
  display: block;
  font-size: var(--fs-caption1);
  margin-bottom: var(--sp-2);
  color: var(--text-faint);
  line-height: 1.5;
}

.step-result-item .detail-text {
  line-height: 1.8;
}

/* ── Result Actions ──────────────────────────────────────── */

.result-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-actions {
  display: flex;
  justify-content: flex-start;
  margin: 0 0 var(--sp-4);
}

.process-box {
  padding: 18px var(--sp-5) var(--sp-4);
}

.process-collapse {
  border-top: none;
  border-bottom: none;
}

.process-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.process-collapse :deep(.el-collapse-item__header) {
  align-items: flex-start;
  min-height: 72px;
  padding: 14px 0;
  line-height: 1.5;
}

.process-stage-header {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-4);
  width: 100%;
  padding-right: var(--sp-4);
}

.process-stage-title {
  font-size: var(--fs-subheadline);
  font-weight: 600;
  color: var(--text-main);
}

.process-stage-header-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.process-stage-token,
.process-stage-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--fill-quaternary);
  color: var(--text-soft);
  font-size: var(--fs-caption1);
  line-height: 1.4;
}

.process-stage-body {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  padding: 0 0 var(--sp-3);
}

.process-block {
  padding: var(--sp-4);
  border-radius: var(--radius-lg);
  background: var(--surface-secondary);
  border: 1px solid var(--line-soft);
}

.process-block-title {
  font-size: var(--fs-footnote);
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: var(--sp-3);
}

.process-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--sp-3);
}

.process-image-card {
  overflow: hidden;
  border-radius: var(--radius-md);
  background: var(--fill-quaternary);
  border: 1px solid var(--line-soft);
  min-height: 140px;
}

.process-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  aspect-ratio: 4 / 3;
}

.process-media-placeholder {
  min-height: 140px;
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  color: var(--text-soft);
  font-size: var(--fs-footnote);
  line-height: 1.6;
}

.process-media-placeholder span {
  color: var(--text-faint);
}

.process-video-list {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  margin-top: var(--sp-3);
}

.process-video-item {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-3);
}

.process-text {
  margin: 0;
  padding: var(--sp-4);
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid var(--line-soft);
  color: var(--text-main);
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.75;
  font-family: var(--font-mono);
}

.process-response {
  max-height: 320px;
  overflow: auto;
}

/* ── Responsive ──────────────────────────────────────────── */

@media (max-width: 768px) {
  .main-content { padding: var(--sp-5) var(--sp-4); }

  .top-nav {
    padding: 0 var(--sp-4);
    height: auto;
    min-height: var(--toolbar-height);
  }

  .header-titles { flex-direction: column; align-items: flex-start; gap: var(--sp-2); }
  .header-titles h2 { font-size: 26px; }
  .hero-section,
  .page-header { padding: var(--sp-5) var(--sp-4); }
  .progress-card,
  .step-container,
  .job-status-card,
  .result-card {
    padding: var(--sp-5) var(--sp-4);
  }
  .step-container :deep(.section-header) {
    margin-bottom: var(--sp-5);
  }
  .step-flow,
  .upload-section {
    padding: var(--sp-5);
  }
  .history-item {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }
  .history-item-badges,
  .history-item-action {
    justify-content: flex-start;
  }
  .progress-card-top {
    flex-direction: column;
  }
  .progress-side {
    align-items: flex-start;
  }
  .step-layout {
    grid-template-columns: 1fr;
  }
  .upload-section-tip {
    align-self: flex-start;
  }
  .result-actions { flex-direction: column; }
  .file-preview,
  .file-actions {
    flex-direction: column;
    align-items: flex-start;
  }
  .step-result-top { flex-direction: column; }
  .process-stage-header,
  .process-video-item {
    flex-direction: column;
  }
  .process-stage-header-meta {
    justify-content: flex-start;
  }
  .segment { padding: var(--sp-2) 18px; font-size: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .logout-btn,
  .task-item,
  .list-item,
  .back-btn,
  .segment,
  .progress-fill,
  :deep(.apple-upload .el-upload-dragger) {
    transition: none;
  }
}
</style>
