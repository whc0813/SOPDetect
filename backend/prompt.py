import json
from typing import List, Optional

from fastapi import HTTPException

try:
    from .models import (
        COMPLETION_LEVEL_VALUES,
        ISSUE_TYPE_VALUES,
        SopData,
        SopStep,
    )
except ImportError:
    from models import (
        COMPLETION_LEVEL_VALUES,
        ISSUE_TYPE_VALUES,
        SopData,
        SopStep,
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



# ── Shared evaluation standards ──────────────────────────────────
# Referenced by all system prompts to keep definitions consistent across stages.

def _shared_issue_type_definitions():
    return (
        "问题类型（issueType）定义：\n"
        "- 正常：步骤按正确顺序完整执行，无异常。\n"
        "- 缺失：步骤在整段视频中未出现或未执行。\n"
        "- 部分完成：步骤有执行动作但未达到完整标准，只做了一部分。\n"
        "- 动作错误：有动作但不符合步骤说明的真实意图，或执行了错误的替代动作。\n"
        "- 顺序颠倒：步骤动作本身正确，但发生在错误的顺序位置（与其他步骤次序互换）。\n"
        "- 过早执行：后置步骤在前置步骤完成前就开始执行。\n"
        "- 延后执行：应在当前阶段完成的步骤明显拖到后续阶段才出现。\n"
        "- 重复操作：步骤被不必要地执行了多次，且步骤说明未允许多次执行。\n"
        "- 前置条件缺失：步骤依赖的前置步骤未完成，但当前步骤仍被执行。\n"
        "- 过快完成：步骤实际持续时间短于最短耗时限制（由后端规则自动判定，模型不使用）。\n"
        "- 超时完成：步骤实际持续时间超过最长耗时限制（由后端规则自动判定，模型不使用）。\n"
        "- 证据不足：画面遮挡、模糊或采样不足，无法支持高置信度判断。\n"
    )


def _shared_completion_level_definitions():
    return (
        "完成程度（completionLevel）定义：\n"
        "- 完整：步骤的所有关键动作均已正确执行。\n"
        "- 部分完成：步骤的关键动作只执行了一部分。\n"
        "- 未完成：步骤的关键动作基本未执行。\n"
        "- 无法判断：证据不足以判断完成程度。\n"
    )


def _shared_evidence_writing_guide():
    return (
        "证据（evidence）写作规范：\n"
        "- 使用中文，点明判断依据和观察到的具体内容。\n"
        "- 引用绝对时间时使用 x.xs 秒数格式，不使用 mm:ss。\n"
        "- 引用的时间点必须在用户视频总时长范围内。\n"
        "- 明确写出判断结论对应的关键词（如\"顺序颠倒\"\"过早执行\"\"证据不足\"等）。\n"
    )


def _shared_core_principles():
    return (
        "核心评估原则：\n"
        "- 从全流程视角评估每个步骤，结合步骤顺序、前置依赖和完整视频上下文综合判断。\n"
        "- 将观察到的动作与步骤的真实意图进行匹配，只有动作形态和意图都匹配才算正确执行。\n"
        "- 如果目标动作在视频中出现过但发生在错误的顺序位置，应标记为顺序类问题（过早执行/延后执行/顺序颠倒），而非缺失。\n"
        "- 如果目标动作在视频中出现且持续时间很短，仍应如实记录起止时间并评估完成度，而非直接判为缺失。\n"
        "- 候选时间窗仅用于提示搜索范围，动作出现在窗外也应如实判断。\n"
        "- 管理员示范视频与用户视频的总时长可能不同，应根据动作形态本身判断而非按绝对秒数对齐。\n"
        "- 严格区分示范视频关键帧（管理员提供的参考）和用户测试视频（待评估的视频）。\n"
        "- 步骤耗时限制（最短/最长）仅作为上下文信息提供；模型应准确检测起止时间，耗时违规判定由后端规则自动完成。\n"
    )


# ── Single-pass evaluation prompts (original / fallback) ──────

def build_evaluation_system_prompt():
    return (
        "你是一个严格的 SOP 执行评估助手，负责从全流程视角综合判断用户是否按正确顺序、正确意图、正确完整度完成了整个流程。\n"
        "\n"
        + _shared_core_principles() + "\n"
        + _shared_issue_type_definitions() + "\n"
        + _shared_completion_level_definitions() + "\n"
        + _shared_evidence_writing_guide() + "\n"
        "输出要求：\n"
        "- feedback、issues、evidence 全部使用中文。\n"
        "- issues 用简短中文短语概括最重要的问题。\n"
        "- sequenceAssessment 从 ['顺序正确', '轻微顺序偏差', '明显顺序错误', '无法判断顺序'] 中选择。\n"
        "- orderIssue 表示该步骤是否存在顺序问题；prerequisiteViolated 表示该步骤是否存在前置条件问题。\n"
        "- passed=true 仅在整个 SOP 基本按正确顺序完成、无漏做/错做/严重错序时给出。\n"
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


def format_duration_constraint(step: SopStep) -> str:
    min_duration = getattr(step, "minDurationSec", None)
    max_duration = getattr(step, "maxDurationSec", None)
    parts = []
    if min_duration is not None and float(min_duration) > 0:
        parts.append(f"最短耗时 {float(min_duration):.1f}s")
    if max_duration is not None and float(max_duration) > 0:
        parts.append(f"最长耗时 {float(max_duration):.1f}s")
    return "，".join(parts) if parts else "无时间限制"


def build_content_blocks(sop: SopData, user_video_data_url: str, user_video_fps: float):
    blocks = [{"type": "text", "text": build_evaluation_overview_text(sop)}]
    blocks.append(
        {
            "type": "text",
            "text": (
                "下面是整段用户测试视频。请结合步骤类型和前置依赖，"
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
        duration_constraint_text = format_duration_constraint(step)
        blocks.append(
            {
                "type": "text",
                "text": (
                    f"步骤 {step.stepNo}\n"
                    f"步骤说明：{step.description}\n"
                    f"步骤类型：{step.stepType}\n"
                    f"条件说明：{step.conditionText or '无'}\n"
                    f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                    f"步骤耗时限制：{duration_constraint_text}\n"
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
                    "passed": {"type": "boolean", "description": "整个SOP是否基本按正确顺序完成，无漏做/错做/严重错序"},
                    "feedback": {"type": "string", "description": "整体评价，中文，总结执行质量和主要问题"},
                    "issues": {"type": "array", "items": {"type": "string"}, "description": "全局性问题列表，每项为简短中文短语"},
                    "sequenceAssessment": {
                        "type": "string",
                        "enum": ["顺序正确", "轻微顺序偏差", "明显顺序错误", "无法判断顺序"],
                        "description": "整体执行顺序评价",
                    },
                    "prerequisiteViolated": {"type": "boolean", "description": "是否存在步骤前置条件未满足的情况"},
                    "stepResults": {
                        "type": "array",
                        "minItems": step_count,
                        "description": "每个步骤的详细评估结果，数量等于SOP步骤总数",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1, "description": "步骤编号"},
                                "description": {"type": "string", "description": "步骤说明原文"},
                                "passed": {"type": "boolean", "description": "该步骤是否通过评估"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "判断置信度，0为完全不确定，1为完全确定"},
                                "applicable": {"type": "boolean", "description": "该步骤在当前场景是否适用"},
                                "issueType": {"type": "string", "enum": ISSUE_TYPE_VALUES, "description": "该步骤的问题类型，正常表示无问题"},
                                "completionLevel": {"type": "string", "enum": COMPLETION_LEVEL_VALUES, "description": "该步骤的完成程度"},
                                "orderIssue": {"type": "boolean", "description": "该步骤是否存在执行顺序问题（过早/延后/颠倒）"},
                                "prerequisiteViolated": {"type": "boolean", "description": "该步骤的前置依赖步骤是否未完成或不存在"},
                                "detectedStartSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤开始时间（秒），null表示未检测到"},
                                "detectedEndSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤结束时间（秒），null表示未检测到"},
                                "evidence": {"type": "string", "description": "判断依据，说明观察到什么、为何做出该判断"},
                            },
                            "required": [
                                "stepNo", "description", "passed", "confidence",
                                "applicable", "issueType", "completionLevel", "orderIssue",
                                "prerequisiteViolated", "detectedStartSec", "detectedEndSec",
                                "evidence",
                            ],
                        },
                    },
                },
                "required": [
                    "passed", "feedback", "issues", "sequenceAssessment",
                    "prerequisiteViolated", "stepResults",
                ],
            },
        },
    }
