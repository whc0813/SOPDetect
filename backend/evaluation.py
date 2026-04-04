"""
evaluation.py – Orchestrates the multi-stage SOP evaluation pipeline.

Phases implemented here:
  Phase 2: 3-stage evaluation (temporal segmentation → per-step eval → global validation)
  Phase 3: Smart demo video segmentation for SOP creation
"""
import asyncio
import base64
import re
import threading
import time
import traceback
from datetime import datetime
from typing import Callable, List, Optional

import httpx
from fastapi import HTTPException

try:
    from .models import (
        AIReferencePlan,
        ApiConfig,
        EvaluationResultPayload,
        SopData,
        SopStep,
    )
    from .prompt import (
        build_content_blocks,
        build_evaluation_system_prompt,
        build_global_validation_content,
        build_global_validation_schema,
        build_global_validation_system_prompt,
        build_per_step_evaluation_blocks,
        build_per_step_evaluation_schema,
        build_per_step_evaluation_system_prompt,
        build_response_schema,
        build_temporal_segmentation_blocks,
        build_temporal_segmentation_schema,
        build_temporal_segmentation_system_prompt,
        build_workflow_segmentation_blocks,
        build_workflow_segmentation_schema,
        build_workflow_segmentation_system_prompt,
        normalize_messages_for_model,
        parse_json_content,
    )
    from .scoring import get_penalty_config, post_process_evaluation_result
    from .storage import (
        append_evaluation_job_log,
        attach_media,
        claim_next_evaluation_job,
        get_config,
        get_evaluation_job,
        get_media,
        get_sop,
        add_history,
        now_display,
        serialize_uploaded_video,
        update_evaluation_job,
    )
    from .video import (
        build_data_url,
        build_reference_bundle,
        build_sample_timestamps,
        build_user_segments,
        cleanup_file,
        data_url_to_temp_path,
        ensure_browser_playable_video,
        extract_analysis_samples,
        normalize_timestamps,
        read_video_meta,
        split_data_url,
    )
except ImportError:
    from models import (
        AIReferencePlan,
        ApiConfig,
        EvaluationResultPayload,
        SopData,
        SopStep,
    )
    from prompt import (
        build_content_blocks,
        build_evaluation_system_prompt,
        build_global_validation_content,
        build_global_validation_schema,
        build_global_validation_system_prompt,
        build_per_step_evaluation_blocks,
        build_per_step_evaluation_schema,
        build_per_step_evaluation_system_prompt,
        build_response_schema,
        build_temporal_segmentation_blocks,
        build_temporal_segmentation_schema,
        build_temporal_segmentation_system_prompt,
        build_workflow_segmentation_blocks,
        build_workflow_segmentation_schema,
        build_workflow_segmentation_system_prompt,
        normalize_messages_for_model,
        parse_json_content,
    )
    from scoring import get_penalty_config, post_process_evaluation_result
    from storage import (
        append_evaluation_job_log,
        attach_media,
        claim_next_evaluation_job,
        get_config,
        get_evaluation_job,
        get_media,
        get_sop,
        add_history,
        now_display,
        serialize_uploaded_video,
        update_evaluation_job,
    )
    from video import (
        build_data_url,
        build_reference_bundle,
        build_sample_timestamps,
        build_user_segments,
        cleanup_file,
        data_url_to_temp_path,
        ensure_browser_playable_video,
        extract_analysis_samples,
        normalize_timestamps,
        read_video_meta,
        split_data_url,
    )

import os

JOB_POLL_INTERVAL_SEC = float(os.getenv("EVALUATION_JOB_POLL_INTERVAL_SEC", "2"))
JOB_WORKER_STOP_EVENT = threading.Event()
JOB_WORKER_THREAD = None


# ── Low-level LLM helpers ──────────────────────────────────────

def choose_analysis_fps(configured_fps: Optional[float], video_fps: Optional[float]) -> float:
    """Raise sampling density for short actions while keeping model input bounded."""
    candidates = [6.0]
    try:
        if configured_fps is not None:
            candidates.append(float(configured_fps))
    except (TypeError, ValueError):
        pass
    try:
        if video_fps is not None:
            candidates.append(min(float(video_fps), 8.0))
    except (TypeError, ValueError):
        pass
    return round(max(0.1, min(8.0, max(candidates))), 3)


def build_focus_sampling_window(
    segment_info: Optional[dict], duration_sec: Optional[float]
) -> tuple[Optional[float], Optional[float], int]:
    """
    Expand the model-produced segment into a search window for short actions.

    Stage 1 ranges are only coarse anchors. Step evaluation needs a slightly padded
    window plus denser sampling so brief gestures near the segment edges are not lost.
    """
    if not segment_info:
        return None, None, 12

    start = segment_info.get("startSec")
    end = segment_info.get("endSec")
    if start is None or end is None:
        return None, None, 12

    try:
        start = float(start)
        end = float(end)
    except (TypeError, ValueError):
        return None, None, 12

    if end < start:
        start, end = end, start

    raw_width = max(0.1, end - start)
    padding = min(0.75, max(0.25, raw_width * 0.25))
    focus_start = max(0.0, start - padding)
    focus_end = end + padding
    if duration_sec and duration_sec > 0:
        focus_end = min(float(duration_sec), focus_end)
    focus_width = max(0.1, focus_end - focus_start)
    sample_count = max(12, min(18, int(round(focus_width / 0.15))))
    return round(focus_start, 3), round(focus_end, 3), sample_count


