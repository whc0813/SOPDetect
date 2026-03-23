import base64
import json
import os
import tempfile
from typing import List, Optional

import cv2
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="SOP Video Evaluation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiConfig(BaseModel):
    apiKey: str = ""
    baseURL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-plus"
    fps: float = 2
    temperature: float = 0.1
    timeoutMs: int = 120000


class KeyMoment(BaseModel):
    title: str
    timestampSec: float


class StepFeatures(BaseModel):
    durationSec: float = 0
    fps: float = 0
    frameCount: int = 0
    sampleTimestamps: List[float] = Field(default_factory=list)


class SopStep(BaseModel):
    stepNo: int
    description: str
    referenceFrames: List[str] = Field(default_factory=list)
    referenceSummary: str = ""
    referenceFeatures: Optional[StepFeatures] = None
    substeps: List[KeyMoment] = Field(default_factory=list)
    roiHint: str = ""


class SopData(BaseModel):
    name: str
    scene: Optional[str] = None
    stepCount: int
    steps: List[SopStep] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    apiConfig: ApiConfig
    sop: SopData
    userVideoDataUrl: str


class PrepareStepVideoRequest(BaseModel):
    stepNo: int
    description: str
    videoDataUrl: str
    maxFrames: int = 4
    apiConfig: Optional[ApiConfig] = None


class AIReferencePlan(BaseModel):
    stepSummary: str
    roiHint: str
    keyMoments: List[KeyMoment] = Field(default_factory=list)


def split_data_url(data_url: str):
    if not data_url or "," not in data_url:
        raise HTTPException(status_code=400, detail="Invalid data URL")

    header, encoded = data_url.split(",", 1)
    if not header.startswith("data:"):
        raise HTTPException(status_code=400, detail="Invalid data URL")

    mime_type = header[5:].split(";")[0] or "application/octet-stream"
    try:
        binary = base64.b64decode(encoded)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Failed to decode media payload") from exc

    return mime_type, binary


def infer_suffix(mime_type: str):
    mapping = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "video/x-msvideo": ".avi",
        "video/avi": ".avi",
    }
    return mapping.get(mime_type, ".mp4")


def data_url_to_temp_path(data_url: str):
    mime_type, binary = split_data_url(data_url)
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=infer_suffix(mime_type))
    try:
        handle.write(binary)
        handle.flush()
        return handle.name
    finally:
        handle.close()


def cleanup_file(path: Optional[str]):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def open_capture(video_path: str):
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        raise HTTPException(status_code=400, detail="Cannot open the uploaded video")
    return capture


def read_video_meta(video_path: str):
    capture = open_capture(video_path)
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration_sec = frame_count / fps if fps > 0 and frame_count > 0 else 0
        return {
            "fps": round(fps, 3) if fps > 0 else 0,
            "frameCount": frame_count,
            "durationSec": round(duration_sec, 3) if duration_sec > 0 else 0,
        }
    finally:
        capture.release()


def build_sample_timestamps(start_sec: float, end_sec: float, count: int):
    if count <= 0:
        return []

    safe_start = max(0.0, float(start_sec or 0))
    safe_end = max(safe_start, float(end_sec or safe_start))

    if safe_end - safe_start < 0.05:
        midpoint = round((safe_start + safe_end) / 2, 3)
        return [midpoint] * count

    gap = (safe_end - safe_start) / (count + 1)
    return [round(safe_start + gap * (index + 1), 3) for index in range(count)]


def normalize_timestamps(values: List[float], duration_sec: float, limit: int):
    cleaned = []
    for value in values:
        second = max(0.0, min(duration_sec, float(value)))
        if not cleaned or abs(cleaned[-1] - second) > 0.08:
            cleaned.append(round(second, 3))
    return cleaned[:limit]


