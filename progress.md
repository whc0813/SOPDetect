# Prompt 优化进度记录

## 2026-05-07
- 完整阅读 `backend/prompt.py`、`backend/evaluation.py`、`backend/scoring.py`
- 识别 10 个优化点，筛选 9 个纳入方案
- 创建 `task_plan.md` 和 `findings.md`

### Phase 1: 枚举语义排序 + Schema description ✓
- `models.py`: ISSUE_TYPE_VALUES / COMPLETION_LEVEL_VALUES 从 set 改为语义分组 list
- `prompt.py`: 移除所有 `sorted()` 调用，直接使用有序 list
- 6 个 schema 构建函数全部补充 `description` 字段
- 后端测试: 39 passed

### Phase 2: System Prompt 重构 ✓
- 新增 4 个共享函数：`_shared_issue_type_definitions`、`_shared_completion_level_definitions`、`_shared_evidence_writing_guide`、`_shared_core_principles`
- 5 个 system prompt 函数全部重写，引用共享模块
- 负向指令全部改为正向约束
- 更新测试断言匹配新 prompt 内容
- 后端测试: 39 passed

### Phase 3: Batch 模式参考关键帧 ✓
- `build_batch_step_evaluation_blocks` 每步追加最多 3 张 referenceFrames
- 附带引导文本说明帧用途
- 后端测试: 39 passed

### Phase 4: Stage 1→2 结构化传递 ✓
- 阶段1结果从字符串拼接改为 `json.dumps()` JSON block 嵌入
- 精简 occurrences 数据，移除冗余文本格式
- 更新测试断言匹配新格式
- 后端测试: 39 passed

### Phase 5: Stage 3 输入精简 ✓
- `build_global_validation_content` 移除 evidence 详细文本
- 仅保留顺序校验必需字段
- 后端测试: 39 passed

### Phase 6: reasoning 推理字段 ✓
- batch schema 增加 `reasoning` 字段（CoT 推理步骤引导）
- batch system prompt 增加 6 步推理引导
- evidence 重新定位为"判断依据摘要"
- 后端测试: 39 passed

### Phase 7: 耗时约束权责统一 ✓
- 共享 issueType 定义中标注"过快完成"/"超时完成"由后端规则自动判定
- 核心原则增加"模型仅检测起止时间，耗时违规由后端判定"
- scoring.py 的 `apply_duration_constraint` 保持为唯一权威来源
- 后端测试: 39 passed，前端构建成功

### 2026-05-07 修复：重复操作误判双显卡安装
- **问题**: 操作者安装两块显卡（符合双显卡要求）被判定为"重复操作"
- **根因分析（两层）**:
  1. `apply_repeated_execution_constraint` 以 `repeatedExecution=true` 作为触发条件，但 `repeatedExecution` 是事实观察（出现多次），`issueType` 才是判断（是否"不必要"地重复）。模型正确输出 `repeatedExecution=true` + `issueType="正常"` 时，后端仍会覆盖为 `issueType="重复操作"`
  2. Stage 2 正确判为"正常"并给出推理，但 Stage 3 在信息不完整（看不到 Stage 2 的 reasoning）的情况下，仅凭"两个不连续片段+空档期"就通过 stepOverrides 改判为"重复操作"
- **修复 1**: `scoring.py` 移除 `repeatedExecution` 作为触发条件，仅当 `issueType="重复操作"` 时才强制覆盖
- **修复 2**: Stage 3 输入追加 Stage 2 的 reasoning 字段，system prompt 增加"override 前应参考 Stage 2 推理，无明显错误不应推翻"的约束
- 涉及文件: `backend/scoring.py:209`, `backend/prompt.py:600-608,640-648`, `backend/tests/test_evaluation_pipeline.py:750-767`
- 后端测试: 31 passed（pipeline 测试），39 passed（全部）
