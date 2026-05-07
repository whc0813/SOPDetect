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
