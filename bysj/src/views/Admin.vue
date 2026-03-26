<template>
  <div class="admin-layout">

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>标准行为识别</span>
      </div>

      <nav class="nav-menu">
        <button :class="['nav-item', { active: activeMenu === 'manage' }]" @click="handleMenuSelect('manage')">
          <el-icon class="nav-icon"><Document /></el-icon>
          <span>SOP 管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'users' }]" @click="handleMenuSelect('users')">
          <el-icon class="nav-icon"><SwitchButton /></el-icon>
          <span>用户管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'stats' }]" @click="handleMenuSelect('stats')">
          <el-icon class="nav-icon"><DataLine /></el-icon>
          <span>数据统计</span>
        </button>
      </nav>

      <div class="sidebar-bottom">
        <div class="user-card">
          <div class="avatar">{{ userInitials }}</div>
          <span class="username">{{ currentUserName }}</span>
        </div>
        <button class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </button>
      </div>
    </aside>

    <!-- Main Area -->
    <div class="main-container">
      <header class="top-header">
        <div class="header-left">
          <h2>{{ panelHeaderTitle }}</h2>
          <p class="header-subtitle">{{ panelHeaderSubtitle }}</p>
        </div>
        <div class="header-right">
          <button class="pill-btn" @click="openConfigDialog">API 配置</button>
          <button v-if="activeMenu === 'stats' || activeMenu === 'users'" class="pill-btn" @click="reloadCurrentView">刷新数据</button>
          <button v-if="activeMenu === 'manage'" class="pill-btn primary-pill" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            新建 SOP
          </button>
        </div>
      </header>

      <main class="content-area">

        <!-- SOP 管理 -->
        <div v-if="activeMenu === 'manage'" class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SOP 名称</th>
                <th>适用场景</th>
                <th style="text-align:center">步骤数</th>
                <th>创建时间</th>
                <th style="text-align:right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in sopList" :key="row.id">
                <td>{{ row.name }}</td>
                <td>{{ row.scene }}</td>
                <td style="text-align:center">
                  <span class="badge badge-default">{{ row.stepCount }}</span>
                </td>
                <td>{{ row.createTime }}</td>
                <td style="text-align:right">
                  <button class="text-btn" @click="openDebugSop(row)">查看</button>
                  <button class="text-btn danger" @click="deleteCurrentSop(row)">删除</button>
                </td>
              </tr>
              <tr v-if="sopList.length === 0">
                <td colspan="5" class="empty-row">暂无 SOP</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 用户管理 -->
        <div v-else-if="activeMenu === 'users'" class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>昵称</th>
                <th>账号</th>
                <th style="text-align:center">角色</th>
                <th style="text-align:center">状态</th>
                <th>最近登录</th>
                <th>创建时间</th>
                <th style="text-align:center">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in userList" :key="row.id">
                <td>{{ row.displayName }}</td>
                <td>{{ row.username }}</td>
                <td style="text-align:center">
                  <span :class="['badge', row.role === 'admin' ? 'badge-danger' : 'badge-default']">
                    {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                  </span>
                </td>
                <td style="text-align:center">
                  <span :class="['badge', row.status === 'active' ? 'badge-success' : 'badge-warning']">
                    {{ row.status === 'active' ? '启用' : '禁用' }}
                  </span>
                </td>
                <td>{{ row.lastLoginAt }}</td>
                <td>{{ row.createdAt }}</td>
                <td style="text-align:center">
                  <button
                    class="text-btn"
                    :disabled="row.role === 'admin' && row.id === currentUser?.id"
                    @click="toggleUserStatus(row)"
                  >{{ row.status === 'active' ? '禁用' : '启用' }}</button>
                </td>
              </tr>
              <tr v-if="userList.length === 0">
                <td colspan="7" class="empty-row">暂无用户</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 数据统计 -->
        <div v-else class="stats-view">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">SOP 总数</div>
              <div class="stat-value">{{ summaryStats.totalSops }}</div>
              <div class="stat-desc">当前已发布流程数量</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">执行记录</div>
              <div class="stat-value">{{ summaryStats.totalExecutions }}</div>
              <div class="stat-desc">累计采集到的用户执行记录</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">通过率</div>
              <div class="stat-value">{{ formatRate(summaryStats.passRate) }}</div>
              <div class="stat-desc">当前自动评测整体通过表现</div>
            </div>
            <div class="stat-card highlight-card">
              <div class="stat-label">待复核</div>
              <div class="stat-value">{{ summaryStats.pendingReviewCount }}</div>
              <div class="stat-desc">还需要人工确认的记录</div>
            </div>
          </div>

          <div class="section-block">
            <div class="section-head">
              <div class="section-title">SOP 维度统计</div>
              <div class="section-subtitle">按流程查看执行次数、通过率和平均得分</div>
            </div>
            <div class="table-card">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>SOP 名称</th>
                    <th>适用场景</th>
                    <th style="text-align:center">执行次数</th>
                    <th style="text-align:center">通过次数</th>
                    <th style="text-align:center">通过率</th>
                    <th style="text-align:center">平均得分</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in sopStatsList" :key="row.taskId || row.taskName">
                    <td>{{ row.taskName }}</td>
                    <td>{{ row.scene }}</td>
                    <td style="text-align:center">{{ row.totalCount }}</td>
                    <td style="text-align:center">{{ row.passedCount }}</td>
                    <td style="text-align:center">{{ formatRate(row.passRate) }}</td>
                    <td style="text-align:center">{{ formatAverageScore(row.averageScore) }}</td>
                  </tr>
                  <tr v-if="sopStatsList.length === 0">
                    <td colspan="6" class="empty-row">暂无统计数据</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="section-block">
            <div class="section-head">
              <div class="section-title">执行记录列表</div>
              <div class="section-subtitle">从这里查看明细并处理人工复核</div>
            </div>
            <div class="table-card">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>SOP 名称</th>
                    <th>所属用户</th>
                    <th>完成时间</th>
                    <th style="text-align:center">AI 结论</th>
                    <th style="text-align:center">人工复核</th>
                    <th style="text-align:right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in historyList" :key="row.id">
                    <td>{{ row.taskName }}</td>
                    <td>{{ row.userDisplayName || row.userName || '未知用户' }}</td>
                    <td>{{ row.finishTime }}</td>
                    <td style="text-align:center">
                      <span :class="['badge', row.status === 'passed' ? 'badge-success' : 'badge-danger']">
                        {{ getStatusText(row.status) }}
                      </span>
                    </td>
                    <td style="text-align:center">
                      <span :class="['badge', getReviewBadgeClass(row.manualReview?.status)]">
                        {{ getReviewStatusText(row.manualReview?.status) }}
                      </span>
                    </td>
                    <td style="text-align:right">
                      <button class="text-btn" @click="openHistoryDetail(row)">详情</button>
                      <button class="text-btn" @click="openReviewDialog(row)">复核</button>
                    </td>
                  </tr>
                  <tr v-if="historyList.length === 0">
                    <td colspan="6" class="empty-row">暂无执行记录</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </main>
    </div>

    <!-- ─── 新建 SOP 对话框 ─────────────────────────────────── -->
    <el-dialog v-model="dialogVisible" title="新建标准操作流程 (SOP)" width="640px" class="minimal-dialog" destroy-on-close>
      <el-form :model="sopForm" label-position="top" class="minimal-form">
        <div class="form-row">
          <el-form-item label="SOP 名称" class="flex-1">
            <el-input v-model="sopForm.name" placeholder="例如：实验室安全操作规范" />
          </el-form-item>
          <el-form-item label="适用场景" class="flex-1">
            <el-input v-model="sopForm.scene" placeholder="例如：化学实验室" />
          </el-form-item>
        </div>

        <el-form-item label="步骤数量">
          <el-input-number v-model="sopForm.stepCount" :min="1" :max="20" @change="handleStepCountChange" class="minimal-input-number" />
        </el-form-item>

        <div class="steps-section">
          <div class="section-title">步骤详情</div>
          <div v-for="(step, index) in sopForm.steps" :key="index" class="step-card">
            <div class="step-header">步骤 {{ index + 1 }}</div>
            <el-input v-model="step.description" type="textarea" :rows="2" resize="none" class="minimal-textarea" placeholder="请描述该步骤的标准动作，大模型将以此为比对依据..." />
            <el-upload action="#" :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="(file) => handleStepVideoChange(index, file)">
              <el-button class="upload-btn">{{ step.video ? step.video.name : '可选：上传示范视频' }}</el-button>
            </el-upload>
            <div class="step-hint">不上传视频时，该步骤会按文字 SOP 规则参与模型评估。</div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" :loading="isSaving" @click="saveSop">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ─── API 配置对话框 ────────────────────────────────────── -->
    <el-dialog v-model="configVisible" title="后端 API 配置" width="640px" class="minimal-dialog">
      <el-alert type="info" :closable="false" show-icon title="当前配置保存到后端，管理员创建 SOP 和用户执行评估都会共用这份配置。" />
      <el-form label-position="top" class="minimal-form config-form">
        <el-form-item label="API Key">
          <el-input v-model="apiConfig.apiKey" type="password" show-password />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="Base URL" class="flex-1">
            <el-input v-model="apiConfig.baseURL" />
          </el-form-item>
          <el-form-item label="模型名称" class="flex-1">
            <el-input v-model="apiConfig.model" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="fps" class="flex-1">
            <el-input-number v-model="apiConfig.fps" :min="0.1" :max="10" :step="0.5" />
          </el-form-item>
          <el-form-item label="temperature" class="flex-1">
            <el-input-number v-model="apiConfig.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="timeout(ms)" class="flex-1">
            <el-input-number v-model="apiConfig.timeoutMs" :min="10000" :max="300000" :step="10000" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetApiConfig">恢复默认</el-button>
          <el-button type="primary" class="submit-btn" @click="saveApiConfig">保存配置</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- ─── SOP 预处理详情对话框 ─────────────────────────────── -->
    <el-dialog v-model="debugVisible" title="SOP 预处理详情" width="900px" class="minimal-dialog">
      <div v-loading="debugLoading" class="detail-wrap">
        <div v-if="selectedSopDebug">
          <div class="summary debug-summary">{{ selectedSopDebug.name }} / {{ selectedSopDebug.scene }}</div>
          <div v-for="step in selectedSopDebug.steps" :key="step.stepNo" class="detail-box debug-step-box">
            <div class="detail-title">步骤 {{ step.stepNo }}: {{ step.description }}</div>
            <div class="detail-text">摘要：{{ step.referenceSummary || '暂无' }}</div>
            <div class="detail-text">预处理 Token：{{ formatTokenUsage(step.tokenUsage) }}</div>
            <div class="detail-text">ROI：{{ step.roiHint || '暂无' }}</div>
            <div class="detail-text">关键时刻：{{ formatSubsteps(step.substeps) }}</div>
            <div class="detail-text">参考模式：{{ step.referenceMode === 'text' ? '仅文字 SOP' : '示范视频关键帧' }}</div>
            <div v-if="step.demoVideo?.url" class="manual-segmentation-box">
              <div class="manual-title">手动关键帧时间点</div>
              <div class="manual-subtitle">用英文逗号分隔秒数，例如：0.8, 1.6, 3.2</div>
              <el-input v-model="step.manualTimestampInput" placeholder="输入时间点" />
              <el-button type="primary" plain class="manual-btn" :loading="step.manualSegmentationLoading" @click="applyManualSegmentation(step)">重新生成关键帧</el-button>
            </div>
            <div v-else-if="step.referenceMode === 'video'" class="detail-text muted-text">该步骤已有示范关键帧，但原始示范视频引用缺失，暂时无法手动切帧。重新上传示范视频后可恢复。</div>
            <div v-else class="detail-text muted-text">该步骤当前仅按文字 SOP 评估，未绑定示范视频。</div>
            <div v-if="!step.demoVideo?.url" class="demo-video-box">
              <div class="manual-title">补传示范视频</div>
              <div class="manual-subtitle">补传后会重新生成该步骤的参考关键帧、关键时刻和 ROI 信息。</div>
              <el-upload action="#" :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="(file) => handleDebugStepVideoChange(step, file)">
                <el-button class="upload-btn">{{ step.reuploadVideo ? step.reuploadVideo.name : '选择示范视频' }}</el-button>
              </el-upload>
              <el-button type="primary" plain class="manual-btn" :loading="step.demoVideoUploadLoading" @click="replaceStepDemoVideo(step)">上传并重建参考</el-button>
            </div>
            <div class="frame-grid">
              <img v-for="(frame, index) in step.referenceFrames || []" :key="`${step.stepNo}-${index}`" :src="frame" class="frame" />
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ─── 执行记录详情对话框 ────────────────────────────────── -->
    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px" class="minimal-dialog">
      <div v-if="selectedHistoryRecord" class="detail-wrap">
        <div class="summary">{{ selectedHistoryRecord.taskName }} / {{ selectedHistoryRecord.userDisplayName || selectedHistoryRecord.userName || '未知用户' }} / {{ selectedHistoryRecord.finishTime }}</div>
        <div class="detail-box">
          <div class="detail-title">综合反馈</div>
          <div class="detail-text">{{ selectedHistoryRecord.detail.feedback || '暂无反馈' }}</div>
        </div>
        <div class="detail-box">
          <div class="detail-title">上传视频</div>
          <video v-if="historyVideoUrl" :src="historyVideoUrl" controls class="video" />
          <el-empty v-else description="未记录上传视频" />
        </div>
        <div class="detail-box" v-if="selectedHistoryRecord.detail.issues?.length">
          <div class="detail-title">问题列表</div>
          <div class="tag-list">
            <el-tag v-for="(item, index) in selectedHistoryRecord.detail.issues" :key="index">{{ item }}</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- ─── 人工复核对话框 ─────────────────────────────────────── -->
    <el-dialog v-model="reviewDialogVisible" title="人工复核" width="560px" class="minimal-dialog">
      <div v-if="reviewTarget" class="detail-wrap">
        <div class="summary">{{ reviewTarget.taskName }} / {{ reviewTarget.userDisplayName || reviewTarget.userName || '未知用户' }} / {{ reviewTarget.finishTime }}</div>
        <video v-if="reviewVideoUrl" :src="reviewVideoUrl" controls class="video" />
        <el-form :model="reviewForm" label-position="top" class="minimal-form">
          <el-form-item label="复核结论">
            <el-radio-group v-model="reviewForm.status" class="review-radio-group">
              <el-radio-button label="approved">复核通过</el-radio-button>
              <el-radio-button label="rejected">复核不通过</el-radio-button>
              <el-radio-button label="needs_attention">需要整改</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复核意见">
            <el-input v-model="reviewForm.note" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="reviewDialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" @click="saveManualReview">保存</el-button>
        </div>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataLine, Document, Monitor, Plus, SwitchButton } from '@element-plus/icons-vue'
