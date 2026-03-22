<template>
  <el-container class="admin-layout">
    <el-aside width="240px" class="sidebar">
      <div class="brand">
        <div class="brand-logo"><el-icon><Monitor /></el-icon></div>
        <span>视觉巡检</span>
      </div>

      <el-menu :default-active="activeMenu" class="menu" :border="false" @select="handleMenuSelect">
        <el-menu-item index="manage">
          <el-icon><Document /></el-icon>
          <span>SOP 管理</span>
        </el-menu-item>
        <el-menu-item index="stats">
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

    <el-container class="main-container">
      <el-header class="top-header">
        <div>
          <h2>{{ headerTitle }}</h2>
          <p class="header-subtitle">{{ headerSubtitle }}</p>
        </div>
        <div class="header-actions">
          <el-button v-if="activeMenu === 'stats'" class="refresh-btn" @click="reloadCurrentView">
            <el-icon><RefreshRight /></el-icon>
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
          <el-table :data="sopList" style="width: 100%" :header-cell-style="tableHeaderStyle" empty-text="暂无 SOP，请先创建">
            <el-table-column prop="id" label="ID" width="180" />
            <el-table-column prop="name" label="SOP 名称" min-width="180" />
            <el-table-column prop="scene" label="适用场景" min-width="140" />
            <el-table-column prop="stepCount" label="步骤数" width="100" align="center">
              <template #default="scope"><el-tag size="small" class="minimal-tag">{{ scope.row.stepCount }}</el-tag></template>
            </el-table-column>
            <el-table-column label="示范视频" width="120" align="center">
              <template #default="scope"><el-tag size="small" class="minimal-tag">{{ scope.row.demoVideoCount || 0 }}</el-tag></template>
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

        <div v-else class="stats-view">
          <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">SOP 总数</div><div class="stat-value">{{ summaryStats.totalSops }}</div><div class="stat-desc">当前已发布流程</div></div>
            <div class="stat-card"><div class="stat-label">执行记录</div><div class="stat-value">{{ summaryStats.totalExecutions }}</div><div class="stat-desc">来自用户端历史</div></div>
            <div class="stat-card"><div class="stat-label">AI 通过率</div><div class="stat-value">{{ summaryStats.passRate }}</div><div class="stat-desc">自动评测结果统计</div></div>
            <div class="stat-card highlight-card"><div class="stat-label">待人工复核</div><div class="stat-value">{{ summaryStats.pendingReviewCount }}</div><div class="stat-desc">尚未给出人工结论</div></div>
          </div>

          <div class="section-block">
            <div class="section-head">
              <div class="section-title">SOP 维度统计</div>
              <div class="section-subtitle">汇总每个 SOP 的执行情况</div>
            </div>
            <div class="table-card">
              <el-table :data="sopStatsList" style="width: 100%" :header-cell-style="tableHeaderStyle" empty-text="暂无统计数据">
                <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
                <el-table-column prop="scene" label="适用场景" min-width="140" />
                <el-table-column prop="totalCount" label="执行次数" width="100" align="center" />
                <el-table-column prop="passedCount" label="通过次数" width="100" align="center" />
                <el-table-column label="通过率" width="110" align="center"><template #default="scope">{{ formatRate(scope.row.passRate) }}</template></el-table-column>
                <el-table-column prop="pendingReviewCount" label="待复核" width="100" align="center" />
                <el-table-column label="平均得分" width="120" align="center"><template #default="scope">{{ formatAverageScore(scope.row.averageScore) }}</template></el-table-column>
              </el-table>
            </div>
          </div>

          <div class="section-block">
            <div class="section-head">
              <div class="section-title">执行记录列表</div>
              <div class="section-subtitle">每条 SOP 记录都支持人工复核</div>
            </div>
            <div class="table-card">
              <el-table :data="historyList" style="width: 100%" :header-cell-style="tableHeaderStyle" empty-text="暂无执行记录">
                <el-table-column prop="taskName" label="SOP 名称" min-width="180" />
                <el-table-column prop="scene" label="适用场景" min-width="140" />
                <el-table-column prop="finishTime" label="完成时间" width="180" />
                <el-table-column label="AI 结论" width="110" align="center">
                  <template #default="scope"><el-tag :class="['minimal-status-tag', scope.row.status === 'passed' ? 'is-passed' : 'is-failed']">{{ getStatusText(scope.row.status) }}</el-tag></template>
                </el-table-column>
                <el-table-column label="得分" width="100" align="center"><template #default="scope">{{ formatScore(scope.row.score) }}</template></el-table-column>
                <el-table-column label="人工复核" width="140" align="center">
                  <template #default="scope"><el-tag :class="['minimal-status-tag', getReviewTagClass(scope.row.manualReview?.status)]">{{ getReviewStatusText(scope.row.manualReview?.status) }}</el-tag></template>
                </el-table-column>
                <el-table-column label="操作" width="200" align="right">
                  <template #default="scope">
                    <el-button text class="action-btn" @click="openHistoryDetail(scope.row)">详情</el-button>
                    <el-button text class="action-btn" @click="openReviewDialog(scope.row)">{{ scope.row.manualReview?.status ? '更新复核' : '人工复核' }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="dialogVisible" title="新建标准操作流程 (SOP)" width="600px" class="minimal-dialog" destroy-on-close>
      <el-form :model="sopForm" label-position="top" class="minimal-form">
        <div class="form-row">
          <el-form-item label="SOP 名称" class="flex-1"><el-input v-model="sopForm.name" placeholder="例如：实验室安全操作规范" /></el-form-item>
          <el-form-item label="适用场景" class="flex-1"><el-input v-model="sopForm.scene" placeholder="例如：化学实验室" /></el-form-item>
        </div>
        <el-form-item label="步骤数量"><el-input-number v-model="sopForm.stepCount" :min="1" :max="20" @change="handleStepCountChange" /></el-form-item>
        <div class="steps-section">
          <div class="section-title">步骤详情</div>
          <div v-for="(step, index) in sopForm.steps" :key="index" class="step-card">
            <div class="step-header">步骤 {{ index + 1 }}</div>
            <el-input v-model="step.description" type="textarea" :rows="2" resize="none" class="minimal-textarea" placeholder="请描述该步骤的标准动作" />
            <div class="step-video-upload">
              <el-upload action="#" :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="(file) => handleStepVideoChange(index, file)">
                <div v-if="!step.video" class="upload-trigger"><el-icon><VideoCamera /></el-icon><span>上传标准动作示范视频</span></div>
                <div v-else class="video-preview-item" @click.stop>
                  <div class="video-info"><el-icon><VideoPlay /></el-icon><span>{{ step.video.name }}</span></div>
                  <el-button text class="remove-video-btn" @click.stop="removeStepVideo(index)"><el-icon><Close /></el-icon></el-button>
                </div>
              </el-upload>
            </div>
          </div>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button text @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="isSaving" @click="saveSop">发布</el-button></div></template>
    </el-dialog>
    <el-dialog v-model="debugVisible" title="SOP 预处理调试" width="880px" class="minimal-dialog" destroy-on-close>
      <div v-loading="debugLoading" class="debug-layout">
        <template v-if="selectedSopDebug">
          <div class="debug-summary">
            <div class="debug-summary-card"><div class="debug-summary-label">SOP 名称</div><div class="debug-summary-value">{{ selectedSopDebug.name || '-' }}</div></div>
            <div class="debug-summary-card"><div class="debug-summary-label">场景</div><div class="debug-summary-value">{{ selectedSopDebug.scene || '-' }}</div></div>
            <div class="debug-summary-card"><div class="debug-summary-label">步骤数</div><div class="debug-summary-value">{{ selectedSopDebug.stepCount || 0 }}</div></div>
          </div>

          <div v-for="step in selectedSopDebug.steps" :key="step.stepNo" class="debug-step-card">
            <div class="debug-step-top">
              <div>
                <div class="debug-step-index">步骤 {{ step.stepNo }}</div>
                <div class="debug-step-desc">{{ step.description || '未填写步骤说明' }}</div>
              </div>
              <el-tag size="small" class="minimal-tag">{{ step.referenceFrames?.length || 0 }} 张关键帧</el-tag>
            </div>
            <div class="debug-meta-grid">
              <div class="debug-meta-item"><span class="debug-meta-label">AI 预处理</span><span class="debug-meta-value">{{ step.aiUsed ? '已启用' : '未启用（回退为均匀抽帧）' }}</span></div>
              <div class="debug-meta-item"><span class="debug-meta-label">参考摘要</span><span class="debug-meta-value">{{ step.referenceSummary || '暂无' }}</span></div>
              <div class="debug-meta-item"><span class="debug-meta-label">关注区域提示</span><span class="debug-meta-value">{{ step.roiHint || '暂无' }}</span></div>
              <div class="debug-meta-item"><span class="debug-meta-label">时长</span><span class="debug-meta-value">{{ formatDuration(step.referenceFeatures?.durationSec) }}</span></div>
              <div class="debug-meta-item"><span class="debug-meta-label">原视频 FPS</span><span class="debug-meta-value">{{ formatNumber(step.referenceFeatures?.fps) }}</span></div>
              <div class="debug-meta-item"><span class="debug-meta-label">原视频帧数</span><span class="debug-meta-value">{{ formatInteger(step.referenceFeatures?.frameCount) }}</span></div>
              <div class="debug-meta-item debug-meta-wide"><span class="debug-meta-label">采样时间点</span><span class="debug-meta-value">{{ formatTimestamps(step.referenceFeatures?.sampleTimestamps) }}</span></div>
            </div>
            <div v-if="step.substeps?.length" class="debug-substeps">
              <div class="debug-substeps-title">AI 子步骤时间点</div>
              <div class="debug-substeps-list">
                <div v-for="(item, index) in step.substeps" :key="`${step.stepNo}-sub-${index}`" class="debug-substep-chip">{{ item.title }} @ {{ formatDuration(item.timestampSec) }}</div>
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
            <el-empty v-if="!step.referenceFrames?.length" description="当前步骤还没有可展示的预处理结果" />
          </div>
        </template>
      </div>
    </el-dialog>

    <el-dialog v-model="historyDetailVisible" title="执行记录详情" width="820px" class="minimal-dialog" destroy-on-close>
      <template v-if="selectedHistoryRecord">
        <div class="detail-layout">
          <div class="debug-summary">
            <div class="debug-summary-card"><div class="debug-summary-label">SOP 名称</div><div class="debug-summary-value">{{ selectedHistoryRecord.taskName || '-' }}</div></div>
            <div class="debug-summary-card"><div class="debug-summary-label">完成时间</div><div class="debug-summary-value">{{ selectedHistoryRecord.finishTime || '-' }}</div></div>
            <div class="debug-summary-card"><div class="debug-summary-label">AI 结论</div><div class="debug-summary-value">{{ getStatusText(selectedHistoryRecord.status) }}</div></div>
            <div class="debug-summary-card"><div class="debug-summary-label">人工复核</div><div class="debug-summary-value">{{ getReviewStatusText(selectedHistoryRecord.manualReview?.status) }}</div></div>
          </div>

          <div class="detail-card">
            <div class="detail-card-title">综合反馈</div>
            <div class="detail-text">{{ selectedHistoryRecord.detail.feedback || '暂无反馈' }}</div>
            <div class="detail-meta">得分：{{ formatScore(selectedHistoryRecord.score) }} · 上传视频：{{ selectedHistoryRecord.detail.uploadedVideo?.name || '未记录' }}</div>
          </div>

          <div class="detail-card">
            <div class="detail-card-title">用户原视频</div>
            <div v-loading="historyVideoLoading" class="video-preview-panel">
              <video v-if="historyVideoUrl" :src="historyVideoUrl" controls class="uploaded-video-player" />
              <el-empty v-else :description="getUploadedVideoEmptyText(selectedHistoryRecord.detail.uploadedVideo)" />
            </div>
          </div>

          <div v-if="selectedHistoryRecord.detail.issues.length" class="detail-card">
            <div class="detail-card-title">问题列表</div>
            <div class="issue-list"><span v-for="(item, index) in selectedHistoryRecord.detail.issues" :key="index" class="issue-chip">{{ item }}</span></div>
          </div>

          <div class="detail-card">
            <div class="detail-card-title">步骤结果</div>
            <el-empty v-if="!selectedHistoryRecord.detail.stepResults.length" description="暂无步骤结果" />
            <div v-else class="step-result-list">
              <div v-for="item in selectedHistoryRecord.detail.stepResults" :key="`${selectedHistoryRecord.id}-${item.stepNo}`" class="step-result-item">
                <div class="step-result-top"><div class="step-result-title">步骤 {{ item.stepNo }}：{{ item.description || '未命名步骤' }}</div><div class="step-result-meta">{{ getStepResultText(item.passed) }} / {{ formatScore(item.score, '-') }}</div></div>
                <div class="step-result-meta">置信度：{{ formatConfidence(item.confidence) }}</div>
                <div class="detail-text">{{ item.evidence || '暂无证据说明' }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #footer><div class="dialog-footer"><el-button text @click="historyDetailVisible = false">关闭</el-button><el-button type="primary" @click="openReviewDialog(selectedHistoryRecord)">人工复核</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="人工复核" width="560px" class="minimal-dialog" destroy-on-close>
      <template v-if="reviewTarget">
        <div class="review-head">
          <div class="review-title">{{ reviewTarget.taskName }}</div>
          <div class="review-subtitle">{{ reviewTarget.finishTime }} · AI 结论：{{ getStatusText(reviewTarget.status) }}</div>
        </div>
        <div class="detail-card review-video-card">
          <div class="detail-card-title">用户上传原视频</div>
          <div v-loading="reviewVideoLoading" class="video-preview-panel review-video-panel">
            <video v-if="reviewVideoUrl" :src="reviewVideoUrl" controls class="uploaded-video-player review-video-player" />
            <el-empty v-else :description="getUploadedVideoEmptyText(reviewTarget.detail.uploadedVideo)" />
          </div>
        </div>
        <el-form :model="reviewForm" label-position="top" class="minimal-form">
          <el-form-item label="复核结论">
            <el-radio-group v-model="reviewForm.status" class="review-radio-group">
              <el-radio-button label="approved">复核通过</el-radio-button>
              <el-radio-button label="rejected">复核不通过</el-radio-button>
              <el-radio-button label="needs_attention">需要整改</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="复核意见"><el-input v-model="reviewForm.note" type="textarea" :rows="4" resize="none" placeholder="请输入人工复核意见" /></el-form-item>
        </el-form>
      </template>
      <template #footer><div class="dialog-footer"><el-button text @click="reviewDialogVisible = false">取消</el-button><el-button type="primary" @click="saveManualReview">保存复核</el-button></div></template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, DataLine, Document, Monitor, Plus, RefreshRight, SwitchButton, VideoCamera, VideoPlay } from '@element-plus/icons-vue'

const router = useRouter()
const SOP_LIST_KEY = 'sopList'
const SOP_HISTORY_KEY = 'sopHistoryList'
const API_CONFIG_KEY = 'dashscopeEvalConfig'
const SOP_DB_NAME = 'sop-demo-db'
const SOP_STORE_NAME = 'videoFiles'
const tableHeaderStyle = { background: '#fafafa', color: '#1d1d1f', fontWeight: '500' }

const activeMenu = ref('manage')
const sopList = ref([])
const historyList = ref([])
const dialogVisible = ref(false)
const isSaving = ref(false)
const debugVisible = ref(false)
const debugLoading = ref(false)
const selectedSopDebug = ref(null)
const historyDetailVisible = ref(false)
const selectedHistoryRecord = ref(null)
const historyVideoUrl = ref('')
const historyVideoLoading = ref(false)
const reviewDialogVisible = ref(false)
const reviewTarget = ref(null)
const reviewVideoUrl = ref('')
const reviewVideoLoading = ref(false)
const reviewForm = reactive({ status: 'approved', note: '' })
const sopForm = reactive({ name: '', scene: '', stepCount: 1, steps: [createEmptyStep()] })

const headerTitle = computed(() => activeMenu.value === 'manage' ? 'SOP 管理' : '数据统计')
const headerSubtitle = computed(() => activeMenu.value === 'manage' ? '维护标准操作流程，并为每个步骤生成参考素材' : '查看用户执行记录，并对每条 SOP 记录进行人工复核')
const summaryStats = computed(() => {
  const totalExecutions = historyList.value.length
  const passedCount = historyList.value.filter(item => item.status === 'passed').length
  const pendingReviewCount = historyList.value.filter(item => !item.manualReview?.status).length
  return { totalSops: sopList.value.length, totalExecutions, pendingReviewCount, passRate: formatRate(totalExecutions ? (passedCount / totalExecutions) * 100 : 0) }
})
const sopStatsList = computed(() => {
  const map = new Map()
  for (const record of historyList.value) {
    const key = record.taskId || record.taskName || `unknown-${record.id}`
    const item = map.get(key) || { taskName: record.taskName || '未命名 SOP', scene: record.scene || '未填写', totalCount: 0, passedCount: 0, pendingReviewCount: 0, scoreSum: 0, scoreCount: 0, passRate: 0, averageScore: null }
    item.totalCount += 1
    if (record.status === 'passed') item.passedCount += 1
    if (!record.manualReview?.status) item.pendingReviewCount += 1
    if (Number.isFinite(Number(record.score))) { item.scoreSum += Number(record.score); item.scoreCount += 1 }
    map.set(key, item)
  }
  return Array.from(map.values()).map(item => ({ ...item, passRate: item.totalCount ? (item.passedCount / item.totalCount) * 100 : 0, averageScore: item.scoreCount ? item.scoreSum / item.scoreCount : null })).sort((a, b) => b.totalCount - a.totalCount)
})

function createEmptyStep() { return { description: '', video: null } }
function getDefaultSops() {
  return [{ id: 'demo-sop-001', name: '穿戴防护装备规范', scene: '无菌车间', stepCount: 3, demoVideoCount: 0, createTime: '2023-10-24 10:00:00', steps: [{ stepNo: 1, description: '戴上防护帽，完全遮盖头发', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null, substeps: [], roiHint: '', aiUsed: false }, { stepNo: 2, description: '佩戴护目镜', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null, substeps: [], roiHint: '', aiUsed: false }, { stepNo: 3, description: '穿上无菌防护服并拉好拉链', videoKey: '', videoMeta: null, referenceAssetKey: '', referenceSummary: '', referenceFeatures: null, substeps: [], roiHint: '', aiUsed: false }] }]
}
function normalizeSop(item = {}) {
  return { ...item, scene: item.scene || '未填写', stepCount: item.stepCount || (item.steps || []).length || 0, demoVideoCount: item.demoVideoCount ?? (item.steps || []).length ?? 0, steps: (item.steps || []).map((step, index) => ({ stepNo: step.stepNo || index + 1, description: step.description || '', videoKey: step.videoKey || '', videoMeta: step.videoMeta || null, referenceAssetKey: step.referenceAssetKey || '', referenceSummary: step.referenceSummary || '', referenceFeatures: step.referenceFeatures || null, substeps: Array.isArray(step.substeps) ? step.substeps : [], roiHint: step.roiHint || '', aiUsed: Boolean(step.aiUsed) })) }
}
function normalizeManualReview(review) { return review && typeof review === 'object' ? { status: review.status || '', note: review.note || '', reviewer: review.reviewer || '管理员', reviewTime: review.reviewTime || '' } : null }
function normalizeUploadedVideo(uploadedVideo) { return uploadedVideo && typeof uploadedVideo === 'object' ? { name: uploadedVideo.name || '', type: uploadedVideo.type || '', size: uploadedVideo.size ?? null, lastModified: uploadedVideo.lastModified ?? null, videoKey: uploadedVideo.videoKey || '' } : null }
function normalizeHistoryRecord(record = {}) {
  const detail = record.detail || {}
  detail.uploadedVideo = normalizeUploadedVideo(detail.uploadedVideo || record.uploadedVideo || null)
  return { ...record, taskName: record.taskName || '未命名 SOP', scene: record.scene || '未填写', finishTime: record.finishTime || '', score: record.score ?? null, status: record.status || 'failed', detail: { feedback: detail.feedback || record.feedback || '', issues: Array.isArray(detail.issues) ? detail.issues : (Array.isArray(record.issues) ? record.issues : []), stepResults: Array.isArray(detail.stepResults) ? detail.stepResults : (Array.isArray(record.stepResults) ? record.stepResults : []), sopSteps: Array.isArray(detail.sopSteps) ? detail.sopSteps : (Array.isArray(record.sopSteps) ? record.sopSteps : []), uploadedVideo: detail.uploadedVideo || record.uploadedVideo || null }, manualReview: normalizeManualReview(record.manualReview) }
}
function persistSopList() { localStorage.setItem(SOP_LIST_KEY, JSON.stringify(sopList.value)) }
function persistHistoryList() { localStorage.setItem(SOP_HISTORY_KEY, JSON.stringify(historyList.value)) }
function loadSopList() { const stored = localStorage.getItem(SOP_LIST_KEY); sopList.value = stored ? JSON.parse(stored).map(normalizeSop) : getDefaultSops().map(normalizeSop); if (!stored) persistSopList() }
function loadHistoryList() { const stored = localStorage.getItem(SOP_HISTORY_KEY); historyList.value = stored ? JSON.parse(stored).map(normalizeHistoryRecord) : [] }
function loadApiConfig() { const stored = localStorage.getItem(API_CONFIG_KEY); if (!stored) return null; try { const parsed = JSON.parse(stored); return parsed?.apiKey?.trim() ? parsed : null } catch { return null } }

onMounted(() => { loadSopList(); loadHistoryList() })

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SOP_DB_NAME, 1)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = () => { const db = request.result; if (!db.objectStoreNames.contains(SOP_STORE_NAME)) db.createObjectStore(SOP_STORE_NAME) }
  })
}
async function setStoreValue(key, value) { const db = await openDB(); return new Promise((resolve, reject) => { const tx = db.transaction(SOP_STORE_NAME, 'readwrite'); tx.objectStore(SOP_STORE_NAME).put(value, key); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error) }) }
async function getStoreValue(key) { if (!key) return null; const db = await openDB(); return new Promise((resolve, reject) => { const tx = db.transaction(SOP_STORE_NAME, 'readonly'); const request = tx.objectStore(SOP_STORE_NAME).get(key); request.onsuccess = () => resolve(request.result || null); request.onerror = () => reject(request.error) }) }
async function deleteStoreValue(key) { const db = await openDB(); return new Promise((resolve, reject) => { const tx = db.transaction(SOP_STORE_NAME, 'readwrite'); tx.objectStore(SOP_STORE_NAME).delete(key); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error) }) }
function handleMenuSelect(index) { activeMenu.value = index; reloadCurrentView() }
function reloadCurrentView() { loadSopList(); if (activeMenu.value === 'stats') loadHistoryList() }
const handleLogout = () => router.push('/login')
const openCreateDialog = () => { sopForm.name = ''; sopForm.scene = ''; sopForm.stepCount = 1; sopForm.steps = [createEmptyStep()]; dialogVisible.value = true }
const handleStepCountChange = (newVal) => { const len = sopForm.steps.length; if (newVal > len) { for (let i = len; i < newVal; i += 1) sopForm.steps.push(createEmptyStep()) } else if (newVal < len) sopForm.steps.splice(newVal) }
const handleStepVideoChange = (index, file) => { sopForm.steps[index].video = file?.raw || file }
const removeStepVideo = (index) => { sopForm.steps[index].video = null }
function fileToDataUrl(file) { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(reader.error || new Error('文件读取失败')); reader.readAsDataURL(file) }) }
async function prepareStepReference(stepNo, description, video) {
  const response = await fetch('http://localhost:8000/api/prepare-step-video', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stepNo, description, videoDataUrl: await fileToDataUrl(video), maxFrames: 8, apiConfig: loadApiConfig() }) })
  const result = await response.json().catch(() => null)
  if (!response.ok || !result?.success) throw new Error(result?.detail || result?.message || '步骤参考素材预处理失败')
  return result.data
}
const saveSop = async () => {
  if (!sopForm.name.trim()) return ElMessage.warning('请输入 SOP 名称')
  if (sopForm.steps.some(step => !step.description.trim())) return ElMessage.warning('请补全每一个步骤的文字描述')
  if (sopForm.steps.some(step => !step.video)) return ElMessage.warning('请为每一个步骤上传示范视频')
  isSaving.value = true
  try {
    if (!loadApiConfig()) ElMessage.warning('未检测到可用 API 配置，本次将回退为普通均匀抽帧预处理')
    const sopId = `sop-${Date.now()}`
    const steps = []
    for (let index = 0; index < sopForm.steps.length; index += 1) {
      const step = sopForm.steps[index]
      const stepNo = index + 1
      const referenceAssetKey = `${sopId}-step-${stepNo}-reference`
      const referenceAsset = await prepareStepReference(stepNo, step.description.trim(), step.video)
      await setStoreValue(referenceAssetKey, referenceAsset)
      steps.push({ stepNo, description: step.description.trim(), videoKey: '', referenceAssetKey, referenceSummary: referenceAsset.referenceSummary || '', referenceFeatures: referenceAsset.referenceFeatures || null, substeps: Array.isArray(referenceAsset.substeps) ? referenceAsset.substeps : [], roiHint: referenceAsset.roiHint || '', aiUsed: Boolean(referenceAsset.aiUsed), videoMeta: { name: step.video.name, type: step.video.type, size: step.video.size, lastModified: step.video.lastModified } })
    }
    sopList.value.unshift(normalizeSop({ id: sopId, name: sopForm.name.trim(), scene: sopForm.scene.trim() || '未填写', stepCount: sopForm.stepCount, demoVideoCount: steps.length, createTime: new Date().toLocaleString(), steps }))
    persistSopList(); dialogVisible.value = false; ElMessage.success('SOP 发布成功')
  } catch (error) { console.error(error); ElMessage.error('保存失败，请检查浏览器本地存储权限') } finally { isSaving.value = false }
}
function formatDuration(value) { const num = Number(value); return Number.isFinite(num) ? `${num.toFixed(2)} s` : '-' }
function formatNumber(value) { const num = Number(value); return Number.isFinite(num) ? num.toFixed(2) : '-' }
function formatInteger(value) { const num = Number(value); return Number.isFinite(num) ? `${Math.round(num)}` : '-' }
function formatTimestamps(values) { return Array.isArray(values) && values.length ? values.map(item => `${Number(item).toFixed(2)}s`).join(' / ') : '-' }
function formatConfidence(value) { const num = Number(value); return Number.isFinite(num) ? num.toFixed(2) : '-' }
function formatScore(value, fallback = '-') { const num = Number(value); return Number.isFinite(num) ? `${num} / 100` : fallback }
function formatAverageScore(value) { const num = Number(value); return Number.isFinite(num) ? `${num.toFixed(1)} / 100` : '-' }
function formatRate(value) { const num = Number(value); return Number.isFinite(num) ? `${num.toFixed(0)}%` : '0%' }
function getStatusText(status) { return status === 'passed' ? '通过' : '异常' }
function getStepResultText(passed) { return passed === true ? '通过' : passed === false ? '异常' : '未知' }
function getReviewStatusText(status) { if (status === 'approved') return '复核通过'; if (status === 'rejected') return '复核不通过'; if (status === 'needs_attention') return '需要整改'; return '待复核' }
function getReviewTagClass(status) { if (status === 'approved') return 'is-review-approved'; if (status === 'rejected') return 'is-review-rejected'; if (status === 'needs_attention') return 'is-review-needs-attention'; return 'is-pending' }
function getUploadedVideoEmptyText(uploadedVideo) { if (uploadedVideo?.name && !uploadedVideo?.videoKey) return '该记录生成于旧版本，未保存原视频'; return uploadedVideo?.videoKey ? '原视频加载失败' : '未记录上传视频' }
function revokeVideoUrl(url) { if (url) URL.revokeObjectURL(url) }
function resetHistoryVideoPreview() { revokeVideoUrl(historyVideoUrl.value); historyVideoUrl.value = ''; historyVideoLoading.value = false }
function resetReviewVideoPreview() { revokeVideoUrl(reviewVideoUrl.value); reviewVideoUrl.value = ''; reviewVideoLoading.value = false }
async function createUploadedVideoUrl(uploadedVideo) { if (!uploadedVideo?.videoKey) return ''; const file = await getStoreValue(uploadedVideo.videoKey); return file instanceof Blob ? URL.createObjectURL(file) : '' }
async function loadHistoryVideoPreview(record) {
  resetHistoryVideoPreview()
  if (!record?.detail?.uploadedVideo?.videoKey) return
  historyVideoLoading.value = true
  try { historyVideoUrl.value = await createUploadedVideoUrl(record.detail.uploadedVideo) } catch (error) { console.error(error); ElMessage.error('加载原视频失败') } finally { historyVideoLoading.value = false }
}
async function loadReviewVideoPreview(record) {
  resetReviewVideoPreview()
  if (!record?.detail?.uploadedVideo?.videoKey) return
  reviewVideoLoading.value = true
  try { reviewVideoUrl.value = await createUploadedVideoUrl(record.detail.uploadedVideo) } catch (error) { console.error(error); ElMessage.error('加载原视频失败') } finally { reviewVideoLoading.value = false }
}
function closeHistoryDetail() { historyDetailVisible.value = false; selectedHistoryRecord.value = null; resetHistoryVideoPreview() }
function closeReviewDialog() { reviewDialogVisible.value = false; reviewTarget.value = null; resetReviewVideoPreview() }
onBeforeUnmount(() => { resetHistoryVideoPreview(); resetReviewVideoPreview() })
const openDebugSop = async (row) => {
  debugVisible.value = true; debugLoading.value = true; selectedSopDebug.value = { ...row, steps: [] }
  try {
    const steps = await Promise.all((row.steps || []).map(async (step, index) => {
      const asset = step.referenceAssetKey ? await getStoreValue(step.referenceAssetKey) : null
      return { stepNo: step.stepNo || index + 1, description: step.description || '', referenceSummary: asset?.referenceSummary || step.referenceSummary || '', referenceFeatures: asset?.referenceFeatures || step.referenceFeatures || null, referenceFrames: Array.isArray(asset?.referenceFrames) ? asset.referenceFrames : [], analysisFrames: Array.isArray(asset?.analysisFrames) ? asset.analysisFrames : [], substeps: Array.isArray(asset?.substeps) ? asset.substeps : (Array.isArray(step.substeps) ? step.substeps : []), roiHint: asset?.roiHint || step.roiHint || '', aiUsed: typeof asset?.aiUsed === 'boolean' ? asset.aiUsed : Boolean(step.aiUsed) }
    }))
    selectedSopDebug.value = { ...row, steps }
  } catch (error) { console.error(error); ElMessage.error('加载预处理调试信息失败'); debugVisible.value = false } finally { debugLoading.value = false }
}
const deleteSop = (row) => {
  ElMessageBox.confirm('确定要删除该 SOP 吗？', '提示', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning', customClass: 'minimal-msgbox' }).then(async () => {
    try { const storeKeys = (row.steps || []).flatMap(item => [item.videoKey, item.referenceAssetKey].filter(Boolean)); await Promise.all(storeKeys.map(item => deleteStoreValue(item))); sopList.value = sopList.value.filter(item => item.id !== row.id); persistSopList(); ElMessage.success('删除成功') } catch (error) { console.error(error); ElMessage.error('删除失败') }
  }).catch(() => {})
}
async function openHistoryDetail(record) { selectedHistoryRecord.value = normalizeHistoryRecord(record); historyDetailVisible.value = true; await loadHistoryVideoPreview(selectedHistoryRecord.value) }
async function openReviewDialog(record) { if (!record) return; reviewTarget.value = normalizeHistoryRecord(record); reviewForm.status = reviewTarget.value.manualReview?.status || (reviewTarget.value.status === 'passed' ? 'approved' : 'needs_attention'); reviewForm.note = reviewTarget.value.manualReview?.note || ''; reviewDialogVisible.value = true; await loadReviewVideoPreview(reviewTarget.value) }
function saveManualReview() {
  if (!reviewTarget.value) return
  const index = historyList.value.findIndex(item => item.id === reviewTarget.value.id)
  if (index === -1) return ElMessage.error('未找到对应执行记录')
  const updated = normalizeHistoryRecord({ ...historyList.value[index], manualReview: { status: reviewForm.status, note: reviewForm.note.trim(), reviewer: '管理员', reviewTime: new Date().toLocaleString() } })
  historyList.value.splice(index, 1, updated)
  persistHistoryList()
  if (selectedHistoryRecord.value?.id === updated.id) selectedHistoryRecord.value = updated
  reviewTarget.value = updated; reviewDialogVisible.value = false; ElMessage.success('人工复核已保存')
}
</script>

