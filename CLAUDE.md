# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 编码规则

- 所有文件编码 UTF-8（无 BOM），禁止 UTF-16 / GBK
- 中文直接输出，不允许 `\uXXXX` 转义
- 不要删除整个文件重写，在原有基础上编辑
- 终端输出的乱码是本地方正常显示，无需处理

## 项目概述

基于视觉分析的 SOP（标准操作流程）管理系统。管理员维护操作规程并上传示范视频，用户上传执行视频，系统调用多模态大模型（OpenAI 兼容接口）完成符合性评估。

- 前端：Vue 3 + Element Plus + Vue Router 4，位于 `bysj/`
- 后端：FastAPI + Pydantic v2，位于 `backend/`
- 数据库：MySQL 8 + PyMySQL，启动时自动建表
- 视频处理：OpenCV + imageio-ffmpeg
- 模型调用：httpx（OpenAI Chat Completions 兼容格式）

## 常用命令

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py                          # 启动后端，监听 :8000
pytest tests/                           # 运行所有测试

# 前端
cd bysj
npm install
npm run serve                           # 启动开发服务器，:8080
npm run build                           # 生产构建
npm run lint                            # ESLint 检查
```

## 架构要点

### 后端模块职责

| 文件 | 职责 |
|---|---|
| `backend/main.py` | FastAPI 入口：路由定义、CORS、鉴权依赖注入、Worker 线程启停 |
| `backend/auth.py` | 自定义 Bearer Token 签发/校验、会话管理、角色鉴权 |
| `backend/storage.py` | MySQL 数据层：建表、CRUD、序列化、统计（文件最大，约 88KB） |
| `backend/evaluation.py` | 评估核心：参考包构建、Prompt 组装、大模型调用、异步 Worker |
| `backend/models.py` | Pydantic v2 请求/响应模型 |
| `backend/scoring.py` | 步骤权重计算、惩罚规则后处理 |
| `backend/video.py` | OpenCV/FFmpeg 视频帧提取与转码 |
| `backend/prompt.py` | Prompt 模板与 JSON Schema 约束构建 |

### 前端结构

| 路径 | 职责 |
|---|---|
| `bysj/src/main.js` | 应用入口，注册 Element Plus、全局图标 |
| `bysj/src/App.vue` | 根组件，路由出口与页面过渡动画 |
| `bysj/src/router/index.js` | 路由定义与角色守卫（`/admin`、`/user`、`/login`） |
| `bysj/src/api/client.js` | 封装 fetch 请求、Token 管理、跨标签页会话同步 |
| `bysj/src/views/Login.vue` | 登录/注册页 |
| `bysj/src/views/Admin.vue` | 管理员端：SOP CRUD、用户管理、数据统计 |
| `bysj/src/views/User.vue` | 用户端：任务列表、视频上传、评测结果、历史记录 |
| `bysj/src/components/` | 可复用组件（GlassCard、StatusBadge、EvalTimeline 等） |
| `bysj/src/styles/` | CSS 变量、基础样式、组件样式 |

### 路由

- `/login` — 登录/注册（公开）
- `/admin` — 管理员控制台（需 `role: admin`）
- `/user` — 用户控制台（需 `role: user`）

路由守卫在 `router/index.js` 中根据 `sessionStorage` 中的角色自动跳转，越权访问被重定向。

### 鉴权机制

自定义 Bearer Token，登录后存入 `sessionStorage`（key: `authSession`）。Token 包含用户 ID、角色、会话 ID、过期时间。同一账号同时只允许一个活跃会话（新登录踢旧会话）。前端通过 `client.js` 的 `storage` 事件实现跨标签页会话同步。

### 评估链路

1. 用户提交视频 → 创建 `evaluation_job`（queued）
2. 后台 Worker 线程每 2 秒轮询队列 → 领取任务（processing）
3. 读取 SOP 步骤信息、关键帧、ROI → 组装 Prompt（SOP 上下文 + Base64 视频帧 + JSON Schema）
4. 调用多模态大模型 → 解析结构化结果 → 应用惩罚规则
5. 写入 `sop_executions` / `execution_step_results` / `execution_issues`
6. 前端 3 秒间隔轮询任务状态（`/api/evaluation-jobs/{job_id}`），完成后停止

### AI 配置

AI 接口配置存储在 `ai_configs` 表中，`apiKey` 使用 `cryptography` 库静态加密（密钥来自 `.env` 的 `CONFIG_ENCRYPTION_KEY`）。默认使用 DashScope 兼容接口（`qwen-vl-plus` 等多模态模型）。

### 媒体存储

本地文件系统 `backend/data/media/Admin/`（示范视频）和 `User/`（执行视频）。媒体访问通过 `/api/media/{media_id}` 鉴权代理，管理员可访问全部，用户仅能访问公开资源或自己上传的文件。

## 测试

- 后端：`backend/tests/`，使用 pytest，覆盖评估链路、SOP 删除级联、历史查询优化、模块导出等
- 前端：`bysj/tests/user-history.test.js`，用户历史功能测试