import { clearAuthSession, createSop, fetchAuthorizedMediaBlobUrl, fileToDataUrl, getConfig, getCurrentUser, getHistoryDetail, getSopDetail, getStats, listHistory, listSops, listUsers, logout, removeSop, reviewHistory, updateConfig, updateSopStepDemoVideo, updateSopStepSegmentation, updateUserStatus } from '../api/client'

const router = useRouter()
const activeMenu = ref('manage')
const sopList = ref([])
const userList = ref([])
const historyList = ref([])
const summaryStats = ref({ totalSops: 0, totalExecutions: 0, pendingReviewCount: 0, passRate: 0 })
const sopStatsList = ref([])
const dialogVisible = ref(false)
const isSaving = ref(false)
const configVisible = ref(false)
const debugVisible = ref(false)
const debugLoading = ref(false)
const selectedSopDebug = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const historyVideoUrl = ref('')
const reviewDialogVisible = ref(false)
const reviewTarget = ref(null)
const reviewVideoUrl = ref('')
const reviewForm = reactive({ status: 'approved', note: '' })
const sopForm = reactive({ name: '', scene: '', stepCount: 1, steps: [{ description: '', video: null }] })
const currentUser = ref(getCurrentUser())
const DEFAULT_API_CONFIG = {
  apiKey: '',
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  model: 'qwen3.5-plus',
  fps: 2,
  temperature: 0.1,
  timeoutMs: 120000
}
const apiConfig = reactive({ ...DEFAULT_API_CONFIG })

