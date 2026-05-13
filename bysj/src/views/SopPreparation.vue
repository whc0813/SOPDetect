<template>
  <div class="prep-page">
    <header class="prep-header">
      <div class="prep-title">
        <h2>{{ sopName }}</h2>
        <p>{{ job?.progressMessage || job?.phase || '等待任务状态更新' }}</p>
      </div>
      <div class="prep-actions">
        <el-button plain @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>返回</span>
        </el-button>
        <el-tag :type="statusTag" effect="dark" round>{{ statusLabel }}</el-tag>
        <el-button type="danger" plain @click="onCancel">取消</el-button>
      </div>
    </header>

    <el-alert
      v-if="showFailedGuidance"
      class="failed-guidance"
      :title="failedGuidanceTitle"
      type="warning"
      show-icon
      :closable="false"
    >
      <template #default>
        <p class="failed-detail">{{ job?.errorMessage || 'AI 时序分割未能完成。' }}</p>
        <p class="failed-hint">已为你按步骤数量准备均匀分段，直接在时间轴上拖动每段的左右边界即可，调整完成后点"使用当前分段开始处理"。</p>
      </template>
    </el-alert>

    <section class="video-section">
      <video
        ref="videoEl"
        :src="videoUrl"
        controls
        @loadedmetadata="onLoadedMetadata"
        @timeupdate="onTimeUpdate"
      />
    </section>

    <section class="timeline-section">
      <div class="section-head">
        <div>
          <h3>步骤时间分段</h3>
          <p v-if="canEditBoundaries">拖动每段两侧的把手调整边界，相邻段允许留间隙；点击段块跳到该时刻。</p>
          <p v-else>当前阶段时间轴只读，处理完成后会更新各步骤的状态色块。</p>
        </div>
        <div class="legend">
          <span class="legend-item"><i class="dot dot-pending" />待处理</span>
          <span class="legend-item"><i class="dot dot-processing" />处理中</span>
          <span class="legend-item"><i class="dot dot-completed" />已完成</span>
          <span class="legend-item"><i class="dot dot-failed" />失败</span>
        </div>
      </div>

      <SegmentTimeline
        :duration="duration"
        :segments="segmentsView"
        :readonly="!canEditBoundaries"
        :current-time="currentTime"
        @update:segments="onSegmentsUpdate"
        @seek="onSeek"
      />

      <div v-if="canEditBoundaries" class="split-tools">
        <span class="split-time">当前播放 {{ formatTime(currentTime) }}</span>
        <el-select
          v-model="boundaryIndex"
          class="boundary-select"
          :disabled="boundaryOptions.length === 0"
          placeholder="选择步骤边界"
        >
          <el-option
            v-for="option in boundaryOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button
          type="primary"
          plain
          :disabled="boundaryOptions.length === 0"
          @click="setBoundaryAtCurrentTime"
        >
          设为步骤边界
        </el-button>
        <el-button plain @click="resetUniformSegments">按步骤均匀切分</el-button>
        <el-button
          v-if="job?.status === 'failed' && job?.phase === 'segmenting'"
          type="warning"
          plain
          @click="onRetrySegmentation"
        >
          重试 AI 分割
        </el-button>
      </div>

      <div v-if="canConfirm" class="confirm-bar">
        <span class="confirm-hint">检查每个步骤的时间窗后开始处理。</span>
        <el-button type="primary" :loading="confirming" @click="onConfirm">
          {{ job?.status === 'failed' ? '使用当前分段开始处理' : '确认分段并开始处理' }}
        </el-button>
      </div>
    </section>

    <section class="steps-section">
      <div class="section-head">
        <div>
          <h3>步骤状态</h3>
          <p>处理中的步骤会实时刷新；失败步骤可单独重试。</p>
        </div>
      </div>
      <StepStateList
        :step-states="stepStates"
        :segments="segmentsView"
        :steps-meta="stepsMeta"
        @seek="onSeek"
        @preview="onPreviewSegment"
        @retry="onRetryStep"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import SegmentTimeline from '../components/SegmentTimeline.vue'
import StepStateList from '../components/StepStateList.vue'
import {
  cancelPreparation,
  confirmSegmentation,
  getPreparationJob,
  retryPreparationStep,
  retrySegmentation
} from '../api/client'

const route = useRoute()
const router = useRouter()
const jobId = route.params.jobId
const videoEl = ref(null)
const job = ref(null)
const sopName = ref('SOP 预处理')
const videoUrl = ref('')
const duration = ref(1)
const segments = ref([])
const stepsMeta = ref([])
const confirming = ref(false)
const currentTime = ref(0)
const previewEndSec = ref(null)
const boundaryIndex = ref(1)
let pollTimer = null
const MIN_SEGMENT_LEN = 0.5