def frame_to_data_url(frame, max_side: int = 320, jpeg_quality: int = 65):
    height, width = frame.shape[:2]
    longest = max(height, width)
    if longest > max_side:
        scale = max_side / float(longest)
        frame = cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode keyframe")
    encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def extract_frames(video_path: str, timestamps: List[float]):
    if not timestamps:
        return []

    capture = open_capture(video_path)
    frames = []
    try:
        for second in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(second)) * 1000)
            success, frame = capture.read()
            if not success or frame is None:
                continue
            frames.append(frame_to_data_url(frame))
    finally:
        capture.release()

    if not frames:
        raise HTTPException(status_code=400, detail="Unable to extract keyframes from video")
    return frames


def extract_analysis_samples(video_path: str, duration_sec: float):
    timestamps = build_sample_timestamps(0, duration_sec if duration_sec > 0 else 0.1, 10)
    frames = extract_frames(video_path, timestamps)
    return timestamps[: len(frames)], frames


def extract_json_from_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_part = next((item.get("text") for item in content if item.get("type") == "text" and item.get("text")), "")
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


async def call_chat_completion(api_config: ApiConfig, payload: dict):
    if not api_config.apiKey or not api_config.apiKey.strip():
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    base_url = api_config.baseURL.rstrip("/")
    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
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
            {
                "type": "text",
                "text": f"采样帧 {index + 1}，估计时间点 {timestamp:.2f} 秒。",
            }
        )
        content_blocks.append({"type": "image_url", "image_url": {"url": frame}})

    payload = {
        "model": api_config.model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 SOP 示范视频的预处理助手。"
                    "请始终返回符合给定 JSON Schema 的合法 JSON。"
                ),
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
    parsed = AIReferencePlan.model_validate(parse_json_content(raw_result.get("choices", [{}])[0].get("message", {}).get("content")))
    return parsed, raw_result


def build_reference_bundle(
    step_no: int,
    description: str,
    video_path: str,
    max_frames: int,
    ai_plan: Optional[AIReferencePlan] = None,
    analysis_samples: Optional[List[float]] = None,
):
    meta = read_video_meta(video_path)
    duration_sec = meta["durationSec"]

    candidate_timestamps = [item.timestampSec for item in ai_plan.keyMoments] if ai_plan and ai_plan.keyMoments else []
    if not candidate_timestamps:
        candidate_timestamps = build_sample_timestamps(0, duration_sec if duration_sec > 0 else 0.1, max_frames)

    timestamps = normalize_timestamps(candidate_timestamps, duration_sec if duration_sec > 0 else 0.1, max_frames)
    frames = extract_frames(video_path, timestamps)

    if ai_plan and ai_plan.stepSummary.strip():
        summary = ai_plan.stepSummary.strip()
    else:
        summary = f"步骤 {step_no}：{description}"

    substeps = []
    if ai_plan:
        for item in ai_plan.keyMoments[:max_frames]:
            substeps.append({"title": item.title, "timestampSec": round(item.timestampSec, 3)})

    return {
        "referenceFrames": frames,
        "referenceSummary": summary,
        "referenceFeatures": {
            "durationSec": duration_sec,
            "fps": meta["fps"],
            "frameCount": meta["frameCount"],
            "sampleTimestamps": timestamps[: len(frames)],
        },
        "substeps": substeps,
        "roiHint": ai_plan.roiHint if ai_plan and ai_plan.roiHint else "",
        "analysisSampleTimestamps": analysis_samples or [],
    }


def build_user_segments(video_path: str, step_count: int, frames_per_segment: int = 2):
    if step_count <= 0:
        raise HTTPException(status_code=400, detail="步骤数量必须大于 0")

    meta = read_video_meta(video_path)
    duration_sec = meta["durationSec"]
    if duration_sec <= 0:
        raise HTTPException(status_code=400, detail="Unable to read uploaded user video duration")

    segment_duration = duration_sec / step_count
    segments = []

    for index in range(step_count):
        start_sec = round(segment_duration * index, 3)
        end_sec = round(duration_sec if index == step_count - 1 else segment_duration * (index + 1), 3)
        timestamps = build_sample_timestamps(start_sec, end_sec, frames_per_segment)
        frames = extract_frames(video_path, timestamps)
        segments.append(
            {
                "stepNo": index + 1,
                "startSec": start_sec,
                "endSec": end_sec,
                "keyframes": frames,
                "sampleTimestamps": timestamps[: len(frames)],
            }
        )

    return segments


