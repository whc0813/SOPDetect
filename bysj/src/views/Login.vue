<template>
  <div class="login-page">
    <AppBlobs />

    <div class="login-card">
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

      <form v-if="mode === 'login'" class="auth-form" @submit.prevent="handleLogin" novalidate>
        <div class="field-wrap" :class="{ 'is-error': errors.username }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="5.5" r="3.5" stroke="currentColor" stroke-width="1.6"/><path d="M2.5 16.5c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <input
              v-model="loginForm.username"
              type="text"
              class="field-input"
              placeholder="账号"
              autocomplete="username"
              @input="clearError('username')"
            />
          </div>
          <p v-if="errors.username" class="field-err" role="alert">{{ errors.username }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.password }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="8" width="12" height="8" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M6 8V5.5a3 3 0 0 1 6 0V8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <input
              v-model="loginForm.password"
              :type="showLoginPwd ? 'text' : 'password'"
              class="field-input"
              placeholder="密码"
              autocomplete="current-password"
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

      <form v-else class="auth-form" @submit.prevent="handleRegister" novalidate>
        <div class="field-wrap" :class="{ 'is-error': errors.displayName }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 2l1.8 3.6L15 6.3l-3 2.9.7 4.1L9 11.5l-3.7 1.8.7-4.1-3-2.9 4.2-.7z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" fill="none"/></svg>
            </span>
            <input v-model="registerForm.displayName" type="text" class="field-input" placeholder="昵称" autocomplete="name" @input="clearError('displayName')" />
          </div>
          <p v-if="errors.displayName" class="field-err" role="alert">{{ errors.displayName }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.username }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><circle cx="9" cy="5.5" r="3.5" stroke="currentColor" stroke-width="1.6"/><path d="M2.5 16.5c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <input v-model="registerForm.username" type="text" class="field-input" placeholder="账号" autocomplete="username" @input="clearError('username')" />
          </div>
          <p v-if="errors.username" class="field-err" role="alert">{{ errors.username }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.password }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="8" width="12" height="8" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M6 8V5.5a3 3 0 0 1 6 0V8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
            </span>
            <input v-model="registerForm.password" :type="showRegPwd ? 'text' : 'password'" class="field-input" placeholder="密码（至少 6 位）" autocomplete="new-password" @input="clearError('password')" />
            <button type="button" class="pwd-toggle" @click="showRegPwd = !showRegPwd">{{ showRegPwd ? '隐藏' : '显示' }}</button>
          </div>
          <p v-if="errors.password" class="field-err" role="alert">{{ errors.password }}</p>
        </div>
        <div class="field-wrap" :class="{ 'is-error': errors.confirmPassword }">
          <div class="field-row">
            <span class="field-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="3" y="8" width="12" height="8" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M6 8V5.5a3 3 0 0 1 6 0V8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="9" cy="12.5" r="1.2" fill="currentColor"/></svg>
            </span>
            <input v-model="registerForm.confirmPassword" :type="showRegConfirm ? 'text' : 'password'" class="field-input" placeholder="确认密码" autocomplete="new-password" @input="clearError('confirmPassword')" />
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
import { clearAuthSession, fetchCurrentUser, login, register, setAuthSession } from '../api/client'
import AppBlobs from '../components/AppBlobs.vue'

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
    const currentUserResult = await fetchCurrentUser()
    const currentUser = currentUserResult.data
    setAuthSession({
      ...auth,
      user: currentUser
    })
    ElMessage.success(`欢迎回来，${currentUser.displayName}`)
    router.push(currentUser.role === 'admin' ? '/admin' : '/user')
  } catch (error) {
    clearAuthSession()
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
.login-page {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: var(--sp-6);
  overflow: hidden;
  background: var(--bg-base);
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 380px;
  padding: 48px 36px 36px;
  border-radius: 30px;
  background: var(--material-thick);
  backdrop-filter: blur(var(--blur-xl)) saturate(180%);
  -webkit-backdrop-filter: blur(var(--blur-xl)) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.04),
    0 4px 16px rgba(0, 0, 0, 0.04),
    0 20px 56px rgba(0, 0, 0, 0.07),
    0 56px 96px rgba(0, 0, 0, 0.05);
  animation: card-enter 0.5s var(--ease-spring) both;
}

