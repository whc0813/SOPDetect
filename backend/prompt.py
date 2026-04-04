import json
from typing import List, Optional

from fastapi import HTTPException

try:
    from .models import (
        COMPLETION_LEVEL_VALUES,
        ISSUE_TYPE_VALUES,
        SopData,
    )
except ImportError:
    from models import (
        COMPLETION_LEVEL_VALUES,
        ISSUE_TYPE_VALUES,
        SopData,
    )


# ── JSON helpers ───────────────────────────────────────────────

def extract_json_from_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_part = next(
            (item.get("text") for item in content if item.get("type") == "text" and item.get("text")),
            "",
        )
        return text_part or ""
    return ""


def parse_json_content(content):
    raw = extract_json_from_content(content).strip()
    if not raw:
        raise HTTPException(status_code=500, detail="Model returned empty JSON content")
    try:
        return json.loads(raw)
    except Exception:
        match_start = raw.find("{")
        match_end = raw.rfind("}")
        if match_start != -1 and match_end != -1 and match_end > match_start:
            return json.loads(raw[match_start : match_end + 1])
        raise HTTPException(status_code=500, detail="Model returned invalid JSON")


def normalize_messages_for_model(model_name: str, messages: List[dict]):
    normalized_messages = list(messages or [])
    model = (model_name or "").strip().lower()
    if not normalized_messages or not model.startswith("qwen3.6"):
        return normalized_messages
    first_message = normalized_messages[0]
    if first_message.get("role") != "system" or len(normalized_messages) < 2:
        return normalized_messages
    second_message = normalized_messages[1]
    if second_message.get("role") != "user":
        return normalized_messages
    system_text = extract_json_from_content(first_message.get("content")).strip()
    if not system_text:
        return normalized_messages[1:]
    user_content = second_message.get("content")
    if isinstance(user_content, list):
        merged_user_content = [{"type": "text", "text": system_text}] + user_content
    elif isinstance(user_content, str):
        merged_user_content = f"{system_text}\n\n{user_content}".strip()
    else:
        merged_user_content = [{"type": "text", "text": system_text}]
    merged_first_user = {**second_message, "content": merged_user_content}
    return [merged_first_user, *normalized_messages[2:]]


# ── Single-pass evaluation prompts (original / fallback) ──────

def build_evaluation_system_prompt():
    return (
        "你是一个严格的 SOP 执行评估助手。"
        "你的任务不是只判断用户\"做没做\"，还要判断是否按正确顺序、正确意图、正确完整度、安全地完成了整个流程。"
        "你必须从全流程视角综合判断，不能把每个步骤彼此孤立地看待。\n"
        "评估时必须重点考虑这些真实情况：\n"
        "1. 漏做步骤，或只做了一部分关键动作。\n"
        "2. 步骤顺序颠倒，后置步骤先于前置步骤发生。\n"
        "3. 过早执行，用户在前一步未完成前就开始后一步。\n"
        "4. 延后执行，某一步应在当前阶段完成，却明显拖到更后面才出现。\n"
        "5. 重复操作或多余操作，出现不必要的重复、额外动作或潜在风险动作。\n"
        "6. 动作错误或替代动作，虽然有动作，但不符合该步骤真实意图。\n"
        "7. 证据不足，画面遮挡、模糊、采样过 sparse 或无法支持高置信判断。\n"
        "8. 前置条件未满足，如果某一步依赖前一步先完成，则顺序错误要明确扣分。\n"
        "输出要求：\n"
        "- feedback、issues、evidence 全部使用中文。\n"
        "- issues 用简短中文短语概括最重要的问题。\n"
        "- 如果动作看起来存在，但顺序位置错误，不能算完全通过。\n"
        "- passed=true 只能在整个 SOP 基本按正确顺序完成、没有明显漏做/错做/严重错序时给出。\n"
        "- 顶层字段 sequenceAssessment 只能从以下值中选择：['顺序正确', '轻微顺序偏差', '明显顺序错误', '无法判断顺序']。\n"
        "- 每个步骤的 issueType 只能从以下值中选择：['正常', '缺失', '顺序颠倒', '过早执行', '延后执行', '重复操作', '动作错误', '部分完成', '证据不足', '前置条件缺失']。\n"
        "- 每个步骤的 completionLevel 只能从以下值中选择：['完整', '部分完成', '未完成', '无法判断']。\n"
        "- orderIssue 表示该步骤是否存在顺序问题；prerequisiteViolated 表示该步骤是否存在前置条件问题。\n"
        "- evidence 必须点明你为什么这样判断，必要时明确写出\"顺序颠倒\"\"过早执行\"\"延后执行\"\"证据不足\"等。\n"
        "- 当前输入里会直接提供整段用户测试视频；除非题面明确提供了用户视频关键帧，否则不要臆造。\n"
        "- 你必须严格区分\"示范视频关键帧\"和\"用户测试视频\"。\n"
        "只返回合法 JSON，不要输出任何额外解释。"
    )