def build_temporal_segmentation_schema(step_count: int):
    occurrence_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "startSec": {"type": ["number", "null"], "minimum": 0, "description": "该次出现的开始时间（秒），null表示无法确定"},
            "endSec": {"type": ["number", "null"], "minimum": 0, "description": "该次出现的结束时间（秒），null表示无法确定"},
            "note": {"type": "string", "description": "对该次出现的补充说明"},
        },
        "required": ["startSec", "endSec", "note"],
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_temporal_segmentation",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "videoDurationSec": {"type": "number", "minimum": 0, "description": "视频总时长（秒）"},
                    "segments": {
                        "type": "array",
                        "minItems": step_count,
                        "description": "每个步骤在视频中的时间片段，数量等于SOP步骤总数",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1, "description": "步骤编号"},
                                "detected": {"type": "boolean", "description": "该步骤是否在视频中被检测到"},
                                "startSec": {"type": ["number", "null"], "minimum": 0, "description": "该步骤最早一次出现的开始时间（秒）"},
                                "endSec": {"type": ["number", "null"], "minimum": 0, "description": "该步骤最早一次出现的结束时间（秒）"},
                                "occurrenceCount": {"type": "integer", "minimum": 0, "description": "该步骤在视频中出现的总次数"},
                                "occurrences": {"type": "array", "items": occurrence_schema, "description": "每次出现的起止时间和说明，出现多次时列出所有"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "该步骤检测的置信度"},
                                "note": {"type": "string", "description": "补充说明，如该步骤为何难以定位"},
                            },
                            "required": [
                                "stepNo", "detected", "startSec", "endSec",
                                "occurrenceCount", "occurrences", "confidence", "note",
                            ],
                        },
                    },
                },
                "required": ["videoDurationSec", "segments"],
            },
        },
    }
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
                    "stepNo": {"type": "integer", "minimum": 1, "description": "步骤编号"},
                    "passed": {"type": "boolean", "description": "该步骤是否通过评估"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "判断置信度，0为完全不确定，1为完全确定"},
                    "applicable": {"type": "boolean", "description": "该步骤在当前场景是否适用"},
                    "issueType": {"type": "string", "enum": ISSUE_TYPE_VALUES, "description": "该步骤的问题类型，正常表示无问题"},
                    "completionLevel": {"type": "string", "enum": COMPLETION_LEVEL_VALUES, "description": "该步骤的完成程度"},
                    "orderIssue": {"type": "boolean", "description": "该步骤是否存在执行顺序问题"},
                    "prerequisiteViolated": {"type": "boolean", "description": "该步骤的前置依赖步骤是否未完成"},
                    "detectedStartSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤开始时间（秒），null表示未检测到"},
                    "detectedEndSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤结束时间（秒），null表示未检测到"},
                    "evidence": {"type": "string", "description": "判断依据，说明观察到什么、为何做出该判断"},
                },
                "required": [
                    "stepNo", "passed", "confidence", "applicable",
                    "issueType", "completionLevel", "orderIssue", "prerequisiteViolated",
                    "detectedStartSec", "detectedEndSec", "evidence",
                ],
            },
        },
    }