const headerTitle = computed(() => activeMenu.value === 'manage' ? 'SOP 管理' : '数据统计')
const headerSubtitle = computed(() => activeMenu.value === 'manage' ? '统一管理 SOP 内容、步骤说明和示范视频' : '查看整体执行情况，并处理需要人工确认的记录')
const currentUserName = computed(() => currentUser.value?.displayName || currentUser.value?.username || '管理员')
const userInitials = computed(() => {
  const name = currentUser.value?.displayName || currentUser.value?.username || 'A'
  return name.charAt(0).toUpperCase()
})
const panelHeaderTitle = computed(() => {
  if (activeMenu.value === 'manage') return 'SOP 管理'
  if (activeMenu.value === 'users') return '用户管理'
  return '数据统计'
})
const panelHeaderSubtitle = computed(() => {
  if (activeMenu.value === 'manage') return '统一管理 SOP 内容、步骤说明和示范视频'
  if (activeMenu.value === 'users') return '查看已注册账号，并启用或禁用普通用户'
  return '查看整体执行情况，并处理需要人工确认的记录'
})

function createEmptyStep() {
  return { description: '', video: null }
}

async function loadApiConfig() {
  const config = (await getConfig()).data || {}
  Object.assign(apiConfig, DEFAULT_API_CONFIG, config)
}

