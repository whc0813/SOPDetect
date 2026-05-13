"""SOP 视频预处理 Worker：异步 Job + 人工确认时间边界."""
import asyncio
import logging
import os
import threading
from typing import Iterable

try:
    from . import storage
    from .evaluation import (
        build_runtime_api_config,
        prepare_reference_bundle,
        segment_workflow_video,
    )
    from .video import (
        build_data_url,
        data_url_to_temp_path,
        ensure_browser_playable_video,
        read_video_meta,
        split_data_url,
        cleanup_file,
    )
except ImportError:
    import storage
    from evaluation import (
        build_runtime_api_config,
        prepare_reference_bundle,
        segment_workflow_video,
    )
    from video import (
        build_data_url,
        data_url_to_temp_path,
        ensure_browser_playable_video,
        read_video_meta,
        split_data_url,
        cleanup_file,
    )


logger = logging.getLogger("backend.preparation")

POLL_INTERVAL_SEC = float(os.getenv("PREPARATION_JOB_POLL_INTERVAL_SEC", "2"))
CONCURRENCY = int(os.getenv("PREPARATION_JOB_CONCURRENCY", "3"))
LLM_TIMEOUT_SEC = float(os.getenv("PREPARATION_LLM_TIMEOUT_SEC", "120"))
STALL_THRESHOLD_SEC = int(os.getenv("PREPARATION_STALL_THRESHOLD_SEC", "600"))

_WORKER_STOP_EVENT = threading.Event()
_WORKER_THREAD: threading.Thread | None = None


def is_worker_running() -> bool:
    return _WORKER_THREAD is not None and _WORKER_THREAD.is_alive()


def start_preparation_worker() -> None:
    global _WORKER_THREAD
    if is_worker_running():
        return
    try:
        recovered = storage.reset_stalled_preparation_jobs(STALL_THRESHOLD_SEC)
        if recovered:
            logger.warning("watchdog reset %d stalled preparation jobs", recovered)
    except Exception:
        logger.exception("preparation watchdog startup failed")
    _WORKER_STOP_EVENT.clear()
    _WORKER_THREAD = threading.Thread(
        target=_worker_loop,
        name="preparation-job-worker",
        daemon=True,
    )
    _WORKER_THREAD.start()


def stop_preparation_worker() -> None:
    global _WORKER_THREAD
    _WORKER_STOP_EVENT.set()
    if _WORKER_THREAD is not None:
        _WORKER_THREAD.join(timeout=2)
    _WORKER_THREAD = None


def _transition(
    job_id: int,
    *,
    status=None,
    phase=None,
    progress_message=None,
    error_message=None,
    metadata_patch=None,
) -> None:
    storage.update_preparation_job(
        job_id,
        status=status,
        phase=phase,
        progress_message=progress_message,
        error_message=error_message,
        metadata_patch=metadata_patch,
    )
    logger.info("preparation job %s -> status=%s phase=%s", job_id, status, phase)


def _worker_loop() -> None:
    while not _WORKER_STOP_EVENT.is_set():
        try:
            job = storage.pick_preparation_job(["queued", "processing_steps"])
            if not job:
                _WORKER_STOP_EVENT.wait(POLL_INTERVAL_SEC)
                continue
            asyncio.run(_process_job(job))
        except Exception:
            logger.exception("preparation worker loop failed")
            _WORKER_STOP_EVENT.wait(POLL_INTERVAL_SEC)


async def _process_job(job: dict) -> None:
    status = job.get("status")
    if status == "queued":
        await _run_segmenting_stage(job)
    elif status == "processing_steps":
        await _run_processing_steps(job)


def _step_no(segment) -> int:
    if hasattr(segment, "stepNo"):
        return int(segment.stepNo)
    return int(segment.get("stepNo") or segment.get("step_no") or 0)


def _segment_start(segment) -> float:
    if hasattr(segment, "startSec"):
        return float(segment.startSec)
    return float(segment.get("startSec", segment.get("start_sec", 0)) or 0)


def _segment_end(segment) -> float:
    if hasattr(segment, "endSec"):
        return float(segment.endSec)
    return float(segment.get("endSec", segment.get("end_sec", 0)) or 0)