def build_per_step_evaluation_system_prompt():
    return (
        "你是一个精细的 SOP 步骤评估助手，基于用户操作视频对单个 SOP 步骤进行深度评估。\n"
        "\n"
        + _shared_core_principles() + "\n"
        + _shared_issue_type_definitions() + "\n"
        + _shared_completion_level_definitions() + "\n"
        + _shared_evidence_writing_guide() + "\n"
        "单步骤评估要点：\n"
        "- 候选时间窗是搜索范围提示，窗内的过渡动作、相邻步骤残留或收手动作属于正常现象。\n"
        "- 应关注候选时间窗中是否出现过目标动作的局部片段，而非窗内占比最高的动作。\n"
        "- 只要局部片段明确出现了目标动作，就应给出该片段的 detectedStartSec / detectedEndSec。\n"
        "- 候选时间窗后半段出现其他动作时，前半段已经出现过的目标动作仍然有效。\n"
        "- 仅当关键帧采样确实不足以支持高置信判断时，才使用\"证据不足\"。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )
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
                        "description": "每个步骤在示范视频中的时间片段",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1, "description": "步骤编号"},
                                "detected": {"type": "boolean", "description": "该步骤是否在视频中被识别到"},
                                "startSec": {"type": ["number", "null"], "minimum": 0, "description": "步骤开始时间（秒），null表示未识别"},
                                "endSec": {"type": ["number", "null"], "minimum": 0, "description": "步骤结束时间（秒），null表示未识别"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "识别的置信度"},
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
def build_per_step_evaluation_blocks(
    step,
    segment_info: Optional[dict],
    user_video_data_url: str,
    user_video_fps: float = 6.0,
    user_video_duration: Optional[float] = None,
    user_focus_frames: Optional[List[str]] = None,
    user_focus_timestamps: Optional[List[float]] = None,
):
    has_reference_frames = bool(step.referenceFrames)
    # 聚焦帧已在候选窗口内提供高密度采样，6 帧足够覆盖 1-2s 窗口的关键动作
    user_focus_limit = min(len(user_focus_frames or []), 6)
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
    duration_constraint_text = format_duration_constraint(step)
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
                f"条件说明：{step.conditionText or '无'}\n"
                f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                f"步骤耗时限制：{duration_constraint_text}\n"
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
        "- 如果某个步骤未出现，设置 detected=false，startSec/endSec=null。\n"
        "- 如果同一 SOP 步骤在视频中出现多次，occurrences 列出每一次出现的起止时间，occurrenceCount 填写出现次数。\n"
        "- startSec/endSec 使用该步骤最早一次有效出现的起止时间。\n"
        "- 多次出现应保留每次独立的时间窗，而非合并成一个长时段。\n"
        "- 时间精度保留一位小数。\n"
        "- 步骤可能乱序发生，请如实输出实际顺序。\n"
        "- 对外观相似的步骤（如 1/2/3 手指手势），应区分手指数量、姿态变化和先后顺序。\n"
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
        # Stage 1 只需定位起止时间，文字描述已足够；省去参考帧以减少输入 token

    return [
        {
            "type": "text",
            "text": (
                f"SOP 名称：{sop.name}\n"
                f"适用场景：{sop.scene or '未提供'}\n\n"
                f"该 SOP 共 {sop.stepCount} 个步骤，下面依次给出每个步骤的参考信息。\n"
                "请分析用户操作视频，识别每个步骤在视频中的大致起止时间（秒）。\n"
                "如果同一步骤出现多次，请列出每一次出现，不要只保留第一次或最后一次。\n"
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
        "你是一个 SOP 全局顺序校验助手，基于每个步骤的独立评估结果和检测时间，判断整体执行顺序、前置依赖、重复执行和乱序情况。\n"
        "\n"
        + _shared_issue_type_definitions() + "\n"
        "重点关注：\n"
        "- 后续步骤的检测开始时间是否早于前置步骤的结束时间（抢先执行）。\n"
        "- 某一步动作正确但实际发生时间与期望顺序不符的，应通过 stepOverrides 改判为对应的顺序类问题。\n"
        "- 检查是否存在不必要的重复执行。注意：每个步骤的评估结果中带有 Stage 2 的推理过程（reasoning），"
        "其中可能已经解释了多次出现的原因（如步骤说明允许多对象执行）。"
        "只有在 reasoning 未提供合理解释、且步骤描述本身也未允许多次执行时，才应通过 stepOverrides 改判为\"重复操作\"。\n"
        "\n"
        "输出要求：\n"
        "- sequenceAssessment 从 ['顺序正确', '轻微顺序偏差', '明显顺序错误', '无法判断顺序'] 中选择。\n"
        "- feedback 和 issues 使用中文。\n"
        "- stepOverrides 只填写需要修正的步骤，使用 stepNo 标识步骤。\n"
        "- stepOverrides 中：orderIssue 和 prerequisiteViolated 为布尔值；issueType 使用标准枚举值（如\"顺序颠倒\"\"过早执行\"\"延后执行\"）；每项含 evidenceNote 说明修正理由。\n"
        "- 对 Stage 2 已判为\"正常\"的步骤进行 override 应谨慎：除非发现明显的顺序错误或 Stage 2 推理中的明显矛盾，否则不应推翻。\n"
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
        duration_constraint_text = format_duration_constraint(step)
        occurrences = result.get("detectedOccurrences") or []
        occurrence_text = "无"
        if occurrences:
            occurrence_parts = []
            for index, occurrence in enumerate(occurrences[:5], start=1):
                occurrence_start = occurrence.get("startSec")
                occurrence_end = occurrence.get("endSec")
                if occurrence_start is None or occurrence_end is None:
                    continue
                occurrence_parts.append(
                    f"第{index}次 {float(occurrence_start):.1f}s~{float(occurrence_end):.1f}s"
                )
            if occurrence_parts:
                occurrence_text = "; ".join(occurrence_parts)
        reasoning_text = result.get("reasoning") or ""
        if reasoning_text:
            reasoning_text = f"\n  Stage2推理={reasoning_text}"
        step_results_lines.append(
            f"步骤 {step.stepNo}: {step.description}\n"
            f"  判断={'通过' if result.get('passed') else '未通过'} | "
            f"问题类型={result.get('issueType', '未知')} | "
            f"检测区间={time_range} | 顺序问题={'是' if result.get('orderIssue') else '否'} | "
            f"重复执行={'是' if result.get('repeatedExecution') else '否'} | "
            f"出现片段={occurrence_text} | 前置依赖={prerequisite_text} | "
            f"步骤耗时限制={duration_constraint_text}"
            f"{reasoning_text}"
        )

    step_order_text = " -> ".join([f"{step.stepNo}:{step.description}" for step in sop.steps])
    return (
        f"SOP 名称：{sop.name}\n"
        f"期望步骤顺序：{step_order_text}\n\n"
        "以下是各步骤的单独评估结果：\n\n"
        + "\n\n".join(step_results_lines)
        + "\n\n请根据以上各步骤结果，给出整体综合判断。如果某一步动作本身正确但顺序不对，或存在不必要的重复执行，请通过 stepOverrides 明确改判。"
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
                    "passed": {"type": "boolean", "description": "整体是否通过，所有步骤正常完成且无顺序问题"},
                    "feedback": {"type": "string", "description": "整体评价，中文"},
                    "issues": {"type": "array", "items": {"type": "string"}, "description": "全局性问题列表，每项为简短中文短语"},
                    "sequenceAssessment": {
                        "type": "string",
                        "enum": ["顺序正确", "轻微顺序偏差", "明显顺序错误", "无法判断顺序"],
                        "description": "整体执行顺序评价",
                    },
                    "prerequisiteViolated": {"type": "boolean", "description": "是否存在前置条件违反的情况"},
                    "stepOverrides": {
                        "type": "array",
                        "description": "需要修正的步骤列表，仅包含与原评估结果不同的步骤",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1, "description": "需要修正的步骤编号"},
                                "orderIssue": {"type": "boolean", "description": "修正后的顺序问题标记"},
                                "prerequisiteViolated": {"type": "boolean", "description": "修正后的前置条件违反标记"},
                                "issueType": {"type": "string", "enum": ISSUE_TYPE_VALUES, "description": "修正后的问题类型"},
                                "detectedStartSec": {"type": ["number", "null"], "minimum": 0, "description": "修正后的开始时间（秒）"},
                                "detectedEndSec": {"type": ["number", "null"], "minimum": 0, "description": "修正后的结束时间（秒）"},
                                "evidenceNote": {"type": "string", "description": "修正理由，中文"},
                            },
                            "required": [
                                "stepNo", "orderIssue", "prerequisiteViolated",
                                "issueType", "detectedStartSec", "detectedEndSec",
                                "evidenceNote",
                            ],
                        },
                    },
                },
                "required": [
                    "passed", "feedback", "issues", "sequenceAssessment",
                    "prerequisiteViolated", "stepOverrides",
                ],
            },
        },
    }