const stepStates = computed(() => job.value?.metadata?.stepStates || {})
const canEditBoundaries = computed(() => {
  const status = job.value?.status
  if (status === 'awaiting_confirmation') return true
  // 时序分割失败时也允许手动卡边界，作为 AI 失败的兜底入口
  if (status === 'failed' && job.value?.phase !== 'processing_steps') return true
  return false
})
const canConfirm = computed(() => canEditBoundaries.value && segments.value.length > 0)
const orderedSegments = computed(() => {
  return [...segments.value].sort((a, b) => Number(a.stepNo) - Number(b.stepNo))
})
const boundaryOptions = computed(() => {
  return orderedSegments.value.slice(0, -1).map((segment, index) => {
    const next = orderedSegments.value[index + 1]
    return {
      value: index + 1,
      label: `步骤 ${segment.stepNo} / 步骤 ${next.stepNo}`
    }
  })
})
const segmentsView = computed(() => {
  const descByNo = new Map(
    (stepsMeta.value || []).map((step) => [Number(step.stepNo), step.description || ''])
  )
  return segments.value.map((segment) => ({
    ...segment,
    description: descByNo.get(Number(segment.stepNo)) || `步骤 ${segment.stepNo}`,
    status: stepStates.value[String(segment.stepNo)]?.status || 'pending'
  }))
})

const showFailedGuidance = computed(() => (
  job.value?.status === 'failed' && job.value?.phase !== 'processing_steps'
))

const failedGuidanceTitle = computed(() => 'AI 时序分割未能完成，请手动卡边界后继续')

const statusLabel = computed(() => ({
  queued: '排队中',
  preparing: '准备中',
  segmenting: '分析中',
  awaiting_confirmation: '等待确认',
  processing_steps: '处理中',
  completed: '已就绪',
  failed: '失败'
}[job.value?.status] || '未知'))

const statusTag = computed(() => ({
  awaiting_confirmation: 'warning',
  completed: 'success',
  failed: 'danger'
}[job.value?.status] || 'info'))