def validate_confirmed_segments(segments: Iterable, step_count: int, duration_sec: float, expected_step_nos: set | None = None) -> list[dict]:
    normalized = []
    for segment in segments:
        step_no = _step_no(segment)
        start_sec = round(_segment_start(segment), 3)
        end_sec = round(_segment_end(segment), 3)
        if start_sec < 0 or end_sec < 0 or start_sec >= end_sec:
            raise ValueError(f"步骤 {step_no} 时间范围不合法")
        if duration_sec and end_sec > float(duration_sec) + 0.001:
            raise ValueError(f"步骤 {step_no} 超出视频时长")
        normalized.append({"stepNo": step_no, "startSec": start_sec, "endSec": end_sec})

    expected = expected_step_nos if expected_step_nos is not None else set(range(1, int(step_count or 0) + 1))
    actual = {item["stepNo"] for item in normalized}
    if actual != expected:
        raise ValueError("分段数量或步骤编号不完整")

    ordered = sorted(normalized, key=lambda item: item["startSec"])
    for prev, current in zip(ordered, ordered[1:]):
        if current["startSec"] < prev["endSec"]:
            raise ValueError("步骤时间范围存在重叠")
    return sorted(normalized, key=lambda item: item["stepNo"])


def _uniform_segments(steps_meta: list[dict], duration_sec: float) -> list[dict]:
    count = max(1, len(steps_meta))
    duration = max(float(duration_sec or count), float(count))
    width = duration / count
    segments = []
    for index, step in enumerate(steps_meta):
        start = round(index * width, 3)
        end = round(duration if index == count - 1 else (index + 1) * width, 3)
        segments.append(
            {
                "stepNo": int(step.get("stepNo") or index + 1),
                "startSec": start,
                "endSec": max(end, start + 0.5),
            }
        )
    return segments


def _normalize_ai_segments(raw_segments: dict, steps_meta: list[dict], duration_sec: float) -> list[dict]:
    fallback = {item["stepNo"]: item for item in _uniform_segments(steps_meta, duration_sec)}
    normalized = []
    for step in steps_meta:
        step_no = int(step.get("stepNo") or 0)
        raw = raw_segments.get(step_no) or {}
        if raw.get("detected") and raw.get("endSec") is not None:
            try:
                start_sec = max(0.0, float(raw.get("startSec") or 0))
                end_sec = min(float(duration_sec or raw.get("endSec")), float(raw.get("endSec")))
                if end_sec > start_sec:
                    normalized.append(
                        {
                            "stepNo": step_no,
                            "startSec": round(start_sec, 3),
                            "endSec": round(end_sec, 3),
                        }
                    )
                    continue
            except (TypeError, ValueError):
                pass
        normalized.append(dict(fallback[step_no]))
    return normalized


def _prepare_workflow_video(job: dict) -> tuple[str, float, dict]:
    metadata = job.get("metadata") or {}
    data_url = (metadata.get("workflowVideoDataUrl") or "").strip()
    if not data_url:
        raise ValueError("缺少完整示范视频")
    video_meta = metadata.get("workflowVideoMeta") or {}
    original_name = video_meta.get("name") or video_meta.get("originalName") or "workflow.mp4"
    mime_type, binary = split_data_url(data_url)
    normalized = ensure_browser_playable_video(mime_type, binary, original_name)
    normalized_data_url = build_data_url(normalized["mimeType"], normalized["binary"])
    demo_video = storage.attach_media(
        {},
        binary=normalized["binary"],
        mime_type=normalized["mimeType"],
        original_name=normalized["name"] or original_name,
        size=len(normalized["binary"]),
        last_modified=video_meta.get("lastModified"),
        owner_role="admin",
        business_type="sop_step_demo",
        # 注意：attach_media 内部用 _fetch_sop_row_by_code 解析此参数，
        # 期望接收 sop_code 字符串而非数字 PK；同时它会用此值做磁盘路径拼接
        # (sub_dir / sop_code)，传 int 会触发 'WindowsPath / int' TypeError。
        related_sop_id=job.get("sopCode") or metadata.get("sopCode"),
        uploaded_by=metadata.get("createdBy") or "admin",
    )
    temp_path = None
    try:
        temp_path = data_url_to_temp_path(normalized_data_url)
        duration_sec = read_video_meta(temp_path).get("durationSec") or 0
    finally:
        cleanup_file(temp_path)
    return normalized_data_url, float(duration_sec or 0), demo_video