def build_batch_step_evaluation_system_prompt():
    return (
        "你是一个严谨的 SOP 批量评估助手，在一次输出中完成所有步骤的评估并返回 stepResults 数组。\n"
        "输入中包含每个步骤的说明、参考摘要、ROI 提示、关键时刻，以及阶段1时序分割给出的候选时间窗。\n"
        "\n"
        + _shared_core_principles() + "\n"
        + _shared_issue_type_definitions() + "\n"
        + _shared_completion_level_definitions() + "\n"
        + _shared_evidence_writing_guide() + "\n"
        "推理步骤（每个步骤按以下顺序在 reasoning 字段中推理）：\n"
        "1. 该步骤期望的动作是什么？\n"
        "2. 视频中实际观察到了什么（具体动作形态、发生时刻）？\n"
        "3. 观察到的动作是否符合期望（匹配/部分匹配/不匹配/未出现）？\n"
        "4. 起止时间的证据是什么（在视频中哪段时间看到了目标动作）？\n"
        "5. 该步骤是否受到其他步骤的影响（前置步骤未完成/后续步骤抢先/重复出现）？\n"
        "6. 综合结论（passed、issueType、completionLevel）。\n"
        "完成推理后，在 evidence 中给出简明的最终判断摘要。\n"
        "\n"
        "批量评估特有要求：\n"
        "- 阶段1时间窗是搜索提示而非硬约束，动作出现在窗外也应如实判断。\n"
        "- 结合完整用户视频评估所有步骤，确保每个 stepNo 都有对应结果。\n"
        "- 检查同一步骤在完整视频中是否出现多次，在 detectedOccurrences 中列出每次出现的起止时间。\n"
        "- 同一步骤出现多次时：若步骤说明明确允许多对象/多次执行（如双显卡安装），不应判为重复操作，并在 evidence 中说明依据；否则设置 repeatedExecution=true，issueType=\"重复操作\"。\n"
        "- feedback、issues、evidence 全部使用中文。\n"
        "只返回合法 JSON，不要输出任何额外说明。"
    )
