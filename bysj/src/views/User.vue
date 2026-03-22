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
        <el-button text class="api-config-btn" @click="configVisible = true">API 配置</el-button>
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
        <!-- Header Tabs -->
        <div class="user-tabs" v-if="!currentSop">
          <el-radio-group v-model="activeTab" class="minimal-radio-group">
            <el-radio-button label="tasks">待执行任务</el-radio-button>
            <el-radio-button label="history">历史记录</el-radio-button>
          </el-radio-group>
        </div>

        <!-- Task List View -->
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

          <el-empty v-if="sopList.length === 0" description="暂无可用流程，请联系管理员创建" class="minimal-empty"></el-empty>
        </div>

        <!-- History List View -->
        <div v-if="!currentSop && activeTab === 'history'" class="view-transition">
          <div class="page-header">
            <h2>执行历史</h2>
            <p class="subtitle">查看您过去完成的操作流程记录</p>
          </div>

          <div class="table-card">
            <el-table :data="historyList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无历史记录">
              <el-table-column prop="taskName" label="SOP 名称" />
              <el-table-column prop="scene" label="适用场景" width="150" />
              <el-table-column prop="finishTime" label="完成时间" width="200" />
              <el-table-column label="最终结果" width="120" align="center">
                <template #default="scope">
                  <el-tag :class="['minimal-status-tag', scope.row.status === 'passed' ? 'is-passed' : 'is-failed']">
                    {{ scope.row.status === 'passed' ? '验证通过' : '存在异常' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center">
                <template #default="scope">
                  <el-button text class="action-link-btn" @click="openHistoryDetail(scope.row)">查看详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- Execution View -->
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
            <div class="overview-title">操作流程说明 (共 {{ currentSop.stepCount }} 步)</div>
            <div class="steps-list">
              <div v-for="(step, index) in currentSop.steps" :key="index" class="step-item">
                <div class="step-index">{{ index + 1 }}</div>
                <div class="step-content">
                  <div>{{ step.description }}</div>
                  <div class="step-subline">
                    {{ step.videoMeta?.name ? `示范视频：${step.videoMeta.name}` : '未配置示范视频' }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="step-container" v-if="!evaluationResult || !evaluationResult.passed">
            <div class="step-instruction">
              <div class="step-label">上传完整操作视频</div>
              <p class="step-desc">请按照上述流程，录制并上传完整的操作视频以供系统自动评估。</p>
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
                  <div class="upload-hint">支持 MP4 或 AVI 格式视频</div>
                </div>
              </el-upload>

              <div v-if="currentVideo" class="file-preview">
                <div class="file-info">
                  <el-icon><VideoPlay /></el-icon>
                  <span>{{ currentVideo.name }}</span>
                </div>
                <el-button 
                  type="primary" 
                  class="submit-action-btn" 
                  @click="submitVideo" 
                  :loading="isEvaluating"
                >
                  解析与验证
                </el-button>
              </div>

              <div v-if="stageText" class="stage-text">{{ stageText }}</div>
            </div>
          </div>

          <!-- Result Area -->
          <div class="result-card" v-if="evaluationResult" :class="evaluationResult.passed ? 'success' : 'error'">
            <div class="result-header">
              <el-icon class="result-icon" v-if="evaluationResult.passed"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>{{ evaluationResult.passed ? '验证通过' : '验证未通过' }}</h3>
            </div>

            <div v-if="typeof evaluationResult.score === 'number'" class="result-score">
              总分：{{ evaluationResult.score }} / 100
            </div>

            <p class="result-feedback">{{ evaluationResult.feedback }}</p>

            <div v-if="evaluationResult.issues?.length" class="issues-list">
              <span v-for="(issue, index) in evaluationResult.issues" :key="index" class="issue-chip">
                {{ issue }}
              </span>
            </div>

            <div v-if="evaluationResult.stepResults?.length" class="step-result-list">
              <div v-for="item in evaluationResult.stepResults" :key="item.stepNo" class="step-result-item">
                <div class="step-result-top">
                  <div class="step-result-title">步骤 {{ item.stepNo }}：{{ item.description }}</div>
                  <div class="step-result-status">{{ item.passed ? '通过' : '异常' }} · {{ item.score }} 分</div>
                </div>
                <div class="step-result-meta">置信度：{{ formatConfidence(item.confidence) }}</div>
                <div class="evidence-text">{{ item.evidence }}</div>
              </div>
            </div>

            <el-collapse v-if="evaluationResult.payloadPreview || evaluationResult.rawModelResult" class="result-collapse">
              <el-collapse-item title="请求载荷预览（已隐藏 Base64）" name="1">
                <pre class="code-wrap">{{ JSON.stringify(evaluationResult.payloadPreview, null, 2) }}</pre>
              </el-collapse-item>
              <el-collapse-item title="原始模型结果" name="2">
                <pre class="code-wrap">{{ JSON.stringify(evaluationResult.rawModelResult, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>

            <div class="result-actions">
              <el-button 
                v-if="evaluationResult.passed" 
                type="primary" 
                class="action-btn-primary"
                @click="finishSop"
              >
                完成整个流程
              </el-button>
              <el-button 
                v-else 
                class="action-btn-secondary"
                @click="retrySop"
              >
                重新上传视频
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-main>

    <el-dialog v-model="configVisible" title="百炼 API 配置" width="680px" class="minimal-dialog" destroy-on-close>
      <el-alert
        class="config-alert"
        type="warning"
        :closable="false"
        show-icon
        title="当前是前端直连版，API Key 会保存在浏览器 localStorage 中，仅建议用于本地调试。"
      />
      <el-form label-position="top" class="minimal-form config-form">
        <el-form-item label="API Key">
          <el-input v-model="apiConfig.apiKey" type="password" show-password placeholder="请输入阿里百炼 API Key" />
        </el-form-item>
        <div class="config-row">
          <el-form-item label="Base URL" class="flex-1">
            <el-input v-model="apiConfig.baseURL" />
          </el-form-item>
          <el-form-item label="模型名称" class="flex-1">
            <el-input v-model="apiConfig.model" />
          </el-form-item>
        </div>
        <div class="config-row config-row-small">
          <el-form-item label="fps" class="flex-1">
            <el-input-number v-model="apiConfig.fps" :min="0.1" :max="10" :step="0.5" />
          </el-form-item>
          <el-form-item label="temperature" class="flex-1">
            <el-input-number v-model="apiConfig.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="超时(ms)" class="flex-1">
            <el-input-number v-model="apiConfig.timeoutMs" :min="10000" :max="300000" :step="10000" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="resetApiConfig">恢复默认</el-button>
          <el-button type="primary" class="submit-btn" @click="saveApiConfig">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="historyDetailVisible"
      title="历史记录详情"
      width="820px"
      class="minimal-dialog history-detail-dialog"
      destroy-on-close
    >
      <template v-if="selectedHistoryRecord">
        <div class="history-detail-layout">
          <div class="history-summary-grid">
            <div class="history-summary-card">
              <div class="history-summary-label">SOP 名称</div>
              <div class="history-summary-value">{{ selectedHistoryRecord.taskName || '-' }}</div>
            </div>
            <div class="history-summary-card">
              <div class="history-summary-label">适用场景</div>
              <div class="history-summary-value">{{ selectedHistoryRecord.scene || '-' }}</div>
            </div>
            <div class="history-summary-card">
              <div class="history-summary-label">完成时间</div>
              <div class="history-summary-value">{{ selectedHistoryRecord.finishTime || '-' }}</div>
            </div>
            <div class="history-summary-card">
              <div class="history-summary-label">最终结果</div>
              <div class="history-summary-value">
                <el-tag :class="['minimal-status-tag', selectedHistoryRecord.status === 'passed' ? 'is-passed' : 'is-failed']">
                  {{ getStatusText(selectedHistoryRecord.status) }}
                </el-tag>
              </div>
            </div>
            <div class="history-summary-card">
              <div class="history-summary-label">总分</div>
              <div class="history-summary-value">{{ formatScore(selectedHistoryRecord.score) }}</div>
            </div>
            <div class="history-summary-card">
              <div class="history-summary-label">上传视频</div>
              <div class="history-summary-value">{{ selectedHistoryRecord.detail.uploadedVideo?.name || '未记录' }}</div>
            </div>
          </div>

          <template v-if="hasHistoryDetail(selectedHistoryRecord)">
            <div class="history-detail-section" v-if="selectedHistoryRecord.detail.feedback">
              <div class="history-detail-title">总体反馈</div>
              <div class="history-feedback-card">{{ selectedHistoryRecord.detail.feedback }}</div>
            </div>

            <div class="history-detail-section" v-if="selectedHistoryRecord.detail.issues.length">
              <div class="history-detail-title">问题摘要</div>
              <div class="issues-list compact">
                <span v-for="(issue, index) in selectedHistoryRecord.detail.issues" :key="index" class="issue-chip">
                  {{ issue }}
                </span>
              </div>
            </div>

            <div class="history-detail-section" v-if="selectedHistoryRecord.detail.stepResults.length">
              <div class="history-detail-title">逐步分析</div>
              <div class="step-result-list compact">
                <div v-for="item in selectedHistoryRecord.detail.stepResults" :key="`${selectedHistoryRecord.id}-${item.stepNo}`" class="step-result-item">
                  <div class="step-result-top">
                    <div class="step-result-title">步骤 {{ item.stepNo }}：{{ item.description || '未命名步骤' }}</div>
                    <div class="step-result-status">{{ getStepResultText(item.passed) }} · {{ formatScore(item.score, '--') }}</div>
                  </div>
                  <div class="step-result-meta">置信度：{{ formatConfidence(item.confidence) }}</div>
                  <div class="evidence-text">{{ item.evidence || '未返回分析说明' }}</div>
                </div>
              </div>
            </div>

            <div class="history-detail-section" v-if="selectedHistoryRecord.detail.sopSteps.length">
              <div class="history-detail-title">执行时 SOP 快照</div>
              <div class="history-step-list">
                <div v-for="item in selectedHistoryRecord.detail.sopSteps" :key="`${selectedHistoryRecord.id}-sop-${item.stepNo}`" class="history-step-item">
                  <div class="history-step-index">{{ item.stepNo }}</div>
                  <div class="history-step-content">
                    <div class="history-step-text">{{ item.description || '未填写步骤说明' }}</div>
                    <div class="history-step-meta">{{ item.videoName ? `示范视频：${item.videoName}` : '未记录示范视频信息' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <el-empty
            v-else
            description="这条历史记录生成于详情功能上线前，当前只保留了摘要信息。"
            class="minimal-empty"
          />
        </div>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight, Location, List, ArrowLeft,
  VideoCamera, VideoPlay, CircleCheckFilled, WarningFilled, Monitor
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

const SOP_LIST_KEY = 'sopList'
const SOP_HISTORY_KEY = 'sopHistoryList'
const API_CONFIG_KEY = 'dashscopeEvalConfig'
const SOP_DB_NAME = 'sop-demo-db'
const SOP_STORE_NAME = 'videoFiles'

const DEFAULT_API_CONFIG = {
  apiKey: '',
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.5-plus',
  fps: 2,
  temperature: 0.1,
  timeoutMs: 120000
}

const sopList = ref([])
const historyList = ref([])
const activeTab = ref('tasks')
const currentSop = ref(null)
const hasErrorInCurrentSop = ref(false)

const currentVideo = ref(null)
const isEvaluating = ref(false)
const evaluationResult = ref(null)
const stageText = ref('')
const configVisible = ref(false)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)

const apiConfig = reactive({ ...DEFAULT_API_CONFIG })

onMounted(() => {
  loadSops()
  loadHistory()
  loadApiConfig()
})

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

async function setStoreValue(key, value) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SOP_STORE_NAME, 'readwrite')
    tx.objectStore(SOP_STORE_NAME).put(value, key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

function normalizeSop(item = {}) {
  return {
    ...item,
    steps: (item.steps || []).map((step, index) => ({
      ...step,
      stepNo: step.stepNo || index + 1,
      description: step.description || '',
      videoKey: step.videoKey || '',
      videoMeta: step.videoMeta || null,
      referenceAssetKey: step.referenceAssetKey || '',
      referenceSummary: step.referenceSummary || '',
      referenceFeatures: step.referenceFeatures || null,
      substeps: Array.isArray(step.substeps) ? step.substeps : [],
      roiHint: step.roiHint || '',
      aiUsed: Boolean(step.aiUsed)
    }))
  }
}

function persistSops() {
  localStorage.setItem(SOP_LIST_KEY, JSON.stringify(sopList.value))
}

function loadSops() {
  const stored = localStorage.getItem(SOP_LIST_KEY)
  sopList.value = stored ? JSON.parse(stored).map(normalizeSop) : []
}

function loadHistory() {
  const historyStored = localStorage.getItem(SOP_HISTORY_KEY)
  historyList.value = historyStored ? JSON.parse(historyStored).map(normalizeHistoryRecord) : []
}

function loadApiConfig() {
  const stored = localStorage.getItem(API_CONFIG_KEY)
  Object.assign(apiConfig, stored ? { ...DEFAULT_API_CONFIG, ...JSON.parse(stored) } : { ...DEFAULT_API_CONFIG })
}

function saveApiConfig() {
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify({ ...apiConfig }))
  ElMessage.success('API 配置已保存')
  configVisible.value = false
}

function resetApiConfig() {
  Object.assign(apiConfig, { ...DEFAULT_API_CONFIG })
}

const handleLogout = () => {
  router.push('/login')
}

const startSop = (sop) => {
  currentSop.value = sop
  hasErrorInCurrentSop.value = false
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
  stageText.value = ''
}

const handleVideoChange = (file) => {
  currentVideo.value = file?.raw || file
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error || new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`请求超时（>${ms}ms）`)), ms)
    promise.then((value) => {
      clearTimeout(timer)
      resolve(value)
    }).catch((err) => {
      clearTimeout(timer)
      reject(err)
    })
  })
}

async function prepareStepReference(stepNo, description, videoFile) {
  const videoDataUrl = await fileToDataUrl(videoFile)
  const response = await withTimeout(fetch('http://localhost:8000/api/prepare-step-video', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      stepNo,
      description,
      videoDataUrl,
      maxFrames: 8,
      apiConfig: {
        apiKey: apiConfig.apiKey,
        baseURL: apiConfig.baseURL,
        model: apiConfig.model,
        fps: apiConfig.fps,
        temperature: apiConfig.temperature,
        timeoutMs: apiConfig.timeoutMs
      }
    })
  }), apiConfig.timeoutMs)

  const rawText = await response.text()
  let resultJson = null
  try {
    resultJson = JSON.parse(rawText)
  } catch {
    throw new Error(rawText || `HTTP ${response.status}`)
  }

  if (!response.ok || !resultJson.success) {
    const message = resultJson?.detail || resultJson?.message || rawText || `HTTP ${response.status}`
    throw new Error(message)
  }

  return resultJson.data
}

