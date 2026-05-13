# Prompt 优化调研记录

## Current State

### 评估链路
- **Phase 2（用户评测）**: 3 阶段流水线
  - Stage 1: 时序分割（`run_temporal_segmentation`）— 识别每步在用户视频中的起止时间
  - Stage 2: 批量步骤评估（`run_per_step_evaluation_batch`）— 一次调用评估所有步骤
  - Stage 3: 全局校验（`run_global_validation`）— 文本型顺序/前置依赖一致性检查
- **Phase 3（示范视频分析）**: 单次调用分割工作流视频

### 关键文件
| 文件 | 涉及内容 |
|------|----------|
| `backend/prompt.py` | 所有 system prompt、user prompt 构建函数、JSON Schema |
| `backend/evaluation.py` | 评估编排、阶段间数据传递、后处理调用 |
| `backend/scoring.py` | 规则型后处理（前置依赖、耗时、重复执行、默认序列） |
| `backend/models.py` | `ISSUE_TYPE_VALUES`、`COMPLETION_LEVEL_VALUES` 枚举定义 |

### 枚举当前定义（models.py）
```python
ISSUE_TYPE_VALUES = {
    "正常", "缺失", "顺序颠倒", "过早执行", "延后执行",
    "重复操作", "动作错误", "部分完成", "证据不足",
    "前置条件缺失", "过快完成", "超时完成",
}
COMPLETION_LEVEL_VALUES = {"完整", "部分完成", "未完成", "无法判断"}
```

## 优化点详细分析

### 1. Batch 模式参考关键帧缺失
- **位置**: `prompt.py:733-807` (`build_batch_step_evaluation_blocks`)
- **现象**: 函数为每步构建文字描述块，但从不调用 `step.referenceFrames`
- **对比**:
  - `build_content_blocks` (L183-184): `for frame in step.referenceFrames[:6]` ✓
  - `build_per_step_evaluation_blocks` (L495-496): `for frame in step.referenceFrames[:6]` ✓
  - `build_batch_step_evaluation_blocks`: 完全没有 ✗
- **影响**: 当 SOP 有示范视频关键帧时，模型在 Stage 2 看不到"正确动作长什么样"，只能凭文字描述判断
- **修复方向**: 每步选取 1-2 张最关键的参考帧（优先 substep 时间点），控制 token 预算

### 2. System Prompt 语义重叠
- **四个 system prompt 函数**:
  - `build_evaluation_system_prompt` (L77-105): single-pass fallback
  - `build_temporal_segmentation_system_prompt` (L530-542): Stage 1
  - `build_per_step_evaluation_system_prompt` (L344-364): per-step Stage 2
  - `build_batch_step_evaluation_system_prompt` (L714-730): batch Stage 2
  - `build_global_validation_system_prompt` (L587-604): Stage 3
- **重叠内容**:
  - issueType 枚举说明（出现在 4 个 prompt 中）
  - completionLevel 枚举说明（出现在 3 个 prompt 中）
  - 时间窗使用方式（出现在 2 个 prompt 中）
  - 证据写作规范（出现在 3 个 prompt 中）
- **表述漂移示例**:
  - L97: "只有步骤明确给出时间限制时才判断耗时问题"（single-pass）
  - L359: "如果步骤配置了最短耗时...使用'过快完成'"（per-step）
  - L727: "步骤配置最短耗时时...应标记'过快完成'"（batch）
  - 三处说的是同一规则但措辞不同

### 3. 负向指令统计
全文件共 16 处"不要"句式：
- L98-99: "不得因耗时长短判为异常"
- L118-122: "不要把'看到了动作'直接等同于'该步骤正确完成'"
- L353-356: "不要把短暂出现的目标动作直接判成'缺失'"
- L357: "不能按绝对秒数机械对齐"
- L537: "重复出现不要合并成一个长时间窗"
- L540: "不要臆造"
- L600-601: "不要写'顺序问题'"
- 等等

### 5. Schema description 缺失
- 所有 `build_*_schema` 函数的 property 定义只有 `type` 约束
- 示例现状（L216-217）:
  ```python
  "orderIssue": {"type": "boolean"},
  "prerequisiteViolated": {"type": "boolean"},
  ```
- 应补充为:
  ```python
  "orderIssue": {
    "type": "boolean",
    "description": "该步骤实际执行时间是否与 SOP 期望顺序不一致"
  },
  ```
- JSON Schema 的 `description` 字段被 GPT-4o、Qwen 等模型原生支持，在生成到对应字段时正好在注意力窗口内