def build_batch_step_evaluation_blocks(
    sop: SopData,
    segments: dict,
    user_video_data_url: str,
    user_video_fps: float,
    user_video_duration: Optional[float] = None,
):
    intro_lines = [
        f"SOP 名称：{sop.name}",
        f"适用场景：{sop.scene or '未提供'}",
        f"总步骤数：{sop.stepCount}",
    ]
    if user_video_duration:
        intro_lines.append(f"用户视频总时长：{float(user_video_duration):.1f}s")
    intro_lines.append("请基于同一段完整用户视频，一次性完成所有步骤的评估。")

    blocks = [{"type": "text", "text": "\n".join(intro_lines)}]

    for step in sop.steps:
        segment_info = segments.get(step.stepNo) or {}
        substeps_text = (
            "; ".join([f"{item.title}@{item.timestampSec:.2f}s" for item in step.substeps])
            if step.substeps
            else "无"
        )
        duration_constraint_text = format_duration_constraint(step)
        start_sec = segment_info.get("startSec")
        end_sec = segment_info.get("endSec")
        occurrences = segment_info.get("occurrences") or []
        # 阶段1结果以结构化JSON嵌入，替代字符串拼接，减少模型解析偏差
        segment_json = json.dumps(
            {
                "startSec": round(float(start_sec), 3) if start_sec is not None else None,
                "endSec": round(float(end_sec), 3) if end_sec is not None else None,
                "occurrenceCount": segment_info.get("occurrenceCount") or len(occurrences) or 0,
                "occurrences": [
                    {"startSec": round(float(o["startSec"]), 3), "endSec": round(float(o["endSec"]), 3)}
                    for o in (occurrences or [])
                    if o.get("startSec") is not None and o.get("endSec") is not None
                ],
            },
            ensure_ascii=False,
        )
        blocks.append(
            {
                "type": "text",
                "text": (
                    f"步骤 {step.stepNo}\n"
                    f"步骤说明：{step.description}\n"
                    f"步骤类型：{step.stepType}\n"
                    f"条件说明：{step.conditionText or '无'}\n"
                    f"前置依赖步骤：{', '.join([str(item) for item in step.prerequisiteStepNos]) or '无'}\n"
                    f"步骤耗时限制：{duration_constraint_text}\n"
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"ROI 提示：{step.roiHint or '无'}\n"
                    f"参考关键时刻：{substeps_text}\n"
                    f"阶段1时序分割结果（时间窗仅作搜索提示）：{segment_json}\n"
                    "请结合完整用户视频判断该步骤是否出现、完成度如何、是否存在顺序问题。"
                ),
            }
        )
        # 附带参考关键帧帮助模型理解正确动作形态（每步最多3张）
        has_frames = bool(step.referenceFrames)
        if has_frames:
            blocks.append(
                {
                    "type": "text",
                    "text": f"下面是步骤 {step.stepNo} 的示范视频关键帧（参考正确动作形态）：",
                }
            )
            for frame in step.referenceFrames[:3]:
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