<style scoped>
.admin-layout { height: 100vh; background: #f5f5f7; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
.sidebar { background: #fff; border-right: 1px solid #e5e5ea; display: flex; flex-direction: column; }
.brand { height: 64px; display: flex; align-items: center; padding: 0 24px; font-size: 18px; font-weight: 600; color: #1d1d1f; border-bottom: 1px solid #e5e5ea; }
.brand-logo { width: 28px; height: 28px; margin-right: 12px; display: flex; align-items: center; justify-content: center; border-radius: 8px; color: #fff; background: linear-gradient(135deg, #000 0%, #434343 100%); }
.menu { flex: 1; padding: 16px 0; border-right: none; }
.sidebar-bottom { padding: 16px 24px; border-top: 1px solid #e5e5ea; }
.user-info { display: flex; align-items: center; margin-bottom: 16px; }
.username { margin-left: 12px; font-size: 14px; font-weight: 500; color: #1d1d1f; }
.logout-btn { width: 100%; justify-content: flex-start; color: #ff3b30; }
.main-container { display: flex; flex-direction: column; }
.top-header { min-height: 64px; display: flex; justify-content: space-between; align-items: center; padding: 0 32px; background: #fff; border-bottom: 1px solid #e5e5ea; }
.top-header h2 { margin: 0; font-size: 20px; color: #1d1d1f; }
.header-subtitle { margin: 4px 0 0; font-size: 13px; color: #86868b; }
.header-actions { display: flex; gap: 12px; align-items: center; }
.create-btn { background: #000; border-color: #000; border-radius: 8px; }
.content-area { padding: 32px; }
.table-card, .stat-card, .detail-card, .debug-step-card { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.05); }
.table-card { padding: 8px; overflow: hidden; }
.stats-view { display: flex; flex-direction: column; gap: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.stat-card { padding: 20px; border: 1px solid #ececf0; }
.highlight-card { background: linear-gradient(135deg, #111 0%, #2f2f2f 100%); }
.highlight-card .stat-label, .highlight-card .stat-value, .highlight-card .stat-desc { color: #fff; }
.stat-label, .section-subtitle, .debug-summary-label, .debug-meta-label, .debug-frame-caption, .step-result-meta, .detail-meta, .review-subtitle { font-size: 13px; color: #86868b; }
.stat-value { margin-top: 10px; font-size: 32px; font-weight: 700; color: #1d1d1f; }
.stat-desc { margin-top: 10px; font-size: 13px; color: #86868b; }
.section-block { display: flex; flex-direction: column; gap: 12px; }
.section-head { display: flex; justify-content: space-between; align-items: flex-end; }
.section-title, .detail-card-title, .debug-substeps-title { font-size: 16px; font-weight: 600; color: #1d1d1f; }
.form-row { display: flex; gap: 16px; }
.flex-1 { flex: 1; }
.steps-section { margin-top: 24px; }
.step-card { background: #fafafa; border: 1px solid #f0f0f0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.step-header { font-size: 12px; font-weight: 600; color: #86868b; margin-bottom: 8px; text-transform: uppercase; }
.step-video-upload { margin-top: 12px; }
.upload-trigger, .video-preview-item { display: flex; align-items: center; gap: 8px; border-radius: 6px; font-size: 13px; }
.upload-trigger { padding: 8px 16px; background: #fff; border: 1px dashed #d2d2d7; color: #86868b; }
.video-preview-item { justify-content: space-between; padding: 8px 12px; background: #e5e5ea; color: #1d1d1f; }
.video-info { display: flex; align-items: center; gap: 8px; font-weight: 500; }
.debug-layout, .detail-layout { display: flex; flex-direction: column; gap: 20px; min-height: 200px; }
.debug-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.debug-summary-card { background: #f5f5f7; border-radius: 12px; padding: 16px; }
.debug-summary-value { margin-top: 8px; font-size: 15px; font-weight: 600; color: #1d1d1f; word-break: break-word; }
.debug-step-card, .detail-card { border: 1px solid #e5e5ea; padding: 18px; }
.debug-step-top, .step-result-top { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.debug-step-desc, .detail-text { margin-top: 6px; font-size: 14px; line-height: 1.7; color: #1d1d1f; }
.debug-meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.debug-meta-item { display: flex; flex-direction: column; gap: 6px; padding: 12px; background: #fafafa; border-radius: 10px; }
.debug-meta-wide { grid-column: 1 / -1; }
.debug-substeps-list, .issue-list { display: flex; flex-wrap: wrap; gap: 8px; }
.debug-substep-chip, .issue-chip { padding: 6px 10px; border-radius: 999px; background: #f5f5f7; font-size: 13px; color: #1d1d1f; }
.debug-frame-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }
.debug-frame-card { border: 1px solid #ececf0; border-radius: 12px; overflow: hidden; background: #fafafa; }
.debug-frame-image { display: block; width: 100%; height: 132px; object-fit: cover; background: #f0f0f0; }
.debug-frame-caption { padding: 10px 12px; }
.step-result-list { display: flex; flex-direction: column; gap: 12px; }
.step-result-item { padding: 14px 16px; border-radius: 12px; background: #fafafa; }
.video-preview-panel { min-height: 240px; display: flex; align-items: center; justify-content: center; border-radius: 12px; background: #f8f8fa; overflow: hidden; }
.uploaded-video-player { width: 100%; max-height: 420px; border-radius: 12px; background: #000; }
.review-video-card { margin-bottom: 16px; }
.review-video-panel { min-height: 220px; }
.review-video-player { max-height: 320px; }
.review-head { margin-bottom: 16px; padding: 14px 16px; border-radius: 12px; background: #f5f5f7; }
.review-title { font-size: 16px; font-weight: 600; color: #1d1d1f; }
.review-radio-group, .dialog-footer { display: flex; flex-wrap: wrap; gap: 12px; }
.dialog-footer { justify-content: flex-end; }
:deep(.el-menu-item) { height: 44px; line-height: 44px; margin: 4px 16px; border-radius: 8px; color: #515154; }
:deep(.el-menu-item.is-active), :deep(.el-menu-item:hover) { background: #f5f5f7; color: #000; }
:deep(.el-table) { --el-table-border-color: #f5f5f7; --el-table-header-bg-color: #fafafa; color: #1d1d1f; }
:deep(.el-table td.el-table__cell) { padding: 16px 0; font-size: 14px; }
:deep(.minimal-dialog) { border-radius: 16px; overflow: hidden; }
:deep(.minimal-dialog .el-dialog__header) { padding: 24px 24px 16px; margin-right: 0; border-bottom: 1px solid #e5e5ea; }
:deep(.minimal-dialog .el-dialog__body) { padding: 24px; }
:deep(.minimal-form .el-form-item__label) { font-size: 13px; font-weight: 500; color: #515154; }
:deep(.minimal-textarea .el-textarea__inner), :deep(.minimal-form .el-textarea__inner), :deep(.minimal-form .el-input__wrapper) { border-radius: 8px; }
:deep(.minimal-tag) { background: #f5f5f7; color: #1d1d1f; border: 1px solid #e5e5ea; border-radius: 6px; font-weight: 500; }
:deep(.minimal-status-tag) { border-radius: 999px; border: 1px solid #e5e5ea; font-weight: 500; }
:deep(.minimal-status-tag.is-passed), :deep(.minimal-status-tag.is-review-approved) { background: #edf9f1; border-color: #cdeed8; color: #157347; }
:deep(.minimal-status-tag.is-failed), :deep(.minimal-status-tag.is-review-rejected) { background: #fff2f0; border-color: #ffd9d4; color: #c0392b; }
:deep(.minimal-status-tag.is-pending), :deep(.minimal-status-tag.is-review-needs-attention) { background: #fff8e8; border-color: #f8e3a5; color: #9a6700; }
.action-btn { font-weight: 500; padding: 4px 8px; }
@media (max-width: 960px) { .content-area { padding: 20px; } .top-header, .form-row, .section-head, .debug-step-top, .step-result-top { flex-direction: column; align-items: flex-start; } .debug-meta-grid { grid-template-columns: 1fr; } }
</style>