def build_evaluation_overview_text(sop: SopData):
    step_order_text = " -> ".join([f"{step.stepNo}:{step.description}" for step in sop.steps]) or "无"
    has_demo_video_reference = any(bool(step.referenceFrames) for step in sop.steps)
    reference_source_text = "含示范视频关键帧" if has_demo_video_reference else "仅文字 SOP，无示范视频关键帧"
    return (
        "请从全流程视角评估用户的 SOP 执行情况。\n"
        f"SOP 名称：{sop.name}\n"
        f"适用场景：{sop.scene or '未提供'}\n"
        f"期望步骤顺序：{step_order_text}\n"
        f"SOP 参考来源：{reference_source_text}\n"
        "系统会直接提供整段用户测试视频，不再先把用户视频切成步骤片段或关键帧。\n"
        "如果 SOP 参考来源显示为\"仅文字 SOP，无示范视频关键帧\"，那么你只能基于文字 SOP 与整段用户测试视频判断，不代表系统存在示范视频关键帧。\n"
        "因此你必须主动考虑这些实际情况：步骤颠倒、后一步抢跑、当前步骤被拖到后面、漏做前置步骤、重复操作、额外风险动作，以及证据不足无法确认完成。\n"
        "判断每一步时，请同时结合步骤说明、参考关键帧、可选的子步骤时间轴，以及整段用户测试视频中的全流程顺序关系。\n"
        "不要把\"看到了动作\"直接等同于\"该步骤正确完成\"；要重点判断动作意图、执行顺序、完成度和前后依赖关系。\n"
        "只返回 JSON。"
    )


def build_content_blocks(sop: SopData, user_video_data_url: str, user_video_fps: float):
    blocks = [{"type": "text", "text": build_evaluation_overview_text(sop)}]
    blocks.append(
        {
            "type": "text",
            "text": (
                "下面是整段用户测试视频。请结合步骤类型、权重和前置依赖，"
                "判断每一步是否适用、是否出现、起止时间大致是多少，并输出结构化结果。"
            ),
        }
    )
    blocks.append(
        {
            "type": "video_url",
            "video_url": {"url": user_video_data_url},
            "fps": max(0.1, float(user_video_fps or 2)),
        }
    )
    for step in sop.steps:
        has_reference_frames = bool(step.referenceFrames)
        substeps_text = (
            "; ".join([f"{item.title}@{item.timestampSec:.2f}s" for item in step.substeps])
            if step.substeps
            else "无"
        )
        blocks.append(
            {
                "type": "text",
                "text": (
                    f"步骤 {step.stepNo}\n"
                    f"步骤说明：{step.description}\n"
                    f"步骤类型：{step.stepType}\n"
                    f"步骤权重：{step.stepWeight}\n"
                    f"条件说明：{step.conditionText or '无'}\n"
                    f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"关注区域提示：{step.roiHint or '无'}\n"
                    f"参考子步骤时间点：{substeps_text}\n"
                    f"参考特征：{json.dumps((step.referenceFeatures.model_dump() if step.referenceFeatures else {}), ensure_ascii=False)}\n"
                    f"参考模式：{'示范视频关键帧' if has_reference_frames else '仅文字 SOP，无示范视频'}\n"
                    "请结合全流程上下文评估该步骤。"
                ),
            }
        )
        for frame in step.referenceFrames[:6]:
            blocks.append({"type": "image_url", "image_url": {"url": frame}})
    return blocks