def ensure_step_segments(sop: SopData, segments: Optional[dict], video_path: str) -> dict:
    """
    Keep valid model-detected temporal windows and fill missing/invalid steps with a uniform fallback.
    """
    normalized_segments = {}
    raw_segments = segments or {}
    fallback_segments = None

    for step in sop.steps:
        current = raw_segments.get(step.stepNo) or {}
        start = current.get("startSec")
        end = current.get("endSec")
        has_valid_window = start is not None and end is not None
        if has_valid_window:
            try:
                has_valid_window = float(end) >= float(start)
            except (TypeError, ValueError):
                has_valid_window = False

        if current.get("detected") and has_valid_window:
            normalized_segments[step.stepNo] = {
                "stepNo": step.stepNo,
                "detected": True,
                "startSec": round(float(start), 3),
                "endSec": round(float(end), 3),
                "confidence": max(0.0, min(1.0, float(current.get("confidence") or 0))),
                "note": (current.get("note") or "").strip(),
            }
            continue

        if fallback_segments is None:
            fallback_segments = {
                int(item.get("stepNo") or 0): item
                for item in build_user_segments(video_path, sop.stepCount, 1)
            }
        fallback = fallback_segments.get(step.stepNo) or {}
        fallback_start = fallback.get("startSec")
        fallback_end = fallback.get("endSec")
        note = (current.get("note") or "").strip()
        if note:
            note = f"{note}；"
        note += "时序分割未稳定命中，已回退为均匀时间窗供后续步骤重点检查。"
        normalized_segments[step.stepNo] = {
            "stepNo": step.stepNo,
            "detected": False,
            "startSec": round(float(fallback_start or 0), 3) if fallback_start is not None else None,
            "endSec": round(float(fallback_end or 0), 3) if fallback_end is not None else None,
            "confidence": 0.0,
            "note": note,
        }

    return normalized_segments


def _append_evidence_note(evidence: str, note: str) -> str:
    text = (evidence or "").strip()
    note_text = (note or "").strip()
    if not note_text:
        return text
    if note_text in text:
        return text
    if not text:
        return note_text
    return f"{text}；{note_text}"


def _clamp_optional_second(value, duration_sec: Optional[float]):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if duration_sec is not None and duration_sec > 0:
        number = max(0.0, min(float(duration_sec), number))
    else:
        number = max(0.0, number)
    return round(number, 3)


def sanitize_evidence_timestamps(evidence: str, duration_sec: Optional[float]) -> str:
    text = (evidence or "").strip()
    if not text or duration_sec is None or duration_sec <= 0:
        return text

    replaced = False

    def replace_mmss_range(match: re.Match) -> str:
        nonlocal replaced
        start_total = int(match.group(1)) * 60 + int(match.group(2))
        end_total = int(match.group(3)) * 60 + int(match.group(4))
        if start_total > duration_sec + 0.05 or end_total > duration_sec + 0.05:
            replaced = True
            return "候选时间窗内"
        return match.group(0)

    text = re.sub(r"(?<!\d)(\d+):(\d{2})\s*[-~至]+\s*(\d+):(\d{2})(?!\d)", replace_mmss_range, text)

    def replace_seconds_range(match: re.Match) -> str:
        nonlocal replaced
        try:
            start_value = float(match.group(1))
            end_value = float(match.group(2))
        except (TypeError, ValueError):
            return match.group(0)
        if start_value > duration_sec + 0.05 or end_value > duration_sec + 0.05:
            replaced = True
            return "候选时间窗内"
        return match.group(0)

    text = re.sub(r"(?<!\d)(\d+(?:\.\d+)?)s\s*[-~至]+\s*(\d+(?:\.\d+)?)s(?!\d)", replace_seconds_range, text)

    def replace_mmss(match: re.Match) -> str:
        nonlocal replaced
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        total = minutes * 60 + seconds
        if total > duration_sec + 0.05:
            replaced = True
            return "候选时间窗内"
        return match.group(0)

    text = re.sub(r"(?<!\d)(\d+):(\d{2})(?!\d)", replace_mmss, text)

    def replace_seconds(match: re.Match) -> str:
        nonlocal replaced
        try:
            value = float(match.group(1))
        except (TypeError, ValueError):
            return match.group(0)
        if value > duration_sec + 0.05:
            replaced = True
            return "候选时间窗内"
        return match.group(0)

    text = re.sub(r"(?<!\d)(\d+(?:\.\d+)?)s(?!\d)", replace_seconds, text)

    if replaced:
        text = _append_evidence_note(
            text,
            f"已按用户视频总时长 {duration_sec:.1f}s 清理超出范围的绝对时间描述",
        )
    return text