async function ensureReferenceAssets(sop) {
  const steps = (sop.steps || []).map((step, index) => ({
    ...step,
    stepNo: step.stepNo || index + 1
  }))

  const sopIndex = sopList.value.findIndex(item => item.id === sop.id)
  let changed = false
  const resolvedSteps = []

  for (const step of steps) {
    let assetKey = step.referenceAssetKey || ''
    let asset = assetKey ? await getVideoFile(assetKey) : null

    if ((!asset || !asset.referenceFrames?.length) && step.videoKey) {
      stageText.value = `正在为步骤 ${step.stepNo} 生成可复用参考素材...`
      const sourceVideo = await getVideoFile(step.videoKey)
      if (!sourceVideo) {
        throw new Error(`步骤 ${step.stepNo} 的示范视频不存在，请联系管理员重新发布 SOP`)
      }
      asset = await prepareStepReference(step.stepNo, step.description, sourceVideo)
      assetKey = assetKey || `${sop.id}-step-${step.stepNo}-reference`
      await setStoreValue(assetKey, asset)
      step.referenceAssetKey = assetKey
      step.referenceSummary = asset.referenceSummary || ''
      step.referenceFeatures = asset.referenceFeatures || null
      step.substeps = Array.isArray(asset.substeps) ? asset.substeps : []
      step.roiHint = asset.roiHint || ''
      step.aiUsed = Boolean(asset.aiUsed)
      changed = true
    }

    if (!asset || !asset.referenceFrames?.length) {
      throw new Error(`步骤 ${step.stepNo} 缺少参考素材，请重新发布 SOP`)
    }

    resolvedSteps.push({
      stepNo: step.stepNo,
      description: step.description,
      referenceFrames: asset.referenceFrames,
      referenceSummary: asset.referenceSummary || step.referenceSummary || '',
      referenceFeatures: asset.referenceFeatures || step.referenceFeatures || null,
      substeps: Array.isArray(asset.substeps) ? asset.substeps : (Array.isArray(step.substeps) ? step.substeps : []),
      roiHint: asset.roiHint || step.roiHint || ''
    })
  }

  if (changed && sopIndex !== -1) {
    const updatedSop = normalizeSop({
      ...sopList.value[sopIndex],
      steps
    })
    sopList.value.splice(sopIndex, 1, updatedSop)
    persistSops()
    if (currentSop.value?.id === updatedSop.id) {
      currentSop.value = updatedSop
    }
  }

  return resolvedSteps
}

