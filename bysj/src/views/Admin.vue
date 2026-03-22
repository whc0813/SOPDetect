<template>
  <el-container class="admin-layout">
    <!-- Sidebar -->
    <el-aside width="240px" class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>视觉智检</span>
      </div>
      <el-menu default-active="1" class="menu" :border="false">
        <el-menu-item index="1">
          <el-icon><Document /></el-icon>
          <span>SOP 管理</span>
        </el-menu-item>
        <el-menu-item index="2" disabled>
          <el-icon><DataLine /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-bottom">
        <div class="user-info">
          <el-avatar :size="32" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
          <span class="username">管理员</span>
        </div>
        <el-button text class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-aside>

    <!-- Main Content -->
    <el-container class="main-container">
      <el-header class="top-header">
        <div class="header-left">
          <h2>SOP 管理</h2>
        </div>
        <div class="header-right">
          <el-button type="primary" class="create-btn" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 新建 SOP
          </el-button>
        </div>
      </el-header>

      <el-main class="content-area">
        <div class="table-card">
          <el-table :data="sopList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }">
            <el-table-column prop="id" label="ID" width="140" />
            <el-table-column prop="name" label="SOP 名称" />
            <el-table-column prop="scene" label="适用场景" />
            <el-table-column prop="stepCount" label="步骤数" width="120" align="center">
              <template #default="scope">
                <el-tag size="small" class="minimal-tag">{{ scope.row.stepCount }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="示范视频" width="120" align="center">
              <template #default="scope">
                <el-tag size="small" class="minimal-tag">{{ scope.row.demoVideoCount || 0 }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="180" />
            <el-table-column label="操作" width="180" align="right">
              <template #default="scope">
                <el-button text class="action-btn" @click="openDebugSop(scope.row)">查看</el-button>
                <el-button text type="danger" class="action-btn" @click="deleteSop(scope.row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-main>
    </el-container>

    <!-- Create SOP Dialog -->
    <el-dialog v-model="dialogVisible" title="新建标准操作流程 (SOP)" width="600px" class="minimal-dialog" destroy-on-close>
      <el-form :model="sopForm" label-position="top" class="minimal-form">
        <div class="form-row">
          <el-form-item label="SOP 名称" class="flex-1">
            <el-input v-model="sopForm.name" placeholder="例如：实验室安全操作规范"></el-input>
          </el-form-item>
          <el-form-item label="适用场景" class="flex-1">
            <el-input v-model="sopForm.scene" placeholder="例如：化学实验室"></el-input>
          </el-form-item>
        </div>

        <el-form-item label="步骤数量">
          <el-input-number v-model="sopForm.stepCount" :min="1" :max="20" @change="handleStepCountChange" class="minimal-input-number" />
        </el-form-item>

        <div class="steps-section">
          <div class="section-title">步骤详情</div>
          <div v-for="(step, index) in sopForm.steps" :key="index" class="step-card">
            <div class="step-header">步骤 {{ index + 1 }}</div>
            <el-input 
              type="textarea" 
              v-model="step.description" 
              placeholder="请描述该步骤的标准动作，大模型将以此为比对依据..."
              :rows="2"
              resize="none"
              class="minimal-textarea"
            ></el-input>
            <div class="step-video-upload">
              <el-upload
                class="minimal-step-upload"
                action="#"
                :auto-upload="false"
                :show-file-list="false"
                accept="video/*"
                :on-change="(file) => handleStepVideoChange(index, file)"
              >
                <div v-if="!step.video" class="upload-trigger">
                  <el-icon><VideoCamera /></el-icon>
                  <span>上传标准动作视频</span>
                </div>
                <div v-else class="video-preview-item" @click.stop>
                  <div class="video-info">
                    <el-icon><VideoPlay /></el-icon>
                    <span>{{ step.video.name }}</span>
                  </div>
                  <el-button text class="remove-video-btn" @click.stop="removeStepVideo(index)">
                    <el-icon><Close /></el-icon>
                  </el-button>
                </div>
              </el-upload>
            </div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" @click="saveSop" :loading="isSaving">发布</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="debugVisible"
      title="SOP 预处理调试"
      width="880px"
      class="minimal-dialog"
      destroy-on-close
    >
      <div v-loading="debugLoading" class="debug-layout">
        <template v-if="selectedSopDebug">
          <div class="debug-summary">
            <div class="debug-summary-card">
              <div class="debug-summary-label">SOP 名称</div>
              <div class="debug-summary-value">{{ selectedSopDebug.name || '-' }}</div>
            </div>
            <div class="debug-summary-card">
              <div class="debug-summary-label">场景</div>
              <div class="debug-summary-value">{{ selectedSopDebug.scene || '-' }}</div>
            </div>
            <div class="debug-summary-card">
              <div class="debug-summary-label">步骤数</div>
              <div class="debug-summary-value">{{ selectedSopDebug.stepCount || 0 }}</div>
            </div>
          </div>

          <div v-for="step in selectedSopDebug.steps" :key="step.stepNo" class="debug-step-card">
            <div class="debug-step-top">
              <div>
                <div class="debug-step-index">步骤 {{ step.stepNo }}</div>
                <div class="debug-step-desc">{{ step.description || '未填写步骤说明' }}</div>
              </div>
              <el-tag size="small" class="minimal-tag">
                {{ step.referenceFrames?.length || 0 }} 张关键帧
              </el-tag>
            </div>

            <div class="debug-meta-grid">
              <div class="debug-meta-item">
                <span class="debug-meta-label">AI 预处理</span>
                <span class="debug-meta-value">{{ step.aiUsed ? '已启用' : '未启用（回退为均匀抽帧）' }}</span>
              </div>
              <div class="debug-meta-item">
                <span class="debug-meta-label">参考摘要</span>
                <span class="debug-meta-value">{{ step.referenceSummary || '暂无' }}</span>
              </div>
              <div class="debug-meta-item">
                <span class="debug-meta-label">关注区域提示</span>
                <span class="debug-meta-value">{{ step.roiHint || '暂无' }}</span>
              </div>
              <div class="debug-meta-item">
                <span class="debug-meta-label">时长</span>
                <span class="debug-meta-value">{{ formatDuration(step.referenceFeatures?.durationSec) }}</span>
              </div>
              <div class="debug-meta-item">
                <span class="debug-meta-label">原视频 FPS</span>
                <span class="debug-meta-value">{{ formatNumber(step.referenceFeatures?.fps) }}</span>
              </div>
              <div class="debug-meta-item">
                <span class="debug-meta-label">原视频帧数</span>
                <span class="debug-meta-value">{{ formatInteger(step.referenceFeatures?.frameCount) }}</span>
              </div>
              <div class="debug-meta-item debug-meta-wide">
                <span class="debug-meta-label">采样时间点</span>
                <span class="debug-meta-value">{{ formatTimestamps(step.referenceFeatures?.sampleTimestamps) }}</span>
              </div>
            </div>

            <div v-if="step.substeps?.length" class="debug-substeps">
              <div class="debug-substeps-title">AI 子步骤时间点</div>
              <div class="debug-substeps-list">
                <div v-for="(item, index) in step.substeps" :key="`${step.stepNo}-sub-${index}`" class="debug-substep-chip">
                  {{ item.title }} @ {{ formatDuration(item.timestampSec) }}
                </div>
              </div>
            </div>

            <div v-if="step.referenceFrames?.length" class="debug-frame-grid">
              <div v-for="(frame, index) in step.referenceFrames" :key="`${step.stepNo}-${index}`" class="debug-frame-card">
                <img :src="frame" :alt="`step-${step.stepNo}-frame-${index + 1}`" class="debug-frame-image" />
                <div class="debug-frame-caption">关键帧 {{ index + 1 }}</div>
              </div>
            </div>

            <div v-if="step.analysisFrames?.length" class="debug-analysis-section">
              <div class="debug-substeps-title">AI 预分析采样帧</div>
              <div class="debug-frame-grid">
                <div v-for="(frame, index) in step.analysisFrames" :key="`${step.stepNo}-analysis-${index}`" class="debug-frame-card">
                  <img :src="frame" :alt="`step-${step.stepNo}-analysis-${index + 1}`" class="debug-frame-image" />
                  <div class="debug-frame-caption">采样帧 {{ index + 1 }}</div>
                </div>
              </div>
            </div>

            <el-empty v-if="!step.referenceFrames?.length" description="当前步骤还没有可展示的预处理结果" class="debug-empty" />
          </div>
        </template>
      </div>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, DataLine, Plus, SwitchButton, Monitor, VideoCamera, VideoPlay, Close } from '@element-plus/icons-vue'

const router = useRouter()

const SOP_LIST_KEY = 'sopList'
const API_CONFIG_KEY = 'dashscopeEvalConfig'
const SOP_DB_NAME = 'sop-demo-db'
const SOP_STORE_NAME = 'videoFiles'

const sopList = ref([])
const dialogVisible = ref(false)
const isSaving = ref(false)
const debugVisible = ref(false)
const debugLoading = ref(false)
const selectedSopDebug = ref(null)

const sopForm = reactive({
  name: '',
  scene: '',
  stepCount: 1,
  steps: [createEmptyStep()]
})

function createEmptyStep() {
  return { description: '', video: null }
}

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

async function setStoreValue(key, value) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SOP_STORE_NAME, 'readwrite')
    tx.objectStore(SOP_STORE_NAME).put(value, key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function getStoreValue(key) {
  if (!key) return null
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SOP_STORE_NAME, 'readonly')
    const request = tx.objectStore(SOP_STORE_NAME).get(key)
    request.onsuccess = () => resolve(request.result || null)
    request.onerror = () => reject(request.error)
  })
}