async function openConfigDialog() {
  try {
    await loadApiConfig()
    configVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载配置失败')
  }
}

async function saveApiConfig() {
  try {
    await updateConfig({ ...apiConfig })
    configVisible.value = false
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存配置失败')
  }
}

function resetApiConfig() {
  Object.assign(apiConfig, DEFAULT_API_CONFIG)
}

function revokeVideoUrl(targetRef) {
  if (targetRef.value) {
    URL.revokeObjectURL(targetRef.value)
    targetRef.value = ''
  }
}

function normalizeHistory(record = {}) {
  return {
    ...record,
    detail: {
      feedback: record.detail?.feedback || '',
      issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
      uploadedVideo: record.detail?.uploadedVideo || null
    },
    manualReview: record.manualReview || null
  }
}

async function loadSopList() {
  sopList.value = (await listSops()).data || []
}

async function loadHistoryList() {
  historyList.value = ((await listHistory()).data || []).map(normalizeHistory)
}

async function loadUserList() {
  userList.value = (await listUsers()).data || []
}

async function loadStats() {
  const result = await getStats()
  summaryStats.value = result.data?.summaryStats || summaryStats.value
  sopStatsList.value = result.data?.sopStatsList || []
}

async function reloadCurrentView() {
  await loadSopList()
  if (activeMenu.value === 'users') {
    await loadUserList()
  } else if (activeMenu.value === 'stats') {
    await Promise.all([loadHistoryList(), loadStats()])
  }
}