def build_evaluation_system_prompt():
    return (
        "你是一个严格的 SOP 执行评估助手。"
        "你的任务不是只判断用户“做没做”，还要判断是否按正确顺序、正确意图、正确完整度、安全地完成了整个流程。"
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
        "- evidence 必须点明你为什么这样判断，必要时明确写出“顺序颠倒”“过早执行”“延后执行”“证据不足”等。\n"
        "只返回合法 JSON，不要输出任何额外解释。"
    )


def build_evaluation_overview_text(sop: SopData):
    step_order_text = " -> ".join([f"{step.stepNo}:{step.description}" for step in sop.steps]) or "无"
    return (
        "请从全流程视角评估用户的 SOP 执行情况。\n"
        f"SOP 名称：{sop.name}\n"
        f"适用场景：{sop.scene or '未提供'}\n"
        f"期望步骤顺序：{step_order_text}\n"
        "系统为了便于分析，把用户视频均匀切成了若干时间片段；这些片段只是辅助观察，不保证与真实步骤边界完全一致。\n"
        "因此你必须主动考虑这些实际情况：步骤颠倒、后一步抢跑、当前步骤被拖到后面、漏做前置步骤、重复操作、额外风险动作，以及证据不足无法确认完成。\n"
        "判断每一步时，请同时结合步骤说明、参考关键帧、可选的子步骤时间轴、用户对应片段关键帧，以及整个流程的全局顺序关系。\n"
        "不要把“看到了动作”直接等同于“该步骤正确完成”；要重点判断动作意图、执行顺序、完成度和前后依赖关系。\n"
        "只返回 JSON。"
    )


def build_content_blocks_legacy(sop: SopData, user_segments: List[dict]):
    blocks = [
        {
                "type": "text",
                "text": (
                    "请评估用户的 SOP 执行情况。\n"
                    f"SOP 名称：{sop.name}\n"
                    f"适用场景：{sop.scene or '未填写'}\n"
                    "系统已经把用户视频切成步骤级片段，每个片段只保留了少量关键帧。"
                    "请结合步骤说明、参考关键帧、可选的子步骤时间轴，以及用户对应片段的关键帧进行判断。"
                    "只返回 JSON，不要输出额外说明。"
                ),
            }
        ]

    segment_map = {item["stepNo"]: item for item in user_segments}

    for step in sop.steps:
        segment = segment_map.get(step.stepNo)
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
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"关注区域提示：{step.roiHint or '无'}\n"
                    f"参考子步骤时间点：{substeps_text}\n"
                    f"参考特征：{json.dumps((step.referenceFeatures.model_dump() if step.referenceFeatures else {}), ensure_ascii=False)}"
                ),
            }
        )

        for frame in step.referenceFrames[:6]:
            blocks.append({"type": "image_url", "image_url": {"url": frame}})

        if segment:
            blocks.append(
                {
                    "type": "text",
                    "text": (
                        f"下面是用户视频中与步骤 {step.stepNo} 对应的片段。"
                        f"时间范围：{segment['startSec']:.2f} 秒 - {segment['endSec']:.2f} 秒。"
                    ),
                }
            )
            for frame in segment["keyframes"][:3]:
                blocks.append({"type": "image_url", "image_url": {"url": frame}})

    return blocks


