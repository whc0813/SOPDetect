<template>
  <div class="login-container">
    <div class="login-content">
      <div class="title-section">
        <h1>标准行为识别</h1>
        <p class="subtitle">标准操作流程管理系统</p>
      </div>

      <div class="switch-row">
        <el-button
          :type="mode === 'login' ? 'primary' : 'default'"
          :class="['switch-btn', { 'is-active': mode === 'login' }]"
          @click="switchMode('login')"
        >
          登录
        </el-button>
        <el-button
          :type="mode === 'register' ? 'primary' : 'default'"
          :class="['switch-btn', { 'is-active': mode === 'register' }]"
          @click="switchMode('register')"
        >
          注册
        </el-button>
      </div>

      <el-form
        v-if="mode === 'login'"
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="账号"
            class="minimal-input"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            class="minimal-input"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <el-form
        v-else
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="login-form"
      >
        <el-form-item prop="displayName">
          <el-input
            v-model="registerForm.displayName"
            placeholder="昵称"
            class="minimal-input"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="账号"
            class="minimal-input"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="密码（至少 6 位）"
            class="minimal-input"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="确认密码"
            class="minimal-input"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleRegister">
            注册账号
          </el-button>
        </el-form-item>
      </el-form>

      <div class="tip">
        <span>默认管理员：admin</span> | <span>新注册账号默认为普通用户</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { login, register, setAuthSession } from '../api/client'

const router = useRouter()
const loading = ref(false)
const mode = ref('login')
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  displayName: '',
  username: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (_rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入密码'))
    return
  }
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const loginRules = reactive({
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
})

const registerRules = reactive({
  displayName: [
    { required: true, message: '请输入昵称', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 3, max: 50, message: '账号长度需在 3 到 50 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
})

function switchMode(nextMode) {
  mode.value = nextMode
}

async function handleLogin() {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await login({
      username: loginForm.username.trim(),
      password: loginForm.password
    })
    const auth = result.data
    setAuthSession(auth)
    ElMessage.success(`欢迎回来，${auth.user.displayName}`)
    router.push(auth.user.role === 'admin' ? '/admin' : '/user')
  } catch (error) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await register({
      displayName: registerForm.displayName.trim(),
      username: registerForm.username.trim(),
      password: registerForm.password
    })
    ElMessage.success('注册成功，请使用新账号登录')
    loginForm.username = registerForm.username.trim()
    loginForm.password = ''
    registerForm.displayName = ''
    registerForm.username = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    mode.value = 'login'
  } catch (error) {
    ElMessage.error(error.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 32px;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.56) 0%, transparent 26%),
    var(--bg-base);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
}

.login-content {
  width: 100%;
  max-width: 380px;
  padding: 32px 28px 28px;
  border-radius: 20px;
  border: 1px solid var(--line-soft);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.52), rgba(255, 255, 255, 0.18)),
    var(--surface);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

.title-section {
  text-align: center;
  margin-bottom: 32px;
}

.title-section h1 {
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.04em;
  margin: 0 0 8px 0;
  color: var(--text-main);
  line-height: 1.1;
}

.subtitle {
  font-size: 15px;
  color: var(--text-soft);
  margin: 0;
  letter-spacing: 0.01em;
  line-height: 1.6;
}

.switch-row {
  display: flex;
  width: 100%;
  gap: 0;
  margin-bottom: 24px;
  padding: 4px;
  min-height: 44px;
  background: var(--apple-fill);
  border: 1px solid transparent;
  border-radius: 9999px;
}

.switch-row :deep(.el-button + .el-button) {
  margin-left: 0;
}

.switch-btn {
  flex: 1;
  height: 40px;
  border: none !important;
  background: transparent !important;
  color: var(--text-soft) !important;
  border-radius: 9999px !important;
  font-size: 16px;
  font-weight: 600;
  transition:
    transform var(--duration-micro) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.switch-btn:hover {
  color: var(--text-main) !important;
  background: transparent !important;
}

.switch-btn.is-active {
  background: var(--surface-strong) !important;
  color: var(--text-main) !important;
  font-weight: 600;
}

.switch-btn.is-active:hover {
  background: var(--surface-strong) !important;
  color: var(--text-main) !important;
}

.switch-btn.is-active:focus,
.switch-btn.is-active:active,
.switch-btn:focus,
.switch-btn:active {
  border: none !important;
}

.switch-btn:active {
  transform: scale(0.96);
}

.login-form {
  margin-top: 8px;
}

:deep(.minimal-input .el-input__wrapper) {
  min-height: 48px;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  padding: 6px 14px;
  background-color: var(--surface-strong);
  transition:
    transform var(--duration-micro) var(--ease-standard),
    border-color var(--duration-short) var(--ease-standard),
    outline-color var(--duration-short) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard);
}

:deep(.minimal-input .el-input__wrapper.is-focus) {
  border-color: var(--apple-blue) !important;
  outline: 4px solid rgba(0, 122, 255, 0.16);
  outline-offset: 0;
}

:deep(.minimal-input .el-input__inner) {
  font-size: 17px;
  color: var(--text-main);
  height: 40px;
}

:deep(.minimal-input .el-input__prefix) {
  color: var(--text-faint);
  margin-right: 12px;
}

.login-btn {
  width: 100%;
  min-height: 48px;
  margin-top: 24px;
  background-color: var(--accent);
  border-color: var(--accent);
  border-radius: 9999px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  transition:
    transform var(--duration-micro) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard),
    border-color var(--duration-short) var(--ease-standard);
}

.login-btn:hover,
.login-btn:focus {
  background-color: var(--accent-deep);
  border-color: var(--accent-deep);
}

.login-btn:active {
  transform: scale(0.96);
}

.tip {
  margin-top: 32px;
  font-size: 13px;
  color: var(--text-faint);
  text-align: center;
  line-height: 1.8;
}

.tip span {
  display: inline-block;
  padding: 0 8px;
}

@media (prefers-color-scheme: dark) {
  .login-container {
    background:
      radial-gradient(circle at top, rgba(255, 255, 255, 0.08) 0%, transparent 24%),
      var(--bg-base);
  }

  .login-content {
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
      var(--surface);
  }
}

@media (prefers-reduced-motion: reduce) {
  .switch-btn,
  .login-btn,
  :deep(.minimal-input .el-input__wrapper) {
    transition: none;
  }
}
</style>