def _job_was_cancelled(job_id: int) -> bool:
    """Worker 在做任何写入前调用，避免 cancel 之后还往已删 SOP 写入。"""
    current = storage.get_preparation_job(job_id)
    return current is None or current.get("status") == "cancelled"


async def _run_segmenting_stage(job: dict) -> None:
    job_id = job["id"]
    metadata = job.get("metadata") or {}
    steps_meta = metadata.get("stepsMeta") or []
    replace_step_no = metadata.get("replaceStepNo")
    try:
        if _job_was_cancelled(job_id):
            return
        _transition(job_id, status="preparing", phase="正在转码示范视频", progress_message="正在转码示范视频")
        video_data_url, duration_sec, workflow_media = _prepare_workflow_video(job)
        if _job_was_cancelled(job_id):
            return

        # 单步骤替换走轻量分支：不调用模型做整体时序分割，
        # 默认把整段视频作为该步骤的候选窗口，由管理员手动卡边界即可。
        if replace_step_no:
            target = int(replace_step_no)
            segments = [
                {
                    "stepNo": target,
                    "startSec": 0.0,
                    "endSec": round(float(duration_sec or 0), 3),
                }
            ]
            step_states = {str(target): {"status": "pending", "retry_count": 0}}
            _transition(
                job_id,
                status="awaiting_confirmation",
                phase="等待管理员确认时间窗",
                progress_message="请为该步骤确认时间边界",
                metadata_patch={
                    "workflowVideoDataUrl": video_data_url,
                    "workflowVideoDataUrlForPreview": video_data_url,
                    "workflowMedia": workflow_media,
                    "duration_sec": duration_sec,
                    "segments": segments,
                    "stepStates": step_states,
                },
                error_message="",
            )
            return

        _transition(
            job_id,
            status="segmenting",
            phase="调用模型识别步骤时间窗",
            progress_message="正在分析步骤时间边界",
            metadata_patch={
                "workflowVideoDataUrl": video_data_url,
                "workflowVideoDataUrlForPreview": video_data_url,
                "workflowMedia": workflow_media,
                "duration_sec": duration_sec,
            },
            error_message="",
        )
        api_config = build_runtime_api_config()
        raw_segments = await asyncio.wait_for(
            segment_workflow_video(api_config, steps_meta, video_data_url),
            timeout=LLM_TIMEOUT_SEC,
        )
        if _job_was_cancelled(job_id):
            return
        segments = _normalize_ai_segments(raw_segments, steps_meta, duration_sec)
        step_states = {str(item["stepNo"]): {"status": "pending", "retry_count": 0} for item in segments}
        _transition(
            job_id,
            status="awaiting_confirmation",
            phase="等待管理员确认时间窗",
            progress_message="请确认每个步骤的时间边界",
            metadata_patch={
                "segments": segments,
                "stepStates": step_states,
                "duration_sec": duration_sec,
            },
        )
    except Exception as exc:
        logger.exception("preparation segmenting failed for job %s", job_id)
        if _job_was_cancelled(job_id):
            return
        # 保留异常类型和首行信息便于管理员定位（不带 stack），同时给出兜底引导
        exc_summary = f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}" if str(exc) else type(exc).__name__
        _transition(
            job_id,
            status="failed",
            phase="segmenting",
            error_message=f"模型时序分割未能完成（{exc_summary}）。可重试，或直接在时间轴上手动卡边界后确认。",
            progress_message="时序分割失败，可手动卡边界继续",
        )


