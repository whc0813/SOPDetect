<template>
  <div class="admin-layout">
    <AppBlobs />

    <!-- Sidebar backdrop (mobile) -->
    <div :class="['sidebar-backdrop', { 'is-open': sidebarOpen }]" @click="sidebarOpen = false"></div>

    <!-- Sidebar -->
    <aside :class="['sidebar', { 'is-open': sidebarOpen }]">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>标准行为识别</span>
      </div>

      <nav class="nav-menu">
        <button :class="['nav-item', { active: activeMenu === 'manage' }]" @click="handleMenuSelect('manage')">
          <span class="nav-icon-wrap icon-blue"><el-icon><Document /></el-icon></span>
          <span>SOP 管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'users' }]" @click="handleMenuSelect('users')">
          <span class="nav-icon-wrap icon-purple"><el-icon><SwitchButton /></el-icon></span>
          <span>用户管理</span>
        </button>
        <button :class="['nav-item', { active: activeMenu === 'stats' }]" @click="handleMenuSelect('stats')">
          <span class="nav-icon-wrap icon-orange"><el-icon><DataLine /></el-icon></span>
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
        <button class="hamburger-btn" @click="sidebarOpen = !sidebarOpen">
          <el-icon><Fold /></el-icon>
        </button>
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
        <GroupedList
          v-if="activeMenu === 'manage'"
          :columns="sopColumns"
          :data="sopList"
          empty-text="暂无 SOP"
        >
          <template #cell-stepCount="{ value }">
            <StatusBadge type="default">{{ value }}</StatusBadge>
          </template>
          <template #cell-actions="{ row }">
            <button class="text-btn" @click="openDebugSop(row)">查看</button>
            <button class="text-btn danger" @click="deleteCurrentSop(row)">删除</button>
          </template>
        </GroupedList>

        <!-- 用户管理 -->
        <GroupedList
          v-else-if="activeMenu === 'users'"
          :columns="userColumns"
          :data="userList"
          empty-text="暂无用户"
        >
          <template #cell-role="{ row }">
            <StatusBadge :type="row.role === 'admin' ? 'danger' : 'default'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </StatusBadge>
          </template>
          <template #cell-status="{ row }">
            <StatusBadge :type="row.status === 'active' ? 'success' : 'warning'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </StatusBadge>
          </template>
          <template #cell-actions="{ row }">
            <button
              class="text-btn"
              :disabled="row.role === 'admin' && row.id === currentUser?.id"
              @click="toggleUserStatus(row)"
            >{{ row.status === 'active' ? '禁用' : '启用' }}</button>
          </template>
        </GroupedList>

        <!-- 数据统计 -->
        <div v-else class="stats-view">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon icon-blue"><el-icon><Document /></el-icon></div>
              <div class="stat-label">SOP 总数</div>
              <div class="stat-value">{{ summaryStats.totalSops }}</div>
              <div class="stat-desc">当前已发布流程数量</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-green"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">执行记录</div>
              <div class="stat-value">{{ summaryStats.totalExecutions }}</div>
              <div class="stat-desc">累计采集到的用户执行记录</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-orange"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">通过率</div>
              <div class="stat-value">{{ formatRate(summaryStats.passRate) }}</div>
              <div class="stat-desc">当前自动评测整体通过表现</div>
            </div>
            <div class="stat-card highlight-card">
              <div class="stat-icon icon-red"><el-icon><DataLine /></el-icon></div>
              <div class="stat-label">待复核</div>
              <div class="stat-value">{{ summaryStats.pendingReviewCount }}</div>
              <div class="stat-desc">还需要人工确认的记录</div>
            </div>
          </div>

          <div class="section-block">
            <SectionHeader title="SOP 维度统计" subtitle="按流程查看执行次数、通过率和平均得分" />
            <GroupedList
              :columns="sopStatsColumns"
              :data="sopStatsList"
              empty-text="暂无统计数据"
            >
              <template #cell-passRate="{ value }">{{ formatRate(value) }}</template>
              <template #cell-averageScore="{ value }">{{ formatAverageScore(value) }}</template>
            </GroupedList>
          </div>

          <div class="section-block">
            <SectionHeader title="执行记录列表" subtitle="从这里查看明细并处理人工复核" />
            <div class="filter-toolbar">
              <div class="filter-form">
                <el-input
                  v-model="historyFilters.keyword"
                  class="filter-input"
                  clearable
                  placeholder="按 SOP 名称搜索"
                  @keyup.enter="applyHistoryFilters"
                />
                <el-select v-model="historyFilters.aiStatus" class="filter-select" placeholder="AI 结论" clearable>
                  <el-option label="全部 AI 结论" value="" />
                  <el-option label="通过" value="passed" />
                  <el-option label="异常" value="failed" />
                </el-select>
                <el-select v-model="historyFilters.reviewStatus" class="filter-select" placeholder="人工复核" clearable>
                  <el-option label="全部复核状态" value="" />
                  <el-option label="待复核" value="pending" />
                  <el-option label="复核通过" value="approved" />
                  <el-option label="复核不通过" value="rejected" />
                  <el-option label="需要整改" value="needs_attention" />
                </el-select>
                <el-select v-model="historyFilters.sortOrder" class="filter-select filter-sort" placeholder="时间排序">
                  <el-option label="按时间倒序" value="desc" />
                  <el-option label="按时间正序" value="asc" />
                </el-select>
              </div>
              <div class="filter-actions">
                <button
                  type="button"
                  :class="['pill-btn', 'filter-pill', { active: historyFilters.reviewStatus === 'pending' }]"
                  @click="togglePendingReviewFilter"
                >
                  只看待复核
                </button>
                <button
                  type="button"
                  :class="['pill-btn', 'filter-pill', { active: historyFilters.aiStatus === 'failed' }]"
                  @click="toggleAiAbnormalFilter"
                >
                  只看 AI 判定异常
                </button>
                <el-button class="filter-action-btn" type="primary" @click="applyHistoryFilters">查询</el-button>
                <el-button class="filter-action-btn" @click="resetHistoryFilters">重置</el-button>
              </div>
            </div>
            <GroupedList
              v-loading="historyLoading"
              :columns="historyColumns"
              :data="historyList"
              :empty-text="historyEmptyText"
            >
              <template #cell-userName="{ row }">{{ row.userDisplayName || row.userName || '未知用户' }}</template>
              <template #cell-aiStatus="{ row }">
                <StatusBadge :type="row.status === 'passed' ? 'success' : 'danger'">
                  {{ getStatusText(row.status) }}
                </StatusBadge>
              </template>
              <template #cell-reviewStatus="{ row }">
                <StatusBadge :type="getReviewBadgeType(row.manualReview?.status)">
                  {{ getReviewStatusText(row.manualReview?.status) }}
                </StatusBadge>
              </template>
              <template #cell-actions="{ row }">
                <button class="text-btn" @click="openHistoryDetail(row)">详情</button>
                <button class="text-btn" @click="openReviewDialog(row)">复核</button>
              </template>
            </GroupedList>
          </div>
        </div>

      </main>
    </div>

    <!-- ─── 新建 SOP 对话框 ─────────────────────────────────── -->
    <el-dialog v-model="dialogVisible" title="新建标准操作流程 (SOP)" width="640px" class="apple-dialog" destroy-on-close>
      <el-form :model="sopForm" label-position="top" class="apple-form">
        <div class="form-row">
          <el-form-item label="SOP 名称" class="flex-1">
            <el-input v-model="sopForm.name" placeholder="例如：实验室安全操作规范" />
          </el-form-item>
          <el-form-item label="适用场景" class="flex-1">
            <el-input v-model="sopForm.scene" placeholder="例如：化学实验室" />
          </el-form-item>
        </div>

        <el-form-item label="步骤数量">
          <el-input-number v-model="sopForm.stepCount" :min="1" :max="20" @change="handleStepCountChange" />
        </el-form-item>

        <div class="steps-section">
          <div class="section-title">步骤详情</div>
          <div v-for="(step, index) in sopForm.steps" :key="index" class="step-card">
            <div class="step-header">步骤 {{ index + 1 }}</div>
            <el-input v-model="step.description" type="textarea" :rows="2" resize="none" placeholder="请描述该步骤的标准动作，大模型将以此为比对依据..." />
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
    <el-dialog v-model="configVisible" title="后端 API 配置" width="640px" class="apple-dialog">
      <el-alert type="info" :closable="false" show-icon title="当前配置保存到后端，管理员创建 SOP 和用户执行评估都会共用这份配置。" />
      <el-form label-position="top" class="apple-form config-form">
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
    <el-dialog v-model="debugVisible" title="SOP 预处理详情" width="900px" class="apple-dialog">
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
    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px" class="apple-dialog">
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
    <el-dialog v-model="reviewDialogVisible" title="人工复核" width="560px" class="apple-dialog">
      <div v-if="reviewTarget" class="detail-wrap">
        <div class="summary">{{ reviewTarget.taskName }} / {{ reviewTarget.userDisplayName || reviewTarget.userName || '未知用户' }} / {{ reviewTarget.finishTime }}</div>
        <video v-if="reviewVideoUrl" :src="reviewVideoUrl" controls class="video" />
        <el-form :model="reviewForm" label-position="top" class="apple-form">
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
import { DataLine, Document, Fold, Monitor, Plus, SwitchButton } from '@element-plus/icons-vue'
import { clearAuthSession, createSop, fetchAuthorizedMediaBlobUrl, fileToDataUrl, getConfig, getCurrentUser, getHistoryDetail, getSopDetail, getStats, isAuthSessionError, listHistory, listSops, listUsers, logout, removeSop, reviewHistory, updateConfig, updateSopStepDemoVideo, updateSopStepSegmentation, updateUserStatus } from '../api/client'
import AppBlobs from '../components/AppBlobs.vue'
import GroupedList from '../components/GroupedList.vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusBadge from '../components/StatusBadge.vue'

