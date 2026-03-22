<template>
  <el-container class="user-layout">
    <el-header class="top-nav">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>视觉智检</span>
      </div>
      <div class="nav-right">
        <div class="user-info">
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          <span class="username">操作用户</span>
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
                  <span class="meta-item"><el-icon><VideoPlay /></el-icon> {{ sop.demoVideoCount || 0 }} 个示范视频</span>
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

        <div v-if="!currentSop && activeTab === 'history'" class="view-transition">
          <div class="page-header">
            <h2>执行历史</h2>
            <p class="subtitle">查看您过去完成的操作流程记录</p>
          </div>

          <div class="table-card">
            <el-table
              :data="historyList"
              style="width: 100%"
              :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }"
              empty-text="暂无历史记录"
            >
              <el-table-column prop="taskName" label="SOP 名称" />
              <el-table-column prop="scene" label="适用场景" width="150" />
              <el-table-column prop="finishTime" label="完成时间" width="200" />
              <el-table-column prop="score" label="总分" width="100" align="center" />
              <el-table-column label="最终结果" width="120" align="center">
                <template #default="scope">
                  <el-tag :class="['minimal-status-tag', scope.row.status === 'passed' ? 'is-passed' : 'is-failed']">
                    {{ scope.row.status === 'passed' ? '验证通过' : '存在异常' }}
                  </el-tag>
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

          <div class="sop-overview">
            <div class="overview-title">操作流程说明（共 {{ currentSop.stepCount }} 步）</div>
            <div class="overview-note">前端演示版会读取管理员端保存到浏览器本地的步骤描述与示范视频元数据，并生成结构化评估结果。</div>

            <div class="steps-list">
              <div v-for="(step, index) in currentSop.steps" :key="index" class="step-item">
                <div class="step-index">{{ index + 1 }}</div>
                <div class="step-main">
                  <div class="step-content">{{ step.description }}</div>
                  <div class="step-meta">
                    <el-tag size="small" effect="plain" :type="step.videoKey ? 'success' : 'warning'">
                      {{ step.videoKey ? '已关联示范视频' : '无示范视频' }}
                    </el-tag>
                    <span v-if="step.videoMeta" class="meta-filename">{{ step.videoMeta.name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="step-container">
            <div class="step-instruction">
              <div class="step-label">上传完整操作视频</div>
              <p class="step-desc">
                当前为纯前端版本：点击“解析与验证”后，会读取本地 SOP 描述和示范视频信息，先走可演示的结构化评估逻辑。
                后续只需把 <code>evaluateByFrontendDemo</code> 替换为真实 API 调用即可。
              </p>
            </div>

            <div class="upload-section">
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
                  <div class="upload-hint">支持 MP4、AVI、MOV 等常见视频格式</div>
                </div>
              </el-upload>

              <div v-if="currentVideo" class="file-preview">
                <div class="file-info">
                  <el-icon><VideoPlay /></el-icon>
                  <div class="file-text">
                    <span>{{ currentVideo.name }}</span>
                    <small>{{ formatFileSize(currentVideo.size || 0) }}</small>
                  </div>
                </div>
                <el-button type="primary" class="submit-action-btn" @click="submitVideo" :loading="isEvaluating">
                  解析与验证
                </el-button>
              </div>
            </div>
          </div>

          <div class="result-card" v-if="evaluationResult" :class="evaluationResult.passed ? 'success' : 'error'">
            <div class="result-header">
              <el-icon class="result-icon" v-if="evaluationResult.passed"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <div>
                <h3>{{ evaluationResult.passed ? '验证通过' : '验证未通过' }}</h3>
                <p class="result-subtitle">总分：{{ evaluationResult.score }} / 100</p>
              </div>
            </div>

            <p class="result-feedback">{{ evaluationResult.feedback }}</p>

            <div class="summary-grid">
              <div class="summary-item">
                <div class="summary-label">识别步骤</div>
                <div class="summary-value">{{ evaluationResult.summary.detectedCount }}/{{ currentSop.stepCount }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-label">顺序判断</div>
                <div class="summary-value">{{ evaluationResult.summary.orderStatus }}</div>
              </div>
              <div class="summary-item">
                <div class="summary-label">示范视频</div>
                <div class="summary-value">{{ evaluationResult.summary.demoVideoCount }}</div>
              </div>
            </div>

            <div class="issues-box" v-if="evaluationResult.issues.length">
              <div class="issues-title">问题摘要</div>
              <div v-for="(issue, index) in evaluationResult.issues" :key="index" class="issue-item">
                {{ issue }}
              </div>
            </div>

            <div class="step-result-list">
              <div class="step-result-title">步骤级评估</div>
              <div v-for="item in evaluationResult.stepResults" :key="item.stepNo" class="step-result-item">
                <div class="step-result-left">
                  <div class="step-result-index">步骤 {{ item.stepNo }}</div>
                  <div class="step-result-desc">{{ item.description }}</div>
                  <div class="step-result-evidence">{{ item.evidence }}</div>
                </div>
                <div class="step-result-right">
                  <el-tag :type="item.passed ? 'success' : 'danger'" effect="plain">
                    {{ item.passed ? '通过' : '异常' }}
                  </el-tag>
                  <span class="step-score">{{ item.score }} 分</span>
                </div>
              </div>
            </div>

            <div class="payload-preview">
              <div class="payload-title">后续接入大模型时可直接复用的请求载荷</div>
              <pre>{{ JSON.stringify(evaluationResult.payloadPreview, null, 2) }}</pre>
            </div>

            <div class="result-actions">
              <el-button v-if="evaluationResult.passed" type="primary" class="action-btn-primary" @click="finishSop">
                完成整个流程
              </el-button>
              <el-button v-else class="action-btn-secondary" @click="retrySop">
                重新上传视频
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight, Location, List, ArrowLeft,
  VideoCamera, VideoPlay, CircleCheckFilled, WarningFilled, Monitor
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

const SOP_LIST_KEY = 'sopList'
const SOP_HISTORY_KEY = 'sopHistoryList'
const SOP_DB_NAME = 'sop-demo-db'
const SOP_STORE_NAME = 'videoFiles'

const sopList = ref([])
const historyList = ref([])
const activeTab = ref('tasks')
const currentSop = ref(null)
const currentVideo = ref(null)
const isEvaluating = ref(false)
const evaluationResult = ref(null)

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SOP_DB_NAME, 1)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(SOP_STORE_NAME)) {
        db.createObjectStore(SOP_STORE_NAME)
      }
    }
  })
}

