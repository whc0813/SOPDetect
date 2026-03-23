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
  --bg-base: #f5f5f7;
  --bg-soft: rgba(255, 255, 255, 0.72);
  --surface: rgba(255, 255, 255, 0.72);
  --surface-strong: #ffffff;
  --surface-dark: #1d1d1f;
  --line-soft: rgba(0, 0, 0, 0.05);
  --line-strong: rgba(0, 0, 0, 0.1);
  --text-main: #1d1d1f;
  --text-soft: #86868b;
  --text-faint: #a1a1a6;
  --accent: #0071e3;
  --accent-deep: #0077ed;
  --success: #34c759;
  --danger: #ff3b30;
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.04);
  --radius-xl: 20px;
  --radius-lg: 16px;
  --radius-md: 12px;
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
  background-image: radial-gradient(circle at 50% 0%, #ffffff 0%, transparent 80%);
  background-attachment: fixed;
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
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

.minimal-msgbox {
  border-radius: var(--radius-lg) !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  box-shadow: var(--shadow-lg) !important;
  padding: 0 !important;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
}

.minimal-msgbox .el-message-box__header {
  padding: 22px 24px 14px !important;
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
}

.minimal-msgbox .el-message-box__btns {
  padding: 16px 24px 22px !important;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: transparent;
}

.minimal-msgbox .el-message-box__btns .el-button {
  min-width: 96px;
  height: 42px;
  border-radius: 999px !important;
  font-weight: 600;
  padding: 8px 24px;
}

.minimal-msgbox .el-message-box__btns .el-button--primary {
  background: var(--accent) !important;
  border-color: transparent !important;
  box-shadow: none;
}

.minimal-msgbox .el-message-box__btns .el-button--primary:hover {
  background: var(--accent-deep) !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary) {
  border-color: var(--line-soft) !important;
  background: #fff !important;
  color: var(--text-main) !important;
}
</style>
