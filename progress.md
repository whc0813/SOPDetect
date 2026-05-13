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

---

## Session: 2026-05-13 创建 SOP 方案一

### Phase 1: 现状确认与测试设计
- **Status:** complete
- **Started:** 2026-05-13
- Actions taken:
  - 加载 `planning-with-files` 技能。
  - 检查已有 `task_plan.md`、`findings.md`、`progress.md`，确认存在旧任务记录。
  - 重新执行 `session-catchup.py`，首次路径调用失败后改用显式脚本路径成功。
  - 读取 `create_sop`、`prepare_reference_bundle`、`build_ai_reference_plan`、`segment_workflow_video`、`build_reference_bundle` 相关代码。
- Files created/modified:
  - `task_plan.md`（追加本次任务计划）
  - `findings.md`（追加本次调研发现）
  - `progress.md`（追加本次进度）

### Phase 2: 实现方案一
- **Status:** complete
- Actions taken:
  - 在 `backend/tests/test_evaluation_pipeline.py` 增加回归测试，固定“候选时间窗存在时仍应使用全视频采样”的行为。
  - 在 `backend/evaluation.py` 新增候选时间窗规范化和分析帧合并逻辑。
  - `prepare_reference_bundle` 改为先抽全视频基础样本，再把候选窗样本作为补充。
  - `build_ai_reference_plan` 的 prompt 改为候选范围仅供参考，并要求模型重新定位 `detected/startSec/endSec/confidence`。
  - 在 `backend/models.py` 扩展 `AIReferencePlan` 字段以承接重新定位结果。
  - 在 `backend/main.py` 创建 SOP 文案中加入全部步骤上下文，并把候选时间窗降级为提示。
- Files created/modified:
  - `backend/tests/test_evaluation_pipeline.py`
  - `backend/evaluation.py`
  - `backend/models.py`
  - `backend/main.py`

### Phase 3: 验证
- **Status:** complete
- Actions taken:
  - 先运行新增测试，确认失败：当前实现只采候选窗，`sample_calls == [(5.0, 6.0)]`。
  - 修改后运行新增测试，结果通过。
  - 运行相关测试：`backend/tests/test_evaluation_pipeline.py backend/tests/test_module_exports.py`，结果 `34 passed`。
  - 运行全部后端测试：`backend/tests`，结果 `40 passed`。
- Files created/modified:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-05-13 | `session-catchup.py` 首次调用时 Python 报 `can't find '__main__' module in 'D:\\'` | 1 | 使用 `C:/Users/whc/.codex/skills/planning-with-files/scripts/session-catchup.py` 显式路径重跑 |

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| 新增回归测试 RED | `python -m pytest backend/tests/test_evaluation_pipeline.py -q -k prepare_reference_bundle_uses_full_video_samples` | 失败，证明当前只采候选窗 | 失败，`sample_calls == [(5.0, 6.0)]` | 通过预期 |
| 新增回归测试 GREEN | 同上 | 通过 | `1 passed, 31 deselected` | 通过 |
| 相关测试 | `python -m pytest backend/tests/test_evaluation_pipeline.py backend/tests/test_module_exports.py -q` | 全部通过 | `34 passed` | 通过 |
| 全部后端测试 | `python -m pytest backend/tests -q` | 全部通过 | `40 passed` | 通过 |
