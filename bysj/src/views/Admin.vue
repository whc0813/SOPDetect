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
            <el-table-column prop="id" label="ID" width="100" />
            <el-table-column prop="name" label="SOP 名称" />
            <el-table-column prop="scene" label="适用场景" />
            <el-table-column prop="stepCount" label="步骤数" width="120" align="center">
              <template #default="scope">
                <el-tag size="small" class="minimal-tag">{{ scope.row.stepCount }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="创建时间" width="180" />
            <el-table-column label="操作" width="180" align="right">
              <template #default="scope">
                <el-button text class="action-btn" @click="viewSop(scope.row)">查看</el-button>
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
          </div>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button text @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" class="submit-btn" @click="saveSop">发布</el-button>
        </div>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, DataLine, Plus, SwitchButton, Monitor } from '@element-plus/icons-vue'

const router = useRouter()

// Mock data
const sopList = ref([
  {
    id: 1,
    name: '穿戴防护装备规范',
    scene: '无菌车间',
    stepCount: 3,
    createTime: '2023-10-24 10:00:00',
    steps: [
      { description: '戴上防护帽，完全遮盖头发' },
      { description: '佩戴护目镜' },
      { description: '穿上无菌防护服并拉好拉链' }
    ]
  }
])

const dialogVisible = ref(false)

const sopForm = reactive({
  name: '',
  scene: '',
  stepCount: 1,
  steps: [{ description: '' }]
})

const handleLogout = () => {
  router.push('/login')
}

const openCreateDialog = () => {
  sopForm.name = ''
  sopForm.scene = ''
  sopForm.stepCount = 1
  sopForm.steps = [{ description: '' }]
  dialogVisible.value = true
}

const handleStepCountChange = (newVal) => {
  const currentLen = sopForm.steps.length
  if (newVal > currentLen) {
    for (let i = currentLen; i < newVal; i++) {
      sopForm.steps.push({ description: '' })
    }
  } else if (newVal < currentLen) {
    sopForm.steps.splice(newVal)
  }
}

const saveSop = () => {
  if (!sopForm.name) {
    ElMessage.warning('请输入 SOP 名称')
    return
  }
  const newSop = {
    id: Date.now(),
    name: sopForm.name,
    scene: sopForm.scene,
    stepCount: sopForm.stepCount,
    createTime: new Date().toLocaleString(),
    steps: JSON.parse(JSON.stringify(sopForm.steps))
  }
  sopList.value.push(newSop)
  localStorage.setItem('sopList', JSON.stringify(sopList.value))
  
  ElMessage.success('SOP 发布成功')
  dialogVisible.value = false
}

const viewSop = (row) => {
  ElMessageBox.alert(
    `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
      ${row.steps.map((s, i) => `
        <div style="margin-bottom: 12px; padding: 12px; background: #f5f5f7; border-radius: 8px;">
          <div style="font-size: 12px; color: #86868b; margin-bottom: 4px;">步骤 ${i+1}</div>
          <div style="font-size: 14px; color: #1d1d1f;">${s.description}</div>
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
  ).catch(() => {
    // 捕获 cancel/close 事件，防止抛出未处理的 Promise 拒绝错误
  })
}

const deleteSop = (row) => {
  ElMessageBox.confirm('确定要删除该 SOP 吗？', '提示', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    customClass: 'minimal-msgbox'
  }).then(() => {
    sopList.value = sopList.value.filter(item => item.id !== row.id)
    localStorage.setItem('sopList', JSON.stringify(sopList.value))
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// Sync to localStorage on init
localStorage.setItem('sopList', JSON.stringify(sopList.value))
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