function handleMenuSelect(index) {
  activeMenu.value = index
  reloadCurrentView().catch((error) => ElMessage.error(error.message || '加载失败'))
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

function openCreateDialog() {
  sopForm.name = ''
  sopForm.scene = ''
  sopForm.stepCount = 1
  sopForm.steps = [createEmptyStep()]
  dialogVisible.value = true
}

function handleStepCountChange(value) {
  while (sopForm.steps.length < value) sopForm.steps.push(createEmptyStep())
  if (sopForm.steps.length > value) sopForm.steps.splice(value)
}

function handleStepVideoChange(index, file) {
  sopForm.steps[index].video = file?.raw || file
}

async function saveSop() {
  if (!sopForm.name.trim()) return ElMessage.warning('请输入 SOP 名称')
  if (sopForm.steps.some((item) => !item.description.trim())) return ElMessage.warning('请补全步骤描述')

  isSaving.value = true
  try {
    const steps = await Promise.all(sopForm.steps.map(async (item) => ({
      description: item.description.trim(),
      videoDataUrl: item.video ? await fileToDataUrl(item.video) : '',
      videoMeta: item.video ? {
        name: item.video.name || '',
        type: item.video.type || '',
        size: item.video.size ?? null,
        lastModified: item.video.lastModified ?? null
      } : null
    })))
    const result = await createSop({ name: sopForm.name.trim(), scene: sopForm.scene.trim(), steps })
    dialogVisible.value = false
    await reloadCurrentView()
    ElMessage.success('SOP 已保存')
    if (result.warnings?.length) ElMessage.warning(result.warnings[0])
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    isSaving.value = false
  }
}

async function openDebugSop(row) {
  debugVisible.value = true
  debugLoading.value = true
  try {
    selectedSopDebug.value = buildDebugSopState((await getSopDetail(row.id)).data)
  } catch (error) {
    ElMessage.error(error.message || '加载详情失败')
    debugVisible.value = false
  } finally {
    debugLoading.value = false
  }
}

async function deleteCurrentSop(row) {
  try {
    await ElMessageBox.confirm('确定删除该 SOP 吗？', '提示', { type: 'warning', customClass: 'minimal-msgbox' })
    await removeSop(row.id)
    await Promise.all([reloadCurrentView(), loadStats()])
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
  }
}

async function openHistoryDetail(row) {
  try {
    selectedHistoryRecord.value = normalizeHistory((await getHistoryDetail(row.id)).data)
    revokeVideoUrl(historyVideoUrl)
    const mediaPath = selectedHistoryRecord.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      historyVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    historyDetailVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载详情失败')
  }
}

async function openReviewDialog(row) {
  try {
    reviewTarget.value = normalizeHistory((await getHistoryDetail(row.id)).data)
    revokeVideoUrl(reviewVideoUrl)
    const mediaPath = reviewTarget.value?.detail?.uploadedVideo?.url || ''
    if (mediaPath) {
      reviewVideoUrl.value = await fetchAuthorizedMediaBlobUrl(mediaPath)
    }
    reviewForm.status = reviewTarget.value.manualReview?.status || (reviewTarget.value.status === 'passed' ? 'approved' : 'needs_attention')
    reviewForm.note = reviewTarget.value.manualReview?.note || ''
    reviewDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载复核对象失败')
  }
}

async function saveManualReview() {
  if (!reviewTarget.value) return
  try {
    await reviewHistory(reviewTarget.value.id, { status: reviewForm.status, note: reviewForm.note.trim() })
    reviewDialogVisible.value = false
    await Promise.all([loadHistoryList(), loadStats()])
    ElMessage.success('复核已保存')
  } catch (error) {
    ElMessage.error(error.message || '保存复核失败')
  }
}

async function toggleUserStatus(row) {
  if (!row?.id) return
  const nextStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await updateUserStatus(row.id, { status: nextStatus })
    await loadUserList()
    ElMessage.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
  } catch (error) {
    ElMessage.error(error.message || '更新用户状态失败')
  }
}

function buildDebugSopState(data) {
  return {
    ...data,
    steps: (data.steps || []).map((step) => ({
      ...step,
      manualTimestampInput: Array.isArray(step.referenceFeatures?.sampleTimestamps) ? step.referenceFeatures.sampleTimestamps.join(', ') : '',
      manualSegmentationLoading: false,
      reuploadVideo: null,
      demoVideoUploadLoading: false
    }))
  }
}

function handleDebugStepVideoChange(step, file) {
  step.reuploadVideo = file?.raw || file
}

function parseTimestampInput(value) {
  return String(value || '')
    .split(/[\s,，、;；]+/)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item >= 0)
}