async function getVideoFile(key) {
  if (!key) return null
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SOP_STORE_NAME, 'readonly')
    const request = tx.objectStore(SOP_STORE_NAME).get(key)
    request.onsuccess = () => resolve(request.result || null)
    request.onerror = () => reject(request.error)
  })
}

function formatFileSize(size) {
  if (!size) return '0 KB'
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

onMounted(() => {
  const stored = localStorage.getItem(SOP_LIST_KEY)
  if (stored) {
    sopList.value = JSON.parse(stored)
  }

  const historyStored = localStorage.getItem(SOP_HISTORY_KEY)
  if (historyStored) {
    historyList.value = JSON.parse(historyStored)
  }
})

const handleLogout = () => {
  router.push('/login')
}

const startSop = (sop) => {
  currentSop.value = sop
  resetState()
}

const backToList = () => {
  currentSop.value = null
  resetState()
}

const resetState = () => {
  currentVideo.value = null
  isEvaluating.value = false
  evaluationResult.value = null
}

const handleVideoChange = (uploadFile) => {
  currentVideo.value = uploadFile?.raw || uploadFile
}

function hashString(input) {
  let hash = 0
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) - hash + input.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

async function getVideoDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      const duration = Number(video.duration) || 0
      URL.revokeObjectURL(url)
      resolve(duration)
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(0)
    }
    video.src = url
  })
}