def build_batch_step_evaluation_schema(step_count: int):
    occurrence_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "startSec": {"type": "number", "minimum": 0, "description": "该次出现的开始时间（秒）"},
            "endSec": {"type": "number", "minimum": 0, "description": "该次出现的结束时间（秒）"},
            "note": {"type": "string", "description": "对该次出现的补充说明"},
        },
        "required": ["startSec", "endSec", "note"],
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sop_batch_step_eval",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "stepResults": {
                        "type": "array",
                        "minItems": step_count,
                        "description": "所有步骤的评估结果，数量等于SOP步骤总数",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "stepNo": {"type": "integer", "minimum": 1, "description": "步骤编号"},
                                "passed": {"type": "boolean", "description": "该步骤是否通过评估"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "判断置信度，0为完全不确定，1为完全确定"},
                                "applicable": {"type": "boolean", "description": "该步骤在当前场景是否适用"},
                                "issueType": {"type": "string", "enum": ISSUE_TYPE_VALUES, "description": "该步骤的问题类型，正常表示无问题"},
                                "completionLevel": {"type": "string", "enum": COMPLETION_LEVEL_VALUES, "description": "该步骤的完成程度"},
                                "orderIssue": {"type": "boolean", "description": "该步骤是否存在执行顺序问题（过早/延后/颠倒）"},
                                "prerequisiteViolated": {"type": "boolean", "description": "该步骤的前置依赖步骤是否未完成"},
                                "detectedStartSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤开始时间（秒），null表示未检测到"},
                                "detectedEndSec": {"type": ["number", "null"], "minimum": 0, "description": "检测到的步骤结束时间（秒），null表示未检测到"},
                                "repeatedExecution": {"type": "boolean", "description": "该步骤是否出现了不必要的重复执行"},
                                "detectedOccurrences": {"type": "array", "items": occurrence_schema, "description": "该步骤在视频中的每次出现，出现多次时列出所有"},
                                "reasoning": {"type": "string", "description": "推理过程：期望动作→实际观察到什么→起止时间证据→是否受其他步骤影响→结论"},
                                "evidence": {"type": "string", "description": "判断依据摘要，简明扼要说明观察到的关键内容和最终结论"},
                            },
                            "required": [
                                "stepNo", "passed", "confidence", "applicable",
                                "issueType", "completionLevel", "orderIssue", "prerequisiteViolated",
                                "detectedStartSec", "detectedEndSec", "repeatedExecution",
                                "detectedOccurrences", "reasoning", "evidence",
                            ],
                        },
                    }
                },
                "required": ["stepResults"],
            },
        },
    }