def sanitize_step_result(result: dict, duration_sec: Optional[float]) -> dict:
    cleaned = dict(result or {})
    cleaned["detectedStartSec"] = _clamp_optional_second(cleaned.get("detectedStartSec"), duration_sec)
    cleaned["detectedEndSec"] = _clamp_optional_second(cleaned.get("detectedEndSec"), duration_sec)
    cleaned["evidence"] = sanitize_evidence_timestamps(cleaned.get("evidence") or "", duration_sec)
    return cleaned


def reconcile_order_issue_from_evidence(step: SopStep, result: dict, duration_sec: Optional[float]) -> dict:
    """
    If the model's evidence explicitly says the target action happened earlier/later,
    do not keep the structured result as "missing".
    """
    cleaned = sanitize_step_result(result, duration_sec)
    issue_type = str(cleaned.get("issueType") or "").strip()
    evidence = str(cleaned.get("evidence") or "").strip()
    if issue_type not in {"缺失", "动作错误"} or not evidence:
        return cleaned

    order_hints = ("顺序", "时序", "之前", "之后", "早期", "过早", "延后", "前置步骤", "抢跑")
    occurrence_hints = ("出现了", "出现过", "做出了", "展示了", "观察到", "伸出三指", "三指手势")
    if not any(token in evidence for token in order_hints):
        return cleaned
    if not any(token in evidence for token in occurrence_hints):
        return cleaned

    ranges = []
    for match in re.finditer(r"(?<!\d)(\d+(?:\.\d+)?)s\s*[-~至]\s*(\d+(?:\.\d+)?)s(?!\d)", evidence):
        try:
            start = float(match.group(1))
            end = float(match.group(2))
        except (TypeError, ValueError):
            continue
        start = max(0.0, start)
        end = max(start, end)
        if duration_sec and duration_sec > 0:
            start = min(float(duration_sec), start)
            end = min(float(duration_sec), end)
        ranges.append((round(start, 3), round(end, 3)))

    if "之后" in evidence or "延后" in evidence:
        inferred_issue = "延后执行"
    elif "之前" in evidence or "早期" in evidence or "过早" in evidence or "前置步骤" in evidence or "抢跑" in evidence:
        inferred_issue = "过早执行"
    else:
        inferred_issue = "顺序颠倒"

    cleaned["issueType"] = inferred_issue
    cleaned["orderIssue"] = True
    if ranges:
        cleaned["detectedStartSec"] = ranges[0][0]
        cleaned["detectedEndSec"] = ranges[0][1]
    cleaned["evidence"] = _append_evidence_note(
        cleaned.get("evidence") or "",
        "后端已根据证据改判为顺序问题",
    )
    return cleaned


def apply_global_validation_overrides(step_results: list, global_result: Optional[dict]) -> list:
    """Merge Stage 3 sequence/prerequisite corrections back into step-level results."""
    override_map = {}
    for item in (global_result or {}).get("stepOverrides") or []:
        try:
            step_no = int(item.get("stepNo") or 0)
        except (TypeError, ValueError):
            continue
        if step_no <= 0:
            continue
        override_map[step_no] = dict(item)

    merged_results = []
    for result in step_results:
        step_no = int(result.get("stepNo") or 0)
        override = override_map.get(step_no)
        if not override:
            merged_results.append(dict(result))
            continue

        updated = dict(result)
        updated["orderIssue"] = bool(updated.get("orderIssue")) or bool(override.get("orderIssue"))
        updated["prerequisiteViolated"] = bool(updated.get("prerequisiteViolated")) or bool(
            override.get("prerequisiteViolated")
        )
        if (override.get("issueType") or "").strip():
            updated["issueType"] = override.get("issueType")

        if override.get("detectedStartSec") is not None:
            try:
                updated["detectedStartSec"] = round(float(override.get("detectedStartSec")), 3)
            except (TypeError, ValueError):
                pass
        if override.get("detectedEndSec") is not None:
            try:
                updated["detectedEndSec"] = round(float(override.get("detectedEndSec")), 3)
            except (TypeError, ValueError):
                pass

        updated["evidence"] = _append_evidence_note(
            updated.get("evidence") or "", override.get("evidenceNote") or ""
        )
        merged_results.append(updated)

    return merged_results


async def call_chat_completion(api_config: ApiConfig, payload: dict):
    if not api_config.apiKey or not api_config.apiKey.strip():
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    if payload is None:
        payload = {}
    payload["enable_thinking"] = False
    payload["messages"] = normalize_messages_for_model(
        api_config.model, payload.get("messages") or []
    )
    if isinstance(payload.get("extra_body"), dict):
        payload["extra_body"] = {**payload["extra_body"], "enable_thinking": False}

    base_url = api_config.baseURL.rstrip("/")
    url = (
        base_url
        if base_url.endswith("/chat/completions")
        else f"{base_url}/chat/completions"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_config.apiKey.strip()}",
    }
    timeout = api_config.timeoutMs / 1000.0

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)

    try:
        raw_json = response.json()
    except Exception:
        raw_json = {"rawText": response.text}

    if response.status_code != 200:
        message = (
            raw_json.get("error", {}).get("message")
            or raw_json.get("message")
            or response.text
            or f"HTTP {response.status_code}"
        )
        raise HTTPException(status_code=response.status_code, detail=message)

    return raw_json


