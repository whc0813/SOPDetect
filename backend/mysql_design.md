# MySQL 库表与视频目录规划

## 1. 数据库名

建议数据库名：`sop_eval_system`

这个名字和当前项目的业务最贴近，后续做毕业设计文档时也比较容易解释。

## 2. 视频目录规划

建议把本地视频文件统一放到：

`D:\毕业设计\backend\data\media`

在这个目录下按角色拆分：

- `D:\毕业设计\backend\data\media\Admin`
- `D:\毕业设计\backend\data\media\User`

进一步建议按业务再分一层，后续排查文件会更清晰：

- `D:\毕业设计\backend\data\media\Admin\sop_step_demo`
- `D:\毕业设计\backend\data\media\User\execution_upload`

建议路径生成规则：

- 管理员步骤示范视频：`Admin/sop_step_demo/{sopId}/step_{stepNo}/{uuid}.mp4`
- 用户执行上传视频：`User/execution_upload/{userId}/{executionId}/{uuid}.mp4`

这样做的好处：

- `Admin` 和 `User` 的视频天然隔离
- SOP 示例视频和用户执行视频不会混在一起
- 后面如果迁移到 OSS、MinIO、七牛云，数据库里的 `storage_path` 字段仍然能继续复用

## 3. 表结构拆分思路

### `users`

存账号信息，统一承载 `admin / user` 两种角色，不建议再单独拆 `admin_users`、`normal_users` 两张表。

核心字段：

- `username`
- `password_hash`
- `display_name`
- `role`
- `status`
- `last_login_at`

### `ai_configs`

存当前前端页面里那组模型配置。

核心字段：

- `provider`
- `base_url`
- `model_name`
- `api_key_encrypted`
- `fps`
- `temperature`
- `timeout_ms`

如果你后面只保留一套配置，这张表也依然值得保留，因为比直接塞到代码里更规范。

### `sops`

存一条 SOP 主记录。

核心字段：

- `sop_code`
- `name`
- `scene`
- `description`
- `step_count`
- `demo_video_count`
- `status`
- `created_by`

### `sop_steps`

存 SOP 的每个步骤，是 `sops` 的子表。

核心字段：

- `sop_id`
- `step_no`
- `description`
- `reference_mode`
- `reference_summary`
- `roi_hint`
- `ai_used`
- `reference_duration_sec`
- `reference_fps`
- `reference_frame_count`
- `raw_ai_result`

### `media_files`

这是最关键的一张文件表，用来统一记录所有视频文件，不要把路径直接散落在各业务表里。

核心字段：

- `owner_role`：标记属于 `admin` 还是 `user`
- `business_type`：标记是 `sop_step_demo` 还是 `execution_upload`
- `storage_path`：真实存储路径
- `original_name`
- `stored_name`
- `mime_type`
- `file_size`
- `related_sop_id`
- `related_step_id`
- `related_execution_id`

这张表正好和你说的 “视频新建 `User/Admin` 文件夹分别存储” 对应起来。

### `sop_step_keyframes`

存步骤参考帧和分析帧。

说明：

- 当前代码里 `referenceFrames`、`analysisFrames` 是数组
- 放到 MySQL 时，不建议整个数组直接塞成一个大字段
- 更适合一帧一行，方便扩展和调试

### `sop_step_substeps`

存步骤里的关键时刻，比如：

- 第一次按按钮
- 第二次按按钮
- 放置器材

就是现在代码里的 `substeps`。

### `sop_executions`

对应当前 `history` 主表，表示一次用户执行记录。

核心字段：

- `execution_code`
- `sop_id`
- `user_id`
- `uploaded_video_media_id`
- `finish_time`
- `score`
- `ai_status`
- `feedback`
- `sequence_assessment`
- `prerequisite_violated`
- `payload_preview`
- `raw_model_result`

### `execution_issues`

对应当前评估结果里的 `issues` 数组，单独拆表更规整。

### `execution_step_results`

对应当前评估结果里的 `stepResults`。

核心字段：

- `execution_id`
- `sop_step_id`
- `step_no`
- `description`
- `passed`
- `score`
- `confidence`
- `issue_type`
- `completion_level`
- `order_issue`
- `prerequisite_violated`
- `evidence`

### `manual_reviews`

对应管理员复核。

核心字段：

- `execution_id`
- `review_status`
- `review_note`
- `reviewer_id`
- `review_time`

## 4. 表关系总览

- `users 1 - n sops`
- `sops 1 - n sop_steps`
- `sop_steps 1 - n sop_step_keyframes`
- `sop_steps 1 - n sop_step_substeps`
- `sops 1 - n sop_executions`
- `users 1 - n sop_executions`
- `sop_executions 1 - n execution_issues`
- `sop_executions 1 - n execution_step_results`
- `sop_executions 1 - 1 manual_reviews`
- `media_files` 通过外键关联 `sops / sop_steps / sop_executions`

## 5. 为什么不建议只建三四张大表

如果把所有内容都塞到一张 `sop` 表和一张 `history` 表里，短期能跑，但后面会很难维护：

- 步骤数组不好查
- 关键帧数组不好查
- 手工复核不好统计
- 视频路径会越来越乱
- 毕设答辩时也不容易说明“规范化设计”

所以这次建议按业务拆成 10 张左右，属于比较稳妥、也比较像正式项目的设计。

## 6. 最推荐的最小落地方案

如果你想先快速从 JSON 切到 MySQL，但又不想一次改太多，我建议第一阶段最少先落这 6 张表：

- `users`
- `sops`
- `sop_steps`
- `media_files`
- `sop_executions`
- `execution_step_results`

然后第二阶段再补：

- `ai_configs`
- `execution_issues`
- `manual_reviews`
- `sop_step_keyframes`
- `sop_step_substeps`

## 7. 和你当前项目的对应关系

当前 JSON 结构到 MySQL 的映射可以理解成：

- `config` -> `ai_configs`
- `sops[]` -> `sops`
- `sops[].steps[]` -> `sop_steps`
- `steps[].demoVideo` / `detail.uploadedVideo` -> `media_files`
- `history[]` -> `sop_executions`
- `history.detail.issues[]` -> `execution_issues`
- `history.detail.stepResults[]` -> `execution_step_results`
- `manualReview` -> `manual_reviews`

## 8. 下一步建议

如果你准备正式改后端，我建议下一步按这个顺序推进：

1. 先把 `storage.py` 从 `db.json` 改成 MySQL CRUD
2. 把 `attach_media()` 改成按 `Admin/User` 分目录保存
3. 登录接口从写死 `admin/user` 改成查 `users` 表
4. 再逐步把 `history / sop / media` 接口切换到数据库

上面的完整建表 SQL 已经放在同目录的 `mysql_schema.sql` 里，可以直接作为第一版数据库脚本使用。
