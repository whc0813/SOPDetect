import asyncio
import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from datetime import datetime
from typing import List, Optional

import cv2
import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
try:
    from storage import (
        add_history,
        add_sop,
        authenticate_user,
        create_user,
        create_user_session,
        attach_media,
        append_evaluation_job_log,
        build_stats,
        claim_next_evaluation_job,
        create_evaluation_job,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_sop,
        get_user_by_id,
        get_user_by_username,
        has_active_session,
        is_user_session_active,
        list_evaluation_jobs,
        list_history,
        list_users,
        list_sops,
        load_db,
        now_display,
        retry_evaluation_job,
        save_db,
        serialize_history,
        serialize_uploaded_video,
        serialize_sop_detail,
        serialize_sop_summary,
        set_config,
        revoke_user_session,
        update_evaluation_job,
        update_sop,
        update_user_status,
        update_manual_review,
    )
except ModuleNotFoundError:
    from .storage import (
        add_history,
        add_sop,
        authenticate_user,
        create_user,
        create_user_session,
        attach_media,
        append_evaluation_job_log,
        build_stats,
        claim_next_evaluation_job,
        create_evaluation_job,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_sop,
        get_user_by_id,
        get_user_by_username,
        has_active_session,
        is_user_session_active,
        list_evaluation_jobs,
        list_history,
        list_users,
        list_sops,
        load_db,
        now_display,
        retry_evaluation_job,
        save_db,
        serialize_history,
        serialize_uploaded_video,
        serialize_sop_detail,
        serialize_sop_summary,
        set_config,
        revoke_user_session,
        update_evaluation_job,
        update_sop,
        update_user_status,
        update_manual_review,
    )

app = FastAPI(title="SOP Video Evaluation API")

TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "sop-eval-dev-secret")
TOKEN_EXPIRES_IN = int(os.getenv("AUTH_TOKEN_EXPIRES_IN", "28800"))
JOB_POLL_INTERVAL_SEC = float(os.getenv("EVALUATION_JOB_POLL_INTERVAL_SEC", "2"))
JOB_WORKER_STOP_EVENT = threading.Event()
JOB_WORKER_THREAD = None

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


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    user: dict


class RegisterRequest(BaseModel):
    username: str
    password: str
    displayName: str = ""


class UpdateUserStatusRequest(BaseModel):
    status: str


class LogoutResponse(BaseModel):
    success: bool = True


class PrepareStepVideoRequest(BaseModel):
    stepNo: int
    description: str
    videoDataUrl: str
    maxFrames: int = 4
    apiConfig: Optional[ApiConfig] = None


class StepVideoMeta(BaseModel):
    name: str = ""
    type: str = ""
    size: Optional[int] = None
    lastModified: Optional[int] = None


class StepVideoInput(BaseModel):
    description: str
    videoDataUrl: str = ""
    videoMeta: Optional[StepVideoMeta] = None


class CreateSopRequest(BaseModel):
    name: str
    scene: Optional[str] = None
    steps: List[StepVideoInput] = Field(default_factory=list)


class UpdateStepDemoVideoRequest(BaseModel):
    videoDataUrl: str
    videoMeta: Optional[StepVideoMeta] = None


class ManualSegmentationRequest(BaseModel):
    timestamps: List[float] = Field(default_factory=list)


class StoredSopEvaluateRequest(BaseModel):
    userVideoDataUrl: str


class StepResultPayload(BaseModel):
    stepNo: int
    description: str
    passed: bool
    score: float
    confidence: float
    issueType: str = ""
    completionLevel: str = ""
    orderIssue: bool = False
    prerequisiteViolated: bool = False
    evidence: str = ""


class EvaluationResultPayload(BaseModel):
    passed: bool
    score: float
    feedback: str
    issues: List[str] = Field(default_factory=list)
    sequenceAssessment: str = ""
    prerequisiteViolated: bool = False
    stepResults: List[StepResultPayload] = Field(default_factory=list)
    payloadPreview: Optional[dict] = None
    rawModelResult: Optional[dict] = None