def build_content_blocks(sop: SopData, user_segments: List[dict]):
    blocks = [{"type": "text", "text": build_evaluation_overview_text(sop)}]
    segment_map = {item["stepNo"]: item for item in user_segments}

    for step in sop.steps:
        segment = segment_map.get(step.stepNo)
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
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"关注区域提示：{step.roiHint or '无'}\n"
                    f"参考子步骤时间点：{substeps_text}\n"
                    f"参考特征：{json.dumps((step.referenceFeatures.model_dump() if step.referenceFeatures else {}), ensure_ascii=False)}\n"
                    "请判断该步骤是否被正确执行、完整执行，并且出现在正确的流程顺序位置。"
                ),
            }
        )

        for frame in step.referenceFrames[:6]:
            blocks.append({"type": "image_url", "image_url": {"url": frame}})

        if segment:
            blocks.append(
                {
                    "type": "text",
                    "text": (
                        f"下面是用户视频中与预期步骤 {step.stepNo} 对应的分析片段\n"
                        f"片段时间范围：{segment['startSec']:.2f}s - {segment['endSec']:.2f}s\n"
                        "注意：这个片段只是分析辅助，不代表真实步骤边界。"
                        "如果该步骤动作明显出现得过早、过晚、跑到了别的顺序位置，或者当前片段证据不足，请在该步骤 evidence 和顶层 issues 中明确体现。"
                    ),
                }
            )
            for frame in segment["keyframes"][:3]:
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
                                "issueType": {
                                    "type": "string",
                                    "enum": ["正常", "缺失", "顺序颠倒", "过早执行", "延后执行", "重复操作", "动作错误", "部分完成", "证据不足", "前置条件缺失"],
                                },
                                "completionLevel": {
                                    "type": "string",
                                    "enum": ["完整", "部分完成", "未完成", "无法判断"],
                                },
                                "orderIssue": {"type": "boolean"},
                                "prerequisiteViolated": {"type": "boolean"},
                                "evidence": {"type": "string"},
                            },
                            "required": [
                                "stepNo",
                                "description",
                                "passed",
                                "score",
                                "confidence",
                                "issueType",
                                "completionLevel",
                                "orderIssue",
                                "prerequisiteViolated",
                                "evidence",
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
                    "stepResults",
                ],
            },
        },
    }


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


@app.post("/api/prepare-step-video")
async def prepare_step_video(req: PrepareStepVideoRequest):
    temp_path = None
    try:
        temp_path = data_url_to_temp_path(req.videoDataUrl)
        meta = read_video_meta(temp_path)
        analysis_timestamps, analysis_frames = extract_analysis_samples(temp_path, meta["durationSec"])
        ai_plan = None
        raw_ai_result = None

        if req.apiConfig and req.apiConfig.apiKey.strip():
            try:
                ai_plan, raw_ai_result = await build_ai_reference_plan(
                    req.apiConfig,
                    req.stepNo,
                    req.description,
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
            req.stepNo,
            req.description,
            temp_path,
            max(1, min(req.maxFrames, 8)),
            ai_plan=ai_plan,
            analysis_samples=analysis_timestamps,
        )

        return {
            "success": True,
            "data": {
                **bundle,
                "analysisFrames": analysis_frames,
                "aiUsed": bool(ai_plan),
                "rawAIResult": sanitize_payload(raw_ai_result) if raw_ai_result else None,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cleanup_file(temp_path)


@app.post("/api/evaluate")
async def evaluate(req: EvaluateRequest):
    if not req.apiConfig.apiKey or not req.apiConfig.apiKey.strip():
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    if not req.sop.steps:
        raise HTTPException(status_code=400, detail="当前 SOP 缺少预处理后的参考数据")

    for step in req.sop.steps:
        if not step.referenceFrames:
            raise HTTPException(status_code=400, detail=f"步骤 {step.stepNo} 缺少参考关键帧")

    temp_user_video = None
    try:
        temp_user_video = data_url_to_temp_path(req.userVideoDataUrl)
        user_segments = build_user_segments(temp_user_video, req.sop.stepCount, frames_per_segment=2)
        content_blocks = build_content_blocks(req.sop, user_segments)

        payload = {
            "model": req.apiConfig.model,
            "temperature": req.apiConfig.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一个 SOP 执行评估助手。"
                        "请根据参考关键帧、子步骤时间轴和用户片段关键帧判断该步骤是否合规完成。"
                        "只返回合法 JSON，不要输出额外解释。"
                    ),
                },
                {"role": "user", "content": content_blocks},
            ],
            "response_format": build_response_schema(req.sop.stepCount),
        }
        payload["messages"][0]["content"] = build_evaluation_system_prompt()

        raw_json = await call_chat_completion(req.apiConfig, payload)
        return {
            "success": True,
            "data": raw_json,
            "payloadPreview": sanitize_payload(payload),
            "segmentPreview": user_segments,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cleanup_file(temp_user_video)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