### 6. Stage 1→2 信息格式
- 当前（L759-795）:
  ```python
  f"阶段1候选时间窗：{segment_text}\n"
  f"阶段1疑似出现次数：{segment_info.get('occurrenceCount')}\n"
  f"阶段1疑似出现片段：{occurrence_text}\n"
  ```
- 问题: 结构化数据→字符串→模型再解析，信息密度低且易出错
- 改进方向: 直接嵌入 JSON block

### 7. Stage 3 输入冗余
- `build_global_validation_content` (L607-654) 每个步骤传递约 10 个字段
- 对"全局顺序校验"关键的只有: 起止时间、前置依赖、issueType
- evidence 文本（可能 50-100 字/步）是噪音
- 粗略估计: 5 步 SOP，每步 80 字 evidence = 400 tokens 冗余

### 8. reasoning 字段缺失
- 当前所有 schema 直接输出结论，只有 evidence 作为摘要
- evidence 更像"判决书"而非"推理过程"
- Chain-of-Thought 效应: 模型先写推理后写结论，准确性显著提升
- 实现方式: 在 step item schema 中增加 `reasoning` 字段，system prompt 引导先推理后判断

### 9. 耗时约束三层处理
- **层1**: System prompt 告诉模型判断（L98-99, L359, L727）
- **层2**: `format_duration_constraint` 在每步描述中注入限制文本
- **层3**: `scoring.py:177-201` `apply_duration_constraint` 后端规则覆盖
- 冲突场景: 模型判"正常"，后端改判"过快完成"，evidence 中的理由仍是"正常完成"的口吻
- 建议: 模型只检测起止时间，耗时判定完全由后端规则负责

### 10. 枚举排序
- 当前: `sorted(ISSUE_TYPE_VALUES)` → 字母序
- 建议: 按语义类别分组，类别内按自然递进排列
  ```
  正常 →                                        # 无问题
  缺失 → 部分完成 → 动作错误 →                   # 步骤执行质量
  顺序颠倒 → 过早执行 → 延后执行 →                # 执行顺序
  重复操作 →                                     # 执行次数
  前置条件缺失 →                                 # 前置依赖
  过快完成 → 超时完成 →                          # 耗时约束
  证据不足                                       # 不确定
  ```
- 理由: "严重程度"在跨场景 SOP 中不可比（安全型 vs 效率型），按类别分组让模型在相近概念间做精细区分
- 同理 `COMPLETION_LEVEL_VALUES`: `完整 → 部分完成 → 未完成 → 无法判断`

---

# Findings: 创建 SOP 示范视频预处理方案一

## Requirements
- 用户选择“方案一”：保留现有两次调用结构，但修复第一次切段不准导致第二次分析被带偏的问题。
- 第二次模型分析不应把第一次 `startSec/endSec` 当成可信范围，只能当作候选提示。
- 文件编辑必须遵守项目约束：UTF-8 无 BOM，不整文件重写，中文直接写入。

## Research Findings
- 创建 SOP 入口是 `backend/main.py::create_sop`。当上传完整示范视频且配置 API Key 时，会先调用 `segment_workflow_video` 得到 `workflow_segments`。
- 每个步骤随后调用 `store_demo_video_and_prepare_bundle`，并把 `workflow_segments[stepNo].startSec/endSec` 传给 `prepare_reference_bundle`。
- `prepare_reference_bundle` 当前用 `extract_analysis_samples(temp_path, meta["durationSec"], start_sec=start_sec, end_sec=end_sec)` 抽分析帧，因此错误候选窗会直接影响二次模型调用的静态帧输入。
- `build_ai_reference_plan` 虽然会把完整示范视频发给模型，但 user 文本当前强调“重点关注该区间”，且采样帧来自候选窗，确实会强化错误定位。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 第二次调用继续发送完整示范视频 | 让模型有机会从全局重新定位当前步骤 |
| 分析帧改为全视频基础采样，候选窗作为附加采样 | 避免候选窗错时所有静态证据都错，同时保留候选窗正确时的局部细节 |
| 测试先覆盖 `prepare_reference_bundle` 的采样行为 | 这是错误时间窗污染二次分析的直接源头 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 现有计划文件属于旧任务 | 不覆盖旧内容，追加本次任务段 |

## Verification Findings
- 新增回归测试先失败，失败原因是 `prepare_reference_bundle` 只调用候选窗采样：`sample_calls == [(5.0, 6.0)]`。
- 修改后新增测试通过，证明候选窗存在时也会先做全视频采样。
- 全部后端测试通过：`python -m pytest backend/tests -q` 结果为 `40 passed`，仅有 FastAPI `on_event` 既有弃用警告。