def build_response_schema(step_count: int):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_video_eval",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "passed": {"type": "boolean"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "feedback": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "sequenceAssessment": {
                        "type": "string",
                        "enum": ["顺序正确", "轻微顺序偏差", "明显顺序错误", "无法判断顺序"],
                    },
                    "prerequisiteViolated": {"type": "boolean"},
                    "stepResults": {
                        "type": "array",
                        "minItems": step_count,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1},
                                "description": {"type": "string"},
                                "passed": {"type": "boolean"},
                                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "applicable": {"type": "boolean"},
                                "issueType": {
                                    "type": "string",
                                    "enum": sorted(ISSUE_TYPE_VALUES),
                                },
                                "completionLevel": {
                                    "type": "string",
                                    "enum": sorted(COMPLETION_LEVEL_VALUES),
                                },
                                "orderIssue": {"type": "boolean"},
                                "prerequisiteViolated": {"type": "boolean"},
                                "detectedStartSec": {"type": ["number", "null"], "minimum": 0},
                                "detectedEndSec": {"type": ["number", "null"], "minimum": 0},
                                "evidence": {"type": "string"},
                            },
                            "required": [
                                "stepNo", "description", "passed", "score", "confidence",
                                "applicable", "issueType", "completionLevel", "orderIssue",
                                "prerequisiteViolated", "detectedStartSec", "detectedEndSec",
                                "evidence",
                            ],
                        },
                    },
                },
                "required": [
                    "passed", "score", "feedback", "issues", "sequenceAssessment",
                    "prerequisiteViolated", "stepResults",
                ],
            },
        },
    }


# ── Stage 1: Temporal Segmentation prompts ────────────────────

def build_temporal_segmentation_system_prompt():
    return (
        "你是一个 SOP 视频分析助手，专门负责识别视频中各操作步骤的时间位置。"
        "请仔细观察整段视频，然后为 SOP 的每个步骤找出其在视频中的大致起止时间。\n"
        "注意事项：\n"
        "- 如果某个步骤在视频中没有出现，将 detected 设为 false，startSec 和 endSec 设为 null。\n"
        "- 时间精度以秒为单位，保留一位小数即可。\n"
        "- 步骤可能不是严格按顺序发生的，如实反映即可。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


def build_temporal_segmentation_blocks(sop: SopData, user_video_data_url: str, user_video_fps: float):
    step_list = "\n".join(
        [f"步骤 {step.stepNo}: {step.description}" for step in sop.steps]
    )
    return [
        {
            "type": "text",
            "text": (
                f"SOP 名称：{sop.name}\n"
                f"适用场景：{sop.scene or '未提供'}\n\n"
                f"该 SOP 共 {sop.stepCount} 个步骤，列表如下：\n{step_list}\n\n"
                "请分析下面的用户操作视频，识别每个步骤在视频中的大致起止时间（秒）。\n"
                "只返回 JSON，不要输出额外说明。"
            ),
        },
        {
            "type": "video_url",
            "video_url": {"url": user_video_data_url},
            "fps": max(0.1, float(user_video_fps or 2)),
        },
    ]


def build_temporal_segmentation_schema(step_count: int):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_temporal_segmentation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "videoDurationSec": {"type": "number", "minimum": 0},
                    "segments": {
                        "type": "array",
                        "minItems": step_count,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1},
                                "detected": {"type": "boolean"},
                                "startSec": {"type": ["number", "null"], "minimum": 0},
                                "endSec": {"type": ["number", "null"], "minimum": 0},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "note": {"type": "string"},
                            },
                            "required": [
                                "stepNo", "detected", "startSec", "endSec", "confidence", "note",
                            ],
                        },
                    },
                },
                "required": ["videoDurationSec", "segments"],
            },
        },
    }


