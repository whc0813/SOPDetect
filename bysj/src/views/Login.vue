<template>
  <div class="login-page">
    <!-- Ambient background blobs -->
    <div class="blob blob-blue" aria-hidden="true"></div>
    <div class="blob blob-purple" aria-hidden="true"></div>
    <div class="blob blob-green" aria-hidden="true"></div>

    <div class="login-card">
      <!-- App Icon -->
      <div class="brand-section">
        <div class="app-icon" aria-hidden="true">
          <svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="6" y="8" width="32" height="22" rx="3" stroke="white" stroke-width="2.5" fill="none"/>
            <path d="M15 30 L22 34 L29 30" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <line x1="14" y1="34" x2="30" y2="34" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="22" cy="19" r="4" fill="white" fill-opacity="0.85"/>
          </svg>
        </div>
        <h1 class="app-name">标准行为识别</h1>
        <p class="app-tagline">标准操作流程管理系统</p>
      </div>

      <!-- Segmented Control -->
      <div class="seg-control" role="tablist">
        <button
          role="tab"
          :class="['seg-btn', { active: mode === 'login' }]"
          :aria-selected="mode === 'login'"
          type="button"
          @click="switchMode('login')"
        >登录</button>
        <button
          role="tab"
          :class="['seg-btn', { active: mode === 'register' }]"
          :aria-selected="mode === 'register'"
          type="button"
          @click="switchMode('register')"
        >注册</button>
      </div>

      <!-- Login Form -->
      <form v-if="mode === 'login'" class="auth-form" @submit.prevent="handleLogin" novalidate>
        <div class="field-wrap" :class="{ 'is-error': errors.username }">
          <input
            v-model="loginForm.username"
            type="text"
            class="field-input"
            placeholder="账号"
            autocomplete="username"
            @input="clearError('username')"
          />
          <p v-if="errors.username" class="field-err" role="alert">{{ errors.username }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.password }">
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
            <button type="button" class="pwd-toggle" @click="showLoginPwd = !showLoginPwd">
              {{ showLoginPwd ? '隐藏' : '显示' }}
            </button>
          </div>
          <p v-if="errors.password" class="field-err" role="alert">{{ errors.password }}</p>
        </div>
        <button type="submit" class="primary-btn" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else class="dots"><i></i><i></i><i></i></span>
        </button>
      </form>

      <!-- Register Form -->
      <form v-else class="auth-form" @submit.prevent="handleRegister" novalidate>
        <div class="field-wrap" :class="{ 'is-error': errors.displayName }">
          <input v-model="registerForm.displayName" type="text" class="field-input" placeholder="昵称" autocomplete="name" @input="clearError('displayName')" />
          <p v-if="errors.displayName" class="field-err" role="alert">{{ errors.displayName }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.username }">
          <input v-model="registerForm.username" type="text" class="field-input" placeholder="账号" autocomplete="username" @input="clearError('username')" />
          <p v-if="errors.username" class="field-err" role="alert">{{ errors.username }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.password }">
          <div class="field-row">
            <input v-model="registerForm.password" :type="showRegPwd ? 'text' : 'password'" class="field-input" placeholder="密码（至少 6 位）" autocomplete="new-password" @input="clearError('password')" />
            <button type="button" class="pwd-toggle" @click="showRegPwd = !showRegPwd">{{ showRegPwd ? '隐藏' : '显示' }}</button>
          </div>
          <p v-if="errors.password" class="field-err" role="alert">{{ errors.password }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.confirmPassword }">
          <div class="field-row">
            <input v-model="registerForm.confirmPassword" :type="showRegConfirm ? 'text' : 'password'" class="field-input" placeholder="确认密码" autocomplete="new-password" @keyup.enter="handleRegister" @input="clearError('confirmPassword')" />
            <button type="button" class="pwd-toggle" @click="showRegConfirm = !showRegConfirm">{{ showRegConfirm ? '隐藏' : '显示' }}</button>
          </div>
          <p v-if="errors.confirmPassword" class="field-err" role="alert">{{ errors.confirmPassword }}</p>
        </div>
        <button type="submit" class="primary-btn" :disabled="loading">
          <span v-if="!loading">注册账号</span>
          <span v-else class="dots"><i></i><i></i><i></i></span>
        </button>
      </form>

      <p class="hint-text">默认管理员：admin &nbsp;·&nbsp; 新注册账号默认为普通用户</p>
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
    const result = await login({ username: loginForm.username.trim(), password: loginForm.password })
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
/* ─── Page Shell ─────────────────────────────────────────── */
.login-page {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 24px;
  overflow: hidden;
  background: var(--bg-base);
}

/* ─── Ambient Blobs ──────────────────────────────────────── */
.blob {
  position: fixed;
  border-radius: 50%;
  filter: blur(72px);
  pointer-events: none;
  z-index: 0;
}

.blob-blue {
  width: 560px;
  height: 560px;
  top: -120px;
  left: -80px;
  background: radial-gradient(circle, rgba(0, 122, 255, 0.18) 0%, transparent 70%);
  animation: float-a 10s ease-in-out infinite alternate;
}

.blob-purple {
  width: 480px;
  height: 480px;
  bottom: -100px;
  right: -60px;
  background: radial-gradient(circle, rgba(88, 86, 214, 0.13) 0%, transparent 70%);
  animation: float-b 13s ease-in-out infinite alternate;
}