async function deleteStoreValue(key) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(SOP_STORE_NAME, 'readwrite')
    tx.objectStore(SOP_STORE_NAME).delete(key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

function persistSopList() {
  localStorage.setItem(SOP_LIST_KEY, JSON.stringify(sopList.value))
}

function loadSopList() {
  const stored = localStorage.getItem(SOP_LIST_KEY)
  if (stored) {
    sopList.value = JSON.parse(stored).map(item => ({
      ...item,
      steps: (item.steps || []).map((step, index) => ({
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
    }))
    return
  }
  sopList.value = [
    {
      id: 'demo-sop-001',
      name: '穿戴防护装备规范',
      scene: '无菌车间',
      stepCount: 3,
      demoVideoCount: 0,
      createTime: '2023-10-24 10:00:00',
      steps: [
        { stepNo: 1, description: '戴上防护帽，完全遮盖头发', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null },
        { stepNo: 2, description: '佩戴护目镜', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null },
        { stepNo: 3, description: '穿上无菌防护服并拉好拉链', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null }
      ]
    }
  ]
  persistSopList()
}

onMounted(() => {
  loadSopList()
})

const handleLogout = () => {
  router.push('/login')
}

const openCreateDialog = () => {
  sopForm.name = ''
  sopForm.scene = ''
  sopForm.stepCount = 1
  sopForm.steps = [createEmptyStep()]
  dialogVisible.value = true
}

const handleStepCountChange = (newVal) => {
  const currentLen = sopForm.steps.length
  if (newVal > currentLen) {
    for (let i = currentLen; i < newVal; i++) {
      sopForm.steps.push(createEmptyStep())
    }
  } else if (newVal < currentLen) {
    sopForm.steps.splice(newVal)
  }
}

const handleStepVideoChange = (index, file) => {
  sopForm.steps[index].video = file?.raw || file
}

const removeStepVideo = (index) => {
  sopForm.steps[index].video = null
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error || new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

function loadApiConfig() {
  const stored = localStorage.getItem(API_CONFIG_KEY)
  if (!stored) return null

  try {
    const parsed = JSON.parse(stored)
    if (!parsed?.apiKey?.trim()) return null
    return parsed
  } catch {
    return null
  }
}

async function prepareStepReference(stepNo, description, video) {
  const videoDataUrl = await fileToDataUrl(video)
  const apiConfig = loadApiConfig()
  const response = await fetch('http://localhost:8000/api/prepare-step-video', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      stepNo,
      description,
      videoDataUrl,
      maxFrames: 8,
      apiConfig
    })
  })

  const result = await response.json().catch(() => null)
  if (!response.ok || !result?.success) {
    throw new Error(result?.detail || result?.message || '步骤参考素材预处理失败')
  }
  return result.data
}

const saveSop = async () => {
  if (!sopForm.name.trim()) {
    ElMessage.warning('请输入 SOP 名称')
    return
  }
  if (sopForm.steps.some(step => !step.description.trim())) {
    ElMessage.warning('请补全每一步的文字描述')
    return
  }
  if (sopForm.steps.some(step => !step.video)) {
    ElMessage.warning('请为每一步上传示范视频')
    return
  }

  isSaving.value = true
  try {
    if (!loadApiConfig()) {
      ElMessage.warning('未检测到可用 API 配置，本次将回退为普通均匀抽帧预处理')
    }
    const sopId = `sop-${Date.now()}`
    const steps = []

    for (let index = 0; index < sopForm.steps.length; index += 1) {
      const step = sopForm.steps[index]
      const stepNo = index + 1
      const referenceAssetKey = `${sopId}-step-${stepNo}-reference`
      const referenceAsset = await prepareStepReference(stepNo, step.description.trim(), step.video)
      await setStoreValue(referenceAssetKey, referenceAsset)

      steps.push({
        stepNo,
        description: step.description.trim(),
        videoKey: '',
        referenceAssetKey,
        referenceSummary: referenceAsset.referenceSummary || '',
        referenceFeatures: referenceAsset.referenceFeatures || null,
        substeps: Array.isArray(referenceAsset.substeps) ? referenceAsset.substeps : [],
        roiHint: referenceAsset.roiHint || '',
        aiUsed: Boolean(referenceAsset.aiUsed),
        videoMeta: {
          name: step.video.name,
          type: step.video.type,
          size: step.video.size,
          lastModified: step.video.lastModified
        }
      })
    }

    const newSop = {
      id: sopId,
      name: sopForm.name.trim(),
      scene: sopForm.scene.trim() || '未填写',
      stepCount: sopForm.stepCount,
      demoVideoCount: steps.length,
      createTime: new Date().toLocaleString(),
      steps
    }
    sopList.value.unshift(newSop)
    persistSopList()
    ElMessage.success('SOP 发布成功')
    dialogVisible.value = false
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败，请检查浏览器本地存储权限')
  } finally {
    isSaving.value = false
  }
}

const viewSop = (row) => {
  ElMessageBox.alert(
    `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
      ${(row.steps || []).map((s, i) => `
        <div style="margin-bottom: 12px; padding: 12px; background: #f5f5f7; border-radius: 8px;">
          <div style="font-size: 12px; color: #86868b; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <span>步骤 ${i + 1}</span>
            ${(s.videoMeta || s.video) ? `<span style="color: #1d1d1f; font-weight: 500; display: flex; align-items: center; gap: 4px;"><svg viewBox="0 0 1024 1024" width="14" height="14"><path d="M512 64a448 448 0 1 1 0 896 448 448 0 0 1 0-896z m0 832a384 384 0 0 0 0-768 384 384 0 0 0 0 768z m-96-544l256 160-256 160V352z" fill="currentColor"></path></svg> ${(s.videoMeta?.name || s.video?.name)}</span>` : ''}
          </div>
          <div style="font-size: 14px; color: #1d1d1f;">${s.description || ''}</div>
        </div>
      `).join('')}
    </div>`,
    row.name,
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '关闭',
      customClass: 'minimal-msgbox',
      showClose: false
    }
  ).catch(() => {})
}

void viewSop

function formatDuration(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(2)} s` : '-'
}

function formatNumber(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : '-'
}

function formatInteger(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${Math.round(num)}` : '-'
}