function formatTokenUsage(usage) {
  if (!usage) return '暂无'
  const input = Number.isFinite(Number(usage.inputTokens)) ? Number(usage.inputTokens) : '-'
  const output = Number.isFinite(Number(usage.outputTokens)) ? Number(usage.outputTokens) : '-'
  const total = Number.isFinite(Number(usage.totalTokens)) ? Number(usage.totalTokens) : '-'
  return `输入 ${input} / 输出 ${output} / 总计 ${total}`
}

async function applyManualSegmentation(step) {
  const timestamps = parseTimestampInput(step.manualTimestampInput)
  if (!timestamps.length) return ElMessage.warning('请输入至少一个有效时间点')
  if (!selectedSopDebug.value?.id) return

  step.manualSegmentationLoading = true
  try {
    const result = await updateSopStepSegmentation(selectedSopDebug.value.id, step.stepNo, { timestamps })
    selectedSopDebug.value = buildDebugSopState(result.data)
    await loadSopList()
    ElMessage.success('关键帧已按手动时间点重建')
  } catch (error) {
    ElMessage.error(error.message || '重建关键帧失败')
  } finally {
    step.manualSegmentationLoading = false
  }
}

async function replaceStepDemoVideo(step) {
  if (!step?.reuploadVideo) return ElMessage.warning('请先选择示范视频')
  if (!selectedSopDebug.value?.id) return

  step.demoVideoUploadLoading = true
  try {
    const file = step.reuploadVideo
    const result = await updateSopStepDemoVideo(selectedSopDebug.value.id, step.stepNo, {
      videoDataUrl: await fileToDataUrl(file),
      videoMeta: {
        name: file.name || '',
        type: file.type || '',
        size: file.size ?? null,
        lastModified: file.lastModified ?? null
      }
    })
    selectedSopDebug.value = buildDebugSopState(result.data)
    await loadSopList()
    ElMessage.success('示范视频已更新，并重新生成参考结果')
  } catch (error) {
    ElMessage.error(error.message || '更新示范视频失败')
  } finally {
    step.demoVideoUploadLoading = false
  }
}

