import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import cv2
from fastapi import HTTPException
from imageio_ffmpeg import get_ffmpeg_exe


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
        return {"mimeType": mime_type, "binary": binary, "name": original_name, "transcoded": False}
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
            ffmpeg_exe, "-y", "-i", source_path,
            "-movflags", "+faststart",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            return {"mimeType": mime_type, "binary": binary, "name": original_name, "transcoded": False}
        normalized_name = original_name or "video.mp4"
        normalized_name = f"{Path(normalized_name).stem or 'video'}.mp4"
        return {
            "mimeType": "video/mp4",
            "binary": Path(output_path).read_bytes(),
            "name": normalized_name,
            "transcoded": True,
        }
    except Exception:
        return {"mimeType": mime_type, "binary": binary, "name": original_name, "transcoded": False}
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


def extract_analysis_samples(
    video_path: str,
    duration_sec: float,
    start_sec: float = 0,
    end_sec: Optional[float] = None,
    sample_count: int = 10,
):
    """Extract evenly-spaced analysis frames, optionally within a time range."""
    actual_start = max(0.0, float(start_sec or 0))
    actual_end = end_sec if end_sec is not None else duration_sec
    if duration_sec > 0:
        actual_end = min(actual_end, duration_sec)
    timestamps = build_sample_timestamps(actual_start, actual_end if actual_end > 0 else 0.1, sample_count)
    frames = extract_frames(video_path, timestamps)
    return timestamps[: len(frames)], frames


def build_reference_bundle(
    step_no: int,
    description: str,
    video_path: str,
    max_frames: int,
    ai_plan=None,
    analysis_samples: Optional[List[float]] = None,
):
    meta = read_video_meta(video_path)
    duration_sec = meta["durationSec"]
    safe_duration = duration_sec if duration_sec > 0 else 0.1

    candidate_timestamps = []
    if ai_plan and getattr(ai_plan, "keyMoments", None):
        candidate_timestamps = [
            float(item.timestampSec)
            for item in ai_plan.keyMoments
            if getattr(item, "timestampSec", None) is not None
        ]
    if not candidate_timestamps:
        candidate_timestamps = build_sample_timestamps(0, safe_duration, max_frames)

    timestamps = normalize_timestamps(candidate_timestamps, safe_duration, max_frames)
    frames = extract_frames(video_path, timestamps)

    summary = f"步骤 {step_no}：{description}"
    if ai_plan and str(getattr(ai_plan, "stepSummary", "")).strip():
        summary = str(ai_plan.stepSummary).strip()

    substeps = []
    if ai_plan and getattr(ai_plan, "keyMoments", None):
        for item in ai_plan.keyMoments[:max_frames]:
            title = str(getattr(item, "title", "") or "").strip()
            timestamp = getattr(item, "timestampSec", None)
            if timestamp is None:
                continue
            substeps.append({"title": title, "timestampSec": round(float(timestamp), 3)})

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
        "roiHint": str(getattr(ai_plan, "roiHint", "") or ""),
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
        end_sec = round(
            duration_sec if index == step_count - 1 else segment_duration * (index + 1), 3
        )
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
