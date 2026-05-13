# Prompt 设计优化方案

## Goal
对评估链路的 Prompt 设计进行系统性优化，提升模型判断准确率、减少阶段间信息损失、消除规则冗余冲突。覆盖 9 个优化点。

## Phases

### Phase 1: 枚举值语义排序与 Schema description 字段
- [ ] 将 `ISSUE_TYPE_VALUES` 和 `COMPLETION_LEVEL_VALUES` 从字母序改为语义序
- [ ] 为所有 JSON Schema 的 property 补充 `description` 字段
- 涉及文件: `backend/prompt.py`（所有 `build_*_schema` 函数）、`backend/models.py`

### Phase 2: System Prompt 重构——统一评估标准，消除表述漂移
- [ ] 抽取共享的"评估标准定义"模块（issueType 语义、completionLevel 语义、证据写作规范）
- [ ] 将所有负向指令（"不要 X"）改写为正向约束（"应当 Y"）
- [ ] 四个 system prompt 各自只保留角色特有指令，公共部分引用共享定义
- 涉及文件: `backend/prompt.py`

### Phase 3: Batch 模式补充参考关键帧
- [ ] `build_batch_step_evaluation_blocks` 中为每个有 referenceFrames 的步骤附带 1-2 张关键帧
- [ ] 控制 token 预算：仅附带 AI 标注的 substeps 中最关键的时刻对应的帧
- 涉及文件: `backend/prompt.py`

### Phase 4: Stage 1→2 结构化信息传递
- [ ] Stage 1 产出的 segments/occurrences 以 JSON block 形式嵌入 Stage 2 user message
- [ ] 替代当前的字符串拼接格式
- 涉及文件: `backend/prompt.py`（`build_batch_step_evaluation_blocks`）

### Phase 5: Stage 3 输入精简
- [ ] 从 `build_global_validation_content` 中移除详细的 evidence 文本
- [ ] 只保留顺序校验必需的字段：起止时间、issueType、前置依赖、耗时限制
- 涉及文件: `backend/prompt.py`

### Phase 6: 增加 reasoning 推理字段
- [ ] 在 Stage 2 batch schema 中为每个 step 增加 `reasoning` 字段
- [ ] 在 system prompt 中添加推理步骤引导
- [ ] evidence 精简为最终摘要
- 涉及文件: `backend/prompt.py`

### Phase 7: 耗时约束权责统一
- [ ] 决定权责归属（建议：模型只负责检测起止时间，后端规则唯一判定耗时类 issue）
- [ ] 从 system prompt 中移除"过快完成"/"超时完成"的判断指令
- [ ] `scoring.py` 的 `apply_duration_constraint` 成为耗时类问题的唯一来源
- 涉及文件: `backend/prompt.py`、`backend/scoring.py`

## Decisions
- 枚举值按语义类别分组排列（执行质量→执行顺序→执行次数→前置依赖→耗时约束→不确定），类别内自然递进
- Schema `description` 使用中文，与 system prompt 保持语言一致
- Batch 模式每步最多附带 3 张参考帧，优先选择 AI 标注的 substep 关键时间点对应的帧
- 耗时类问题（过快完成/超时完成）完全由后端规则判定，模型不再负责

## Errors Encountered
（暂无）

---

# Task Plan: 创建 SOP 示范视频预处理方案一

## Goal
将创建 SOP 时的第二次示范视频分析从“依赖第一次切段时间窗”改为“完整视频重新定位，候选时间窗仅作提示”，避免错误切段污染关键帧、关键时刻和 ROI。

## Current Phase
Phase 3 complete

## Phases

### Phase 1: 现状确认与测试设计
- [x] 确认 `create_sop -> segment_workflow_video -> store_demo_video_and_prepare_bundle -> prepare_reference_bundle -> build_ai_reference_plan` 调用链
- [x] 确认根因：`prepare_reference_bundle` 当前按 `start_sec/end_sec` 抽分析帧，错误候选窗会带偏二次分析
- [x] 写入回归测试，证明二次分析需要完整视频采样，不应只拿候选窗采样
- **Status:** complete

### Phase 2: 实现方案一
- [x] 保留第一次整体切段调用
- [x] 第二次单步骤分析保留完整示范视频输入
- [x] 第二次单步骤分析把候选时间窗降级为提示
- [x] 分析帧改为全视频采样 + 候选窗补充采样，避免候选窗错误时全部样本失真
- **Status:** complete

### Phase 3: 验证与交付
- [x] 运行新增回归测试，确认先失败后通过
- [x] 运行相关后端测试
- [x] 总结影响范围和后续可选优化
- **Status:** complete

## Key Questions
1. `prepare_reference_bundle` 是否可以在不改变接口返回结构的前提下同时提供全视频和候选窗采样？
2. 是否需要扩展 `AIReferencePlan`，让模型在第二次调用中重新返回当前步骤的 detected/startSec/endSec/confidence？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 采用方案一，不直接合并两次模型调用 | 最小改动，风险低，保留当前失败回退能力 |
| 候选时间窗只作为提示，不作为二次分析的唯一采样范围 | 第一次切段不准时，第二次仍可从完整视频中找回正确动作 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| `session-catchup.py` 首次调用时 Python 误把工作目录当模块路径 | 1 | 改用显式脚本绝对路径重新执行，成功返回 |
