<template>
  <el-container class="admin-layout">
    <el-aside width="240px" class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <el-icon><Monitor /></el-icon>
        </div>
        <span>视觉巡检</span>
      </div>

      <el-menu :default-active="activeMenu" class="menu" :border="false" @select="handleMenuSelect">
        <el-menu-item index="manage">
          <el-icon><Document /></el-icon>
          <span>SOP 管理</span>
        </el-menu-item>
        <el-menu-item index="users">
          <el-icon><SwitchButton /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="stats">
          <el-icon><DataLine /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-bottom">
        <div class="user-info">
          <el-avatar :size="32" src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png" />
          <span class="username">{{ currentUserName }}</span>
        </div>
        <el-button text class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header class="top-header">
        <div class="header-left">
          <h2>{{ panelHeaderTitle }}</h2>
          <p class="header-subtitle">{{ panelHeaderSubtitle }}</p>
        </div>
        <div class="header-right">
          <el-button v-if="activeMenu === 'stats' || activeMenu === 'users'" class="refresh-btn" @click="reloadCurrentView">
            刷新数据
          </el-button>
          <el-button v-if="activeMenu === 'manage'" type="primary" class="create-btn" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            新建 SOP
          </el-button>
        </div>
      </el-header>

      <el-main class="content-area">
        <div v-if="activeMenu === 'manage'" class="table-card">
          <el-table :data="sopList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无 SOP">
            <el-table-column prop="name" label="SOP 名称" min-width="180" />
            <el-table-column prop="scene" label="适用场景" min-width="140" />
            <el-table-column prop="stepCount" label="步骤数" width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" class="minimal-tag">{{ row.stepCount }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="180" />
            <el-table-column label="操作" width="180" align="right">
              <template #default="{ row }">
                <el-button text class="action-btn" @click="openDebugSop(row)">查看</el-button>
                <el-button text type="danger" class="action-btn" @click="deleteCurrentSop(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-else-if="activeMenu === 'users'" class="table-card">
          <el-table :data="userList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无用户">
            <el-table-column prop="displayName" label="昵称" min-width="140" />
            <el-table-column prop="username" label="账号" min-width="140" />
            <el-table-column label="角色" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.role === 'admin' ? 'danger' : 'info'">
                  {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'active' ? 'success' : 'warning'">
                  {{ row.status === 'active' ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="lastLoginAt" label="最近登录" width="180" />
            <el-table-column prop="createdAt" label="创建时间" width="180" />
            <el-table-column label="操作" width="160" align="center">
              <template #default="{ row }">
                <el-button
                  text
                  :disabled="row.role === 'admin' && row.id === currentUser?.id"
                  @click="toggleUserStatus(row)"
                >
                  {{ row.status === 'active' ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

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
              <el-table :data="sopStatsList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无统计数据">
                <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
                <el-table-column prop="scene" label="适用场景" min-width="140" />
                <el-table-column prop="totalCount" label="执行次数" width="100" align="center" />
                <el-table-column prop="passedCount" label="通过次数" width="100" align="center" />
                <el-table-column label="通过率" width="110" align="center">
                  <template #default="{ row }">{{ formatRate(row.passRate) }}</template>
                </el-table-column>
                <el-table-column label="平均得分" width="120" align="center">
                  <template #default="{ row }">{{ formatAverageScore(row.averageScore) }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div class="section-block">
            <div class="section-head">
              <div class="section-title">执行记录列表</div>
              <div class="section-subtitle">从这里查看明细并处理人工复核</div>
            </div>
            <div class="table-card">
              <el-table :data="historyList" style="width: 100%" :header-cell-style="{ background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }" empty-text="暂无执行记录">
                <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
                <el-table-column label="所属用户" min-width="140">
                  <template #default="{ row }">
                    {{ row.userDisplayName || row.userName || '未知用户' }}
                  </template>
                </el-table-column>
                <el-table-column prop="finishTime" label="完成时间" width="180" />
                <el-table-column label="AI 结论" width="110" align="center">
                  <template #default="{ row }">
                    <el-tag :class="['minimal-status-tag', row.status === 'passed' ? 'is-passed' : 'is-failed']">
                      {{ getStatusText(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="人工复核" width="140" align="center">
                  <template #default="{ row }">
                    <el-tag :class="['minimal-status-tag', getReviewTagClass(row.manualReview?.status)]">
                      {{ getReviewStatusText(row.manualReview?.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="190" align="right">
                  <template #default="{ row }">
                    <el-button text class="action-btn" @click="openHistoryDetail(row)">详情</el-button>
                    <el-button text class="action-btn" @click="openReviewDialog(row)">复核</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>

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

    <el-dialog v-model="debugVisible" title="SOP 预处理详情" width="900px" class="minimal-dialog">
      <div v-loading="debugLoading" class="detail-wrap">
        <div v-if="selectedSopDebug">
          <div class="summary">{{ selectedSopDebug.name }} / {{ selectedSopDebug.scene }}</div>
          <div v-for="step in selectedSopDebug.steps" :key="step.stepNo" class="detail-box">
            <div class="detail-title">步骤 {{ step.stepNo }}: {{ step.description }}</div>
            <div class="detail-text">摘要：{{ step.referenceSummary || '暂无' }}</div>
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
  </el-container>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataLine, Document, Monitor, Plus, SwitchButton } from '@element-plus/icons-vue'
import { clearAuthSession, createSop, fileToDataUrl, getCurrentUser, getHistoryDetail, getSopDetail, getStats, listHistory, listSops, listUsers, logout, removeSop, reviewHistory, toAbsoluteApiUrl, updateSopStepDemoVideo, updateSopStepSegmentation, updateUserStatus } from '../api/client'

const router = useRouter()
const activeMenu = ref('manage')
const sopList = ref([])
const userList = ref([])
const historyList = ref([])
const summaryStats = ref({ totalSops: 0, totalExecutions: 0, pendingReviewCount: 0, passRate: 0 })
const sopStatsList = ref([])
const dialogVisible = ref(false)
const isSaving = ref(false)
const debugVisible = ref(false)
const debugLoading = ref(false)
const selectedSopDebug = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const reviewDialogVisible = ref(false)
const reviewTarget = ref(null)
const reviewForm = reactive({ status: 'approved', note: '' })
const sopForm = reactive({ name: '', scene: '', stepCount: 1, steps: [{ description: '', video: null }] })
const currentUser = ref(getCurrentUser())

const headerTitle = computed(() => activeMenu.value === 'manage' ? 'SOP 管理' : '数据统计')
const headerSubtitle = computed(() => activeMenu.value === 'manage' ? '统一管理 SOP 内容、步骤说明和示范视频' : '查看整体执行情况，并处理需要人工确认的记录')
const historyVideoUrl = computed(() => toAbsoluteApiUrl(selectedHistoryRecord.value?.detail?.uploadedVideo?.url || ''))
const reviewVideoUrl = computed(() => toAbsoluteApiUrl(reviewTarget.value?.detail?.uploadedVideo?.url || ''))
const currentUserName = computed(() => currentUser.value?.displayName || currentUser.value?.username || '管理员')
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
    historyDetailVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载详情失败')
  }
}

async function openReviewDialog(row) {
  try {
    reviewTarget.value = normalizeHistory((await getHistoryDetail(row.id)).data)
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

function formatSubsteps(list) {
  return Array.isArray(list) && list.length ? list.map((item) => `${item.title}@${Number(item.timestampSec).toFixed(2)}s`).join(' / ') : '暂无'
}

onMounted(() => {
  reloadCurrentView().catch((error) => ElMessage.error(error.message || '初始化失败'))
})
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

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
}

.header-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #86868b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.create-btn,
.refresh-btn {
  border-radius: 8px;
  font-weight: 500;
}

.create-btn {
  background-color: #000000;
  border-color: #000000;
  padding: 8px 20px;
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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

.stats-view {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.stat-card {
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  border: 1px solid #e5e5ea;
  border-radius: 16px;
  padding: 24px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.03);
}

.highlight-card {
  border-color: #1d1d1f;
}

.stat-label {
  font-size: 13px;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  margin-top: 12px;
  font-size: 36px;
  line-height: 1;
  font-weight: 600;
  color: #1d1d1f;
  letter-spacing: -0.03em;
}

.stat-desc {
  margin-top: 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #86868b;
}

.section-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
}

.section-subtitle {
  font-size: 14px;
  color: #86868b;
}

:deep(.minimal-status-tag) {
  border-radius: 6px;
  padding: 0 12px;
  font-weight: 500;
  border: 1px solid;
}

:deep(.minimal-status-tag.is-passed),
:deep(.minimal-status-tag.is-review-approved) {
  background-color: #ffffff;
  color: #1d1d1f;
  border-color: #1d1d1f;
}

:deep(.minimal-status-tag.is-failed),
:deep(.minimal-status-tag.is-review-rejected) {
  background-color: #f5f5f7;
  color: #86868b;
  border-color: #e5e5ea;
}

:deep(.minimal-status-tag.is-review-attention),
:deep(.minimal-status-tag.is-review-pending) {
  background-color: #fff8e8;
  color: #9a6700;
  border-color: #f3d58b;
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

.upload-btn {
  margin-top: 12px;
}

.step-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #86868b;
  line-height: 1.6;
}

.detail-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary {
  font-weight: 600;
  color: #1d1d1f;
}

.detail-box {
  background: #ffffff;
  border-radius: 12px;
  padding: 18px;
  border: 1px solid #e5e5ea;
}

.detail-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.detail-text {
  color: #515154;
  line-height: 1.7;
}

.manual-segmentation-box,
.demo-video-box {
  margin-top: 14px;
  padding: 14px;
  border-radius: 12px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #f0f0f0;
}

.manual-title {
  font-weight: 600;
  color: #1d1d1f;
}

.manual-subtitle,
.muted-text {
  font-size: 12px;
  color: #86868b;
  line-height: 1.6;
}

.manual-btn {
  align-self: flex-start;
}

.frame-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.frame {
  width: 100%;
  height: 116px;
  object-fit: cover;
  border-radius: 12px;
  background: #f5f5f7;
}

.video {
  width: 100%;
  max-height: 360px;
  background: #000;
  border-radius: 18px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.review-radio-group .el-radio-button__inner) {
  min-width: 118px;
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

@media (max-width: 1100px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .admin-layout {
    display: block;
    height: auto;
  }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e5e5ea;
  }

  .top-header {
    height: auto;
    padding: 20px 16px;
    align-items: flex-start;
  }

  .header-right,
  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .content-area {
    padding: 20px 16px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
