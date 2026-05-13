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
python main.py                          # 启动后端，监听 :8000；API 文档 http://localhost:8000/docs

# 后端测试（从仓库根目录执行，保证 backend 包可被正确导入）
python -m pytest backend/tests                                    # 全量
python -m pytest backend/tests/test_evaluation_pipeline.py        # 单文件
python -m pytest backend/tests/test_evaluation_pipeline.py::test_xxx  # 单用例

# 前端
cd bysj
npm install
npm run serve                           # 启动开发服务器，:8080（默认请求 :8000）
npm run build                           # 生产构建
npm run lint                            # ESLint 检查

# 前端测试（node:test，无需 jest/vitest）
cd bysj && node --test tests/*.test.js                  # 全量
cd bysj && node --test tests/user-history.test.js       # 单文件
```

### 环境变量（`backend/.env`）

| 变量 | 说明 |
|---|---|
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | 数据库连接，首次启动时自动建库建表 |
| `AUTH_TOKEN_SECRET` | Token 签名密钥（生产必填） |
| `AUTH_TOKEN_EXPIRES_IN` | Token 有效期（秒），默认 28800 |
| `EVALUATION_JOB_POLL_INTERVAL_SEC` | Worker 队列轮询间隔，默认 2 |
| `CONFIG_ENCRYPTION_KEY` | `ai_configs.apiKey` 加密密钥 |

### 默认种子账号

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin` | 管理员 |
| `user` | `user` | 普通用户 |

新注册账号默认为普通用户；管理员账号无法通过前端注册创建。

## 架构要点

### 后端模块职责

| 文件 | 职责 |
|---|---|
| `backend/main.py` | FastAPI 入口：路由定义、CORS、鉴权依赖注入、Worker 线程启停 |
| `backend/auth.py` | 自定义 Bearer Token 签发/校验、会话管理、角色鉴权 |
| `backend/storage.py` | MySQL 数据层：建表、CRUD、序列化、统计（文件最大，约 88KB） |
| `backend/evaluation.py` | 评估核心：参考包构建、Prompt 组装、大模型调用、异步 Worker |
| `backend/models.py` | Pydantic v2 请求/响应模型 |
| `backend/scoring.py` | 二值状态判定、前置依赖与耗时规则后处理 |
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

评测任务由后台 Worker 线程异步执行，**核心是三阶段串联的多模态模型调用**：

1. 用户提交视频 → 创建 `evaluation_job`（queued）
2. 后台 Worker 线程每 2 秒轮询队列 → 领取任务（processing）
3. 读取 SOP 步骤信息、关键帧、关键时刻、ROI
4. **Stage 1 时序分割**：调用模型识别用户视频中每步的起止时间和出现次数
5. **Stage 2 步骤评估**：基于完整用户视频、参考关键帧和候选时间窗，批量评估各步骤完成度、问题类型、证据
6. **Stage 3 顺序校验**：基于步骤结果做全局校验，修正错序、前置依赖违反和重复执行
7. 后端应用可选 / 条件步骤、最短/最长耗时等规则，生成最终二值通过状态（`scoring.py`）
8. 汇总 `payloadPreview`、`rawModelResult` 和 Token 用量，写入 `sop_executions` / `execution_step_results` / `execution_issues`
9. 前端 3 秒间隔轮询 `/api/evaluation-jobs/{job_id}`，完成后停止

SOP 创建时上传完整流程示范视频，后端做时序分割后按步骤抽帧并调用模型生成步骤摘要、关键时刻、ROI 提示，作为评估时的参考包。底层评估模型仍支持文字参考模式，用于内联评估 `/api/evaluate` 与历史兼容数据。

### AI 配置

AI 接口配置存储在 `ai_configs` 表中，`apiKey` 使用 `cryptography` 库静态加密（密钥来自 `.env` 的 `CONFIG_ENCRYPTION_KEY`）。默认使用 DashScope 兼容的 OpenAI Chat Completions 接口（`qwen-vl-plus` 等多模态模型）。可通过 `/api/prepare-step-video` 与 `/api/evaluate` 的请求体临时覆盖全局 `apiConfig`。

### 媒体存储

本地文件系统 `backend/data/media/Admin/`（示范视频）和 `User/`（执行视频）。媒体访问通过 `/api/media/{media_id}` 鉴权代理，管理员可访问全部，用户仅能访问公开资源或自己上传的文件。

## 测试

- 后端：`backend/tests/`，使用 pytest，覆盖评估链路（`test_evaluation_pipeline.py`）、SOP / 历史记录删除级联（`test_delete_sop_media_cleanup.py`、`test_delete_history.py`）、历史查询优化、模块导出、风险耗时移除等
- 前端：`bysj/tests/`，使用 Node.js 内置 `node:test`，覆盖用户历史（`user-history.test.js`）与管理员惩罚配置（`admin-penalty-config.test.js`）
- 后端测试需从仓库根目录执行（`python -m pytest backend/tests`），保证 `backend` 作为包正确导入
