# SOP 步骤耗时约束调研记录

## Current State
- 当前问题类型在 `backend/models.py` 的 `ISSUE_TYPE_VALUES` 中集中定义。
- 默认罚分在 `backend/scoring.py` 的 `DEFAULT_ISSUE_TYPE_PENALTIES` 中定义。
- SOP 步骤已有 `stepType`、`stepWeight`、`conditionText`、`prerequisiteStepNos`，但没有结构化耗时约束字段。
- 数据库启动迁移位于 `backend/storage.py` 的 `column_statements`。
- 前端管理员创建 SOP 表单位于 `bysj/src/views/Admin.vue`，罚分配置由 `PENALTY_ISSUE_TYPES` 和 `DEFAULT_PENALTY_VALUES` 控制。

## Compatibility
- 旧代码曾移除 `timingStatus` 和旧时间窗口字段，本次不恢复这些字段。