# ── Stage 2: Per-step evaluation prompts ──────────────────────

def build_per_step_evaluation_system_prompt():
    return (
        "你是一个精细的 SOP 步骤评估助手。"
        "你将基于用户操作视频对单个 SOP 步骤进行深度评估。\n"
        "评估要点：\n"
        "1. 该步骤是否在指定时间区间内出现？\n"
        "2. 动作是否符合步骤说明的真实意图？\n"
        "3. 动作完成度如何？是否完整执行？\n"
        "4. 是否存在操作错误、遗漏关键动作或证据不足的情况？\n"
        "- issueType 只能从以下值中选择：['正常', '缺失', '顺序颠倒', '过早执行', '延后执行', '重复操作', '动作错误', '部分完成', '证据不足', '前置条件缺失']。\n"
        "- completionLevel 只能从以下值中选择：['完整', '部分完成', '未完成', '无法判断']。\n"
        "- evidence 必须说明判断依据，指出具体观察到的内容。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


def build_per_step_evaluation_blocks(
    step, segment_info: Optional[dict], user_video_data_url: str, user_video_fps: float
):
    has_reference_frames = bool(step.referenceFrames)
    substeps_text = (
        "; ".join([f"{item.title}@{item.timestampSec:.2f}s" for item in step.substeps])
        if step.substeps
        else "无"
    )
    detected = segment_info.get("detected", False) if segment_info else False
    start_sec = segment_info.get("startSec") if segment_info else None
    end_sec = segment_info.get("endSec") if segment_info else None

    if detected and start_sec is not None and end_sec is not None:
        time_range_text = (
            f"时序分析已识别该步骤出现在视频 {start_sec:.1f}s - {end_sec:.1f}s 区间，请重点关注此区间内的执行内容。"
        )
    else:
        time_range_text = "时序分析未能定位该步骤的具体时间范围，请全局搜索该步骤是否出现。"

    blocks = [
        {
            "type": "text",
            "text": (
                f"当前需要评估的步骤：步骤 {step.stepNo}\n"
                f"步骤说明：{step.description}\n"
                f"步骤类型：{step.stepType}\n"
                f"步骤权重：{step.stepWeight}\n"
                f"条件说明：{step.conditionText or '无'}\n"
                f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                f"参考摘要：{step.referenceSummary or '无'}\n"
                f"关注区域提示：{step.roiHint or '无'}\n"
                f"参考子步骤时间点：{substeps_text}\n"
                f"参考模式：{'示范视频关键帧' if has_reference_frames else '仅文字 SOP，无示范视频'}\n"
                f"{time_range_text}\n"
                "请仔细观察下方完整视频，评估该步骤的执行情况。"
            ),
        },
    ]
    for frame in step.referenceFrames[:6]:
        blocks.append({"type": "image_url", "image_url": {"url": frame}})
    blocks.append({"type": "text", "text": "下面是完整用户操作视频："})
    blocks.append(
        {
            "type": "video_url",
            "video_url": {"url": user_video_data_url},
            "fps": max(0.1, float(user_video_fps or 2)),
        }
    )
    return blocks


def build_per_step_evaluation_schema():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_step_eval",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stepNo": {"type": "integer", "minimum": 1},
                    "passed": {"type": "boolean"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "applicable": {"type": "boolean"},
                    "issueType": {"type": "string", "enum": sorted(ISSUE_TYPE_VALUES)},
                    "completionLevel": {"type": "string", "enum": sorted(COMPLETION_LEVEL_VALUES)},
                    "orderIssue": {"type": "boolean"},
                    "prerequisiteViolated": {"type": "boolean"},
                    "detectedStartSec": {"type": ["number", "null"], "minimum": 0},
                    "detectedEndSec": {"type": ["number", "null"], "minimum": 0},
                    "evidence": {"type": "string"},
                },
                "required": [
                    "stepNo", "passed", "score", "confidence", "applicable",
                    "issueType", "completionLevel", "orderIssue", "prerequisiteViolated",
                    "detectedStartSec", "detectedEndSec", "evidence",
                ],
            },
        },
    }


