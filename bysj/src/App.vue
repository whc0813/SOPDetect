<template>
  <router-view></router-view>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
:root {
  --apple-label: #000000;
  --apple-secondary-label: rgba(60, 60, 67, 0.6);
  --apple-tertiary-label: rgba(60, 60, 67, 0.38);
  --apple-bg: #f2f2f7;
  --apple-grouped-bg: #ffffff;
  --apple-secondary-bg: #ffffff;
  --apple-tertiary-bg: #f9f9fb;
  --apple-separator: rgba(60, 60, 67, 0.29);
  --apple-blue: #007aff;
  --apple-blue-pressed: #0063cc;
  --apple-fill: rgba(120, 120, 128, 0.2);
  --apple-fill-strong: rgba(120, 120, 128, 0.28);
  --bg-base: var(--apple-bg);
  --bg-elevated: rgba(255, 255, 255, 0.72);
  --bg-soft: rgba(255, 255, 255, 0.56);
  --surface: var(--apple-grouped-bg);
  --surface-strong: var(--apple-secondary-bg);
  --surface-secondary: var(--apple-tertiary-bg);
  --surface-dark: #1d1d1f;
  --line-soft: var(--apple-separator);
  --line-strong: rgba(60, 60, 67, 0.36);
  --text-main: var(--apple-label);
  --text-soft: var(--apple-secondary-label);
  --text-faint: var(--apple-tertiary-label);
  --accent: var(--apple-blue);
  --accent-deep: var(--apple-blue-pressed);
  --success: #34c759;
  --danger: #ff3b30;
  --warning-fill: rgba(255, 159, 10, 0.14);
  --success-fill: rgba(52, 199, 89, 0.14);
  --danger-fill: rgba(255, 59, 48, 0.12);
  --shadow-lg: none;
  --shadow-md: none;
  --radius-xl: 20px;
  --radius-lg: 16px;
  --radius-md: 12px;
  --radius-sm: 8px;
  --blur-md: 24px;
  --sidebar-width: 240px;
  --toolbar-height: 64px;
  --touch-target: 44px;
  --duration-micro: 100ms;
  --duration-short: 250ms;
  --duration-medium: 400ms;
  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}


@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-micro: 0ms;
    --duration-short: 0ms;
    --duration-medium: 0ms;
  }
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: var(--bg-base);
  background-image:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.52) 0%, transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.32), transparent 22%);
  background-attachment: fixed;
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: inherit;
}

#app {
  min-height: 100vh;
  color: var(--text-main);
}

button,
input,
textarea,
select {
  font: inherit;
}

.minimal-msgbox {
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--line-soft) !important;
  padding: 0 !important;
  overflow: hidden;
  background: var(--surface-strong) !important;
  backdrop-filter: blur(var(--blur-md));
  -webkit-backdrop-filter: blur(var(--blur-md));
}

.minimal-msgbox .el-message-box__header {
  padding: 24px 24px 16px !important;
  border-bottom: 1px solid var(--line-soft);
  background: transparent;
}

.minimal-msgbox .el-message-box__title {
  font-weight: 600 !important;
  font-size: 18px !important;
  letter-spacing: -0.02em;
  color: var(--text-main) !important;
}

.minimal-msgbox .el-message-box__content {
  padding: 20px 24px !important;
  color: var(--text-soft);
  font-size: 14px;
  line-height: 1.7;
}

.minimal-msgbox .el-message-box__btns {
  padding: 0 24px 24px !important;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: transparent;
}

.minimal-msgbox .el-message-box__btns .el-button {
  min-width: 96px;
  height: 44px;
  border-radius: 12px !important;
  font-weight: 500;
  padding: 8px 20px;
  transition:
    transform var(--duration-micro) var(--ease-standard),
    background-color var(--duration-short) var(--ease-standard),
    border-color var(--duration-short) var(--ease-standard),
    color var(--duration-short) var(--ease-standard) !important;
}

.minimal-msgbox .el-message-box__btns .el-button:active {
  transform: scale(0.96);
}

.minimal-msgbox .el-message-box__btns .el-button--primary {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #ffffff !important;
}

.minimal-msgbox .el-message-box__btns .el-button--primary:hover {
  background: var(--accent-deep) !important;
  border-color: var(--accent-deep) !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary) {
  border-color: var(--line-strong) !important;
  background: var(--surface-secondary) !important;
  color: var(--text-main) !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary):hover {
  border-color: var(--line-strong) !important;
  color: var(--text-main) !important;
  background: var(--surface) !important;
}

</style>
