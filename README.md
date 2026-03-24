# 基于视觉分析的标准操作流程管理系统

本项目是一个面向毕业设计场景的 SOP（Standard Operating Procedure，标准操作流程）管理与视频评估系统，采用前后端分离架构。管理员负责创建 SOP、维护步骤说明并上传步骤示范视频；普通用户选择 SOP 后上传完整操作视频，系统调用多模态大模型完成流程符合性评估，并保存执行记录与人工复核结果。

## 1. 项目概览

### 核心能力

- 账号登录、注册与基于角色的路由控制
- 管理员创建 SOP，按步骤录入文字说明，可选上传每一步示范视频
- 后端自动从示范视频中抽取关键帧、生成步骤摘要、关键时刻和 ROI 提示
- 普通用户选择 SOP 后上传一段完整执行视频
- 后端组装 SOP 上下文与用户视频，调用大模型输出结构化评估结果
- 保存执行历史、步骤级评分、问题列表、原始上传视频与人工复核结果
- 管理员可查看统计数据、复核历史记录、启用或禁用普通用户

### 角色划分

- 管理员：维护 SOP、查看统计、复核执行记录、管理用户状态
- 普通用户：注册登录、查看任务、上传执行视频、查看历史与复核结果

## 2. 技术栈

### 前端

- Vue 3
- Vue Router 4
- Element Plus
- Vue CLI 5

前端目录：`bysj`

### 后端

- FastAPI
- Pydantic v2
- httpx
- OpenCV
- NumPy
- PyMySQL

后端目录：`backend`

### 数据与存储

- MySQL：存储用户、SOP、步骤、媒体、执行记录、复核和统计数据
- 本地文件系统：存储管理员示范视频与用户执行视频
- 媒体目录：
  - `backend/data/media/Admin`
  - `backend/data/media/User`

## 3. 实际业务流程

### 管理员端

1. 登录后台后进入 `SOP 管理 / 用户管理 / 数据统计` 三个模块。
2. 新建 SOP 时填写 SOP 名称、适用场景、步骤数量，为每一步填写说明，并可选上传示范视频。
3. 保存 SOP 时，后端会对每一步做如下处理：
   - 有示范视频：保存媒体文件，读取视频信息，抽取分析帧与参考关键帧；
   - 已配置 AI Key：调用模型生成步骤摘要、关键时刻、ROI 提示；
   - 未配置 AI Key：退化为基于均匀采样的关键帧方案。
4. 管理员可在 SOP 详情页查看预处理结果，并支持：
   - 手动输入时间点，重新生成关键帧；
   - 补传或替换某一步示范视频。
5. 在统计页可查看总 SOP 数、执行次数、待复核数、通过率，以及按 SOP 聚合的统计结果。
6. 对用户执行记录可进行人工复核，结论支持 `approved / rejected / needs_attention`。

### 用户端

1. 用户注册后默认角色为 `user`。
2. 登录后可浏览待执行 SOP 列表。
3. 进入某个 SOP 后，前端会展示每个步骤的文字说明，以及后端生成的参考摘要。
4. 用户上传一段完整操作视频，后端对该视频进行评估。
5. 评估结果包括：
   - 是否通过
   - 综合得分
   - 总体反馈
   - 问题列表
   - 每一步的通过状态、得分、置信度和证据说明
6. 用户确认后可将本次结果写入历史记录，并在“历史记录”中查看详情及人工复核结论。

## 4. 评估链路

后端的核心逻辑集中在 `backend/main.py`，整体链路如下：

1. 接收管理员配置的 SOP 步骤信息与示范视频。
2. 对示范视频做元数据读取、抽帧和关键时刻整理。
3. 将步骤描述、关键帧、关键时刻、ROI 提示组织成 SOP 上下文。
4. 接收用户上传的完整执行视频。
5. 将 SOP 上下文和用户视频一起发送到兼容 OpenAI Chat Completions 风格的多模态接口。
6. 通过 JSON Schema 约束模型输出结构化结果。
7. 保存执行记录、步骤级结果、问题列表、上传视频和原始模型返回摘要。

当前默认模型配置来自数据库中的 `ai_configs` 表，默认值为：

- `baseURL`: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `model`: `qwen3.5-plus`
- `fps`: `2`
- `temperature`: `0.1`
- `timeoutMs`: `120000`

## 5. 目录结构

