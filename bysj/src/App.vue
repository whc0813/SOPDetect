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
  border-radius: 16px !important;
  border: 1px solid #e5e5ea !important;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08) !important;
  padding: 0 !important;
  overflow: hidden;
  background: #ffffff !important;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.minimal-msgbox .el-message-box__header {
  padding: 24px 24px 16px !important;
  border-bottom: 1px solid #e5e5ea;
  background: #ffffff;
}

.minimal-msgbox .el-message-box__title {
  font-weight: 600 !important;
  font-size: 18px !important;
  letter-spacing: -0.02em;
  color: #1d1d1f !important;
}

.minimal-msgbox .el-message-box__content {
  padding: 20px 24px !important;
  color: #515154;
  font-size: 14px;
  line-height: 1.7;
}

.minimal-msgbox .el-message-box__btns {
  padding: 0 24px 24px !important;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: #ffffff;
}

.minimal-msgbox .el-message-box__btns .el-button {
  min-width: 96px;
  height: 40px;
  border-radius: 8px !important;
  font-weight: 500;
  padding: 8px 20px;
  box-shadow: none !important;
}

.minimal-msgbox .el-message-box__btns .el-button--primary {
  background: #000000 !important;
  border-color: #000000 !important;
  color: #ffffff !important;
}

.minimal-msgbox .el-message-box__btns .el-button--primary:hover {
  background: #333333 !important;
  border-color: #333333 !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary) {
  border-color: #d2d2d7 !important;
  background: #ffffff !important;
  color: #1d1d1f !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary):hover {
  border-color: #86868b !important;
  color: #000000 !important;
  background: #ffffff !important;
}
</style>