const router = useRouter()
const sidebarOpen = ref(false)
const activeMenu = ref('manage')
const sopList = ref([])
const userList = ref([])
const historyList = ref([])
const historyLoading = ref(false)
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
const historyFilters = reactive({
  keyword: '',
  aiStatus: '',
  reviewStatus: '',
  sortOrder: 'desc'
})
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

const hasActiveHistoryFilters = computed(() => {
  return !!(
    String(historyFilters.keyword || '').trim() ||
    historyFilters.aiStatus ||
    historyFilters.reviewStatus ||
    historyFilters.sortOrder !== 'desc'
  )
})
const historyEmptyText = computed(() => hasActiveHistoryFilters.value ? '当前筛选条件下暂无记录' : '暂无执行记录')

const sopColumns = [
  { key: 'name', label: 'SOP 名称' },
  { key: 'scene', label: '适用场景' },
  { key: 'stepCount', label: '步骤数', align: 'center' },
  { key: 'createTime', label: '创建时间' },
  { key: 'actions', label: '操作', align: 'right' }
]
const userColumns = [
  { key: 'displayName', label: '昵称' },
  { key: 'username', label: '账号' },
  { key: 'role', label: '角色', align: 'center' },
  { key: 'status', label: '状态', align: 'center' },
  { key: 'lastLoginAt', label: '最近登录' },
  { key: 'createdAt', label: '创建时间' },
  { key: 'actions', label: '操作', align: 'center' }
]
const sopStatsColumns = [
  { key: 'taskName', label: 'SOP 名称' },
  { key: 'scene', label: '适用场景' },
  { key: 'totalCount', label: '执行次数', align: 'center' },
  { key: 'passedCount', label: '通过次数', align: 'center' },
  { key: 'passRate', label: '通过率', align: 'center' },
  { key: 'averageScore', label: '平均得分', align: 'center' }
]
const historyColumns = [
  { key: 'taskName', label: 'SOP 名称' },
  { key: 'userName', label: '所属用户' },
  { key: 'finishTime', label: '完成时间' },
  { key: 'aiStatus', label: 'AI 结论', align: 'center' },
  { key: 'reviewStatus', label: '人工复核', align: 'center' },
  { key: 'actions', label: '操作', align: 'right' }
]