async function refresh() {
  const data = await getPreparationJob(jobId)
  job.value = data
  const metadata = data.metadata || {}
  sopName.value = metadata.sopName || `SOP ${data.sopId || ''}`
  duration.value = Number(metadata.duration_sec || metadata.durationSec || duration.value || 1)
  videoUrl.value = metadata.workflowVideoDataUrlForPreview || metadata.workflowVideoDataUrl || videoUrl.value
  stepsMeta.value = metadata.stepsMeta || stepsMeta.value
  if (!canEditBoundaries.value || segments.value.length === 0) {
    segments.value = (metadata.segments || []).map((item) => ({ ...item }))
  }
  // 失败状态下若服务端没有 segments，本地用均匀分段做种子，让用户能直接拖
  if (
    canEditBoundaries.value &&
    segments.value.length === 0 &&
    stepsMeta.value.length > 0 &&
    duration.value > 0
  ) {
    resetUniformSegments(false)
  }
  syncBoundaryIndex()
  if (data.status === 'completed') {
    stopPolling()
    ElMessage.success('SOP 已就绪')
    setTimeout(() => router.push('/admin'), 3000)
  } else if (data.status === 'failed') {
    stopPolling()
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    refresh().catch((error) => ElMessage.error(error.message || '刷新失败'))
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function onLoadedMetadata() {
  if (videoEl.value?.duration) {
    duration.value = videoEl.value.duration
    if (segments.value.length === 0 && canEditBoundaries.value) resetUniformSegments(false)
  }
}

function onTimeUpdate() {
  if (!videoEl.value) return
  currentTime.value = videoEl.value.currentTime
  // 预览到达终点：自动暂停
  if (
    previewEndSec.value != null &&
    videoEl.value.currentTime >= previewEndSec.value - 0.05
  ) {
    videoEl.value.pause()
    previewEndSec.value = null
  }
}

function onSeek(sec) {
  const value = clampSec(sec, 0, duration.value)
  currentTime.value = value
  if (videoEl.value) videoEl.value.currentTime = value
  // 任何手动 seek（包括拖把手）都中断当前预览
  previewEndSec.value = null
}

function onPreviewSegment(row) {
  if (!videoEl.value || row.startSec == null || row.endSec == null) return
  const start = clampSec(row.startSec, 0, duration.value)
  const end = clampSec(row.endSec, 0, duration.value)
  if (end <= start) return
  videoEl.value.currentTime = start
  currentTime.value = start
  previewEndSec.value = end
  videoEl.value.play().catch(() => {
    // 自动播放被浏览器拦截时取消预览状态
    previewEndSec.value = null
  })
}

function onSegmentsUpdate(updated) {
  segments.value = updated
  syncBoundaryIndex()
}

function goBack() {
  router.push('/admin')
}

function clampSec(value, min, max) {
  const numeric = Number(value || 0)
  return Math.max(Number(min || 0), Math.min(Number(max || 0), numeric))
}

function roundSec(value) {
  return Math.round(Number(value || 0) * 1000) / 1000
}

function formatTime(sec) {
  return `${Number(sec || 0).toFixed(1)}s`
}

function syncBoundaryIndex() {
  const options = boundaryOptions.value
  if (options.length === 0) return
  if (!options.some((option) => option.value === boundaryIndex.value)) {
    boundaryIndex.value = options[0].value
  }
}

function setBoundaryAtCurrentTime() {
  const ordered = orderedSegments.value
  const index = Number(boundaryIndex.value)
  if (!Number.isInteger(index) || index <= 0 || index >= ordered.length) {
    ElMessage.warning('请先选择步骤边界')
    return
  }

  const prev = ordered[index - 1]
  const next = ordered[index]
  const min = Number(prev.startSec || 0) + MIN_SEGMENT_LEN
  const max = Number(next.endSec || duration.value) - MIN_SEGMENT_LEN
  if (max < min) {
    ElMessage.warning('相邻步骤时间过短，无法设置边界')
    return
  }

  const sec = roundSec(clampSec(currentTime.value, min, max))
  segments.value = segments.value.map((item) => {
    if (Number(item.stepNo) === Number(prev.stepNo)) return { ...item, endSec: sec }
    if (Number(item.stepNo) === Number(next.stepNo)) return { ...item, startSec: sec }
    return item
  })
  currentTime.value = sec
  if (videoEl.value) videoEl.value.currentTime = sec
}

function resetUniformSegments(showMessage = true) {
  const count = stepsMeta.value.length || segments.value.length
  if (!duration.value || count <= 0) {
    if (showMessage) ElMessage.warning('缺少视频时长或步骤信息，无法均匀切分')
    return
  }

  const width = Number(duration.value) / count
  segments.value = Array.from({ length: count }, (_, index) => ({
    stepNo: stepsMeta.value[index]?.stepNo || index + 1,
    startSec: roundSec(index * width),
    endSec: roundSec(index === count - 1 ? duration.value : (index + 1) * width),
    source: 'manual'
  }))
  syncBoundaryIndex()
}

async function onConfirm() {
  confirming.value = true
  try {
    await confirmSegmentation(jobId, segments.value.map((item) => ({
      stepNo: item.stepNo,
      startSec: item.startSec,
      endSec: item.endSec
    })))
    await refresh()
    startPolling()
  } catch (error) {
    ElMessage.error(error.message || '确认失败')
  } finally {
    confirming.value = false
  }
}

async function onRetryStep(stepNo) {
  await retryPreparationStep(jobId, stepNo)
  await refresh()
  startPolling()
}

async function onRetrySegmentation() {
  await retrySegmentation(jobId)
  await refresh()
  startPolling()
}

async function onCancel() {
  try {
    await ElMessageBox.confirm('取消后草稿 SOP 会被删除，是否继续？', '取消预处理', { type: 'warning' })
    await cancelPreparation(jobId)
    router.push('/admin')
  } catch (error) {
    if (error instanceof Error) ElMessage.error(error.message || '取消失败')
  }
}

function onVisibilityChange() {
  if (typeof document === 'undefined') return
  if (document.hidden) {
    stopPolling()
  } else if (
    job.value &&
    !['completed', 'failed'].includes(job.value.status)
  ) {
    refresh()
      .catch((error) => ElMessage.error(error.message || '刷新失败'))
      .finally(() => startPolling())
  }
}

onMounted(async () => {
  await refresh()
  startPolling()
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', onVisibilityChange)
  }
})
onUnmounted(() => {
  stopPolling()
  if (typeof document !== 'undefined') {
    document.removeEventListener('visibilitychange', onVisibilityChange)
  }
})
</script>

<style scoped>
.prep-page {
  min-height: 100vh;
  padding: 28px 32px 48px;
  background: linear-gradient(180deg, #f4f6fb 0%, #eef1f7 100%);
  color: #1f2937;
}

.prep-header,
.timeline-section,
.steps-section,
.failed-guidance {
  margin-bottom: 18px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.05);
}

.prep-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.prep-title h2 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  color: #0f172a;
}

.prep-title p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.prep-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.failed-guidance {
  padding: 4px 8px;
}

.failed-detail {
  margin: 2px 0;
  color: #b45309;
  font-size: 13px;
  word-break: break-all;
}

.failed-hint {
  margin: 2px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.video-section {
  margin-bottom: 18px;
  background: #0f172a;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.12);
}

.video-section video {
  display: block;
  width: 100%;
  max-height: 44vh;
  background: #0f172a;
}

.timeline-section,
.steps-section {
  padding: 20px 24px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.section-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.section-head p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #475569;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot-pending { background: hsl(210, 70%, 52%); }
.dot-processing { background: linear-gradient(135deg, #fbbf24, #d97706); }
.dot-completed { background: linear-gradient(135deg, #34d399, #059669); }
.dot-failed { background: linear-gradient(135deg, #f87171, #dc2626); }

.split-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.split-time {
  color: #475569;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.boundary-select {
  width: 180px;
}

.confirm-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.confirm-hint {
  color: #475569;
  font-size: 13px;
}
</style>
