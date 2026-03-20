<template>
  <div class="login-container">
    <div class="login-content">
      <div class="title-section">
        <h1>视觉智检</h1>
        <p class="subtitle">标准操作流程管理系统</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" class="login-form">
        <el-form-item prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="账号 (admin / user)"
            class="minimal-input"
            :prefix-icon="User"
          ></el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input 
            type="password" 
            v-model="loginForm.password" 
            placeholder="密码" 
            @keyup.enter="handleLogin"
            class="minimal-input"
            :prefix-icon="Lock"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="tip">
        <span>管理员: admin</span> | <span>用户: user</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
})

const handleLogin = () => {
  loginFormRef.value.validate((valid) => {
    if (valid) {
      loading.value = true
      setTimeout(() => {
        loading.value = false
        if (loginForm.username === 'admin') {
          ElMessage.success('欢迎回来，管理员')
          router.push('/admin')
        } else if (loginForm.username === 'user') {
          ElMessage.success('欢迎回来，用户')
          router.push('/user')
        } else {
          ElMessage.error('账号不存在')
        }
      }, 600)
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #ffffff;
  color: #1a1a1a;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.login-content {
  width: 100%;
  max-width: 360px;
  padding: 40px;
}

.title-section {
  text-align: center;
  margin-bottom: 48px;
}

.title-section h1 {
  font-size: 32px;
  font-weight: 600;
  letter-spacing: -0.5px;
  margin: 0 0 8px 0;
  color: #000000;
}

.subtitle {
  font-size: 14px;
  color: #86868b;
  margin: 0;
  letter-spacing: 0.5px;
}

.login-form {
  margin-top: 20px;
}

:deep(.minimal-input .el-input__wrapper) {
  box-shadow: none !important;
  border-bottom: 1px solid #e5e5ea;
  border-radius: 0;
  padding: 8px 0;
  background-color: transparent;
  transition: border-color 0.3s ease;
}

:deep(.minimal-input .el-input__wrapper.is-focus) {
  border-bottom: 1px solid #000000;
}

:deep(.minimal-input .el-input__inner) {
  font-size: 15px;
  color: #1d1d1f;
  height: 40px;
}

:deep(.minimal-input .el-input__prefix) {
  color: #86868b;
  margin-right: 12px;
}

.login-btn {
  width: 100%;
  height: 48px;
  margin-top: 24px;
  background-color: #000000;
  border-color: #000000;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.login-btn:hover, .login-btn:focus {
  background-color: #333333;
  border-color: #333333;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tip {
  margin-top: 32px;
  font-size: 13px;
  color: #86868b;
  text-align: center;
}

.tip span {
  display: inline-block;
  padding: 0 8px;
}
</style>
