<template>
  <div class="login-container">
    <div class="login-card">
      <div class="brand-section">
        <div class="brand-mark"></div>
        <h1 class="title">标准行为识别</h1>
        <p class="subtitle">标准操作流程管理系统</p>
      </div>

      <div class="segmented-control" role="tablist">
        <button
          role="tab"
          :class="['segment', { active: mode === 'login' }]"
          :aria-selected="mode === 'login'"
          type="button"
          @click="switchMode('login')"
        >登录</button>
        <button
          role="tab"
          :class="['segment', { active: mode === 'register' }]"
          :aria-selected="mode === 'register'"
          type="button"
          @click="switchMode('register')"
        >注册</button>
      </div>

      <form v-if="mode === 'login'" class="auth-form" @submit.prevent="handleLogin" novalidate>
        <div class="field-group" :class="{ 'has-error': errors.username }">
          <input
            v-model="loginForm.username"
            type="text"
            class="field-input"
            placeholder="账号"
            autocomplete="username"
            @input="clearError('username')"
          />
          <span v-if="errors.username" class="field-error-msg" role="alert">{{ errors.username }}</span>
        </div>
        <div class="field-group" :class="{ 'has-error': errors.password }">
          <div class="field-row">
            <input
              v-model="loginForm.password"
              :type="showLoginPwd ? 'text' : 'password'"
              class="field-input"
              placeholder="密码"
              autocomplete="current-password"
              @keyup.enter="handleLogin"
              @input="clearError('password')"
            />
            <button type="button" class="toggle-btn" @click="showLoginPwd = !showLoginPwd">
              {{ showLoginPwd ? '隐藏' : '显示' }}
            </button>
          </div>
          <span v-if="errors.password" class="field-error-msg" role="alert">{{ errors.password }}</span>
        </div>
        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else class="loading-dots"><i></i><i></i><i></i></span>
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="handleRegister" novalidate>
        <div class="field-group" :class="{ 'has-error': errors.displayName }">
          <input
            v-model="registerForm.displayName"
            type="text"
            class="field-input"
            placeholder="昵称"
            autocomplete="name"
            @input="clearError('displayName')"
          />
          <span v-if="errors.displayName" class="field-error-msg" role="alert">{{ errors.displayName }}</span>
        </div>
        <div class="field-group" :class="{ 'has-error': errors.username }">
          <input
            v-model="registerForm.username"
            type="text"
            class="field-input"
            placeholder="账号"
            autocomplete="username"
            @input="clearError('username')"
          />
          <span v-if="errors.username" class="field-error-msg" role="alert">{{ errors.username }}</span>
        </div>
        <div class="field-group" :class="{ 'has-error': errors.password }">
          <div class="field-row">
            <input
              v-model="registerForm.password"
              :type="showRegPwd ? 'text' : 'password'"
              class="field-input"
              placeholder="密码（至少 6 位）"
              autocomplete="new-password"
              @input="clearError('password')"
            />
            <button type="button" class="toggle-btn" @click="showRegPwd = !showRegPwd">
              {{ showRegPwd ? '隐藏' : '显示' }}
            </button>
          </div>
          <span v-if="errors.password" class="field-error-msg" role="alert">{{ errors.password }}</span>
        </div>
        <div class="field-group" :class="{ 'has-error': errors.confirmPassword }">
          <div class="field-row">
            <input
              v-model="registerForm.confirmPassword"
              :type="showRegConfirm ? 'text' : 'password'"
              class="field-input"
              placeholder="确认密码"
              autocomplete="new-password"
              @keyup.enter="handleRegister"
              @input="clearError('confirmPassword')"
            />
            <button type="button" class="toggle-btn" @click="showRegConfirm = !showRegConfirm">
              {{ showRegConfirm ? '隐藏' : '显示' }}
            </button>
          </div>
          <span v-if="errors.confirmPassword" class="field-error-msg" role="alert">{{ errors.confirmPassword }}</span>
        </div>
        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="!loading">注册账号</span>
          <span v-else class="loading-dots"><i></i><i></i><i></i></span>
        </button>
      </form>

      <p class="hint">默认管理员：admin &nbsp;·&nbsp; 新注册账号默认为普通用户</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register, setAuthSession } from '../api/client'

const router = useRouter()
const loading = ref(false)
const mode = ref('login')
const showLoginPwd = ref(false)
const showRegPwd = ref(false)
const showRegConfirm = ref(false)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ displayName: '', username: '', password: '', confirmPassword: '' })
const errors = reactive({})

function clearError(field) {
  errors[field] = ''
}

function switchMode(nextMode) {
  mode.value = nextMode
  Object.keys(errors).forEach((k) => { errors[k] = '' })
}

function validateLogin() {
  errors.username = loginForm.username.trim() ? '' : '请输入账号'
  errors.password = loginForm.password ? '' : '请输入密码'
  return !errors.username && !errors.password
}