function showErrorMessage(error, fallback) {
  if (isAuthSessionError(error)) return
  ElMessage.error(error.message || fallback)
}

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
    showErrorMessage(error, '加载配置失败')
  }
}

async function saveApiConfig() {
  try {
    await updateConfig({ ...apiConfig })
    configVisible.value = false
    ElMessage.success('配置已保存')
  } catch (error) {
    showErrorMessage(error, '保存配置失败')
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
  historyLoading.value = true
  try {
    historyList.value = ((await listHistory({
      keyword: historyFilters.keyword,
      aiStatus: historyFilters.aiStatus,
      reviewStatus: historyFilters.reviewStatus,
      sortOrder: historyFilters.sortOrder
    })).data || []).map(normalizeHistory)
  } finally {
    historyLoading.value = false
  }
}

async function loadUserList() {
  userList.value = (await listUsers()).data || []
}

async function loadStats() {
  const result = await getStats()
  summaryStats.value = result.data?.summaryStats || summaryStats.value
  sopStatsList.value = result.data?.sopStatsList || []
}

function applyHistoryFilters() {
  loadHistoryList().catch((error) => showErrorMessage(error, '加载执行记录失败'))
}

function resetHistoryFilters() {
  historyFilters.keyword = ''
  historyFilters.aiStatus = ''
  historyFilters.reviewStatus = ''
  historyFilters.sortOrder = 'desc'
  applyHistoryFilters()
}

function togglePendingReviewFilter() {
  historyFilters.reviewStatus = historyFilters.reviewStatus === 'pending' ? '' : 'pending'
  applyHistoryFilters()
}

function toggleAiAbnormalFilter() {
  historyFilters.aiStatus = historyFilters.aiStatus === 'failed' ? '' : 'failed'
  applyHistoryFilters()
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
  sidebarOpen.value = false
  reloadCurrentView().catch((error) => showErrorMessage(error, '加载失败'))
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
    showErrorMessage(error, '保存失败')
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
    showErrorMessage(error, '加载详情失败')
    debugVisible.value = false
  } finally {
    debugLoading.value = false
  }
}

