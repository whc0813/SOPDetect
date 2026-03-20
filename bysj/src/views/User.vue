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

          <div class="progress-section">
            <div class="progress-text">进度 {{ activeStep + 1 }} / {{ currentSop.stepCount }}</div>
            <el-progress 
              :percentage="((activeStep) / currentSop.stepCount) * 100" 
              :show-text="false"
              color="#000000"
              class="minimal-progress"
            />
          </div>

          <div class="step-container" v-if="activeStep < currentSop.stepCount">
            <div class="step-instruction">
              <div class="step-label">当前步骤 {{ activeStep + 1 }}</div>
              <p class="step-desc">{{ currentSop.steps[activeStep].description }}</p>
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
                  @click="submitStepVideo" 
                  :loading="isEvaluating"
                >
                  解析与验证
                </el-button>
              </div>
            </div>
          </div>

          <!-- Result Area -->
          <div class="result-card" v-if="evaluationResult" :class="evaluationResult.passed ? 'success' : 'error'">
            <div class="result-header">
              <el-icon class="result-icon" v-if="evaluationResult.passed"><CircleCheckFilled /></el-icon>
              <el-icon class="result-icon" v-else><WarningFilled /></el-icon>
              <h3>{{ evaluationResult.passed ? '验证通过' : '验证未通过' }}</h3>
            </div>
            <p class="result-feedback">{{ evaluationResult.feedback }}</p>
            
            <div class="result-actions">
              <el-button 
                v-if="evaluationResult.passed" 
                type="primary" 
                class="action-btn-primary"
                @click="nextStep"
              >
                {{ activeStep === currentSop.stepCount - 1 ? '完成整个流程' : '进入下一步' }}
              </el-button>
              <el-button 
                v-else 
                class="action-btn-secondary"
                @click="retryStep"
              >
                重新操作本步骤
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
const sopList = ref([])
const historyList = ref([])
const activeTab = ref('tasks')
const currentSop = ref(null)
const activeStep = ref(0)
const hasErrorInCurrentSop = ref(false)

const currentVideo = ref(null)
const isEvaluating = ref(false)
const evaluationResult = ref(null)

onMounted(() => {
  const stored = localStorage.getItem('sopList')
  if (stored) {
    sopList.value = JSON.parse(stored)
  }
  
  const historyStored = localStorage.getItem('sopHistoryList')
  if (historyStored) {
    historyList.value = JSON.parse(historyStored)
  }
})

const handleLogout = () => {
  router.push('/login')
}

const startSop = (sop) => {
  currentSop.value = sop
  activeStep.value = 0
  hasErrorInCurrentSop.value = false
  resetStepState()
}

const backToList = () => {
  currentSop.value = null
  resetStepState()
}

const resetStepState = () => {
  currentVideo.value = null
  isEvaluating.value = false
  evaluationResult.value = null
}

const handleVideoChange = (file) => {
  currentVideo.value = file
}

const submitStepVideo = () => {
  if (!currentVideo.value) {
    ElMessage.warning('请先上传视频')
    return
  }
  
  isEvaluating.value = true
  
  setTimeout(() => {
    isEvaluating.value = false
    const isPassed = Math.random() > 0.3
    
    if (isPassed) {
      evaluationResult.value = {
        passed: true,
        feedback: '动作顺序正确，操作符合规范要求。'
      }
    } else {
      evaluationResult.value = {
        passed: false,
        feedback: '检测到动作不规范：未完全按照描述执行操作，请注意关键动作细节。建议重新操作并上传。'
      }
      hasErrorInCurrentSop.value = true
    }
  }, 2500)
}

const saveHistory = () => {
  const record = {
    id: Date.now(),
    taskId: currentSop.value.id,
    taskName: currentSop.value.name,
    scene: currentSop.value.scene,
    finishTime: new Date().toLocaleString(),
    status: hasErrorInCurrentSop.value ? 'failed' : 'passed'
  }
  historyList.value.unshift(record)
  localStorage.setItem('sopHistoryList', JSON.stringify(historyList.value))
}

const nextStep = () => {
  if (activeStep.value === currentSop.value.stepCount - 1) {
    saveHistory()
    ElMessage.success('恭喜，SOP 流程已全部完成！')
    backToList()
  } else {
    activeStep.value++
    resetStepState()
  }
}

const retryStep = () => {
  resetStepState()
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

.result-feedback {
  font-size: 15px;
  line-height: 1.5;
  margin: 0 0 24px 0;
}

.success .result-feedback { color: #515154; }
.error .result-feedback { color: #86868b; }

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
</style>