@media (prefers-color-scheme: dark) {
  .login-card {
    border-color: rgba(84, 84, 88, 0.5);
    box-shadow:
      0 0 0 0.5px rgba(0, 0, 0, 0.2),
      0 4px 16px rgba(0, 0, 0, 0.2),
      0 20px 56px rgba(0, 0, 0, 0.3),
      0 56px 96px rgba(0, 0, 0, 0.2);
  }
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* ── Brand ───────────────────────────────────────────────── */

.brand-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: var(--sp-8);
}

.app-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-xl);
  background: linear-gradient(150deg, #1D9BF0 0%, #0077E6 45%, #005BBF 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--sp-5);
  box-shadow:
    0 6px 28px rgba(0, 122, 255, 0.40),
    0 2px 8px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.26),
    inset 0 -1px 0 rgba(0, 0, 0, 0.10);
}

.app-name {
  font-size: var(--fs-title1);
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

/* ── Segmented Control ───────────────────────────────────── */

.seg-control {
  display: flex;
  padding: 3px;
  background: var(--fill-tertiary);
  border-radius: 11px;
  gap: 3px;
  margin-bottom: var(--sp-6);
}

.seg-btn {
  flex: 1;
  height: 38px;
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: var(--fs-subheadline);
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-family: inherit;
  transition:
    background var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard),
    box-shadow var(--duration-short) var(--ease-standard);
}

.seg-btn.active {
  background: var(--surface);
  color: var(--text-main);
  font-weight: 600;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.10), 0 0 0 0.5px rgba(0, 0, 0, 0.04);
}

@media (prefers-color-scheme: dark) {
  .seg-btn.active {
    background: var(--fill-secondary);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  }
}

.seg-btn:hover:not(.active) { color: var(--text-main); }
.seg-btn:active { transform: scale(0.97); }

/* ── Form ────────────────────────────────────────────────── */

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
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

.field-icon {
  position: absolute;
  left: 14px;
  display: flex;
  align-items: center;
  color: var(--text-faint);
  z-index: 1;
  pointer-events: none;
}

.field-input {
  width: 100%;
  height: 50px;
  padding: 0 16px 0 42px;
  background: var(--fill-tertiary);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-main);
  font-size: var(--fs-body);
  font-family: inherit;
  outline: none;
  -webkit-appearance: none;
  box-sizing: border-box;
  transition: background var(--duration-short), box-shadow var(--duration-short);
}

.field-row .field-input {
  padding-right: 64px;
}

.field-input::placeholder {
  color: var(--text-faint);
}

.field-input:focus {
  background: var(--fill-quaternary);
  box-shadow: 0 0 0 3.5px rgba(0, 122, 255, 0.30);
}

@media (prefers-color-scheme: dark) {
  .field-input:focus {
    box-shadow: 0 0 0 3.5px rgba(10, 132, 255, 0.40);
  }
}

.is-error .field-input {
  background: rgba(255, 59, 48, 0.07);
}

.is-error .field-input:focus {
  box-shadow: 0 0 0 3.5px rgba(255, 59, 48, 0.26);
}

.is-error .field-icon {
  color: var(--danger);
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
  font-size: var(--fs-footnote);
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  min-width: var(--touch-target);
  justify-content: center;
}

.field-err {
  font-size: var(--fs-footnote);
  color: var(--danger);
  margin: 0;
  padding-left: 4px;
  line-height: 1.4;
}

/* ── Primary Button ──────────────────────────────────────── */

.primary-btn {
  width: 100%;
  height: 52px;
  margin-top: var(--sp-2);
  background: linear-gradient(180deg, #0A84FF, #007AFF);
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: var(--fs-body);
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
  transition: background var(--duration-micro), transform var(--duration-micro), box-shadow var(--duration-micro);
}

.primary-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, #0077EE, #006AE0);
}

.primary-btn:active:not(:disabled) {
  transform: scale(0.985);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

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

/* ── Hint ────────────────────────────────────────────────── */

.hint-text {
  margin-top: var(--sp-6);
  font-size: var(--fs-caption1);
  color: var(--text-faint);
  text-align: center;
  line-height: 1.8;
}

/* ── Reduced Motion ──────────────────────────────────────── */

@media (prefers-reduced-motion: reduce) {
  .login-card { animation: none; }
  .seg-btn, .field-input, .primary-btn { transition: none; }
  .dots i { animation: none; opacity: 0.7; }
}

/* ── Mobile ──────────────────────────────────────────────── */

@media (max-width: 480px) {
  .login-card {
    padding: 36px 24px 28px;
    border-radius: var(--radius-2xl);
  }
  .app-icon { width: 68px; height: 68px; }
  .app-name { font-size: var(--fs-title2); }
}
</style>