# ── Stage 3: Global validation prompts ────────────────────────

def build_global_validation_system_prompt():
    return (
        "你是一个 SOP 全局合规性验证助手。"
        "你将基于各步骤的单独评估结果和时序信息，对整个 SOP 执行进行综合判断。\n"
        "重点关注：\n"
        "1. 步骤执行顺序是否与 SOP 要求一致？\n"
        "2. 前置依赖关系是否满足？\n"
        "3. 整体是否达到通过标准（无严重错序、漏做等问题）？\n"
        "- sequenceAssessment 只能从以下值中选择：['顺序正确', '轻微顺序偏差', '明显顺序错误', '无法判断顺序']。\n"
        "- feedback 和 issues 使用中文。\n"
        "- issues 用简短短语概括最重要的问题（最多 5 个）。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


def build_global_validation_content(sop: SopData, step_results: list, segments: dict):
    step_results_lines = []
    for result in step_results:
        step_no = result.get("stepNo")
        seg = segments.get(step_no) or {}
        start = seg.get("startSec")
        end = seg.get("endSec")
        time_range = f"{start:.1f}s~{end:.1f}s" if (start is not None and end is not None) else "未定位"
        step_results_lines.append(
            f"步骤 {step_no}: {result.get('description', '')}\n"
            f"  判断={'通过' if result.get('passed') else '未通过'} | "
            f"得分={result.get('score', 0)} | 问题类型={result.get('issueType', '未知')} | "
            f"检测区间={time_range} | 顺序问题={'是' if result.get('orderIssue') else '否'}\n"
            f"  证据：{result.get('evidence', '无')}"
        )
    step_order_text = " -> ".join([f"{step.stepNo}:{step.description}" for step in sop.steps])
    return (
        f"SOP 名称：{sop.name}\n"
        f"期望步骤顺序：{step_order_text}\n\n"
        "以下是各步骤的单独评估结果：\n\n"
        + "\n\n".join(step_results_lines)
        + "\n\n请根据以上各步骤结果，给出整体综合判断。"
    )


def build_global_validation_schema():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_global_validation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "passed": {"type": "boolean"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "feedback": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "sequenceAssessment": {
                        "type": "string",
                        "enum": ["顺序正确", "轻微顺序偏差", "明显顺序错误", "无法判断顺序"],
                    },
                    "prerequisiteViolated": {"type": "boolean"},
                },
                "required": [
                    "passed", "score", "feedback", "issues",
                    "sequenceAssessment", "prerequisiteViolated",
                ],
            },
        },
    }


