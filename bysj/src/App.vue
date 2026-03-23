<template>
  <router-view></router-view>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background-color: #f5f5f7;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  color: #1d1d1f;
  height: 100%;
}

.minimal-msgbox {
  border-radius: 16px !important;
  border: none !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1) !important;
  padding: 0 !important;
  overflow: hidden;
}

.minimal-msgbox .el-message-box__header {
  padding: 24px 24px 16px !important;
  border-bottom: 1px solid #e5e5ea;
}

.minimal-msgbox .el-message-box__title {
  font-weight: 600 !important;
  font-size: 18px !important;
  color: #1d1d1f !important;
}

.minimal-msgbox .el-message-box__content {
  padding: 24px !important;
}

.minimal-msgbox .el-message-box__btns {
  padding: 16px 24px 24px !important;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.minimal-msgbox .el-message-box__btns .el-button {
  border-radius: 8px !important;
  font-weight: 500;
  padding: 8px 24px;
  height: 40px;
}

.minimal-msgbox .el-message-box__btns .el-button--primary {
  background-color: #000000 !important;
  border-color: #000000 !important;
}

.minimal-msgbox .el-message-box__btns .el-button--primary:hover {
  background-color: #333333 !important;
  border-color: #333333 !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary) {
  border-color: transparent !important;
  background-color: transparent !important;
  color: #1d1d1f !important;
}

.minimal-msgbox .el-message-box__btns .el-button:not(.el-button--primary):hover {
  background-color: #f5f5f7 !important;
}
</style>