def build_runtime_api_config() -> ApiConfig:
    return ApiConfig.model_validate(get_config())


def sanitize_payload(payload):
    def strip_data_url(value):
        if isinstance(value, str) and value.startswith("data:"):
            index = value.find(",")
            return f"{value[: index + 1]}<base64 omitted>"
        return value

    def walk(value):
        if isinstance(value, dict):
            return {key: walk(strip_data_url(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        return strip_data_url(value)

    return walk(payload)


# ── Demo video / reference bundle helpers ─────────────────────

async def build_ai_reference_plan(
    api_config: Optional[ApiConfig],
    step_no: int,
    description: str,
    duration_sec: float,
    sample_timestamps: List[float],
    sample_frames: List[str],
):
    if not api_config or not api_config.apiKey.strip():
        return None, None

    content_blocks = [
        {
            "type": "text",
            "text": (
                "你正在分析一个 SOP 示范视频。\n"
                f"步骤编号：{step_no}\n"
                f"步骤说明：{description}\n"
                f"视频时长：{duration_sec:.2f} 秒\n"
                "下面会给你一组从示范视频中均匀采样得到的画面。"
                "请根据这些画面，推断这个步骤中最关键的子动作，并按发生顺序给出时间点估计。"
                "时间点尽量对应明显动作发生的时刻，而不是过渡阶段。"
                "如果这个步骤本身包含连续动作，例如依次按多个按键，请把每次按键都拆成单独的子步骤。\n"
                "只返回 JSON，不要输出额外说明。"
            ),
        }
    ]
    for index, frame in enumerate(sample_frames):
        timestamp = sample_timestamps[index] if index < len(sample_timestamps) else 0
        content_blocks.append(
            {"type": "text", "text": f"采样帧 {index + 1}，估计时间点 {timestamp:.2f} 秒。"}
        )
        content_blocks.append({"type": "image_url", "image_url": {"url": frame}})

    payload = {
        "model": api_config.model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "你是 SOP 示范视频的预处理助手。请始终返回符合给定 JSON Schema 的合法 JSON。",
            },
            {"role": "user", "content": content_blocks},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sop_reference_plan",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "stepSummary": {"type": "string"},
                        "roiHint": {"type": "string"},
                        "keyMoments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "title": {"type": "string"},
                                    "timestampSec": {"type": "number", "minimum": 0},
                                },
                                "required": ["title", "timestampSec"],
                            },
                        },
                    },
                    "required": ["stepSummary", "roiHint", "keyMoments"],
                },
            },
        },
    }

    raw_result = await call_chat_completion(api_config, payload)
    parsed = AIReferencePlan.model_validate(
        parse_json_content(
            raw_result.get("choices", [{}])[0].get("message", {}).get("content")
        )
    )
    return parsed, raw_result


async def prepare_reference_bundle(
    step_no: int,
    description: str,
    video_data_url: str,
    max_frames: int = 8,
    api_config: Optional[ApiConfig] = None,
    start_sec: float = 0,
    end_sec: Optional[float] = None,
):
    """Prepare step reference bundle, optionally restricted to a time range (Phase 3)."""
    temp_path = None
    try:
        temp_path = data_url_to_temp_path(video_data_url)
        meta = read_video_meta(temp_path)
        analysis_timestamps, analysis_frames = extract_analysis_samples(
            temp_path, meta["durationSec"], start_sec=start_sec, end_sec=end_sec
        )
        ai_plan = None
        raw_ai_result = None

        if api_config and api_config.apiKey.strip():
            try:
                ai_plan, raw_ai_result = await build_ai_reference_plan(
                    api_config,
                    step_no,
                    description,
                    meta["durationSec"],
                    analysis_timestamps,
                    analysis_frames,
                )
            except HTTPException:
                raise
            except Exception:
                ai_plan = None
                raw_ai_result = None

        bundle = build_reference_bundle(
            step_no,
            description,
            temp_path,
            max(1, min(max_frames, 8)),
            ai_plan=ai_plan,
            analysis_samples=analysis_timestamps,
        )

        return {
            **bundle,
            "analysisFrames": analysis_frames,
            "aiUsed": bool(ai_plan),
            "rawAIResult": sanitize_payload(raw_ai_result) if raw_ai_result else None,
        }
    finally:
        cleanup_file(temp_path)


async def store_demo_video_and_prepare_bundle(
    data: dict,
    api_config: ApiConfig,
    sop_id: Optional[str],
    step_no: int,
    description: str,
    video_data_url: str,
    video_meta,
    uploaded_by=None,
    start_sec: float = 0,
    end_sec: Optional[float] = None,
):
    mime_type, binary = split_data_url(video_data_url)
    normalized_video = ensure_browser_playable_video(
        mime_type,
        binary,
        (video_meta.name if video_meta else "") or f"sop-step-{step_no}",
    )
    normalized_data_url = build_data_url(normalized_video["mimeType"], normalized_video["binary"])
    demo_video = attach_media(
        data,
        binary=normalized_video["binary"],
        mime_type=normalized_video["mimeType"],
        original_name=normalized_video["name"]
        or ((video_meta.name if video_meta else "") or f"sop-step-{step_no}"),
        size=len(normalized_video["binary"]),
        last_modified=video_meta.lastModified if video_meta else None,
        owner_role="admin",
        business_type="sop_step_demo",
        related_sop_id=sop_id,
        related_step_no=step_no,
        uploaded_by=uploaded_by or "admin",
    )
    bundle = await prepare_reference_bundle(
        step_no=step_no,
        description=description,
        video_data_url=normalized_data_url,
        max_frames=8,
        api_config=api_config,
        start_sec=start_sec,
        end_sec=end_sec,
    )
    return demo_video, bundle