```text
.
├─ backend
│  ├─ main.py                # FastAPI 入口，鉴权、SOP、评估、历史、媒体接口
│  ├─ storage.py             # MySQL 存储层、建表、序列化、统计
│  ├─ requirements.txt       # Python 依赖
│  ├─ mysql_schema.sql       # 独立 SQL 建表脚本
│  ├─ mysql_design.md        # 数据库设计说明
│  ├─ .env                   # MySQL 连接配置
│  └─ data
│     └─ media               # 本地媒体文件存储目录
├─ bysj
│  ├─ package.json           # 前端依赖与脚本
│  ├─ vue.config.js
│  ├─ public
│  └─ src
│     ├─ api/client.js       # 前端 API 封装与会话管理
│     ├─ router/index.js     # 路由与权限守卫
│     └─ views
│        ├─ Login.vue        # 登录/注册页
│        ├─ Admin.vue        # 管理员端
│        └─ User.vue         # 用户端
├─ PRD.md                    # 产品需求文档
└─ readme.txt                # 旧版简要说明
```

## 6. 数据库设计

`storage.py` 会在首次连接时自动创建数据库和表结构，核心表包括：

- `users`：用户信息
- `user_login_sessions`：登录会话，限制同一账号同时仅保留一个活跃会话
- `ai_configs`：模型配置
- `sops`：SOP 主表
- `sop_steps`：SOP 步骤
- `media_files`：媒体文件索引
- `sop_step_keyframes`：步骤关键帧
- `sop_step_substeps`：步骤关键时刻
- `sop_executions`：执行记录主表
- `execution_issues`：问题列表
- `execution_step_results`：步骤级评估结果
- `manual_reviews`：人工复核记录

## 7. 默认账号与鉴权机制

系统首次初始化时会自动写入两个种子账号：

- 管理员：`admin / admin`
- 普通用户：`user / user`

鉴权方式为后端自定义 Bearer Token，Token 中包含：

- 用户 ID
- 用户名
- 角色
- 会话 ID
- 过期时间

同时会结合 `user_login_sessions` 做会话有效性校验，因此账号重复登录会被拦截。

## 8. 本地运行方式

### 运行前准备

- Node.js 16+ 或更高版本
- Python 3.10+ 或兼容版本
- 本地 MySQL 8.x

### 1. 配置数据库

编辑 `backend/.env`：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=sop_eval_system
```

说明：

- 后端启动后会自动创建数据库与表
- 所有表字符集均为 `utf8mb4`

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

默认监听地址：

- `http://localhost:8000`

### 3. 启动前端

```bash
cd bysj
npm install
npm run serve
```

默认前端开发地址通常为：

- `http://localhost:8080`

如果需要修改前端请求地址，可设置环境变量 `VUE_APP_API_BASE_URL`，否则默认请求 `http://localhost:8000`。

## 9. 主要接口

### 认证

- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/logout`

### 用户与配置

- `GET /api/users`
- `PUT /api/users/{user_id}/status`
- `GET /api/config`
- `PUT /api/config`

### SOP

- `GET /api/sops`
- `GET /api/sops/{sop_id}`
- `POST /api/sops`
- `DELETE /api/sops/{sop_id}`
- `PUT /api/sops/{sop_id}/steps/{step_no}/demo-video`
- `PUT /api/sops/{sop_id}/steps/{step_no}/manual-segmentation`

### 评估与历史

- `POST /api/sops/{sop_id}/evaluate`
- `GET /api/history`
- `GET /api/history/{record_id}`
- `POST /api/history`
- `PUT /api/history/{record_id}/review`
- `GET /api/stats`

### 媒体与辅助能力

- `GET /api/media/{media_id}`
- `POST /api/prepare-step-video`
- `POST /api/evaluate`
- `GET /api/health`

## 10. 代码层面的几个特点

- 前端登录态保存在 `sessionStorage` 中，键名为 `authSession`
- 路由守卫会根据角色自动跳转到 `/admin` 或 `/user`
- 用户端当前没有实际开放 API 配置修改能力，按钮会直接提示“普通用户无权修改系统配置”
- 管理员创建 SOP 时，步骤示范视频不是强制项；没有视频时，系统会退化为“仅基于文字 SOP 的评估”
- 媒体访问受权限控制：管理员可访问全部，普通用户仅能访问公开示范视频或与自己相关的执行视频

## 11. 当前适合作为 README 关注的事实

从当前代码来看，这个项目已经不是早期“纯前端 + 本地存储”的版本，而是已经切换为：

- Vue 3 + FastAPI 的前后端分离实现
- MySQL 持久化
- 本地文件系统媒体存储
- 多模态模型驱动的视频 SOP 评估
- 管理员人工复核闭环

如果后续继续完善，优先建议补充：

- 后端接口测试与前端页面说明截图
- 生产环境部署文档
- 更安全的密码哈希与密钥管理
- 模型调用失败时的重试与降级策略说明