async function evaluateByFrontendDemo(sop, userVideoFile) {
  const demoFiles = await Promise.all(
    (sop.steps || []).map(async step => ({
      stepNo: step.stepNo,
      description: step.description,
      demoFile: await getVideoFile(step.videoKey),
      videoMeta: step.videoMeta || null
    }))
  )

  const duration = await getVideoDuration(userVideoFile)
  const seed = hashString(`${sop.id}|${userVideoFile.name}|${userVideoFile.size}|${duration}`)
  const stepResults = demoFiles.map((step, index) => {
    const stepSeed = (seed + (index + 1) * 97) % 100
    const hasDemo = !!step.demoFile
    const passed = hasDemo ? stepSeed >= 28 : stepSeed >= 45
    const score = passed ? 18 + (stepSeed % 8) : Math.max(6, 12 - (stepSeed % 7))
    const evidence = passed
      ? `检测到与步骤描述基本一致的操作片段，且存在示范视频可供后续二次比对。`
      : `当前片段与预期步骤存在偏差，建议重点核查动作完整性、执行顺序和关键节点。`

    return {
      stepNo: index + 1,
      description: step.description,
      passed,
      score,
      evidence,
      hasDemo
    }
  })

  const detectedCount = stepResults.filter(item => item.passed).length
  const score = Math.max(
    0,
    Math.min(
      100,
      stepResults.reduce((sum, item) => sum + item.score, 0)
    )
  )

  const issues = []
  if (detectedCount < sop.stepCount) {
    issues.push(`检测到 ${sop.stepCount - detectedCount} 个步骤存在异常或置信度不足。`)
  }
  if (duration && duration < sop.stepCount * 2) {
    issues.push('用户上传的视频时长偏短，可能未完整覆盖全部步骤。')
  }
  if ((sop.demoVideoCount || 0) < sop.stepCount) {
    issues.push('部分步骤未找到示范视频，后续接入真实模型时建议补齐。')
  }

  const passed = score >= 60 && detectedCount >= Math.ceil(sop.stepCount * 0.7)
  const feedback = passed
    ? '前端演示版判定：整体流程较完整，关键步骤基本匹配 SOP 描述，可进入“通过”状态。'
    : '前端演示版判定：存在步骤缺失、置信度不足或时长异常，建议重新录制后再验证。'

  const payloadPreview = {
    model: 'qwen3.5-plus',
    systemPrompt: '你是SOP视频评估助手，请结合SOP步骤描述、管理员示范视频与用户完整视频，返回结构化JSON结果。',
    sopName: sop.name,
    scene: sop.scene,
    steps: (sop.steps || []).map((step, index) => ({
      stepNo: index + 1,
      description: step.description,
      demoVideoName: step.videoMeta?.name || '未上传'
    })),
    userVideoName: userVideoFile.name,
    expectedOutputFields: ['passed', 'score', 'issues', 'stepResults']
  }

  return {
    passed,
    score,
    feedback,
    issues,
    summary: {
      detectedCount,
      orderStatus: passed ? '基本正确' : '存在风险',
      demoVideoCount: `${sop.demoVideoCount || 0}/${sop.stepCount}`
    },
    stepResults,
    payloadPreview
  }
}

const submitVideo = async () => {
  if (!currentVideo.value) {
    ElMessage.warning('请先上传视频')
    return
  }

  if (!currentSop.value) {
    ElMessage.warning('请先选择 SOP')
    return
  }

  isEvaluating.value = true

  try {
    await new Promise(resolve => setTimeout(resolve, 1200))
    evaluationResult.value = await evaluateByFrontendDemo(currentSop.value, currentVideo.value)
    ElMessage.success('前端演示版解析完成')
  } catch (error) {
    console.error(error)
    ElMessage.error('解析失败，请重试')
  } finally {
    isEvaluating.value = false
  }
}

const saveHistory = () => {
  if (!currentSop.value || !evaluationResult.value) return

  const record = {
    id: Date.now(),
    taskId: currentSop.value.id,
    taskName: currentSop.value.name,
    scene: currentSop.value.scene,
    finishTime: new Date().toLocaleString(),
    score: evaluationResult.value.score,
    status: evaluationResult.value.passed ? 'passed' : 'failed'
  }

  historyList.value.unshift(record)
  localStorage.setItem(SOP_HISTORY_KEY, JSON.stringify(historyList.value))
}

const finishSop = () => {
  saveHistory()
  ElMessage.success('SOP 流程验证完成并已记录到历史')
  backToList()
}

const retrySop = () => {
  currentVideo.value = null
  evaluationResult.value = null
}
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
  max-width: 980px;
  margin: 0 auto;
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
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
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
  flex-wrap: wrap;
  gap: 12px 16px;
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

.user-tabs {
  margin-bottom: 32px;
  display: flex;
  justify-content: center;
}

:deep(.minimal-radio-group) {
  background-color: #e5e5ea;
  padding: 4px;
  border-radius: 12px;
  display: inline-flex;
}