class CreateHistoryRequest(BaseModel):
    taskId: str
    userVideoDataUrl: Optional[str] = None
    uploadedVideo: Optional[StepVideoMeta] = None
    evaluationResult: EvaluationResultPayload


class CreateEvaluationJobRequest(BaseModel):
    userVideoDataUrl: str
    uploadedVideo: Optional[StepVideoMeta] = None


class ManualReviewRequest(BaseModel):
    status: str
    note: str = ""
    reviewer: str = "管理员"


class AIReferencePlan(BaseModel):
    stepSummary: str
    roiHint: str
    keyMoments: List[KeyMoment] = Field(default_factory=list)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def create_access_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "sid": user["sessionId"],
        "exp": int(time.time()) + TOKEN_EXPIRES_IN,
    }
    payload_raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_part = _b64url_encode(payload_raw)
    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def parse_access_token(token: str) -> Optional[dict]:
    if not token or "." not in token:
        return None
    payload_part, signature_part = token.split(".", 1)
    expected_signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        actual_signature = _b64url_decode(signature_part)
    except Exception:
        return None
    if not hmac.compare_digest(expected_signature, actual_signature):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp") or 0) < int(time.time()):
        return None
    return payload


def get_current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    token = authorization.split(" ", 1)[1].strip()
    payload = parse_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录凭证无效或已过期")
    user = get_user_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在或已被禁用")
    if not is_user_session_active(user["id"], payload.get("sid")):
        raise HTTPException(status_code=401, detail="当前登录已失效，请重新登录")
    user["sessionId"] = payload.get("sid")
    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权限访问该资源")
    return current_user


def serialize_auth_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "displayName": user["displayName"],
        "status": user.get("status"),
    }


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


def build_data_url(mime_type: str, binary: bytes):
    encoded = base64.b64encode(binary).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def ensure_browser_playable_video(mime_type: str, binary: bytes, original_name: str = ""):
    if not str(mime_type or "").startswith("video/"):
        return {
            "mimeType": mime_type,
            "binary": binary,
            "name": original_name,
            "transcoded": False,
        }

    source_path = None
    output_path = None
    try:
        source_handle = tempfile.NamedTemporaryFile(delete=False, suffix=infer_suffix(mime_type))
        source_path = source_handle.name
        source_handle.write(binary)
        source_handle.flush()
        source_handle.close()

        output_handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        output_path = output_handle.name
        output_handle.close()

        ffmpeg_exe = get_ffmpeg_exe()
        command = [
            ffmpeg_exe,
            "-y",
            "-i",
            source_path,
            "-movflags",
            "+faststart",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            return {
                "mimeType": mime_type,
                "binary": binary,
                "name": original_name,
                "transcoded": False,
            }

        normalized_name = original_name or "video.mp4"
        normalized_name = f"{Path(normalized_name).stem or 'video'}.mp4"
        return {
            "mimeType": "video/mp4",
            "binary": Path(output_path).read_bytes(),
            "name": normalized_name,
            "transcoded": True,
        }
    except Exception:
        return {
            "mimeType": mime_type,
            "binary": binary,
            "name": original_name,
            "transcoded": False,
        }
    finally:
        cleanup_file(source_path)
        cleanup_file(output_path)


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


async def store_demo_video_and_prepare_bundle(
    data: dict,
    api_config: ApiConfig,
    sop_id: Optional[str],
    step_no: int,
    description: str,
    video_data_url: str,
    video_meta: Optional[StepVideoMeta],
    uploaded_by=None,
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
        original_name=normalized_video["name"] or ((video_meta.name if video_meta else "") or f"sop-step-{step_no}"),
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
    )
    return demo_video, bundle


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


def build_video_overview(video_path: str, max_frames: int = 6):
    meta = read_video_meta(video_path)
    duration_sec = meta["durationSec"]
    if duration_sec <= 0:
        raise HTTPException(status_code=400, detail="Unable to read uploaded user video duration")

    timestamps = build_sample_timestamps(0, duration_sec, max_frames)
    frames = extract_frames(video_path, timestamps)
    return {
        "durationSec": duration_sec,
        "timestamps": timestamps[: len(frames)],
        "frames": frames,
    }


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
        "- 当前输入里会直接提供整段用户测试视频；除非题面明确提供了用户视频关键帧，否则不要臆造“用户视频关键帧”“全局关键帧”“步骤片段”等不存在的证据形式。\n"
        "- 你必须严格区分“示范视频关键帧”和“用户测试视频”。如果 SOP 没有示范视频，只能说“仅基于文字 SOP + 用户测试视频”进行判断，不能让人误以为系统存在示范视频关键帧。\n"
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
        "如果 SOP 参考来源显示为“仅文字 SOP，无示范视频关键帧”，那么你只能基于文字 SOP 与整段用户测试视频判断，不代表系统存在示范视频关键帧。\n"
        "因此你必须主动考虑这些实际情况：步骤颠倒、后一步抢跑、当前步骤被拖到后面、漏做前置步骤、重复操作、额外风险动作，以及证据不足无法确认完成。\n"
        "判断每一步时，请同时结合步骤说明、参考关键帧、可选的子步骤时间轴，以及整段用户测试视频中的全流程顺序关系。\n"
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
                    "这是旧版的关键帧辅助评估输入。"
                    "请结合步骤说明、参考关键帧、可选的子步骤时间轴，以及提供的辅助片段内容进行判断。"
                    "只返回 JSON，不要输出额外说明。"
                ),
            }
        ]

    segment_map = {item["stepNo"]: item for item in user_segments}

    for step in sop.steps:
        segment = segment_map.get(step.stepNo)
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