def build_per_step_evaluation_system_prompt():
    return (
        "你是一个精细的 SOP 步骤评估助手。\n"
        "你将基于用户操作视频，对单个 SOP 步骤进行深度评估。\n"
        "评估要点：\n"
        "1. 该步骤是否在候选时间窗内的某个局部片段出现过。\n"
        "2. 动作是否符合步骤说明的真实意图，而不是只看窗口内占比最高的动作。\n"
        "3. 候选时间窗只是搜索范围，里面可以包含过渡动作、相邻步骤残留或收手动作。\n"
        "4. 只要候选时间窗中的局部片段明确出现了目标动作，就应给出该局部片段的 detectedStartSec / detectedEndSec。\n"
        "5. 不要因为候选时间窗后半段出现了别的动作，就否定前半段已经出现过的目标动作。\n"
        "6. 如果关键帧采样仍然不足以支撑高置信判断，才使用“证据不足”，不要把短暂出现的目标动作直接判成“缺失”。\n"
        "7. 如果目标动作确实出现过，但出现在错误的步骤顺序上，必须标记为“过早执行”“延后执行”或“顺序颠倒”，绝不能判成“缺失”。\n"
        "- 管理员示范视频与用户视频总时长可能不同，不能按绝对秒数机械对齐。\n"
        "- evidence 中引用绝对时间时，只能使用 x.xs 这种秒数格式，不要使用 mm:ss，也不要写出超过用户视频总时长的时间点。\n"
        "- issueType 只能从以下值中选择：['正常', '缺失', '顺序颠倒', '过早执行', '延后执行', '重复操作', '动作错误', '部分完成', '证据不足', '前置条件缺失']。\n"
        "- completionLevel 只能从以下值中选择：['完整', '部分完成', '未完成', '无法判断']。\n"
        "- evidence 必须说明判断依据，指出具体观察到的内容。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


# ── Demo video workflow segmentation prompts (Phase 3) ─────────

def build_workflow_segmentation_system_prompt():
    return (
        "你是一个 SOP 示范视频分析助手。"
        "请分析整段流程示范视频，识别每个操作步骤在视频中的时间范围。\n"
        "只返回合法 JSON，不要输出额外说明。"
    )


def build_workflow_segmentation_blocks(steps: list, video_data_url: str, fps: float):
    step_list = "\n".join(
        [f"步骤 {step['stepNo']}: {step['description']}" for step in steps]
    )
    return [
        {
            "type": "text",
            "text": (
                f"这是一个 SOP 流程的完整示范视频，共 {len(steps)} 个步骤：\n{step_list}\n\n"
                "请识别每个步骤在视频中的起止时间（秒）。如果某步骤无法识别，将 detected 设为 false。"
            ),
        },
        {
            "type": "video_url",
            "video_url": {"url": video_data_url},
            "fps": max(0.1, float(fps or 2)),
        },
    ]


def build_workflow_segmentation_schema(step_count: int):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "workflow_segmentation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "segments": {
                        "type": "array",
                        "minItems": step_count,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1},
                                "detected": {"type": "boolean"},
                                "startSec": {"type": ["number", "null"], "minimum": 0},
                                "endSec": {"type": ["number", "null"], "minimum": 0},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                            "required": [
                                "stepNo", "detected", "startSec", "endSec", "confidence",
                            ],
                        },
                    },
                },
                "required": ["segments"],
            },
        },
    }


# Re-define the multistage evaluation prompts below with stronger sequence signals.