def build_text_only_reference_bundle(step_no: int, description: str):
    return {
        "stepType": "required",
        "stepWeight": 1.0,
        "conditionText": "",
        "prerequisiteStepNos": [],
        "referenceFrames": [],
        "analysisFrames": [],
        "referenceSummary": f"仅基于文字 SOP 评估：{description}",
        "referenceFeatures": None,
        "substeps": [],
        "roiHint": "",
        "aiUsed": False,
        "rawAIResult": None,
    }


def rebuild_reference_bundle_from_video(
    video_path: str,
    step_no: int,
    description: str,
    timestamps: List[float],
):
    try:
        from .video import extract_frames
    except ImportError:
        from video import extract_frames

    meta = read_video_meta(video_path)
    duration_sec = meta["durationSec"] if meta["durationSec"] > 0 else 0.1
    normalized = normalize_timestamps(timestamps, duration_sec, max(len(timestamps), 1))
    if not normalized:
        raise HTTPException(status_code=400, detail="请至少提供一个有效时间点")

    frames = extract_frames(video_path, normalized)
    return {
        "referenceFrames": frames,
        "analysisFrames": [],
        "referenceSummary": f"管理员手动切帧：步骤 {step_no} / {description}",
        "referenceFeatures": {
            "durationSec": meta["durationSec"],
            "fps": meta["fps"],
            "frameCount": meta["frameCount"],
            "sampleTimestamps": normalized[: len(frames)],
        },
        "substeps": [
            {"title": f"手动关键帧 {index + 1}", "timestampSec": value}
            for index, value in enumerate(normalized[: len(frames)])
        ],
        "roiHint": "",
        "aiUsed": False,
        "rawAIResult": None,
    }


def build_sop_model_from_record(record: dict) -> SopData:
    try:
        from .scoring import normalize_step_payload
    except ImportError:
        from scoring import normalize_step_payload

    steps = []
    for index, step in enumerate(record.get("steps") or []):
        normalized_step = normalize_step_payload(
            {
                "stepNo": step.get("stepNo") or index + 1,
                "stepType": step.get("stepType"),
                "stepWeight": step.get("stepWeight"),
                "conditionText": step.get("conditionText"),
                "prerequisiteStepNos": step.get("prerequisiteStepNos"),
            }
        )
        steps.append(
            {
                "stepNo": normalized_step["stepNo"],
                "description": step.get("description") or "",
                "stepType": normalized_step["stepType"],
                "stepWeight": normalized_step["stepWeight"],
                "conditionText": normalized_step["conditionText"],
                "prerequisiteStepNos": normalized_step["prerequisiteStepNos"],
                "referenceFrames": step.get("referenceFrames") or [],
                "referenceSummary": step.get("referenceSummary") or "",
                "referenceFeatures": step.get("referenceFeatures") or None,
                "substeps": step.get("substeps") or [],
                "roiHint": step.get("roiHint") or "",
            }
        )

    return SopData.model_validate(
        {
            "name": record.get("name") or "",
            "scene": record.get("scene") or "",
            "stepCount": record.get("stepCount") or len(steps),
            "steps": steps,
            "penaltyConfig": record.get("penaltyConfig") or None,
        }
    )


# ── Phase 3: Smart demo video segmentation ────────────────────

async def segment_workflow_video(
    api_config: ApiConfig, steps: list, video_data_url: str
) -> dict:
    """
    Single LLM call to segment a workflow demo video into per-step time ranges.
    Returns {stepNo: {"detected": bool, "startSec": float|None, "endSec": float|None}}.
    Falls back to empty dict on failure (caller uses uniform splitting instead).
    """
    if not api_config or not api_config.apiKey.strip():
        return {}
    if not steps or not (video_data_url or "").strip():
        return {}

    try:
        payload = {
            "model": api_config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": build_workflow_segmentation_system_prompt(),
                },
                {
                    "role": "user",
                    "content": build_workflow_segmentation_blocks(
                        steps, video_data_url, api_config.fps or 2
                    ),
                },
            ],
            "response_format": build_workflow_segmentation_schema(len(steps)),
        }
        raw_json = await call_chat_completion(api_config, payload)
        parsed = parse_json_content(
            raw_json.get("choices", [{}])[0].get("message", {}).get("content")
        )
        return {
            int(seg["stepNo"]): seg
            for seg in (parsed.get("segments") or [])
            if int(seg.get("stepNo") or 0) > 0
        }
    except Exception:
        return {}