async def _process_single_step(job: dict, step: dict, segment: dict) -> dict:
    metadata = job.get("metadata") or {}
    description = step.get("description") or ""
    step_no = int(step.get("stepNo") or segment.get("stepNo") or 0)
    all_steps_text = "; ".join(
        f"{item.get('stepNo')}.{item.get('description')}" for item in metadata.get("stepsMeta") or []
    )
    return await prepare_reference_bundle(
        step_no=step_no,
        description=(
            f"该步骤是第 {step_no} 步：{description}。"
            f"全部步骤：{all_steps_text}。"
            f"管理员确认本步骤时间窗为 {segment.get('startSec'):.1f}s - {segment.get('endSec'):.1f}s。"
            "请只提取该时间窗内与本步骤相关的关键帧、关键时刻和 ROI。"
        ),
        video_data_url=metadata.get("workflowVideoDataUrl") or metadata.get("workflowVideoDataUrlForPreview") or "",
        max_frames=8,
        api_config=build_runtime_api_config(),
        start_sec=float(segment.get("startSec") or 0),
        end_sec=float(segment.get("endSec") or 0),
    )


async def _run_processing_steps(job: dict) -> None:
    job_id = job["id"]
    metadata = dict(job.get("metadata") or {})
    segments = metadata.get("segments") or []
    steps_meta = metadata.get("stepsMeta") or []
    step_states = dict(metadata.get("stepStates") or {})
    segment_by_step = {int(item.get("stepNo") or 0): item for item in segments}
    steps_by_no = {int(item.get("stepNo") or 0): item for item in steps_meta}
    pending_step_nos = [
        int(step_no)
        for step_no, state in step_states.items()
        if (state or {}).get("status") in {"pending", "retrying"}
    ]
    if not pending_step_nos:
        pending_step_nos = [int(item.get("stepNo") or 0) for item in steps_meta]

    semaphore = asyncio.Semaphore(max(1, CONCURRENCY))

    # 用独立锁保护"读最新 stepStates → 计算终态"的窗口；
    # 每步状态本身用 storage.update_preparation_step_state 原子写入，避免并发 read-modify-write。
    async def run_one(step_no: int):
        async with semaphore:
            if _job_was_cancelled(job_id):
                return
            prev = step_states.get(str(step_no)) or {}
            storage.update_preparation_step_state(
                job_id,
                step_no,
                {
                    **prev,
                    "status": "processing",
                    "error": "",
                },
            )
            step = steps_by_no.get(step_no) or {"stepNo": step_no, "description": ""}
            segment = segment_by_step.get(step_no)
            if not segment:
                raise ValueError(f"步骤 {step_no} 缺少时间窗")
            result = await _process_single_step(job, step, segment)
            if _job_was_cancelled(job_id):
                return
            storage.update_sop_step_reference_bundle(job["sop_id"], step_no, result)
            storage.update_preparation_step_state(
                job_id,
                step_no,
                {
                    **prev,
                    "status": "completed",
                    "usage": (result.get("rawAIResult") or {}).get("usage") or result.get("usage") or {},
                    "error": "",
                },
            )

    async def guarded(step_no: int):
        try:
            await run_one(step_no)
        except Exception as exc:
            logger.exception("preparation step %s failed for job %s", step_no, job_id)
            if _job_was_cancelled(job_id):
                return
            prev = step_states.get(str(step_no)) or {}
            storage.update_preparation_step_state(
                job_id,
                step_no,
                {
                    **prev,
                    "status": "failed",
                    "error": "处理失败，请稍后重试该步骤",
                    "retry_count": int(prev.get("retry_count") or 0),
                },
            )

    await asyncio.gather(*(guarded(step_no) for step_no in pending_step_nos))

    if _job_was_cancelled(job_id):
        return

    # 读取并发写入后的最新状态来判定终态
    refreshed = storage.get_preparation_job(job_id)
    final_states = (refreshed or {}).get("metadata", {}).get("stepStates") or {}
    if any((state or {}).get("status") == "failed" for state in final_states.values()):
        _transition(
            job_id,
            status="failed",
            phase="部分步骤处理失败",
            progress_message="部分步骤处理失败",
            error_message="部分步骤处理失败，请重试失败步骤",
        )
        return
    storage.publish_prepared_sop(job["sop_id"], job_id)
    _transition(
        job_id,
        status="completed",
        phase="SOP 已就绪",
        progress_message="SOP 已就绪",
    )
