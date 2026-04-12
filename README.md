# 基于视觉分析的标准操作流程管理系统

> 一个前后端分离的 SOP（Standard Operating Procedure）管理与视频评估平台。管理员维护操作规程，用户上传执行视频，系统调用多模态大模型完成符合性评估并保存闭环复核记录。

---

## 目录

1. [核心功能](#核心功能)
2. [技术栈](#技术栈)
3. [系统架构](#系统架构)
4. [目录结构](#目录结构)
5. [快速开始](#快速开始)
6. [默认账号](#默认账号)
7. [API 一览](#api-一览)
8. [数据库设计](#数据库设计)
9. [评估链路](#评估链路)
10. [设计说明](#设计说明)
11. [测试](#测试)

---

## 核心功能

### 管理员端
- 创建 SOP，录入步骤说明，支持**必要步骤**与**条件步骤**（含前置步骤约束）
- 可选上传整段工作流视频，后端自动按步骤分割、抽帧，调用多模态模型生成步骤摘要、关键时刻和 ROI 提示
- 支持手动覆盖时间戳重建关键帧（`manual-segmentation-override`），或替换单步示范视频
- 配置步骤权重与惩罚规则（`penaltyConfig`），精细控制评分策略
- 查看 SOP 维度统计（执行次数、通过率、平均得分）
- 对执行记录进行人工复核（通过 / 不通过 / 需整改）
- 管理用户状态（启用 / 禁用）
- 配置 AI 接口参数（API Key、BaseURL、模型、fps、temperature、超时）

### 用户端
- 注册、登录，浏览待执行 SOP 列表
- 进入 SOP 查看各步骤说明与参考摘要，上传完整执行视频
- 后端异步评测，前端以 3 秒间隔轮询任务状态
- 查看评测结果（是否通过、综合得分、反馈、步骤级得分与证据）
- 查看历史执行记录及人工复核结论

---

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端框架 | Vue 3 + Vue Router 4 | 组件化 SPA |
| UI 组件库 | Element Plus 2 | 对话框、上传、图标等 |
| 前端构建 | Vue CLI 5 | `npm run serve / build` |
| 后端框架 | FastAPI + Pydantic v2 | 异步 HTTP API，自动生成 OpenAPI 文档 |
| 视频处理 | OpenCV + imageio-ffmpeg | 帧提取、帧率读取、FFmpeg 转码 |
| HTTP 客户端 | httpx | 调用多模态大模型接口 |
| 数据库 | MySQL 8 + PyMySQL | 持久化存储，启动时自动建表 |
| 媒体存储 | 本地文件系统 | `backend/data/media/Admin` / `User` |
| 鉴权 | 自定义 Bearer Token + 会话表 | 防止同一账号重复登录 |
| 模型接口 | OpenAI Chat Completions 兼容 | 默认 DashScope `qwen-vl-plus` 等多模态模型 |

---

## 系统架构

```
浏览器 (Vue 3 SPA)
    │  Bearer Token
    ▼
FastAPI (backend/main.py)
    ├── 鉴权中间件（Token 解析 + 会话校验）
    ├── SOP 管理接口（CRUD + 视频分割预处理）
    ├── 评估任务接口（创建 / 轮询 / 重试）
    ├── 历史记录接口（查询 + 人工复核）
    └── 后台评估 Worker（独立线程，每 2s 轮询队列）
            │
            ├── OpenCV / FFmpeg：视频帧提取与转码
            ├── httpx：调用多模态大模型
            └── MySQL：读写所有持久化数据
                    └── 本地文件系统：媒体文件
```

---

## 目录结构

```
.
├── backend/
│   ├── main.py              # FastAPI 入口：路由定义、鉴权、Worker 启停
│   ├── auth.py              # JWT/Token 签发与校验
│   ├── storage.py           # MySQL 存储层：建表、CRUD、序列化、统计
│   ├── evaluation.py        # 评估核心流程与后台 Worker
│   ├── models.py            # Pydantic 请求/响应模型
│   ├── scoring.py           # 步骤权重计算与后处理
│   ├── video.py             # 视频工具函数（帧提取、FFmpeg 调用）
│   ├── prompt.py            # Prompt 构建（SOP 上下文 + JSON Schema）
│   ├── requirements.txt     # Python 依赖
│   ├── mysql_schema.sql     # 独立建表脚本（可选导入）
│   ├── mysql_design.md      # 数据库设计说明
│   ├── .env                 # 环境变量（需自行创建，见快速开始）
│   ├── tests/               # pytest 测试（评估流程、SOP 删除等）
│   └── data/
│       └── media/
│           ├── Admin/       # 管理员上传的示范视频及关键帧
│           └── User/        # 用户上传的执行视频
├── bysj/
│   ├── package.json
│   ├── vue.config.js
│   ├── public/
│   └── src/
│       ├── main.js          # 应用入口，注册 Element Plus、全局图标
│       ├── App.vue          # 根组件，路由出口与页面过渡动画
│       ├── router/
│       │   └── index.js     # 路由定义与角色守卫
│       ├── api/
│       │   └── client.js    # 封装 fetch、Token 管理、跨标签页会话同步
│       ├── views/
│       │   ├── Login.vue    # 登录 / 注册页
│       │   ├── Admin.vue    # 管理员端（SOP 管理、用户管理、数据统计）
│       │   └── User.vue     # 用户端（任务列表、评测执行、历史记录）
│       ├── components/      # AppBlobs、GlassCard、GroupedList、SectionHeader、StatusBadge 等
│       └── styles/          # variables.css、base.css、components.css
└── README.md
```

---

## 快速开始

### 环境依赖

| 工具 | 版本要求 |
|---|---|
| Node.js | 16 及以上 |
| Python | 3.10 及以上 |
| MySQL | 8.x |
| FFmpeg | 由 `imageio-ffmpeg` 自动管理，无需手动安装 |

### 1. 配置数据库

在 `backend/` 目录下创建 `.env` 文件：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=sop_eval_system
```

> 后端首次启动时会自动创建数据库及所有表，无需手动导入 SQL。

可选项（写入 `.env`）：

```env
AUTH_TOKEN_SECRET=自定义签名密钥（不填则使用随机默认值）
AUTH_TOKEN_EXPIRES_IN=28800        # Token 有效期（秒），默认 8 小时
EVALUATION_JOB_POLL_INTERVAL_SEC=2 # 评估队列轮询间隔（秒）
CONFIG_ENCRYPTION_KEY=自定义加密密钥（用于 AI 配置中 apiKey 的静态加密）
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

启动后监听 `http://localhost:8000`，可访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

### 3. 启动前端

```bash
cd bysj
npm install
npm run serve
```

前端默认运行在 `http://localhost:8080`，请求地址默认为 `http://localhost:8000`。

如需修改后端地址，在 `bysj/` 下创建 `.env.local`：

```env
VUE_APP_API_BASE_URL=http://你的后端地址:8000
```

---

## 默认账号

系统首次初始化时自动写入以下种子账号：

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin` | 管理员 |
| `user` | `user` | 普通用户 |

> 新注册账号默认角色为普通用户。管理员账号无法通过前端注册创建。

---

## API 一览

### 认证

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `POST` | `/api/auth/login` | 公开 | 登录，返回 Bearer Token；同账号已登录时返回 409 |
| `POST` | `/api/auth/register` | 公开 | 注册普通用户 |
| `GET` | `/api/auth/me` | 已登录 | 获取当前登录用户信息 |
| `POST` | `/api/auth/logout` | 已登录 | 登出，撤销当前会话 |

### 用户与配置

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/users` | 管理员 | 获取用户列表 |
| `PUT` | `/api/users/{user_id}/status` | 管理员 | 启用或禁用用户 |
| `GET` | `/api/config` | 管理员 | 获取 AI 接口配置 |
| `PUT` | `/api/config` | 管理员 | 更新 AI 接口配置 |

### SOP 管理

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/sops` | 已登录 | SOP 列表 |
| `GET` | `/api/sops/{sop_id}` | 已登录 | SOP 详情（含步骤、关键帧、关键时刻） |
| `POST` | `/api/sops` | 管理员 | 新建 SOP；含工作流视频时自动分割步骤并预处理 |
| `DELETE` | `/api/sops/{sop_id}` | 管理员 | 删除 SOP 及全部关联媒体 |
| `PUT` | `/api/sops/{sop_id}/steps/{step_no}/demo-video` | 管理员 | 替换步骤示范视频并重建参考包 |
| `PUT` | `/api/sops/{sop_id}/steps/{step_no}/manual-segmentation` | — | **已弃用（返回 410）**，请改用 `manual-segmentation-override` 或重传示范视频 |
| `PUT` | `/api/sops/{sop_id}/steps/{step_no}/manual-segmentation-override` | 管理员 | 手动指定时间戳，从已存储媒体重建关键帧与参考包 |
| `PUT` | `/api/sops/{sop_id}/steps/{step_no}/reference-metadata` | 管理员 | 更新步骤参考摘要、ROI 提示和关键时刻 |

### 评估任务

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `POST` | `/api/sops/{sop_id}/evaluate` | 已登录 | **同步**评估（小文件场景，直接返回结果） |
| `POST` | `/api/sops/{sop_id}/evaluation-jobs` | 已登录 | **异步**创建评测任务（视频作为 multipart 上传） |
| `GET` | `/api/evaluation-jobs` | 已登录 | 获取当前用户的任务列表，可按 `status` 筛选 |
| `GET` | `/api/evaluation-jobs/{job_id}` | 已登录 | 轮询单个任务状态、进度与日志 |
| `POST` | `/api/evaluation-jobs/{job_id}/retry` | 已登录 | 重试失败任务 |

### 历史记录

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/history` | 已登录 | 执行历史列表；支持 `keyword`、`aiStatus`、`reviewStatus`、`sortOrder` 筛选 |
| `GET` | `/api/history/{record_id}` | 已登录 | 执行历史详情 |
| `POST` | `/api/history` | 已登录 | 从评估结果创建执行记录（含可选视频上传） |
| `PUT` | `/api/history/{record_id}/review` | 管理员 | 人工复核（通过 / 不通过 / 需整改） |
| `GET` | `/api/stats` | 管理员 | 汇总统计数据 |

### 媒体与工具

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/media/{media_id}` | 已登录 | 鉴权后返回媒体文件（FileResponse） |
| `POST` | `/api/prepare-step-video` | 管理员 | 单步视频预处理（抽帧 + AI），可传入 `apiConfig` 覆盖全局配置 |
| `POST` | `/api/evaluate` | 已登录 | 内联评估：请求体直接携带 `apiConfig`、`sop` 与视频 DataURL，无需预存 SOP |
| `GET` | `/api/health` | 公开 | 健康检查 |

---

## 数据库设计

`storage.py` 在首次连接时自动初始化以下表（字符集均为 `utf8mb4`）：

| 表名 | 说明 |
|---|---|
| `users` | 用户信息、角色、状态 |
| `user_login_sessions` | 登录会话，限制同账号只有一个活跃会话 |
| `ai_configs` | 模型接口配置（apiKey 加密存储、baseURL、model、fps 等） |
| `sops` | SOP 主表（名称、场景、步骤数、惩罚配置） |
| `sop_steps` | SOP 步骤（描述、摘要、ROI、参考模式、步骤类型、前置条件） |
| `media_files` | 媒体文件索引（路径、类型、归属） |
| `sop_step_keyframes` | 步骤关键帧（base64 图像，按顺序排列） |
| `sop_step_substeps` | 步骤关键时刻（标题 + 时间戳） |
| `evaluation_jobs` | 评测任务队列（状态、进度、阶段、日志） |
| `sop_executions` | 执行记录主表（得分、是否通过、反馈） |
| `execution_issues` | 执行问题列表 |
| `execution_step_results` | 步骤级评测结果（得分、置信度、证据） |
| `manual_reviews` | 人工复核记录（结论、意见） |

---

## 评估链路

评估任务由后台 Worker 线程异步执行，完整流程如下：

```
1. 用户提交视频
       │
       ▼
2. 创建 evaluation_job（状态: queued）
       │
       ▼
3. Worker 轮询，领取任务（状态: processing）
       │
       ▼
4. 读取 SOP 步骤信息、关键帧、关键时刻、ROI
       │
       ▼
5. 用 Base64 编码用户视频帧
       │
       ▼
6. 组装 Prompt（SOP 上下文 + 用户视频 + JSON Schema 约束）
       │
       ▼
7. 通过 httpx 调用多模态大模型接口（兼容 OpenAI 格式）
       │
       ▼
8. 解析结构化结果（整体得分、通过状态、步骤级结果、问题列表）
       │
       ▼
9. 应用 penaltyConfig 惩罚规则，重新计算加权综合分
       │
       ▼
10. 写入 sop_executions / execution_step_results / execution_issues
    更新 job 状态为 succeeded，记录 resultRecordId
       │
       ▼
11. 前端轮询到 succeeded → 拉取历史详情展示结果
```

**评估结果结构：**

- `passed`：是否通过
- `score`：综合得分（0–100）
- `feedback`：整体反馈文本
- `issues`：问题标签列表
- `stepResults[]`：每步的 `passed`、`score`、`confidence`、`evidence`

**SOP 退化策略：**  
步骤示范视频为可选项；无视频时系统退化为"仅基于文字 SOP 的评估"，评测仍可执行但缺少视觉参考。

---

## 设计说明

**鉴权机制**
- 登录成功后返回自定义 Bearer Token（含用户 ID、角色、会话 ID、过期时间），前端存入 `sessionStorage`
- 每次请求在服务端同时校验 Token 签名、过期时间、会话有效性，实现重复登录拦截
- 同一账号同时只允许一个活跃会话（新登录会踢掉旧会话）

**媒体权限**
- 管理员可访问全部媒体（示范视频、关键帧、执行视频）
- 普通用户仅能访问公开示范资源或自己上传的执行视频

**AI 配置加密**
- AI 接口的 `apiKey` 以加密形式写入数据库，通过 `.env` 中的 `CONFIG_ENCRYPTION_KEY` 控制加解密密钥

**评测任务队列**
- 评测为计算密集型操作，采用异步任务队列（`evaluation_jobs` 表 + 独立 Worker 线程），前端以 3 秒间隔轮询，任务完成后立即停止轮询

**前端会话**
- 登录态保存在 `sessionStorage`，页面关闭后自动清除
- 路由守卫根据角色自动跳转（`admin` → `/admin`，`user` → `/user`），越权访问会被重定向
- 通过监听 `storage` 事件实现跨标签页会话同步（`client.js` 的 `initializeAuthSessionSync`）

---

## 测试

后端测试位于 `backend/tests/`，使用 **pytest**。

```bash
cd backend
pytest tests/
```

测试覆盖范围包括：评估流程端到端验证、SOP 删除级联逻辑等。