def build_per_step_evaluation_blocks(
    step,
    segment_info: Optional[dict],
    user_video_data_url: str,
    user_video_fps: float,
    user_video_duration: Optional[float] = None,
    user_focus_frames: Optional[List[str]] = None,
    user_focus_timestamps: Optional[List[float]] = None,
):
    has_reference_frames = bool(step.referenceFrames)
    user_focus_limit = min(len(user_focus_frames or []), 10)
    duration_text = (
        f"用户视频总时长：{float(user_video_duration):.1f}s\n"
        if user_video_duration
        else ""
    )
    duration_guardrail = (
        f"证据中如需引用绝对时间，只能写成 x.xs，且不要写出超过 {float(user_video_duration):.1f}s 的时间点。\n"
        if user_video_duration
        else ""
    )
    substeps_text = (
        "; ".join([f"{item.title}@{item.timestampSec:.2f}s" for item in step.substeps])
        if step.substeps
        else "无"
    )
    detected = segment_info.get("detected", False) if segment_info else False
    start_sec = segment_info.get("startSec") if segment_info else None
    end_sec = segment_info.get("endSec") if segment_info else None

    if detected and start_sec is not None and end_sec is not None:
        time_range_text = (
            f"时序分割识别该步骤出现在用户视频 {start_sec:.1f}s - {end_sec:.1f}s 区间。"
            "这个时间窗只用于提示用户视频中的候选位置，不能拿管理员示范视频的绝对秒数直接对齐。"
        )
    else:
        time_range_text = "时序分割未稳定定位该步骤，请在整段用户视频中搜索该动作是否出现。"

    blocks = [
        {
            "type": "text",
            "text": (
                f"当前需要评估的步骤：步骤 {step.stepNo}\n"
                f"步骤说明：{step.description}\n"
                f"步骤类型：{step.stepType}\n"
                f"步骤权重：{step.stepWeight}\n"
                f"条件说明：{step.conditionText or '无'}\n"
                f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                f"参考摘要：{step.referenceSummary or '无'}\n"
                f"ROI 提示：{step.roiHint or '无'}\n"
                f"参考关键时刻：{substeps_text}\n"
                f"参考模式：{'示范视频关键帧' if has_reference_frames else '仅文字 SOP，无示范视频'}\n"
                f"{duration_text}"
                f"{time_range_text}\n"
                f"{duration_guardrail}"
                "管理员示范视频和用户视频总时长可能不同，请根据动作形态本身判断，不要按绝对秒数机械对齐。"
            ),
        },
    ]
    for frame in step.referenceFrames[:6]:
        blocks.append({"type": "image_url", "image_url": {"url": frame}})

    if user_focus_frames:
        focus_lines = []
        for index, _frame in enumerate(user_focus_frames[:user_focus_limit]):
            timestamp = (
                user_focus_timestamps[index]
                if user_focus_timestamps and index < len(user_focus_timestamps)
                else None
            )
            focus_lines.append(
                f"采样时刻@{float(timestamp):.2f}s"
                if timestamp is not None
                else "候选窗口采样帧"
            )
        blocks.append(
            {
                "type": "text",
                "text": "下面是从用户视频候选时间窗中抽取的用户视频关键帧：\n" + " / ".join(focus_lines),
            }
        )
        for frame in user_focus_frames[:user_focus_limit]:
            blocks.append({"type": "image_url", "image_url": {"url": frame}})

    blocks.append({"type": "text", "text": "下面是完整用户视频："})
    blocks.append(
        {
            "type": "video_url",
            "video_url": {"url": user_video_data_url},
            "fps": max(0.1, float(user_video_fps or 2)),
        }
    )
    return blocks

