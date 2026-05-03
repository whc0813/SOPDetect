# SOP 步骤耗时约束进度记录

## 2026-05-03
- 创建实施记录文件。
- 已确认当前分支为 `codex/sop-duration-constraints`。
- 已按 TDD 写入后端失败测试；新增测试当前 4 失败、1 通过，失败点符合预期：新问题类型、耗时规则和非法范围校验尚未实现。
- 已实现后端模型、存储迁移、评分后处理、Prompt 耗时提示，以及管理员端表单/罚分配置。
- 验证通过：`python -m pytest backend/tests/test_evaluation_pipeline.py backend/tests/test_remove_risk_time.py -q`，26 passed。
- 验证通过：`npm run build`，构建成功，仅保留原有包体积警告。
- 修复管理员问题类型统计口径：`正常` 不再进入 `issueTypeStats`；新增回归测试覆盖该场景。