# ── Phase 2: Three-stage evaluation pipeline ──────────────────

async def run_temporal_segmentation(
    api_config: ApiConfig, sop: SopData, user_video_data_url: str, user_video_fps: float
) -> dict:
    """
    Stage 1: Ask the model to identify where each SOP step occurs in the user video.
    Returns {stepNo: {"detected": bool, "startSec": float|None, "endSec": float|None, "confidence": float}}.
    Falls back to uniform split dict on failure.
    """
    try:
        payload = {
            "model": api_config.model,
            "temperature": api_config.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": build_temporal_segmentation_system_prompt(),
                },
                {
                    "role": "user",
                    "content": build_temporal_segmentation_blocks(
                        sop, user_video_data_url, user_video_fps
                    ),
                },
            ],
            "response_format": build_temporal_segmentation_schema(sop.stepCount),
        }
        raw_json = await call_chat_completion(api_config, payload)
        parsed = parse_json_content(
            raw_json.get("choices", [{}])[0].get("message", {}).get("content")
        )
        segments = {
            int(seg["stepNo"]): seg
            for seg in (parsed.get("segments") or [])
            if int(seg.get("stepNo") or 0) > 0
        }
        return segments, parsed.get("videoDurationSec")
    except Exception:
        return {}, None


async def run_per_step_evaluation(
    api_config: ApiConfig,
    step: SopStep,
    segment_info: Optional[dict],
    user_video_data_url: str,
    user_video_fps: float,
    user_video_duration: Optional[float] = None,
    user_focus_frames: Optional[List[str]] = None,
    user_focus_timestamps: Optional[List[float]] = None,
) -> dict:
    """
    Stage 2: Evaluate a single SOP step against the user video.
    Returns a step result dict.
    """
    payload = {
        "model": api_config.model,
        "temperature": api_config.temperature,
        "messages": [
            {
                "role": "system",
                "content": build_per_step_evaluation_system_prompt(),
            },
            {
                "role": "user",
                "content": build_per_step_evaluation_blocks(
                    step,
                    segment_info,
                    user_video_data_url,
                    user_video_fps,
                    user_video_duration=user_video_duration,
                    user_focus_frames=user_focus_frames,
                    user_focus_timestamps=user_focus_timestamps,
                ),
            },
        ],
        "response_format": build_per_step_evaluation_schema(),
    }
    raw_json = await call_chat_completion(api_config, payload)
    result = parse_json_content(
        raw_json.get("choices", [{}])[0].get("message", {}).get("content")
    )
    result["stepNo"] = step.stepNo
    result.setdefault("description", step.description)
    return reconcile_order_issue_from_evidence(step, result, user_video_duration)


async def run_per_step_evaluation_batch(
    api_config: ApiConfig,
    sop: SopData,
    segments: dict,
    user_video_path: str,
    user_video_data_url: str,
    user_video_fps: float,
    on_step_done: Optional[Callable] = None,
) -> list:
    """
    Stage 2 batch: evaluate all steps concurrently (max 3 at a time).
    """
    semaphore = asyncio.Semaphore(3)
    total = len(sop.steps)
    user_video_meta = read_video_meta(user_video_path)
    user_video_duration = user_video_meta.get("durationSec") or 0

    async def eval_one(step: SopStep):
        async with semaphore:
            try:
                segment_info = segments.get(step.stepNo)
                user_focus_timestamps = []
                user_focus_frames = []
                if (
                    segment_info
                    and segment_info.get("startSec") is not None
                    and segment_info.get("endSec") is not None
                    and user_video_duration > 0
                ):
                    try:
                        focus_start, focus_end, focus_sample_count = build_focus_sampling_window(
                            segment_info, user_video_duration
                        )
                        user_focus_timestamps, user_focus_frames = extract_analysis_samples(
                            user_video_path,
                            user_video_duration,
                            start_sec=focus_start if focus_start is not None else float(segment_info.get("startSec") or 0),
                            end_sec=focus_end if focus_end is not None else float(segment_info.get("endSec") or 0),
                            sample_count=focus_sample_count,
                        )
                    except Exception:
                        user_focus_timestamps, user_focus_frames = [], []
                result = await run_per_step_evaluation(
                    api_config=api_config,
                    step=step,
                    segment_info=segment_info,
                    user_video_data_url=user_video_data_url,
                    user_video_fps=user_video_fps,
                    user_video_duration=user_video_duration,
                    user_focus_frames=user_focus_frames,
                    user_focus_timestamps=user_focus_timestamps,
                )
            except Exception as exc:
                result = {
                    "stepNo": step.stepNo,
                    "description": step.description,
                    "passed": False,
                    "score": 0,
                    "confidence": 0.0,
                    "applicable": True,
                    "issueType": "证据不足",
                    "completionLevel": "无法判断",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": None,
                    "detectedEndSec": None,
                    "evidence": f"该步骤评估调用异常：{exc}",
                }
            if on_step_done:
                on_step_done(step.stepNo, total)
            return result

    results = await asyncio.gather(*[eval_one(step) for step in sop.steps])
    return list(results)