.blob-green {
  width: 360px;
  height: 360px;
  top: 10%;
  right: 20%;
  background: radial-gradient(circle, rgba(52, 199, 89, 0.09) 0%, transparent 70%);
  animation: float-c 16s ease-in-out infinite alternate;
}

@keyframes float-a {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(40px, 30px) scale(1.08); }
}
@keyframes float-b {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(-30px, -40px) scale(1.06); }
}
@keyframes float-c {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(20px, -25px) scale(1.04); }
}

/* ─── Card ───────────────────────────────────────────────── */
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  padding: 52px 40px 40px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.80);
  backdrop-filter: blur(60px) saturate(180%);
  -webkit-backdrop-filter: blur(60px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.04),
    0 4px 16px rgba(0, 0, 0, 0.04),
    0 20px 56px rgba(0, 0, 0, 0.07),
    0 56px 96px rgba(0, 0, 0, 0.05);
}

/* ─── Brand / App Icon ──────────────────────────────────── */
.brand-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 36px;
}

.app-icon {
  width: 84px;
  height: 84px;
  border-radius: 20px;
  background: linear-gradient(150deg, #1D9BF0 0%, #0077E6 45%, #005BBF 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow:
    0 6px 28px rgba(0, 122, 255, 0.40),
    0 2px 8px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.26),
    inset 0 -1px 0 rgba(0, 0, 0, 0.10);
}

.app-name {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.05em;
  color: var(--text-main);
  margin: 0 0 6px;
  line-height: 1.1;
}

.app-tagline {
  font-size: 14px;
  color: var(--text-soft);
  margin: 0;
  letter-spacing: -0.01em;
}

/* ─── Segmented Control ─────────────────────────────────── */
.seg-control {
  display: flex;
  padding: 3px;
  background: rgba(120, 120, 128, 0.12);
  border-radius: 11px;
  gap: 3px;
  margin-bottom: 28px;
}

.seg-btn {
  flex: 1;
  height: 38px;
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: 15px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.18s, color 0.18s, box-shadow 0.18s;
}

.seg-btn.active {
  background: #ffffff;
  color: var(--text-main);
  font-weight: 600;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.10), 0 0 0 0.5px rgba(0, 0, 0, 0.04);
}

.seg-btn:hover:not(.active) { color: var(--text-main); }
.seg-btn:active { transform: scale(0.97); }

/* ─── Form ──────────────────────────────────────────────── */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-wrap {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-row {
  position: relative;
  display: flex;
  align-items: center;
}

/* Filled input — iOS/macOS style (no border, gray fill) */
.field-input {
  width: 100%;
  height: 52px;
  padding: 0 16px;
  background: rgba(120, 120, 128, 0.11);
  border: none;
  border-radius: 13px;
  color: var(--text-main);
  font-size: 17px;
  font-family: inherit;
  outline: none;
  -webkit-appearance: none;
  box-sizing: border-box;
  transition: background 0.15s, box-shadow 0.15s;
}

.field-row .field-input {
  padding-right: 64px;
}

.field-input::placeholder {
  color: var(--text-faint);
}

.field-input:focus {
  background: rgba(120, 120, 128, 0.07);
  box-shadow: 0 0 0 3.5px rgba(0, 122, 255, 0.30);
}

.is-error .field-input {
  background: rgba(255, 59, 48, 0.07);
}

.is-error .field-input:focus {
  box-shadow: 0 0 0 3.5px rgba(255, 59, 48, 0.26);
}

.pwd-toggle {
  position: absolute;
  right: 14px;
  height: 100%;
  display: flex;
  align-items: center;
  border: none;
  background: none;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  min-width: 44px;
  justify-content: center;
}

.field-err {
  font-size: 13px;
  color: var(--danger);
  margin: 0;
  padding-left: 4px;
  line-height: 1.4;
}

/* ─── Primary Button ─────────────────────────────────────── */
.primary-btn {
  width: 100%;
  height: 54px;
  margin-top: 8px;
  background: #007AFF;
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  cursor: pointer;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    0 1px 4px rgba(0, 0, 0, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.18),
    inset 0 -1px 0 rgba(0, 0, 0, 0.08);
  transition: background 0.12s, transform 0.08s, box-shadow 0.12s;
}

.primary-btn:hover:not(:disabled) {
  background: #0071F5;
}

.primary-btn:active:not(:disabled) {
  background: #0064DB;
  transform: scale(0.985);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Loading dots */
.dots {
  display: flex;
  gap: 5px;
  align-items: center;
}

.dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
  display: block;
  font-style: normal;
  animation: dot-pulse 1.2s ease-in-out infinite;
}

.dots i:nth-child(2) { animation-delay: 0.2s; }
.dots i:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.35; }
  40% { transform: scale(1); opacity: 1; }
}

/* ─── Hint ───────────────────────────────────────────────── */
.hint-text {
  margin-top: 24px;
  font-size: 12px;
  color: var(--text-faint);
  text-align: center;
  line-height: 1.8;
}


/* ─── Reduced Motion ────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .blob { animation: none; }
  .seg-btn, .field-input, .primary-btn { transition: none; }
  .dots i { animation: none; opacity: 0.7; }
}

/* ─── Mobile ────────────────────────────────────────────── */
@media (max-width: 480px) {
  .login-card {
    padding: 40px 28px 32px;
    border-radius: 24px;
  }

  .app-icon { width: 72px; height: 72px; }
  .app-name { font-size: 24px; }
}
</style>