function extractJsonString(content) {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    const textPart = content.find(item => item?.type === 'text' && item?.text)
    if (textPart?.text) return textPart.text
  }
  return ''
}

function parseJsonFromModel(content) {
  const raw = extractJsonString(content).trim()
  if (!raw) throw new Error('模型未返回可解析内容')
  try {
    return JSON.parse(raw)
  } catch {
    const match = raw.match(/\{[\s\S]*\}/)
    if (match) return JSON.parse(match[0])
    throw new Error('模型返回不是合法 JSON')
  }
}

async function evaluateByRealApi(sop, userVideoFile) {
  if (!apiConfig.apiKey?.trim()) throw new Error('请先配置 API Key')

  const steps = (sop.steps || []).map((step, index) => ({
    ...step,
    stepNo: step.stepNo || index + 1
  }))

  if (steps.some(step => !step.videoKey)) {
    throw new Error('该 SOP 仍有步骤未上传示范视频，无法调用真实评测')
  }

  stageText.value = '正在读取管理员示范视频...'
  const demoFiles = []
  for (const step of steps) {
    const file = await getVideoFile(step.videoKey)
    if (!file) {
      throw new Error(`步骤 ${step.stepNo} 的示范视频不存在，请回管理员端重新上传`)
    }
    demoFiles.push({
      stepNo: step.stepNo,
      description: step.description,
      dataUrl: await fileToDataUrl(file)
    })
  }

  stageText.value = '正在转换用户视频...'
  const userVideoDataUrl = await fileToDataUrl(userVideoFile)

  const payload = {
    apiConfig: {
      apiKey: apiConfig.apiKey,
      baseURL: apiConfig.baseURL,
      model: apiConfig.model,
      fps: apiConfig.fps,
      temperature: apiConfig.temperature,
      timeoutMs: apiConfig.timeoutMs
    },
    sop: {
      name: sop.name,
      scene: sop.scene,
      stepCount: steps.length
    },
    demoFiles,
    userVideoDataUrl
  }

  stageText.value = '正在请求后端评估接口...'
  const response = await withTimeout(fetch('http://localhost:8000/api/evaluate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }), apiConfig.timeoutMs + 10000)

  const rawText = await response.text()
  let resultJson = null
  try {
    resultJson = JSON.parse(rawText)
  } catch {
    throw new Error(rawText || `HTTP ${response.status}`)
  }

  if (!response.ok || !resultJson.success) {
    const message = resultJson?.detail || resultJson?.message || rawText || `HTTP ${response.status}`
    throw new Error(message)
  }

  const rawModelResult = resultJson.data
  const parsed = parseJsonFromModel(rawModelResult?.choices?.[0]?.message?.content)
  return {
    ...parsed,
    rawModelResult,
    payloadPreview: resultJson.payloadPreview
  }
}

async function evaluateByStepAssets(sop, userVideoFile) {
  if (!apiConfig.apiKey?.trim()) throw new Error('请先配置 API Key')

  stageText.value = '正在准备可复用的参考素材...'
  const steps = await ensureReferenceAssets(sop)

  stageText.value = '正在转换用户视频...'
  const userVideoDataUrl = await fileToDataUrl(userVideoFile)

  const payload = {
    apiConfig: {
      apiKey: apiConfig.apiKey,
      baseURL: apiConfig.baseURL,
      model: apiConfig.model,
      fps: apiConfig.fps,
      temperature: apiConfig.temperature,
      timeoutMs: apiConfig.timeoutMs
    },
    sop: {
      name: sop.name,
      scene: sop.scene,
      stepCount: steps.length,
      steps
    },
    userVideoDataUrl
  }

  stageText.value = '正在请求后端评估接口...'
  const response = await withTimeout(fetch('http://localhost:8000/api/evaluate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  }), apiConfig.timeoutMs + 10000)

  const rawText = await response.text()
  let resultJson = null
  try {
    resultJson = JSON.parse(rawText)
  } catch {
    throw new Error(rawText || `HTTP ${response.status}`)
  }

  if (!response.ok || !resultJson.success) {
    const message = resultJson?.detail || resultJson?.message || rawText || `HTTP ${response.status}`
    throw new Error(message)
  }

  const rawModelResult = resultJson.data
  const parsed = parseJsonFromModel(rawModelResult?.choices?.[0]?.message?.content)
  return {
    ...parsed,
    rawModelResult,
    payloadPreview: resultJson.payloadPreview,
    segmentPreview: resultJson.segmentPreview
  }
}

function formatConfidence(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '-'
  return num.toFixed(2)
}

function formatScore(value, fallback = '-') {
  const num = Number(value)
  return Number.isFinite(num) ? `${num} / 100` : fallback
}

function getStatusText(status) {
  return status === 'passed' ? '验证通过' : '存在异常'
}

function getStepResultText(passed) {
  if (passed === true) return '通过'
  if (passed === false) return '异常'
  return '未知'
}

function normalizeHistoryRecord(record = {}) {
  const detail = record.detail || {}
  return {
    ...record,
    detail: {
      feedback: detail.feedback || record.feedback || '',
      issues: Array.isArray(detail.issues) ? detail.issues : (Array.isArray(record.issues) ? record.issues : []),
      stepResults: Array.isArray(detail.stepResults) ? detail.stepResults : (Array.isArray(record.stepResults) ? record.stepResults : []),
      sopSteps: Array.isArray(detail.sopSteps) ? detail.sopSteps : (Array.isArray(record.sopSteps) ? record.sopSteps : []),
      uploadedVideo: detail.uploadedVideo || record.uploadedVideo || null
    }
  }
}

function hasHistoryDetail(record) {
  const normalized = normalizeHistoryRecord(record)
  const detail = normalized.detail
  return Boolean(
    detail.feedback ||
    detail.issues.length ||
    detail.stepResults.length ||
    detail.sopSteps.length ||
    detail.uploadedVideo?.name
  )
}

function openHistoryDetail(record) {
  selectedHistoryRecord.value = normalizeHistoryRecord(record)
  historyDetailVisible.value = true
}

const submitVideo = async () => {
  if (!currentVideo.value) {
    ElMessage.warning('请先上传视频')
    return
  }
  if (!apiConfig.apiKey?.trim()) {
    ElMessage.warning('请先配置 API Key')
    configVisible.value = true
    return
  }

  isEvaluating.value = true
  evaluationResult.value = null
  stageText.value = ''

  try {
    const result = await evaluateByStepAssets(currentSop.value, currentVideo.value)
    evaluationResult.value = result
    hasErrorInCurrentSop.value = !result.passed
    ElMessage.success('解析完成')
  } catch (error) {
    console.error(error)
    ElMessage.error(error?.message || '调用失败')
  } finally {
    isEvaluating.value = false
    if (!evaluationResult.value) stageText.value = ''
  }
}

const saveHistory = () => {
  const record = normalizeHistoryRecord({
    id: Date.now(),
    taskId: currentSop.value.id,
    taskName: currentSop.value.name,
    scene: currentSop.value.scene,
    finishTime: new Date().toLocaleString(),
    score: evaluationResult.value?.score ?? null,
    status: hasErrorInCurrentSop.value ? 'failed' : 'passed',
    detail: {
      feedback: evaluationResult.value?.feedback || '',
      issues: Array.isArray(evaluationResult.value?.issues) ? [...evaluationResult.value.issues] : [],
      stepResults: Array.isArray(evaluationResult.value?.stepResults)
        ? evaluationResult.value.stepResults.map(item => ({
          stepNo: item.stepNo ?? null,
          description: item.description || '',
          passed: typeof item.passed === 'boolean' ? item.passed : null,
          score: item.score ?? null,
          confidence: item.confidence ?? null,
          evidence: item.evidence || ''
        }))
        : [],
      sopSteps: Array.isArray(currentSop.value?.steps)
        ? currentSop.value.steps.map((step, index) => ({
          stepNo: step.stepNo || index + 1,
          description: step.description || '',
          videoName: step.videoMeta?.name || ''
        }))
        : [],
      uploadedVideo: currentVideo.value
        ? {
          name: currentVideo.value.name || '',
          type: currentVideo.value.type || '',
          size: currentVideo.value.size ?? null,
          lastModified: currentVideo.value.lastModified ?? null
        }
        : null
    }
  })
  historyList.value.unshift(record)
  localStorage.setItem(SOP_HISTORY_KEY, JSON.stringify(historyList.value))
}

const finishSop = () => {
  saveHistory()
  ElMessage.success('恭喜，SOP 流程验证完成并已记录！')
  backToList()
}

const retrySop = () => {
  currentVideo.value = null
  evaluationResult.value = null
  stageText.value = ''
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

.api-config-btn,
.logout-btn {
  color: #86868b;
  font-weight: 500;
}

.api-config-btn:hover,
.logout-btn:hover {
  color: #1d1d1f;
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

.main-content {
  padding: 40px 32px;
}

.content-wrapper {
  max-width: 800px;
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

/* Grid layout for Task Cards */
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

:deep(.minimal-radio-group .el-radio-button:first-child .el-radio-button__inner) {
  border-left: none;
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

.table-card {
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  padding: 8px;
  overflow: hidden;
}

.action-link-btn {
  color: #1d1d1f;
  font-weight: 500;
}

.action-link-btn:hover {
  color: #000000;
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

/* Execution View Styles */
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

.sop-overview {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e5e5ea;
  padding: 32px;
  margin-bottom: 24px;
}

.overview-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 24px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
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

.step-content {
  font-size: 15px;
  line-height: 1.6;
  color: #1d1d1f;
  padding-top: 2px;
}

.step-subline {
  font-size: 13px;
  color: #86868b;
  margin-top: 4px;
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

.step-desc {
  font-size: 18px;
  line-height: 1.5;
  color: #1d1d1f;
  margin: 0;
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

.stage-text {
  margin-top: 16px;
  font-size: 13px;
  color: #86868b;
}

.result-card {
  margin-top: 24px;
  border-radius: 16px;
  padding: 32px;
  border: 1px solid;
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

.success .result-icon { color: #1d1d1f; }
.error .result-icon { color: #86868b; }

.result-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.success h3 { color: #1d1d1f; }
.error h3 { color: #515154; }

.result-score {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
}

.result-feedback {
  font-size: 15px;
  line-height: 1.5;
  margin: 0 0 24px 0;
}

.success .result-feedback { color: #515154; }
.error .result-feedback { color: #86868b; }

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

.step-result-item {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 10px;
  padding: 14px 16px;
}

.step-result-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 6px;
}

.step-result-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.step-result-status {
  font-size: 13px;
  color: #86868b;
  white-space: nowrap;
}

.step-result-meta {
  font-size: 13px;
  color: #86868b;
  margin-bottom: 6px;
}

.evidence-text {
  font-size: 14px;
  line-height: 1.6;
  color: #515154;
}

.result-collapse {
  margin-bottom: 24px;
}

:deep(.result-collapse .el-collapse-item__header) {
  font-weight: 500;
  color: #1d1d1f;
}

.code-wrap {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  background: #f5f5f7;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
  color: #515154;
}

.result-actions {
  display: flex;
  gap: 16px;
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

.config-alert {
  margin-bottom: 20px;
}

.config-form {
  margin-top: 8px;
}

.config-row {
  display: flex;
  gap: 16px;
}

.config-row-small :deep(.el-input-number) {
  width: 100%;
}

.history-detail-layout {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.history-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.history-summary-card {
  background: #f5f5f7;
  border-radius: 12px;
  padding: 16px;
}

.history-summary-label {
  font-size: 12px;
  color: #86868b;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.history-summary-value {
  font-size: 14px;
  color: #1d1d1f;
  font-weight: 500;
  line-height: 1.5;
  word-break: break-word;
}

.history-detail-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-detail-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
}

.history-feedback-card {
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 12px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: #515154;
}

.issues-list.compact,
.step-result-list.compact {
  margin-bottom: 0;
}

.history-step-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-step-item {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 12px;
}

.history-step-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #000000;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.history-step-content {
  min-width: 0;
}

.history-step-text {
  font-size: 14px;
  line-height: 1.6;
  color: #1d1d1f;
}

.history-step-meta {
  margin-top: 4px;
  font-size: 13px;
  color: #86868b;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.submit-btn {
  background-color: #000000;
  border-color: #000000;
  border-radius: 8px;
}

.submit-btn:hover {
  background-color: #333333;
  border-color: #333333;
}

:deep(.minimal-dialog) {
  border-radius: 16px;
  overflow: hidden;
}

:deep(.minimal-dialog .el-dialog__header) {
  padding: 24px 24px 16px;
  margin-right: 0;
  border-bottom: 1px solid #e5e5ea;
}

:deep(.minimal-dialog .el-dialog__title) {
  font-weight: 600;
  font-size: 18px;
  color: #1d1d1f;
}

:deep(.minimal-dialog .el-dialog__body) {
  padding: 24px;
}

:deep(.minimal-form .el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: #515154;
  padding-bottom: 4px;
}

:deep(.minimal-form .el-input__wrapper) {
  box-shadow: 0 0 0 1px #e5e5ea inset;
  border-radius: 8px;
  padding: 4px 12px;
  transition: all 0.2s ease;
}

:deep(.minimal-form .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #000000 inset;
}

.flex-1 {
  flex: 1;
}

@media (max-width: 768px) {
  .main-content {
    padding: 24px 16px;
  }

  .top-nav {
    padding: 0 16px;
  }

  .nav-right {
    gap: 12px;
  }

  .header-titles,
  .file-preview,
  .step-result-top,
  .config-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .result-actions {
    flex-direction: column;
  }
}
</style>