function validateRegister() {
  errors.displayName = registerForm.displayName.trim() ? '' : '请输入昵称'
  errors.username = registerForm.username.trim() ? '' : '请输入账号'
  if (!errors.username && (registerForm.username.length < 3 || registerForm.username.length > 50)) {
    errors.username = '账号长度需在 3 到 50 个字符之间'
  }
  errors.password = registerForm.password ? '' : '请输入密码'
  if (!errors.password && registerForm.password.length < 6) {
    errors.password = '密码长度不能少于 6 位'
  }
  errors.confirmPassword = registerForm.confirmPassword ? '' : '请再次输入密码'
  if (!errors.confirmPassword && registerForm.confirmPassword !== registerForm.password) {
    errors.confirmPassword = '两次输入的密码不一致'
  }
  return !errors.displayName && !errors.username && !errors.password && !errors.confirmPassword
}

async function handleLogin() {
  if (!validateLogin()) return
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
  if (!validateRegister()) return
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
  padding: 24px;
  background: var(--bg-base);
}

.login-card {
  width: 100%;
  max-width: 390px;
  padding: 44px 36px 36px;
  border-radius: 24px;
  border: 1px solid var(--line-soft);
  background: var(--surface);
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

/* Brand */
.brand-section {
  text-align: center;
  margin-bottom: 36px;
}

.brand-mark {
  width: 60px;
  height: 60px;
  background: linear-gradient(150deg, #007aff 0%, #0056cc 100%);
  border-radius: 16px;
  margin: 0 auto 18px;
  position: relative;
  box-shadow: 0 4px 16px rgba(0, 122, 255, 0.28);
}

.brand-mark::before {
  content: '';
  position: absolute;
  inset: 14px 12px 18px;
  border: 2.5px solid rgba(255, 255, 255, 0.9);
  border-radius: 3px;
}

.brand-mark::after {
  content: '';
  position: absolute;
  bottom: 9px;
  left: 50%;
  transform: translateX(-50%);
  width: 16px;
  height: 3px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 2px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.04em;
  margin: 0 0 8px;
  color: var(--text-main);
  line-height: 1.1;
}

.subtitle {
  font-size: 15px;
  color: var(--text-soft);
  margin: 0;
  line-height: 1.5;
}

/* Segmented Control */
.segmented-control {
  display: flex;
  padding: 3px;
  background: var(--apple-fill);
  border-radius: 9999px;
  margin-bottom: 28px;
}

.segment {
  flex: 1;
  padding: 9px 0;
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: 15px;
  font-weight: 500;
  border-radius: 9999px;
  cursor: pointer;
  font-family: inherit;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard);
}

.segment.active {
  background: var(--surface-strong);
  color: var(--text-main);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.segment:hover:not(.active) {
  color: var(--text-main);
}

.segment:active {
  transform: scale(0.97);
}

/* Form */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-row {
  position: relative;
  display: flex;
  align-items: center;
}

.field-input {
  width: 100%;
  height: 50px;
  padding: 0 14px;
  border: 1.5px solid var(--line-soft);
  border-radius: 13px;
  background: var(--surface-secondary);
  color: var(--text-main);
  font-size: 16px;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
  transition:
    border-color var(--duration-short) var(--ease-standard),
    box-shadow var(--duration-short) var(--ease-standard);
  -webkit-appearance: none;
}

.field-row .field-input {
  padding-right: 60px;
}

.field-input::placeholder {
  color: var(--text-faint);
}

.field-input:focus {
  border-color: var(--apple-blue);
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.14);
}

.has-error .field-input {
  border-color: var(--danger);
}

.has-error .field-input:focus {
  box-shadow: 0 0 0 4px rgba(255, 59, 48, 0.12);
}

.toggle-btn {
  position: absolute;
  right: 14px;
  border: none;
  background: none;
  color: var(--accent);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 4px 2px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.field-error-msg {
  font-size: 13px;
  color: var(--danger);
  padding-left: 4px;
  line-height: 1.4;
}

.submit-btn {
  width: 100%;
  height: 52px;
  margin-top: 6px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: 9999px;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background-color var(--duration-short) var(--ease-standard),
    transform var(--duration-micro) var(--ease-standard),
    opacity var(--duration-short) var(--ease-standard);
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-deep);
}

.submit-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.submit-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Loading dots */
.loading-dots {
  display: flex;
  gap: 5px;
  align-items: center;
}

.loading-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  display: block;
  animation: dot-bounce 1.2s ease-in-out infinite;
  list-style: none;
  font-style: normal;
}

.loading-dots i:nth-child(2) { animation-delay: 0.2s; }
.loading-dots i:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.55); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.hint {
  margin-top: 28px;
  font-size: 13px;
  color: var(--text-faint);
  text-align: center;
  line-height: 1.8;
}

@media (prefers-color-scheme: dark) {
  .login-card {
    background: var(--surface);
  }

  .brand-mark {
    box-shadow: 0 4px 20px rgba(0, 122, 255, 0.2);
  }
}

@media (prefers-reduced-motion: reduce) {
  .segment,
  .field-input,
  .submit-btn {
    transition: none;
  }

  .loading-dots i {
    animation: none;
    opacity: 0.7;
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 36px 24px 28px;
    border-radius: 20px;
  }
}
</style>