function formatAverageScore(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(1)} / 100` : '-'
}

function formatRate(value) {
  const num = Number(value)
  return Number.isFinite(num) ? `${num.toFixed(0)}%` : '0%'
}

function getStatusText(status) {
  return status === 'passed' ? '通过' : '异常'
}

function getReviewStatusText(status) {
  if (status === 'approved') return '复核通过'
  if (status === 'rejected') return '复核不通过'
  if (status === 'needs_attention') return '需要整改'
  return '待复核'
}

function getReviewTagClass(status) {
  if (status === 'approved') return 'is-review-approved'
  if (status === 'rejected') return 'is-review-rejected'
  if (status === 'needs_attention') return 'is-review-attention'
  return 'is-review-pending'
}

function getReviewBadgeClass(status) {
  if (status === 'approved') return 'badge-success'
  if (status === 'rejected') return 'badge-danger'
  if (status === 'needs_attention') return 'badge-warning'
  return 'badge-default'
}

function formatSubsteps(list) {
  return Array.isArray(list) && list.length ? list.map((item) => `${item.title}@${Number(item.timestampSec).toFixed(2)}s`).join(' / ') : '暂无'
}

onMounted(() => {
  reloadCurrentView().catch((error) => ElMessage.error(error.message || '初始化失败'))
})

onUnmounted(() => {
  revokeVideoUrl(historyVideoUrl)
  revokeVideoUrl(reviewVideoUrl)
})
</script>

<style scoped>
/* ─── Layout Shell ───────────────────────────────────────── */
.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
}

/* ─── Sidebar ─────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--bg-elevated);
  border-right: 1px solid var(--line-soft);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
  display: flex;
  flex-direction: column;
  padding: 16px 0 20px;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 16px 20px;
  padding: 10px 12px;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-main);
  border-radius: 14px;
  background: rgba(120, 120, 128, 0.08);
}

.brand-logo {
  width: 30px;
  height: 30px;
  background: linear-gradient(150deg, var(--accent), var(--accent-deep));
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 15px;
  flex-shrink: 0;
}

/* ─── Nav Menu ────────────────────────────────────────────── */
.nav-menu {
  flex: 1;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--text-soft);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard),
    transform var(--duration-micro) var(--ease-standard);
}

.nav-item:hover {
  background: rgba(120, 120, 128, 0.1);
  color: var(--text-main);
}

.nav-item.active {
  background: rgba(120, 120, 128, 0.14);
  color: var(--text-main);
  font-weight: 600;
}

.nav-item:active {
  transform: scale(0.98);
}

.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

/* ─── Sidebar Bottom ──────────────────────────────────────── */
.sidebar-bottom {
  margin: 16px 10px 0;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 14px;
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
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.logout-btn:hover {
  background: var(--apple-fill);
  color: var(--text-main);
}

.logout-btn:active {
  transform: scale(0.97);
}

/* ─── Main Container ──────────────────────────────────────── */
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ─── Top Header ──────────────────────────────────────────── */
.top-header {
  min-height: 88px;
  background: var(--bg-elevated);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  border-bottom: 1px solid var(--line-soft);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-left h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.header-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-soft);
  line-height: 1.4;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* ─── Pill Buttons ────────────────────────────────────────── */
.pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  min-height: 44px;
  border-radius: 9999px;
  border: 1px solid var(--line-soft);
  background: var(--apple-fill);
  color: var(--text-main);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    border-color var(--duration-short) var(--ease-standard),
    transform var(--duration-micro) var(--ease-standard);
}

.pill-btn:hover {
  background: rgba(120, 120, 128, 0.18);
  border-color: var(--line-strong);
}

.pill-btn:active {
  transform: scale(0.97);
}

.primary-pill {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}

.primary-pill:hover {
  background: var(--accent-deep);
  border-color: var(--accent-deep);
}

/* ─── Content Area ────────────────────────────────────────── */
.content-area {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* ─── Data Table ──────────────────────────────────────────── */
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
  padding: 14px 16px;
  font-size: 14px;
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
  color: var(--text-faint) !important;
  padding: 48px 16px !important;
  font-size: 14px;
}

/* ─── Badges ──────────────────────────────────────────────── */
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
  font-size: 13px;
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
.text-btn.danger { color: var(--danger); }
.text-btn.danger:hover { background: rgba(255, 59, 48, 0.08); }
.text-btn:disabled { opacity: 0.35; cursor: not-allowed; }

/* ─── Stats ───────────────────────────────────────────────── */
.stats-view {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: 16px;
  padding: 24px;
  min-height: 148px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.highlight-card {
  border-color: rgba(0, 122, 255, 0.28);
  background: linear-gradient(160deg, rgba(0, 122, 255, 0.06) 0%, transparent 60%), var(--surface);
}

.stat-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.04em;
  line-height: 1;
}

.stat-desc {
  font-size: 13px;
  color: var(--text-soft);
  line-height: 1.5;
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

.section-subtitle {
  font-size: 14px;
  color: var(--text-soft);
}

/* ─── Dialogs ─────────────────────────────────────────────── */
:deep(.minimal-dialog) {
  border-radius: 20px !important;
  overflow: hidden;
  border: 1px solid var(--line-soft) !important;
  background: var(--surface-strong) !important;
}

:deep(.minimal-dialog .el-dialog__header) {
  padding: 22px 24px 16px;
  margin-right: 0;
  border-bottom: 1px solid var(--line-soft);
  background: transparent;
}

:deep(.minimal-dialog .el-dialog__title) {
  font-weight: 700;
  font-size: 19px;
  color: var(--text-main);
  letter-spacing: -0.02em;
}

:deep(.minimal-dialog .el-dialog__body) {
  padding: 20px 24px;
  background: transparent;
}

:deep(.minimal-dialog .el-dialog__footer) {
  background: transparent;
}

/* ─── Dialog Form Styles ──────────────────────────────────── */
.form-row {
  display: flex;
  gap: 16px;
}

.flex-1 { flex: 1; }

:deep(.minimal-form .el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-soft);
  padding-bottom: 4px;
}

:deep(.minimal-form .el-input__wrapper) {
  border: 1.5px solid var(--line-soft);
  border-radius: 12px;
  padding: 4px 12px;
  background: var(--surface-strong);
  box-shadow: none !important;
  transition:
    border-color var(--duration-short) var(--ease-standard),
    box-shadow var(--duration-short) var(--ease-standard);
}

:deep(.minimal-form .el-input__wrapper.is-focus) {
  border-color: var(--apple-blue) !important;
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.12) !important;
}

:deep(.minimal-form .el-input__inner) {
  color: var(--text-main);
}

:deep(.minimal-form .el-textarea__inner) {
  background: var(--surface-strong);
  border: 1.5px solid var(--line-soft);
  border-radius: 12px;
  padding: 8px 12px;
  font-family: inherit;
  color: var(--text-main);
  box-shadow: none !important;
  resize: none;
}

:deep(.minimal-form .el-textarea__inner:focus) {
  border-color: var(--apple-blue);
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.12) !important;
  outline: none;
}

/* Steps Section in Create Dialog */
.steps-section {
  margin-top: 20px;
}

.step-card {
  background: var(--surface-secondary);
  border-radius: 12px;
  padding: 16px;
  margin-top: 10px;
  border: 1px solid var(--line-soft);
}

.step-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}

.upload-btn {
  margin-top: 10px;
  min-height: 40px;
  border-radius: 10px !important;
  border-color: var(--line-soft) !important;
  background: var(--surface-strong) !important;
  color: var(--text-main) !important;
  font-size: 13px !important;
}

.step-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-faint);
  line-height: 1.6;
}

/* Config Form */
.config-form {
  margin-top: 16px;
}

:deep(.minimal-dialog .el-input-number) { width: 100%; }

:deep(.minimal-dialog .el-input-number .el-input__wrapper) {
  border-radius: 0;
  border-left: none;
  border-right: none;
}

:deep(.minimal-dialog .el-input-number__decrease) {
  width: 38px;
  border-color: var(--line-soft);
  background: rgba(120, 120, 128, 0.08);
  color: var(--text-soft);
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
}

:deep(.minimal-dialog .el-input-number__increase) {
  width: 38px;
  border-color: var(--line-soft);
  background: rgba(120, 120, 128, 0.08);
  color: var(--text-soft);
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
}

/* Alert in config dialog */
:deep(.minimal-dialog .el-alert) {
  border-radius: 12px;
  border: 1px solid transparent;
  background: rgba(0, 122, 255, 0.07);
  color: var(--text-soft);
}

/* Dialog Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 24px 22px;
}

.submit-btn {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
  border-radius: 9999px !important;
  min-height: 44px !important;
  font-weight: 600 !important;
}

.submit-btn:hover {
  background-color: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

.dialog-footer :deep(.el-button:not(.submit-btn)) {
  min-height: 44px;
  border-radius: 9999px;
  border-color: var(--line-soft);
  background: var(--apple-fill);
  color: var(--text-soft);
  padding: 8px 18px;
}

.dialog-footer :deep(.el-button:not(.submit-btn):hover) {
  background: rgba(120, 120, 128, 0.18);
  color: var(--text-main);
}

/* ─── Debug Dialog ────────────────────────────────────────── */
.detail-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.summary {
  font-weight: 600;
  color: var(--text-main);
  font-size: 14px;
}

.debug-summary {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 4px;
}

.detail-box {
  background: var(--surface-strong);
  border-radius: 14px;
  padding: 16px 18px;
  border: 1px solid var(--line-soft);
}

.debug-step-box {
  border-radius: 16px;
  padding: 20px 22px;
}

.debug-step-box + .debug-step-box {
  margin-top: 4px;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 8px;
}

.debug-step-box .detail-title {
  font-size: 16px;
  line-height: 1.5;
  margin-bottom: 12px;
}

.detail-text {
  color: var(--text-soft);
  font-size: 14px;
  line-height: 1.7;
}

.debug-step-box .detail-text + .detail-text {
  margin-top: 6px;
}

.manual-segmentation-box,
.demo-video-box {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
  background: var(--surface-secondary);
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--line-soft);
}

.manual-title {
  font-weight: 600;
  color: var(--text-main);
  font-size: 14px;
}

.manual-subtitle,
.muted-text {
  font-size: 12px;
  color: var(--text-faint);
  line-height: 1.7;
}

.manual-btn {
  align-self: flex-start;
  border-radius: 9999px !important;
}

.frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.frame {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 10px;
  background: var(--surface-secondary);
}

.video {
  width: 100%;
  max-height: 340px;
  background: #000;
  border-radius: 16px;
  display: block;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Review Radio */
:deep(.review-radio-group .el-radio-button__inner) {
  min-width: 108px;
  border-color: var(--line-soft);
  background: var(--surface-strong);
  color: var(--text-soft);
}

:deep(.review-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
}

/* ─── Dark Mode ───────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  .sidebar {
    background: var(--bg-elevated);
  }

  .stat-card {
    background: var(--surface);
  }

  .brand,
  .nav-item.active {
    background: rgba(120, 120, 128, 0.16);
  }
}

/* ─── Reduced Motion ──────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .nav-item,
  .logout-btn,
  .pill-btn,
  .text-btn {
    transition: none;
  }
}

/* ─── Responsive ──────────────────────────────────────────── */
@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 768px) {
  .admin-layout {
    flex-direction: column;
    height: auto;
    overflow: auto;
  }

  .sidebar {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    height: auto;
    padding: 12px;
    border-right: none;
    border-bottom: 1px solid var(--line-soft);
  }

  .brand { margin-bottom: 0; }

  .nav-menu {
    flex-direction: row;
    gap: 4px;
  }

  .nav-item { height: 40px; }

  .sidebar-bottom {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding-top: 10px;
    margin-top: 8px;
  }

  .user-card { padding-bottom: 0; }

  .main-container { overflow: visible; }

  .content-area { padding: 16px; }

  .top-header {
    padding: 16px;
    min-height: auto;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-right {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .stats-grid { grid-template-columns: 1fr; }

  .form-row { flex-direction: column; }
}
</style>