def build_temporal_segmentation_system_prompt():
    return (
        "你是一个 SOP 视频时序分割助手，负责识别视频中每个步骤的大致起止时间。\n"
        "请结合步骤说明、参考摘要、ROI 提示、关键时刻和参考关键帧来定位动作。\n"
        "注意事项：\n"
        "- 如果某个步骤没有出现，detected=false，startSec/endSec=null。\n"
        "- 时间精度保留一位小数即可。\n"
        "- 步骤可能乱序发生，请如实输出实际顺序。\n"
        "- 对外观相似的步骤，例如 1/2/3 手势，务必区分手指数量、姿态变化和先后顺序。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


def build_temporal_segmentation_blocks(sop: SopData, user_video_data_url: str, user_video_fps: float):
    step_blocks = []
    for step in sop.steps:
        substeps_text = (
            "; ".join([f"{item.title}@{item.timestampSec:.2f}s" for item in step.substeps])
            if step.substeps
            else "无"
        )
        step_blocks.append(
            {
                "type": "text",
                "text": (
                    f"步骤 {step.stepNo}: {step.description}\n"
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"ROI 提示：{step.roiHint or '无'}\n"
                    f"关键时刻：{substeps_text}"
                ),
            }
        )
        for frame in step.referenceFrames[:2]:
            step_blocks.append({"type": "image_url", "image_url": {"url": frame}})

    return [
        {
            "type": "text",
            "text": (
                f"SOP 名称：{sop.name}\n"
                f"适用场景：{sop.scene or '未提供'}\n\n"
                f"该 SOP 共 {sop.stepCount} 个步骤，下面依次给出每个步骤的参考信息。\n"
                "请分析用户操作视频，识别每个步骤在视频中的大致起止时间（秒）。\n"
                "只返回 JSON，不要输出额外说明。"
            ),
        },
        *step_blocks,
        {
            "type": "video_url",
            "video_url": {"url": user_video_data_url},
            "fps": max(0.1, float(user_video_fps or 2)),
        },
    ]


def build_global_validation_system_prompt():
    return (
        "你是一个 SOP 全局顺序校验助手。\n"
        "你将基于每个步骤的独立评估结果和检测时间，判断整体执行顺序、前置依赖和是否存在乱序。\n"
        "重点关注：\n"
        "1. 是否存在后续步骤抢先执行。\n"
        "2. 是否存在某一步虽然动作正确，但实际发生顺序错误，应改判为顺序问题。\n"
        "3. 是否需要把顺序结论回写到具体步骤上。\n"
        "- sequenceAssessment 只能从以下值中选择：['顺序正确', '轻微顺序偏差', '明显顺序错误', '无法判断顺序']。\n"
        "- feedback 和 issues 使用中文。\n"
        "- stepOverrides 只填写需要修正的步骤；如果某一步需要改判，请明确给出 issueType、orderIssue、prerequisiteViolated 和 evidenceNote。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )


def build_global_validation_content(sop: SopData, step_results: list, segments: dict):
    step_results_lines = []
    for step in sop.steps:
        result = next((item for item in step_results if int(item.get("stepNo") or 0) == step.stepNo), {})
        seg = segments.get(step.stepNo) or {}

        start = result.get("detectedStartSec")
        end = result.get("detectedEndSec")
        if start is None or end is None:
            start = seg.get("startSec")
            end = seg.get("endSec")

        time_range = f"{start:.1f}s~{end:.1f}s" if (start is not None and end is not None) else "未定位"
        prerequisite_text = ", ".join([str(item) for item in step.prerequisiteStepNos]) or "无"
        step_results_lines.append(
            f"步骤 {step.stepNo}: {step.description}\n"
            f"  判断={'通过' if result.get('passed') else '未通过'} | "
            f"得分={result.get('score', 0)} | 问题类型={result.get('issueType', '未知')} | "
            f"检测区间={time_range} | 顺序问题={'是' if result.get('orderIssue') else '否'} | "
            f"前置依赖={prerequisite_text}\n"
            f"  证据：{result.get('evidence', '无')}"
        )

    step_order_text = " -> ".join([f"{step.stepNo}:{step.description}" for step in sop.steps])
    return (
        f"SOP 名称：{sop.name}\n"
        f"期望步骤顺序：{step_order_text}\n\n"
        "以下是各步骤的单独评估结果：\n\n"
        + "\n\n".join(step_results_lines)
        + "\n\n请根据以上各步骤结果，给出整体综合判断。如果某一步动作本身正确但顺序不对，请通过 stepOverrides 明确改判。"
    )


def build_global_validation_schema():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_global_validation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "passed": {"type": "boolean"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "feedback": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "sequenceAssessment": {
                        "type": "string",
                        "enum": ["顺序正确", "轻微顺序偏差", "明显顺序错误", "无法判断顺序"],
                    },
                    "prerequisiteViolated": {"type": "boolean"},
                    "stepOverrides": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1},
                                "orderIssue": {"type": "boolean"},
                                "prerequisiteViolated": {"type": "boolean"},
                                "issueType": {"type": "string", "enum": sorted(ISSUE_TYPE_VALUES)},
                                "detectedStartSec": {"type": ["number", "null"], "minimum": 0},
                                "detectedEndSec": {"type": ["number", "null"], "minimum": 0},
                                "evidenceNote": {"type": "string"},
                            },
                            "required": [
                                "stepNo",
                                "orderIssue",
                                "prerequisiteViolated",
                                "issueType",
                                "detectedStartSec",
                                "detectedEndSec",
                                "evidenceNote",
                            ],
                        },
                    },
                },
                "required": [
                    "passed",
                    "score",
                    "feedback",
                    "issues",
                    "sequenceAssessment",
                    "prerequisiteViolated",
                    "stepOverrides",
                ],
            },
        },
    }