async function deleteCurrentSop(row) {
  try {
    await ElMessageBox.confirm('确定删除该 SOP 吗？', '提示', { type: 'warning', customClass: 'apple-msgbox' })
    await removeSop(row.id)
    await Promise.all([reloadCurrentView(), loadStats()])
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') showErrorMessage(error, '删除失败')
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
    showErrorMessage(error, '加载详情失败')
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
    showErrorMessage(error, '加载复核对象失败')
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
    showErrorMessage(error, '保存复核失败')
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
    showErrorMessage(error, '更新用户状态失败')
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
    showErrorMessage(error, '重建关键帧失败')
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
    showErrorMessage(error, '更新示范视频失败')
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

function getReviewBadgeClass(status) {
  if (status === 'approved') return 'badge-success'
  if (status === 'rejected') return 'badge-danger'
  if (status === 'needs_attention') return 'badge-warning'
  return 'badge-default'
}

function getReviewBadgeType(status) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  if (status === 'needs_attention') return 'warning'
  return 'default'
}

function formatSubsteps(list) {
  return Array.isArray(list) && list.length ? list.map((item) => `${item.title}@${Number(item.timestampSec).toFixed(2)}s`).join(' / ') : '暂无'
}

onMounted(() => {
  reloadCurrentView().catch((error) => showErrorMessage(error, '初始化失败'))
})

onUnmounted(() => {
  revokeVideoUrl(historyVideoUrl)
  revokeVideoUrl(reviewVideoUrl)
})
</script>

<style scoped>
/* ── Layout Shell ────────────────────────────────────────── */

.admin-layout {
  position: relative;
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
  font-family: var(--font-family);
}

/* ── Sidebar ─────────────────────────────────────────────── */

.sidebar {
  position: relative;
  z-index: 10;
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--material-regular);
  border-right: 1px solid var(--separator);
  backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  display: flex;
  flex-direction: column;
  padding: var(--sp-4) 0 var(--sp-5);
  overflow-y: auto;
}

@media (prefers-color-scheme: dark) {
  .sidebar {
    box-shadow: 1px 0 0 rgba(0, 0, 0, 0.3);
  }
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: var(--sp-1) var(--sp-4) var(--sp-5);
  padding: 10px var(--sp-3);
  font-size: var(--fs-headline);
  font-weight: 700;
  color: var(--text-main);
  border-radius: 14px;
  background: var(--fill-quaternary);
}