function formatTimestamps(values) {
  return Array.isArray(values) && values.length
    ? values.map(item => `${Number(item).toFixed(2)}s`).join(' / ')
    : '-'
}

const openDebugSop = async (row) => {
  debugVisible.value = true
  debugLoading.value = true
  selectedSopDebug.value = {
    ...row,
    steps: []
  }

  try {
    const steps = await Promise.all((row.steps || []).map(async (step, index) => {
      const asset = step.referenceAssetKey ? await getStoreValue(step.referenceAssetKey) : null
      return {
        stepNo: step.stepNo || index + 1,
        description: step.description || '',
        referenceSummary: asset?.referenceSummary || step.referenceSummary || '',
        referenceFeatures: asset?.referenceFeatures || step.referenceFeatures || null,
        referenceFrames: Array.isArray(asset?.referenceFrames) ? asset.referenceFrames : [],
        analysisFrames: Array.isArray(asset?.analysisFrames) ? asset.analysisFrames : [],
        substeps: Array.isArray(asset?.substeps) ? asset.substeps : (Array.isArray(step.substeps) ? step.substeps : []),
        roiHint: asset?.roiHint || step.roiHint || '',
        aiUsed: typeof asset?.aiUsed === 'boolean' ? asset.aiUsed : Boolean(step.aiUsed)
      }
    }))

    selectedSopDebug.value = {
      ...row,
      steps
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('加载预处理调试信息失败')
    debugVisible.value = false
  } finally {
    debugLoading.value = false
  }
}

const deleteSop = (row) => {
  ElMessageBox.confirm('确定要删除该 SOP 吗？', '提示', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    customClass: 'minimal-msgbox'
  }).then(async () => {
    try {
      const storeKeys = (row.steps || []).flatMap(item => [item.videoKey, item.referenceAssetKey].filter(Boolean))
      await Promise.all(storeKeys.map(item => deleteStoreValue(item)))
      sopList.value = sopList.value.filter(item => item.id !== row.id)
      persistSopList()
      ElMessage.success('删除成功')
    } catch (error) {
      console.error(error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  background-color: #f5f5f7;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.sidebar {
  background-color: #ffffff;
  border-right: 1px solid #e5e5ea;
  display: flex;
  flex-direction: column;
}

.brand {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  border-bottom: 1px solid #e5e5ea;
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

.menu {
  flex: 1;
  border-right: none;
  padding: 16px 0;
}

:deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 4px 16px;
  border-radius: 8px;
  color: #515154;
}

:deep(.el-menu-item.is-active) {
  background-color: #f5f5f7;
  color: #000000;
  font-weight: 500;
}

:deep(.el-menu-item:hover) {
  background-color: #f5f5f7;
}

.sidebar-bottom {
  padding: 16px 24px;
  border-top: 1px solid #e5e5ea;
}

.user-info {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.username {
  margin-left: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  color: #ff3b30;
  padding: 8px 0;
}

.logout-btn:hover {
  background-color: #fff0f0;
  color: #ff3b30;
}

.main-container {
  display: flex;
  flex-direction: column;
}

.top-header {
  height: 64px;
  background-color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  border-bottom: 1px solid #e5e5ea;
}

.top-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.create-btn {
  background-color: #000000;
  border-color: #000000;
  border-radius: 8px;
  font-weight: 500;
  padding: 8px 20px;
  transition: all 0.2s ease;
}

.create-btn:hover {
  background-color: #333333;
  border-color: #333333;
}

.content-area {
  padding: 32px;
}

.table-card {
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  padding: 8px;
  overflow: hidden;
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

.action-btn {
  font-weight: 500;
  padding: 4px 8px;
}

:deep(.minimal-tag) {
  background-color: #f5f5f7;
  color: #1d1d1f;
  border: 1px solid #e5e5ea;
  border-radius: 6px;
  padding: 0 12px;
  font-weight: 500;
}

/* Dialog Styles */
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

.form-row {
  display: flex;
  gap: 16px;
}

.flex-1 {
  flex: 1;
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

.steps-section {
  margin-top: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 16px;
}

.step-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  border: 1px solid #f0f0f0;
}

.step-header {
  font-size: 12px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  margin-bottom: 8px;
}

:deep(.minimal-textarea .el-textarea__inner) {
  box-shadow: none;
  background: #ffffff;
  border: 1px solid #e5e5ea;
  border-radius: 6px;
  padding: 8px 12px;
  font-family: inherit;
}

:deep(.minimal-textarea .el-textarea__inner:focus) {
  border-color: #000000;
}

.step-video-upload {
  margin-top: 12px;
}

.upload-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #ffffff;
  border: 1px dashed #d2d2d7;
  border-radius: 6px;
  color: #86868b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-trigger:hover {
  border-color: #000000;
  color: #1d1d1f;
}

.video-preview-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: #e5e5ea;
  border-radius: 6px;
  font-size: 13px;
  color: #1d1d1f;
}

.video-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.remove-video-btn {
  padding: 4px;
  height: auto;
  color: #86868b;
}

.remove-video-btn:hover {
  color: #ff3b30;
}

.debug-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 200px;
}

.debug-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.debug-summary-card {
  background: #f5f5f7;
  border-radius: 12px;
  padding: 16px;
}

.debug-summary-label,
.debug-meta-label,
.debug-step-index,
.debug-frame-caption {
  font-size: 12px;
  color: #86868b;
}

.debug-summary-value {
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  word-break: break-word;
}

.debug-step-card {
  border: 1px solid #e5e5ea;
  border-radius: 14px;
  padding: 18px;
  background: #ffffff;
}

.debug-step-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.debug-step-desc {
  margin-top: 6px;
  font-size: 15px;
  line-height: 1.6;
  color: #1d1d1f;
}

.debug-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.debug-meta-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: #fafafa;
  border-radius: 10px;
}

.debug-meta-wide {
  grid-column: 1 / -1;
}

.debug-meta-value {
  font-size: 14px;
  line-height: 1.6;
  color: #1d1d1f;
  word-break: break-word;
}

.debug-substeps,
.debug-analysis-section {
  margin-bottom: 16px;
}

.debug-substeps-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 10px;
}

.debug-substeps-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.debug-substep-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #f5f5f7;
  color: #1d1d1f;
  font-size: 13px;
}

.debug-frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.debug-frame-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 12px;
}

.debug-frame-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 8px;
  background: #e5e5ea;
}

.debug-frame-caption {
  margin-top: 8px;
}

.debug-empty {
  padding: 8px 0 0;
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
</style>