:deep(.minimal-radio-group .el-radio-button__inner) {
  border: none !important;
  background: transparent;
  color: #515154;
  font-weight: 500;
  box-shadow: none !important;
  border-radius: 8px !important;
  padding: 8px 32px;
  font-size: 15px;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

:deep(.minimal-radio-group .el-radio-button:hover .el-radio-button__inner) {
  color: #1d1d1f;
}

:deep(.minimal-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background-color: #000000;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  font-weight: 600;
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

:deep(.minimal-status-tag.is-failed) {
  background-color: #f5f5f7;
  color: #86868b;
  border-color: #e5e5ea;
}

.table-card,
.sop-overview,
.step-container,
.result-card {
  background-color: #ffffff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  padding: 24px;
  overflow: hidden;
}

.execution-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.execution-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  font-weight: 500;
}

.header-titles h2 {
  margin: 0 0 4px;
  color: #1d1d1f;
}

.scene-tag {
  font-size: 13px;
  color: #86868b;
}

.overview-title,
.step-result-title,
.issues-title,
.payload-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.overview-note {
  font-size: 13px;
  line-height: 1.7;
  color: #86868b;
  margin: 10px 0 18px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: flex;
  gap: 14px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px;
  background: #fafafa;
}

.step-index,
.step-result-index {
  width: 70px;
  min-width: 70px;
  height: 32px;
  border-radius: 16px;
  background: #1d1d1f;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}

.step-main {
  flex: 1;
}

.step-content {
  color: #1d1d1f;
  line-height: 1.7;
}

.step-meta {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.meta-filename {
  font-size: 12px;
  color: #86868b;
}

.step-instruction {
  margin-bottom: 16px;
}

.step-label {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #1d1d1f;
}

.step-desc {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: #666;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.minimal-upload {
  width: 100%;
}

:deep(.minimal-upload .el-upload-dragger) {
  width: 100%;
  border-radius: 14px;
  border: 1px dashed #d5d7de;
  background: #fafafa;
  padding: 28px 20px;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #86868b;
}

.upload-icon {
  font-size: 32px;
}

.upload-text {
  font-size: 15px;
}

.bold {
  color: #1d1d1f;
  font-weight: 600;
}

.upload-hint {
  font-size: 12px;
}

.file-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid #ededed;
  gap: 16px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-text {
  display: flex;
  flex-direction: column;
}

.file-text span {
  font-size: 14px;
  color: #1d1d1f;
}

.file-text small {
  color: #86868b;
}

.submit-action-btn,
.action-btn-primary {
  background: #000000;
  border-color: #000000;
  border-radius: 8px;
}

.result-card.success {
  border: 1px solid #dbefdf;
}

.result-card.error {
  border: 1px solid #f1d6d6;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.result-icon {
  font-size: 28px;
}

.result-card.success .result-icon {
  color: #2b8a3e;
}

.result-card.error .result-icon {
  color: #d94841;
}

.result-header h3 {
  margin: 0;
  color: #1d1d1f;
}

.result-subtitle {
  margin: 4px 0 0;
  color: #86868b;
  font-size: 13px;
}

.result-feedback {
  color: #333;
  line-height: 1.8;
  margin: 0 0 18px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-item {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px;
}

.summary-label {
  font-size: 12px;
  color: #86868b;
  margin-bottom: 6px;
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.issues-box {
  margin-bottom: 18px;
}

.issue-item {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fafafa;
  color: #555;
  line-height: 1.7;
}

.step-result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-result-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  background: #fafafa;
}

.step-result-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.step-result-desc {
  color: #1d1d1f;
  line-height: 1.7;
}

.step-result-evidence {
  font-size: 13px;
  color: #666;
  line-height: 1.7;
}

.step-result-right {
  min-width: 90px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.step-score {
  font-size: 13px;
  color: #86868b;
}

.payload-preview {
  margin-top: 18px;
}

.payload-preview pre {
  margin: 12px 0 0;
  padding: 16px;
  background: #111827;
  color: #f8fafc;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.action-btn-secondary {
  border-radius: 8px;
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

@media (max-width: 768px) {
  .main-content {
    padding: 24px 16px;
  }

  .top-nav {
    padding: 0 16px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .file-preview,
  .step-result-item,
  .execution-header {
    flex-direction: column;
    align-items: stretch;
  }

  .step-result-right {
    align-items: flex-start;
  }
}
</style>