async def run_global_validation(
    api_config: ApiConfig, sop: SopData, step_results: list, segments: dict
) -> dict:
    """
    Stage 3: Text-only global validation of sequence correctness and prerequisites.
    Returns an overall evaluation dict (merged with step_results).
    """
    payload = {
        "model": api_config.model,
        "temperature": api_config.temperature,
        "messages": [
            {
                "role": "system",
                "content": build_global_validation_system_prompt(),
            },
            {
                "role": "user",
                "content": build_global_validation_content(sop, step_results, segments),
            },
        ],
        "response_format": build_global_validation_schema(),
    }
    raw_json = await call_chat_completion(api_config, payload)
    return parse_json_content(
        raw_json.get("choices", [{}])[0].get("message", {}).get("content")
    )


async def _run_multistage_evaluation(
    api_config: ApiConfig,
    sop: SopData,
    user_video_path: str,
    user_video_data_url: str,
    user_video_fps: float,
    job_id: Optional[str] = None,
) -> dict:
    """
    Orchestrate the full 3-stage evaluation. Reports progress to the DB if job_id is given.
    """
    def _log(stage: str, percent: int, msg: str):
        if job_id:
            update_evaluation_job(job_id, stage=stage, progress_percent=percent)
            append_evaluation_job_log(job_id, "info", stage, msg)

    # Stage 1
    _log("stage1_segmentation", 20, "正在分析视频时序结构，识别各步骤起止时间...")
    segments, detected_duration = await run_temporal_segmentation(
        api_config, sop, user_video_data_url, user_video_fps
    )
    segments = ensure_step_segments(sop, segments, user_video_path)

    # Stage 2
    total_steps = len(sop.steps)
    _log("stage2_step_eval", 35, f"时序分析完成，开始逐步精细评估（共 {total_steps} 步）...")

    def on_step_done(step_no: int, total: int):
        percent = 35 + int((step_no / total) * 40)
        if job_id:
            update_evaluation_job(job_id, stage="stage2_step_eval", progress_percent=percent)
            append_evaluation_job_log(
                job_id, "info", "stage2_step_eval", f"步骤 {step_no}/{total} 评估完成"
            )

    step_results = await run_per_step_evaluation_batch(
        api_config, sop, segments, user_video_path, user_video_data_url, user_video_fps, on_step_done
    )

    # Stage 3
    _log("stage3_validation", 80, "逐步评估完成，正在进行全局顺序校验...")
    global_result = await run_global_validation(api_config, sop, step_results, segments)
    step_results = apply_global_validation_overrides(step_results, global_result)

    # Merge step results into the global structure
    merged = {
        **global_result,
        "stepResults": step_results,
    }

    # Apply rule-based post-processing with SOP-specific penalties
    penalty_config = sop.penaltyConfig or None
    result = post_process_evaluation_result(sop, merged, penalty_config=penalty_config)
    return result, segments, detected_duration


async def run_sop_evaluation(
    api_config: ApiConfig,
    sop: SopData,
    user_video_data_url: str,
    job_id: Optional[str] = None,
) -> dict:
    """Main entry point for SOP evaluation (3-stage pipeline)."""
    if not api_config.apiKey or not api_config.apiKey.strip():
        raise HTTPException(status_code=400, detail="请先配置 API Key")
    if not sop.steps:
        raise HTTPException(status_code=400, detail="当前 SOP 缺少预处理后的参考数据")

    temp_user_video = None
    try:
        temp_user_video = data_url_to_temp_path(user_video_data_url)
        user_video_meta = read_video_meta(temp_user_video)
        user_video_fps = choose_analysis_fps(api_config.fps, user_video_meta.get("fps"))

        result, segments, detected_duration = await _run_multistage_evaluation(
            api_config, sop, temp_user_video, user_video_data_url, user_video_fps, job_id=job_id
        )

        overview_duration = detected_duration or user_video_meta.get("durationSec")
        result["segmentPreview"] = [
            {"stepNo": k, **v} for k, v in segments.items()
        ] if segments else []
        result["overviewPreview"] = {
            "mode": "multistage",
            "durationSec": overview_duration,
            "fps": user_video_meta.get("fps"),
        }
        return result
    finally:
        cleanup_file(temp_user_video)


# ── History helpers ────────────────────────────────────────────

def build_history_record_from_result(sop_record: dict, uploaded_video: dict, evaluation: dict):
    record_id = f"history-{int(time.time() * 1000)}"
    return {
        "id": record_id,
        "createdAtMs": int(time.time() * 1000),
        "taskId": sop_record.get("id"),
        "taskName": sop_record.get("name"),
        "scene": sop_record.get("scene"),
        "finishTime": now_display(),
        "score": evaluation.get("score"),
        "status": "passed" if evaluation.get("passed") else "failed",
        "manualReview": None,
        "detail": {
            "feedback": evaluation.get("feedback") or "",
            "issues": evaluation.get("issues") or [],
            "sequenceAssessment": evaluation.get("sequenceAssessment") or "",
            "prerequisiteViolated": bool(evaluation.get("prerequisiteViolated")),
            "stepResults": evaluation.get("stepResults") or [],
            "segmentPreview": evaluation.get("segmentPreview") or [],
            "overviewPreview": evaluation.get("overviewPreview") or {},
            "sopSteps": [
                {
                    "stepNo": step.get("stepNo"),
                    "description": step.get("description") or "",
                    "videoName": (
                        (step.get("videoMeta") or {}).get("name")
                        if isinstance(step.get("videoMeta"), dict)
                        else ""
                    ),
                }
                for step in (sop_record.get("steps") or [])
            ],
            "uploadedVideo": uploaded_video,
            "payloadPreview": evaluation.get("payloadPreview"),
            "rawModelResult": evaluation.get("rawModelResult"),
        },
    }