def build_content_blocks(sop: SopData, user_video_data_url: str, user_video_fps: float):
    blocks = [{"type": "text", "text": build_evaluation_overview_text(sop)}]
    blocks.append(
        {
            "type": "text",
            "text": (
                "下面是整段用户测试视频。"
                "请直接基于完整视频判断各步骤是否出现、出现顺序是否正确、前置条件是否满足，以及是否存在延后执行、过早执行、缺失步骤等问题。"
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
                    f"参考摘要：{step.referenceSummary or '无'}\n"
                    f"关注区域提示：{step.roiHint or '无'}\n"
                    f"参考子步骤时间点：{substeps_text}\n"
                    f"参考特征：{json.dumps((step.referenceFeatures.model_dump() if step.referenceFeatures else {}), ensure_ascii=False)}\n"
                    f"参考模式：{'示范视频关键帧' if has_reference_frames else '仅文字 SOP，无示范视频'}\n"
                    "请判断该步骤是否被正确执行、完整执行，并且出现在正确的流程顺序位置。"
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


def build_runtime_api_config():
    return ApiConfig.model_validate(get_config())


def build_text_only_reference_bundle(step_no: int, description: str):
    return {
        "referenceFrames": [],
        "analysisFrames": [],
        "referenceSummary": f"仅基于文字 SOP 评估：{description}",
        "referenceFeatures": None,
        "substeps": [],
        "roiHint": "",
        "aiUsed": False,
        "rawAIResult": None,
    }


def build_sop_model_from_record(record: dict):
    steps = []
    for index, step in enumerate(record.get("steps") or []):
        steps.append(
            {
                "stepNo": step.get("stepNo") or index + 1,
                "description": step.get("description") or "",
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
        }
    )


async def prepare_reference_bundle(
    step_no: int,
    description: str,
    video_data_url: str,
    max_frames: int = 8,
    api_config: Optional[ApiConfig] = None,
):
    temp_path = None
    try:
        temp_path = data_url_to_temp_path(video_data_url)
        meta = read_video_meta(temp_path)
        analysis_timestamps, analysis_frames = extract_analysis_samples(temp_path, meta["durationSec"])
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


def rebuild_reference_bundle_from_video(
    video_path: str,
    step_no: int,
    description: str,
    timestamps: List[float],
):
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


async def run_sop_evaluation(api_config: ApiConfig, sop: SopData, user_video_data_url: str):
    if not api_config.apiKey or not api_config.apiKey.strip():
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    if not sop.steps:
        raise HTTPException(status_code=400, detail="当前 SOP 缺少预处理后的参考数据")

    temp_user_video = None
    try:
        temp_user_video = data_url_to_temp_path(user_video_data_url)
        user_video_meta = read_video_meta(temp_user_video)
        content_blocks = build_content_blocks(sop, user_video_data_url, api_config.fps or user_video_meta.get("fps") or 2)

        payload = {
            "model": api_config.model,
            "temperature": api_config.temperature,
            "messages": [
                {"role": "system", "content": build_evaluation_system_prompt()},
                {"role": "user", "content": content_blocks},
            ],
            "response_format": build_response_schema(sop.stepCount),
        }

        raw_json = await call_chat_completion(api_config, payload)
        parsed = EvaluationResultPayload.model_validate(
            parse_json_content(raw_json.get("choices", [{}])[0].get("message", {}).get("content"))
        )
        result = parsed.model_dump()
        result["payloadPreview"] = sanitize_payload(payload)
        result["rawModelResult"] = sanitize_payload(raw_json)
        result["segmentPreview"] = []
        result["overviewPreview"] = {
            "mode": "full_video",
            "durationSec": user_video_meta.get("durationSec"),
            "fps": user_video_meta.get("fps"),
        }
        return result
    finally:
        cleanup_file(temp_user_video)


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
            "sopSteps": [
                {
                    "stepNo": step.get("stepNo"),
                    "description": step.get("description") or "",
                    "videoName": (step.get("videoMeta") or {}).get("name") if isinstance(step.get("videoMeta"), dict) else "",
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
        update_evaluation_job(job_id, stage="preparing_video", progress_percent=18, start_time=datetime.now())
        append_evaluation_job_log(job_id, "info", "preparing_video", "已读取任务信息，准备加载视频与 SOP")

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

        update_evaluation_job(job_id, stage="building_prompt", progress_percent=35)
        append_evaluation_job_log(job_id, "info", "building_prompt", "已完成资源装载，正在构建评测上下文")

        update_evaluation_job(job_id, stage="calling_model", progress_percent=68)
        append_evaluation_job_log(job_id, "info", "calling_model", "正在调用多模态模型，请稍候")
        evaluation = asyncio.run(
            run_sop_evaluation(
                build_runtime_api_config(),
                build_sop_model_from_record(sop_record),
                user_video_data_url,
            )
        )

        update_evaluation_job(job_id, stage="parsing_result", progress_percent=86)
        append_evaluation_job_log(job_id, "info", "parsing_result", "模型响应已返回，正在整理结构化结果")

        history_record = build_history_record_from_result(sop_record, serialize_uploaded_video(media), evaluation)
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


@app.on_event("startup")
async def start_evaluation_job_worker():
    global JOB_WORKER_THREAD
    if JOB_WORKER_THREAD and JOB_WORKER_THREAD.is_alive():
        return
    JOB_WORKER_STOP_EVENT.clear()
    JOB_WORKER_THREAD = threading.Thread(target=evaluation_job_worker_loop, name="evaluation-job-worker", daemon=True)
    JOB_WORKER_THREAD.start()


@app.on_event("shutdown")
async def stop_evaluation_job_worker():
    JOB_WORKER_STOP_EVENT.set()
    if JOB_WORKER_THREAD and JOB_WORKER_THREAD.is_alive():
        JOB_WORKER_THREAD.join(timeout=2)


@app.get("/api/health")
async def health_check():
    return {"success": True}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    username = (req.username or "").strip()
    password = (req.password or "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = authenticate_user(username, password)
    if not user:
        existing_user = get_user_by_username(username)
        if existing_user and existing_user.get("status") == "disabled":
            raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")
        raise HTTPException(status_code=401, detail="账号或密码错误")

    if has_active_session(user["id"]):
        raise HTTPException(status_code=409, detail="该账号已在其他页面登录，请先退出当前会话")

    session_id = uuid.uuid4().hex
    user["sessionId"] = session_id
    access_token = create_access_token(user)
    create_user_session(user["id"], session_id)
    return {
        "success": True,
        "data": LoginResponse(
            accessToken=access_token,
            tokenType="Bearer",
            expiresIn=TOKEN_EXPIRES_IN,
            user=serialize_auth_user(user),
        ).model_dump(),
    }


@app.get("/api/auth/me")
async def fetch_current_auth_user(current_user=Depends(get_current_user)):
    return {"success": True, "data": serialize_auth_user(current_user)}


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    try:
        user = create_user(
            username=req.username,
            password=req.password,
            display_name=req.displayName,
            role="user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "data": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user["displayName"],
            "role": user["role"],
        },
        "message": "注册成功",
    }


@app.post("/api/auth/logout")
async def logout(current_user=Depends(get_current_user)):
    revoke_user_session(current_user.get("id"), current_user.get("sessionId"))
    return LogoutResponse().model_dump()


@app.get("/api/users")
async def fetch_users(_current_user=Depends(require_admin)):
    return {"success": True, "data": list_users()}


@app.put("/api/users/{user_id}/status")
async def change_user_status(user_id: int, req: UpdateUserStatusRequest, current_user=Depends(require_admin)):
    if current_user.get("id") == user_id and (req.status or "").strip() == "disabled":
        raise HTTPException(status_code=400, detail="不能禁用当前登录管理员")

    try:
        user = update_user_status(user_id, req.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {"success": True, "data": user}


@app.get("/api/config")
async def fetch_config(_current_user=Depends(require_admin)):
    return {"success": True, "data": get_config()}


@app.put("/api/config")
async def update_config(config: ApiConfig, _current_user=Depends(require_admin)):
    return {"success": True, "data": set_config(config.model_dump())}


@app.get("/api/sops")
async def fetch_sops(_current_user=Depends(get_current_user)):
    return {"success": True, "data": [serialize_sop_summary(item) for item in list_sops()]}


@app.get("/api/sops/{sop_id}")
async def fetch_sop_detail(sop_id: str, _current_user=Depends(get_current_user)):
    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return {"success": True, "data": serialize_sop_detail(sop)}


@app.put("/api/sops/{sop_id}/steps/{step_no}/demo-video")
async def update_step_demo_video(sop_id: str, step_no: int, req: UpdateStepDemoVideoRequest, current_user=Depends(require_admin)):
    if not (req.videoDataUrl or "").strip():
        raise HTTPException(status_code=400, detail="请上传示范视频")

    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    step_record = next((item for item in (sop.get("steps") or []) if int(item.get("stepNo") or 0) == step_no), None)
    if not step_record:
        raise HTTPException(status_code=404, detail="步骤不存在")

    api_config = build_runtime_api_config()
    data = load_db()
    demo_video, bundle = await store_demo_video_and_prepare_bundle(
        data=data,
        api_config=api_config,
        sop_id=sop_id,
        step_no=step_no,
        description=step_record.get("description") or "",
        video_data_url=req.videoDataUrl,
        video_meta=req.videoMeta,
        uploaded_by=current_user,
    )
    save_db(data)

    def apply_update(existing):
        updated_steps = []
        for item in existing.get("steps") or []:
            if int(item.get("stepNo") or 0) != step_no:
                updated_steps.append(item)
                continue
            updated_steps.append(
                {
                    **item,
                    "videoMeta": req.videoMeta.model_dump() if req.videoMeta else item.get("videoMeta"),
                    "demoVideo": demo_video,
                    "referenceMode": "video",
                    "referenceFrames": bundle["referenceFrames"],
                    "analysisFrames": bundle["analysisFrames"],
                    "referenceSummary": bundle["referenceSummary"],
                    "referenceFeatures": bundle["referenceFeatures"],
                    "substeps": bundle["substeps"],
                    "roiHint": bundle["roiHint"],
                    "aiUsed": bool(bundle["aiUsed"]),
                    "rawAIResult": bundle["rawAIResult"],
                }
            )
        return {
            **existing,
            "steps": updated_steps,
            "demoVideoCount": sum(1 for item in updated_steps if item.get("demoVideo")),
        }

    updated = update_sop(sop_id, apply_update)
    if not updated:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return {"success": True, "data": serialize_sop_detail(updated)}


@app.put("/api/sops/{sop_id}/steps/{step_no}/manual-segmentation")
async def update_step_segmentation(sop_id: str, step_no: int, req: ManualSegmentationRequest, _current_user=Depends(require_admin)):
    if not req.timestamps:
        raise HTTPException(status_code=400, detail="请至少提供一个时间点")

    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    step_record = next((item for item in (sop.get("steps") or []) if int(item.get("stepNo") or 0) == step_no), None)
    if not step_record:
        raise HTTPException(status_code=404, detail="步骤不存在")

    demo_video = step_record.get("demoVideo") or {}
    media_id = demo_video.get("mediaId")
    if not media_id:
        if step_record.get("referenceMode") == "video" or step_record.get("referenceFrames"):
            raise HTTPException(status_code=400, detail="该步骤已有参考帧，但原始示范视频引用缺失，请重新上传示范视频后再手动切帧")
        raise HTTPException(status_code=400, detail="该步骤没有示范视频，无法手动切帧")

    media = get_media(media_id, current_user=_current_user)
    if not media:
        raise HTTPException(status_code=404, detail="示范视频文件不存在")

    bundle = rebuild_reference_bundle_from_video(media["path"], step_no, step_record.get("description") or "", req.timestamps)

    def apply_update(existing):
        updated_steps = []
        for item in existing.get("steps") or []:
            if int(item.get("stepNo") or 0) != step_no:
                updated_steps.append(item)
                continue
            updated_steps.append(
                {
                    **item,
                    "referenceMode": "video",
                    "referenceFrames": bundle["referenceFrames"],
                    "analysisFrames": bundle["analysisFrames"],
                    "referenceSummary": bundle["referenceSummary"],
                    "referenceFeatures": bundle["referenceFeatures"],
                    "substeps": bundle["substeps"],
                    "roiHint": bundle["roiHint"],
                    "aiUsed": False,
                    "rawAIResult": None,
                }
            )
        return {
            **existing,
            "steps": updated_steps,
            "demoVideoCount": sum(1 for item in updated_steps if item.get("demoVideo")),
        }

    updated = update_sop(sop_id, apply_update)
    if not updated:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return {"success": True, "data": serialize_sop_detail(updated)}


@app.post("/api/sops")
async def create_sop(req: CreateSopRequest, current_user=Depends(require_admin)):
    name = (req.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请输入 SOP 名称")
    if not req.steps:
        raise HTTPException(status_code=400, detail="至少需要一个步骤")

    for index, step in enumerate(req.steps):
        if not (step.description or "").strip():
            raise HTTPException(status_code=400, detail=f"步骤 {index + 1} 缺少文字描述")

    api_config = build_runtime_api_config()
    step_items = []
    warnings = []
    data = load_db()
    sop_id = f"sop-{int(time.time() * 1000)}"
    if not api_config.apiKey.strip():
        warnings.append("后端未配置 API Key，本次已回退为均匀抽帧预处理。")

    for index, step in enumerate(req.steps):
        step_no = index + 1
        description = step.description.strip()
        demo_video = None

        if (step.videoDataUrl or "").strip():
            demo_video, bundle = await store_demo_video_and_prepare_bundle(
                data=data,
                api_config=api_config,
                sop_id=sop_id,
                step_no=step_no,
                description=description,
                video_data_url=step.videoDataUrl,
                video_meta=step.videoMeta,
                uploaded_by=current_user,
            )
        else:
            bundle = build_text_only_reference_bundle(step_no, description)
            warnings.append(f"步骤 {step_no} 未上传示范视频，将仅基于文字 SOP 评估。")

        step_items.append(
            {
                "stepNo": step_no,
                "description": description,
                "videoMeta": step.videoMeta.model_dump() if step.videoMeta else None,
                "demoVideo": demo_video,
                "referenceMode": "video" if bundle["referenceFrames"] else "text",
                "referenceFrames": bundle["referenceFrames"],
                "analysisFrames": bundle["analysisFrames"],
                "referenceSummary": bundle["referenceSummary"],
                "referenceFeatures": bundle["referenceFeatures"],
                "substeps": bundle["substeps"],
                "roiHint": bundle["roiHint"],
                "aiUsed": bool(bundle["aiUsed"]),
                "rawAIResult": bundle["rawAIResult"],
            }
        )

    save_db(data)
    sop = {
        "id": sop_id,
        "name": name,
        "scene": (req.scene or "").strip() or "未填写",
        "stepCount": len(step_items),
        "demoVideoCount": sum(1 for item in step_items if item.get("demoVideo")),
        "createTime": now_display(),
        "createdAtMs": int(time.time() * 1000),
        "steps": step_items,
    }
    add_sop(sop, created_by=current_user)
    return {
        "success": True,
        "data": serialize_sop_summary(sop),
        "warnings": warnings,
    }


@app.delete("/api/sops/{sop_id}")
async def remove_sop(sop_id: str, _current_user=Depends(require_admin)):
    if not delete_sop(sop_id):
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return {"success": True}


@app.post("/api/sops/{sop_id}/evaluate")
async def evaluate_sop(sop_id: str, req: StoredSopEvaluateRequest, _current_user=Depends(get_current_user)):
    sop_record = get_sop(sop_id)
    if not sop_record:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    result = await run_sop_evaluation(
        build_runtime_api_config(),
        build_sop_model_from_record(sop_record),
        req.userVideoDataUrl,
    )
    return {"success": True, "data": result}


@app.post("/api/sops/{sop_id}/evaluation-jobs")
async def create_sop_evaluation_job(sop_id: str, req: CreateEvaluationJobRequest, current_user=Depends(get_current_user)):
    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")
    if not (req.userVideoDataUrl or "").strip():
        raise HTTPException(status_code=400, detail="请先上传待评测视频")

    mime_type, binary = split_data_url(req.userVideoDataUrl)
    normalized_video = ensure_browser_playable_video(
        mime_type,
        binary,
        (req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video",
    )
    data = load_db()
    uploaded_video = attach_media(
        data,
        binary=normalized_video["binary"],
        mime_type=normalized_video["mimeType"],
        original_name=normalized_video["name"] or ((req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video"),
        size=len(normalized_video["binary"]),
        last_modified=req.uploadedVideo.lastModified if req.uploadedVideo else None,
        owner_role="user",
        business_type="evaluation_job_upload",
        related_sop_id=sop.get("id"),
        uploaded_by=current_user,
    )
    save_db(data)

    try:
        job = create_evaluation_job(sop.get("id"), uploaded_video, current_user=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "data": job}


@app.get("/api/evaluation-jobs")
async def fetch_evaluation_jobs(status: Optional[str] = None, current_user=Depends(get_current_user)):
    return {
        "success": True,
        "data": list_evaluation_jobs(current_user=current_user, status=(status or "").strip() or None),
    }


@app.get("/api/evaluation-jobs/{job_id}")
async def fetch_evaluation_job_detail(job_id: str, current_user=Depends(get_current_user)):
    job = get_evaluation_job(job_id, current_user=current_user)
    if not job:
        raise HTTPException(status_code=404, detail="评测任务不存在")
    return {"success": True, "data": job}


@app.post("/api/evaluation-jobs/{job_id}/retry")
async def retry_sop_evaluation_job(job_id: str, current_user=Depends(get_current_user)):
    try:
        job = retry_evaluation_job(job_id, current_user=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not job:
        raise HTTPException(status_code=404, detail="评测任务不存在")
    return {"success": True, "data": job}


@app.get("/api/history")
async def fetch_history(current_user=Depends(get_current_user)):
    return {"success": True, "data": [serialize_history(item) for item in list_history(current_user=current_user)]}


@app.get("/api/history/{record_id}")
async def fetch_history_detail(record_id: str, current_user=Depends(get_current_user)):
    record = get_history(record_id, current_user=current_user)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": serialize_history(record)}


@app.post("/api/history")
async def create_history(req: CreateHistoryRequest, current_user=Depends(get_current_user)):
    sop = get_sop(req.taskId)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    record_id = f"history-{int(time.time() * 1000)}"
    uploaded_video = None
    data = load_db()
    if req.userVideoDataUrl:
        mime_type, binary = split_data_url(req.userVideoDataUrl)
        normalized_video = ensure_browser_playable_video(
            mime_type,
            binary,
            (req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video",
        )
        uploaded_video = attach_media(
            data,
            binary=normalized_video["binary"],
            mime_type=normalized_video["mimeType"],
            original_name=normalized_video["name"] or ((req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video"),
            size=len(normalized_video["binary"]),
            last_modified=req.uploadedVideo.lastModified if req.uploadedVideo else None,
            owner_role="user",
            business_type="execution_upload",
            related_sop_id=sop.get("id"),
            related_execution_id=record_id,
            uploaded_by=current_user,
        )
        save_db(data)

    evaluation = req.evaluationResult.model_dump()
    record = {
        "id": record_id,
        "createdAtMs": int(time.time() * 1000),
        "taskId": sop.get("id"),
        "taskName": sop.get("name"),
        "scene": sop.get("scene"),
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
            "sopSteps": [
                {
                    "stepNo": step.get("stepNo"),
                    "description": step.get("description") or "",
                    "videoName": (step.get("videoMeta") or {}).get("name") if isinstance(step.get("videoMeta"), dict) else "",
                }
                for step in (sop.get("steps") or [])
            ],
            "uploadedVideo": uploaded_video,
        },
    }
    add_history(record, current_user=current_user)
    return {"success": True, "data": serialize_history(record)}


@app.put("/api/history/{record_id}/review")
async def review_history(record_id: str, req: ManualReviewRequest, current_user=Depends(require_admin)):
    review = {
        "status": req.status,
        "note": (req.note or "").strip(),
        "reviewer": (req.reviewer or "").strip() or "管理员",
        "reviewTime": now_display(),
    }
    updated = update_manual_review(record_id, review, current_user=current_user)
    if not updated:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": serialize_history(updated)}


@app.get("/api/stats")
async def fetch_stats(_current_user=Depends(require_admin)):
    return {"success": True, "data": build_stats()}


@app.get("/api/media/{media_id}")
async def fetch_media(media_id: str, current_user=Depends(get_current_user)):
    media = get_media(media_id, current_user=current_user)
    if not media:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    return FileResponse(path=media["path"], media_type=media.get("type") or "application/octet-stream", filename=media.get("name") or None)


@app.post("/api/prepare-step-video")
async def prepare_step_video(req: PrepareStepVideoRequest, _current_user=Depends(require_admin)):
    try:
        bundle = await prepare_reference_bundle(
            step_no=req.stepNo,
            description=req.description,
            video_data_url=req.videoDataUrl,
            max_frames=req.maxFrames,
            api_config=req.apiConfig,
        )
        return {
            "success": True,
            "data": bundle,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/evaluate")
async def evaluate(req: EvaluateRequest, _current_user=Depends(get_current_user)):
    try:
        result = await run_sop_evaluation(req.apiConfig, req.sop, req.userVideoDataUrl)
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