.brand-logo {
  width: 30px;
  height: 30px;
  background: linear-gradient(150deg, var(--accent), var(--accent-deep));
  border-radius: var(--radius-sm);
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 15px;
  flex-shrink: 0;
}

/* ── Nav Menu ────────────────────────────────────────────── */

.nav-menu {
  flex: 1;
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  width: 100%;
  height: 44px;
  padding: 0 var(--sp-3);
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-soft);
  font-size: var(--fs-subheadline);
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
  background: var(--fill-quaternary);
  color: var(--text-main);
}

.nav-item.active {
  background: rgba(0, 122, 255, 0.12);
  color: var(--accent);
  font-weight: 600;
}

@media (prefers-color-scheme: dark) {
  .nav-item.active {
    background: rgba(10, 132, 255, 0.18);
  }
}

.nav-item:active {
  transform: scale(0.97);
}

.nav-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}

.icon-blue   { background: linear-gradient(140deg, #1D9BF0, #007AFF); }
.icon-purple { background: linear-gradient(140deg, #BF5AF2, #9B59F5); }
.icon-orange { background: linear-gradient(140deg, #FF9F0A, #FF6B00); }
.icon-green  { background: linear-gradient(140deg, #34C759, #28A745); }
.icon-red    { background: linear-gradient(140deg, #FF6B6B, #FF3B30); }

/* ── Sidebar Bottom ──────────────────────────────────────── */

.sidebar-bottom {
  margin: var(--sp-4) 10px 0;
  padding-top: var(--sp-4);
  border-top: 1px solid var(--line-soft);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--sp-2) var(--sp-2) 14px;
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
  gap: var(--sp-2);
  width: 100%;
  height: var(--touch-target);
  padding: 0 14px;
  border: none;
  border-radius: var(--radius-md);
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
  background: var(--fill-quaternary);
  color: var(--text-main);
}

.logout-btn:active {
  transform: scale(0.97);
}

/* ── Main Container ──────────────────────────────────────── */

.main-container {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Top Header ──────────────────────────────────────────── */

.top-header {
  height: 64px;
  background: var(--material-regular);
  border-bottom: 1px solid var(--separator);
  backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(160%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--sp-8);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
}

.header-left h2 {
  margin: 0;
  font-size: var(--fs-title2);
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.03em;
  line-height: 1.1;
}

.header-subtitle {
  margin: 0;
  font-size: var(--fs-footnote);
  color: var(--text-faint);
  line-height: 1.4;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* ── Content Area ────────────────────────────────────────── */

.content-area {
  flex: 1;
  padding: var(--sp-6);
  overflow-y: auto;
}

/* ── Stats ───────────────────────────────────────────────── */

.stats-view {
  display: flex;
  flex-direction: column;
  gap: var(--sp-8);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-4);
}

.stat-card {
  position: relative;
  background: var(--material-chrome);
  backdrop-filter: blur(var(--blur-md)) saturate(150%);
  -webkit-backdrop-filter: blur(var(--blur-md)) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.60);
  border-radius: var(--radius-xl);
  padding: var(--sp-5) var(--sp-6) var(--sp-6);
  min-height: 160px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: box-shadow var(--duration-short) ease, transform var(--duration-short) ease;
}

@media (prefers-color-scheme: dark) {
  .stat-card {
    border-color: rgba(84, 84, 88, 0.4);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  }
}

.stat-card:hover {
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.10), 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.stat-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  margin-bottom: var(--sp-1);
}

.highlight-card {
  border-color: rgba(255, 59, 48, 0.22);
  background: linear-gradient(160deg, rgba(255, 59, 48, 0.04) 0%, transparent 60%), var(--material-chrome);
}

.stat-label {
  font-size: var(--fs-caption1);
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 44px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.04em;
  line-height: 1;
}

.stat-desc {
  font-size: var(--fs-footnote);
  color: var(--text-soft);
  line-height: 1.5;
}

/* ── Filter ──────────────────────────────────────────────── */

.filter-input {
  min-width: 220px;
  flex: 1 1 260px;
}

.filter-select {
  width: 160px;
}

.filter-sort {
  width: 150px;
}

/* ── Debug Dialog ────────────────────────────────────────── */

.debug-summary {
  font-size: var(--fs-subheadline);
  line-height: 1.6;
  margin-bottom: var(--sp-1);
}

.debug-step-box {
  border-radius: var(--radius-lg);
  padding: var(--sp-5) 22px;
}

.debug-step-box + .debug-step-box {
  margin-top: var(--sp-1);
}

.debug-step-box .detail-title {
  font-size: var(--fs-callout);
  line-height: 1.5;
  margin-bottom: var(--sp-3);
}

.debug-step-box .detail-text + .detail-text {
  margin-top: 6px;
}

.manual-segmentation-box,
.demo-video-box {
  margin-top: var(--sp-4);
  padding: 18px var(--sp-5);
  border-radius: 14px;
  background: var(--info-fill);
  border: 1px solid rgba(0, 122, 255, 0.14);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.manual-title {
  font-weight: 600;
  color: var(--text-main);
  font-size: 14px;
}

.manual-subtitle,
.muted-text {
  font-size: var(--fs-caption1);
  color: var(--text-faint);
  line-height: 1.7;
}

.manual-btn {
  align-self: flex-start;
  border-radius: var(--radius-full) !important;
}

.frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: var(--sp-3);
  margin-top: var(--sp-4);
}

.frame {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 10px;
  background: var(--surface-secondary);
}

/* ── Config Form ─────────────────────────────────────────── */

.config-form {
  margin-top: var(--sp-4);
}

/* ── Review Radio — segmented control style ──────────────── */

:deep(.review-radio-group) {
  background: var(--fill-tertiary);
  border-radius: 11px;
  padding: 3px;
  display: inline-flex;
  gap: 3px;
}

:deep(.review-radio-group .el-radio-button) {
  flex: 1;
}

:deep(.review-radio-group .el-radio-button__inner) {
  border: none !important;
  border-radius: var(--radius-sm) !important;
  background: transparent !important;
  color: var(--text-soft) !important;
  font-size: 14px;
  font-weight: 500;
  min-width: 100px;
  height: 38px;
  line-height: 38px;
  padding: 0 14px;
  transition: background var(--duration-short), color var(--duration-short), box-shadow var(--duration-short);
  box-shadow: none !important;
}

:deep(.review-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--accent) !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 6px rgba(0, 122, 255, 0.35) !important;
}

/* ── Hamburger Button ────────────────────────────────────── */

.hamburger-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: var(--touch-target);
  height: var(--touch-target);
  border: none;
  background: var(--fill-quaternary);
  color: var(--text-main);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 20px;
  transition: background var(--duration-short);
}

.hamburger-btn:hover {
  background: var(--fill-secondary);
}

/* ── Sidebar Backdrop ───────────────────────────────────── */

.sidebar-backdrop {
  display: none;
}

/* ── Responsive ──────────────────────────────────────────── */

@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 768px) {
  .hamburger-btn {
    display: flex;
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 99;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-medium) var(--ease-standard);
  }

  .sidebar-backdrop.is-open {
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    z-index: 100;
    transform: translateX(-100%);
    transition: transform var(--duration-medium) var(--ease-spring);
  }

  .sidebar.is-open {
    transform: translateX(0);
  }

  .main-container { overflow: visible; margin-left: 0; }
  .content-area { padding: var(--sp-4); }

  .filter-toolbar,
  .filter-form,
  .filter-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input,
  .filter-select,
  .filter-sort {
    width: 100%;
  }

  .top-header {
    padding: var(--sp-4);
    height: auto;
    flex-direction: row;
    flex-wrap: wrap;
    gap: var(--sp-3);
  }

  .header-left {
    flex: 1;
    flex-direction: column;
    gap: var(--sp-1);
  }

  .header-right {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .stats-grid { grid-template-columns: 1fr; }
  .form-row { flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  .nav-item,
  .logout-btn,
  .stat-card,
  .sidebar,
  .sidebar-backdrop {
    transition: none;
  }
}
</style>