def map_job_failure(error: Exception):
    detail = ""
    if isinstance(error, HTTPException):
        detail = str(error.detail or "").strip()
        status_code = int(error.status_code or 500)
        if "API Key" in detail:
            return "模型配置缺失，请联系管理员检查 API Key", detail
        if "decode" in detail.lower() or "data url" in detail.lower():
            return "上传视频无法解析，请重新上传有效视频文件", detail
        if "Cannot open the uploaded video" in detail or "Unable to extract keyframes" in detail:
            return "上传视频无法解析，请重新上传清晰有效的视频文件", detail
        if status_code == 408 or "timeout" in detail.lower():
            return "评测超时，请稍后重试", detail
        if status_code >= 500:
            return "模型服务异常，请稍后重试", detail
        return detail or "评测任务处理失败", detail
    detail = str(error).strip()
    if "timeout" in detail.lower():
        return "评测超时，请稍后重试", detail
    return "系统处理异常，请稍后重试", detail or traceback.format_exc(limit=3)


def process_evaluation_job(job_id: str):
    job = get_evaluation_job(job_id)
    if not job:
        return

    try:
        update_evaluation_job(
            job_id, stage="preparing_video", progress_percent=10, start_time=datetime.now()
        )
        append_evaluation_job_log(
            job_id, "info", "preparing_video", "已读取任务信息，准备加载视频与 SOP"
        )

        sop_record = get_sop(job.get("taskId"))
        if not sop_record:
            raise HTTPException(status_code=404, detail="SOP 不存在或已被删除")

        uploaded_video = job.get("uploadedVideo") or {}
        media_id = uploaded_video.get("mediaId")
        if not media_id:
            raise HTTPException(status_code=400, detail="任务缺少上传视频")

        media = get_media(media_id, current_user={"role": "admin"})
        if not media or not media.get("path"):
            raise HTTPException(status_code=404, detail="上传视频文件不存在")

        with open(media["path"], "rb") as file_obj:
            encoded = base64.b64encode(file_obj.read()).decode("utf-8")
        user_video_data_url = f"data:{media.get('type') or 'video/mp4'};base64,{encoded}"

        evaluation = asyncio.run(
            run_sop_evaluation(
                build_runtime_api_config(),
                build_sop_model_from_record(sop_record),
                user_video_data_url,
                job_id=job_id,
            )
        )

        update_evaluation_job(job_id, stage="parsing_result", progress_percent=90)
        append_evaluation_job_log(
            job_id, "info", "parsing_result", "模型响应已返回，正在整理结构化结果"
        )

        history_record = build_history_record_from_result(
            sop_record, serialize_uploaded_video(media), evaluation
        )
        saved_record = add_history(history_record, current_user={"id": job.get("userId")})

        update_evaluation_job(
            job_id,
            status="succeeded",
            stage="done",
            progress_percent=100,
            failure_reason="",
            failure_detail="",
            result_record_id=saved_record.get("id"),
            finish_time=datetime.now(),
        )
        append_evaluation_job_log(job_id, "info", "done", "评测完成，结果已写入历史记录")
    except Exception as exc:
        failure_reason, failure_detail = map_job_failure(exc)
        update_evaluation_job(
            job_id,
            status="failed",
            stage="error",
            failure_reason=failure_reason,
            failure_detail=failure_detail,
            finish_time=datetime.now(),
        )
        append_evaluation_job_log(job_id, "error", "error", f"任务失败：{failure_reason}")


def evaluation_job_worker_loop():
    while not JOB_WORKER_STOP_EVENT.is_set():
        try:
            job = claim_next_evaluation_job()
            if not job:
                JOB_WORKER_STOP_EVENT.wait(JOB_POLL_INTERVAL_SEC)
                continue
            process_evaluation_job(job.get("id"))
        except Exception:
            JOB_WORKER_STOP_EVENT.wait(JOB_POLL_INTERVAL_SEC)


def start_worker():
    global JOB_WORKER_THREAD
    if JOB_WORKER_THREAD and JOB_WORKER_THREAD.is_alive():
        return
    JOB_WORKER_STOP_EVENT.clear()
    JOB_WORKER_THREAD = threading.Thread(
        target=evaluation_job_worker_loop,
        name="evaluation-job-worker",
        daemon=True,
    )
    JOB_WORKER_THREAD.start()


def stop_worker():
    JOB_WORKER_STOP_EVENT.set()
    if JOB_WORKER_THREAD and JOB_WORKER_THREAD.is_alive():
        JOB_WORKER_THREAD.join(timeout=2)
