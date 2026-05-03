import time
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from .auth import (
        LoginRequest,
        LoginResponse,
        LogoutResponse,
        RegisterRequest,
        TOKEN_EXPIRES_IN,
        UpdateUserStatusRequest,
        create_access_token,
        get_current_user,
        require_admin,
        serialize_auth_user,
    )
    from .evaluation import (
        build_runtime_api_config,
        build_sop_model_from_record,
        build_text_only_reference_bundle,
        prepare_reference_bundle,
        rebuild_reference_bundle_from_video,
        run_sop_evaluation,
        segment_workflow_video,
        start_worker,
        stop_worker,
        store_demo_video_and_prepare_bundle,
    )
    from .models import (
        ApiConfig,
        EvaluationResultPayload,
        KeyMoment,
        SopData,
        SopStep,
        StepResultPayload,
    )
    from .scoring import (
        normalize_duration_limit,
        normalize_prerequisite_step_nos,
        normalize_step_type,
        normalize_step_weight,
        post_process_evaluation_result,
    )
    from .storage import (
        add_history,
        add_sop,
        attach_media,
        authenticate_user,
        build_stats,
        create_evaluation_job,
        create_user,
        create_user_session,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_sop,
        get_user_by_username,
        has_active_session,
        list_evaluation_jobs,
        list_history,
        list_sops,
        list_users,
        load_db,
        now_display,
        retry_evaluation_job,
        save_db,
        serialize_history,
        serialize_sop_detail,
        serialize_sop_summary,
        set_config,
        revoke_user_session,
        update_evaluation_job,
        update_manual_review,
        update_sop,
        update_user_status,
    )
    from .video import (
        ensure_browser_playable_video,
        split_data_url,
    )
except ImportError:
    from auth import (
        LoginRequest,
        LoginResponse,
        LogoutResponse,
        RegisterRequest,
        TOKEN_EXPIRES_IN,
        UpdateUserStatusRequest,
        create_access_token,
        get_current_user,
        require_admin,
        serialize_auth_user,
    )
    from evaluation import (
        build_runtime_api_config,
        build_sop_model_from_record,
        build_text_only_reference_bundle,
        prepare_reference_bundle,
        rebuild_reference_bundle_from_video,
        run_sop_evaluation,
        segment_workflow_video,
        start_worker,
        stop_worker,
        store_demo_video_and_prepare_bundle,
    )
    from models import (
        ApiConfig,
        EvaluationResultPayload,
        KeyMoment,
        SopData,
        SopStep,
        StepResultPayload,
    )
    from scoring import (
        normalize_duration_limit,
        normalize_prerequisite_step_nos,
        normalize_step_type,
        normalize_step_weight,
        post_process_evaluation_result,
    )
    from storage import (
        add_history,
        add_sop,
        attach_media,
        authenticate_user,
        build_stats,
        create_evaluation_job,
        create_user,
        create_user_session,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_sop,
        get_user_by_username,
        has_active_session,
        list_evaluation_jobs,
        list_history,
        list_sops,
        list_users,
        load_db,
        now_display,
        retry_evaluation_job,
        save_db,
        serialize_history,
        serialize_sop_detail,
        serialize_sop_summary,
        set_config,
        revoke_user_session,
        update_evaluation_job,
        update_manual_review,
        update_sop,
        update_user_status,
    )
    from video import (
        ensure_browser_playable_video,
        split_data_url,
    )

# ── App setup ──────────────────────────────────────────────────

app = FastAPI(title="SOP Video Evaluation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Route-specific request/response models ─────────────────────

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


class StepVideoMeta(BaseModel):
    name: str = ""
    type: str = ""
    size: Optional[int] = None
    lastModified: Optional[int] = None


class StepVideoInput(BaseModel):
    description: str
    stepType: str = "required"
    stepWeight: float = 1.0
    conditionText: str = ""
    prerequisiteStepNos: List[int] = Field(default_factory=list)
    minDurationSec: Optional[float] = None
    maxDurationSec: Optional[float] = None
    videoDataUrl: str = ""
    videoMeta: Optional[StepVideoMeta] = None


class CreateSopRequest(BaseModel):
    name: str
    scene: Optional[str] = None
    steps: List[StepVideoInput] = Field(default_factory=list)
    workflowVideoDataUrl: str = ""
    workflowVideoMeta: Optional[StepVideoMeta] = None
    penaltyConfig: Optional[dict] = None  # Phase 4: per-SOP penalty weights


class UpdateStepDemoVideoRequest(BaseModel):
    videoDataUrl: str
    videoMeta: Optional[StepVideoMeta] = None


class ManualSegmentationRequest(BaseModel):
    timestamps: List[float] = Field(default_factory=list)


class UpdateStepReferenceMetadataRequest(BaseModel):
    referenceSummary: str = ""
    roiHint: str = ""
    substeps: List[KeyMoment] = Field(default_factory=list)


class StoredSopEvaluateRequest(BaseModel):
    userVideoDataUrl: str


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


# ── Helpers ────────────────────────────────────────────────────

def validate_sop_step_inputs(steps: List[StepVideoInput]):
    for index, raw_step in enumerate(steps):
        step_no = index + 1
        if not (raw_step.description or "").strip():
            raise HTTPException(status_code=400, detail=f"步骤 {step_no} 缺少文字描述")
        step_type = normalize_step_type(raw_step.stepType)
        condition_text = (raw_step.conditionText or "").strip()
        if step_type == "conditional" and not condition_text:
            raise HTTPException(
                status_code=400,
                detail=f"步骤 {step_no} 为条件触发步骤，必须填写触发说明",
            )
        min_duration = normalize_duration_limit(raw_step.minDurationSec)
        max_duration = normalize_duration_limit(raw_step.maxDurationSec)
        if (
            min_duration is not None
            and max_duration is not None
            and min_duration > max_duration
        ):
            raise HTTPException(
                status_code=400,
                detail=f"步骤 {step_no} 时间范围不合法，最短耗时不能大于最长耗时",
            )


# ── Startup / shutdown ─────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    start_worker()


@app.on_event("shutdown")
async def on_shutdown():
    stop_worker()


# ── Routes ─────────────────────────────────────────────────────

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
async def change_user_status(
    user_id: int, req: UpdateUserStatusRequest, current_user=Depends(require_admin)
):
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
async def update_step_demo_video(
    sop_id: str,
    step_no: int,
    req: UpdateStepDemoVideoRequest,
    current_user=Depends(require_admin),
):
    if not (req.videoDataUrl or "").strip():
        raise HTTPException(status_code=400, detail="请上传示范视频")

    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    step_record = next(
        (item for item in (sop.get("steps") or []) if int(item.get("stepNo") or 0) == step_no),
        None,
    )
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
async def update_step_segmentation(
    sop_id: str,
    step_no: int,
    req: ManualSegmentationRequest,
    _current_user=Depends(require_admin),
):
    # This endpoint is deprecated; the override endpoint below handles manual frame selection
    raise HTTPException(
        status_code=410,
        detail="该接口已停用，请改为上传步骤完整示范视频，由系统自动生成关键帧、关键时刻和 ROI",
    )


@app.put("/api/sops/{sop_id}/steps/{step_no}/manual-segmentation-override")
async def update_step_segmentation_override(
    sop_id: str,
    step_no: int,
    req: ManualSegmentationRequest,
    _current_user=Depends(require_admin),
):
    if not req.timestamps:
        raise HTTPException(status_code=400, detail="请至少提供一个时间点")

    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    step_record = next(
        (item for item in (sop.get("steps") or []) if int(item.get("stepNo") or 0) == step_no),
        None,
    )
    if not step_record:
        raise HTTPException(status_code=404, detail="步骤不存在")

    demo_video = step_record.get("demoVideo") or {}
    media_id = demo_video.get("mediaId")
    if not media_id:
        if step_record.get("referenceMode") == "video" or step_record.get("referenceFrames"):
            raise HTTPException(
                status_code=400,
                detail="该步骤已有参考帧，但原始示范视频引用缺失，请重新上传示范视频后再手动切帧",
            )
        raise HTTPException(status_code=400, detail="该步骤没有示范视频，无法手动切帧")

    media = get_media(media_id, current_user=_current_user)
    if not media:
        raise HTTPException(status_code=404, detail="示范视频文件不存在")

    bundle = rebuild_reference_bundle_from_video(
        media["path"], step_no, step_record.get("description") or "", req.timestamps
    )

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
                    "referenceSummary": item.get("referenceSummary") or bundle["referenceSummary"],
                    "referenceFeatures": bundle["referenceFeatures"],
                    "substeps": bundle["substeps"],
                    "roiHint": item.get("roiHint") or bundle["roiHint"],
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


@app.put("/api/sops/{sop_id}/steps/{step_no}/reference-metadata")
async def update_step_reference_metadata(
    sop_id: str,
    step_no: int,
    req: UpdateStepReferenceMetadataRequest,
    _current_user=Depends(require_admin),
):
    sop = get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    step_record = next(
        (item for item in (sop.get("steps") or []) if int(item.get("stepNo") or 0) == step_no),
        None,
    )
    if not step_record:
        raise HTTPException(status_code=404, detail="步骤不存在")

    normalized_substeps = []
    for index, item in enumerate(req.substeps):
        title = (item.title or "").strip() or f"关键时刻 {index + 1}"
        timestamp = round(max(0.0, float(item.timestampSec or 0)), 3)
        normalized_substeps.append({"title": title, "timestampSec": timestamp})
    normalized_substeps.sort(key=lambda item: item["timestampSec"])

    def apply_update(existing):
        updated_steps = []
        for item in existing.get("steps") or []:
            if int(item.get("stepNo") or 0) != step_no:
                updated_steps.append(item)
                continue
            updated_steps.append(
                {
                    **item,
                    "referenceSummary": (req.referenceSummary or "").strip(),
                    "roiHint": (req.roiHint or "").strip(),
                    "substeps": normalized_substeps,
                }
            )
        return {**existing, "steps": updated_steps}

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
    validate_sop_step_inputs(req.steps)
    if not (req.workflowVideoDataUrl or "").strip():
        raise HTTPException(status_code=400, detail="请上传整个流程的完整示范视频")

    api_config = build_runtime_api_config()
    step_items = []
    warnings = []
    data = load_db()
    sop_id = f"sop-{int(time.time() * 1000)}"

    if not api_config.apiKey.strip():
        warnings.append("后端未配置 API Key，本次已回退为均匀抽帧预处理。")

    # Phase 3: pre-segment the workflow demo video once before per-step processing
    step_dicts = [
        {"stepNo": i + 1, "description": (step.description or "").strip()}
        for i, step in enumerate(req.steps)
    ]
    workflow_segments: dict = {}
    if (req.workflowVideoDataUrl or "").strip() and api_config.apiKey.strip():
        try:
            workflow_segments = await segment_workflow_video(
                api_config, step_dicts, req.workflowVideoDataUrl
            )
            if workflow_segments:
                detected = sum(1 for v in workflow_segments.values() if v.get("detected"))
                warnings.append(
                    f"整体时序预分析完成，已识别 {detected}/{len(req.steps)} 个步骤的大致时间范围，"
                    "将按此范围提取各步关键帧。"
                )
        except Exception:
            workflow_segments = {}

    for index, step in enumerate(req.steps):
        step_no = index + 1
        description = step.description.strip()
        demo_video = None

        if (req.workflowVideoDataUrl or "").strip():
            seg = workflow_segments.get(step_no, {})
            start_sec = seg.get("startSec") if seg.get("detected") else 0
            end_sec = seg.get("endSec") if seg.get("detected") else None

            demo_video, bundle = await store_demo_video_and_prepare_bundle(
                data=data,
                api_config=api_config,
                sop_id=sop_id,
                step_no=step_no,
                description=(
                    f"该步骤是第 {step_no} 步：{description}。"
                    + (
                        f"时序分析已识别本步在视频中的时间范围约为 {start_sec:.1f}s - {end_sec:.1f}s，"
                        "请重点关注该区间内的内容提取关键帧、关键时刻和 ROI。"
                        if end_sec is not None
                        else f"全部步骤：{'; '.join([f'{i+1}.{s.description}' for i, s in enumerate(req.steps)])}。"
                        "请提取该步骤相关的关键帧、关键时刻和 ROI。"
                    )
                ),
                video_data_url=req.workflowVideoDataUrl,
                video_meta=req.workflowVideoMeta,
                uploaded_by=current_user,
                start_sec=float(start_sec or 0),
                end_sec=end_sec,
            )
        else:
            bundle = build_text_only_reference_bundle(step_no, description)
            warnings.append(f"步骤 {step_no} 未上传示范视频，将仅基于文字 SOP 评估。")

        step_items.append(
            {
                "stepNo": step_no,
                "description": description,
                "videoMeta": req.workflowVideoMeta.model_dump() if req.workflowVideoMeta else None,
                "demoVideo": demo_video,
                "stepType": normalize_step_type(step.stepType),
                "stepWeight": normalize_step_weight(step.stepWeight),
                "conditionText": (step.conditionText or "").strip(),
                "prerequisiteStepNos": normalize_prerequisite_step_nos(
                    step.prerequisiteStepNos, step_no
                ),
                "minDurationSec": normalize_duration_limit(step.minDurationSec),
                "maxDurationSec": normalize_duration_limit(step.maxDurationSec),
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
        "penaltyConfig": req.penaltyConfig or None,  # Phase 4
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
async def evaluate_sop(
    sop_id: str, req: StoredSopEvaluateRequest, _current_user=Depends(get_current_user)
):
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
async def create_sop_evaluation_job(
    sop_id: str, req: CreateEvaluationJobRequest, current_user=Depends(get_current_user)
):
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
        original_name=normalized_video["name"]
        or ((req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video"),
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
async def fetch_evaluation_jobs(
    status: Optional[str] = None, current_user=Depends(get_current_user)
):
    return {
        "success": True,
        "data": list_evaluation_jobs(
            current_user=current_user, status=(status or "").strip() or None
        ),
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
async def fetch_history(
    keyword: Optional[str] = None,
    aiStatus: Optional[str] = None,
    reviewStatus: Optional[str] = None,
    sortOrder: Optional[str] = "desc",
    current_user=Depends(get_current_user),
):
    keyword = (keyword or "").strip() or None
    ai_status = (aiStatus or "").strip() or None
    review_status = (reviewStatus or "").strip() or None
    sort_order = ((sortOrder or "desc").strip() or "desc").lower()

    if ai_status not in (None, "passed", "failed"):
        raise HTTPException(status_code=400, detail="AI 状态筛选参数不合法")
    if review_status not in (None, "pending", "approved", "rejected", "needs_attention"):
        raise HTTPException(status_code=400, detail="人工复核筛选参数不合法")
    if sort_order not in ("desc", "asc"):
        raise HTTPException(status_code=400, detail="排序参数不合法")

    return {
        "success": True,
        "data": [
            serialize_history(item)
            for item in list_history(
                current_user=current_user,
                keyword=keyword,
                ai_status=ai_status,
                review_status=review_status,
                sort_order=sort_order,
            )
        ],
    }


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
            original_name=normalized_video["name"]
            or ((req.uploadedVideo.name if req.uploadedVideo else "") or "uploaded-video"),
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
                    "videoName": (
                        (step.get("videoMeta") or {}).get("name")
                        if isinstance(step.get("videoMeta"), dict)
                        else ""
                    ),
                }
                for step in (sop.get("steps") or [])
            ],
            "uploadedVideo": uploaded_video,
        },
    }
    add_history(record, current_user=current_user)
    return {"success": True, "data": serialize_history(record)}


@app.put("/api/history/{record_id}/review")
async def review_history(
    record_id: str, req: ManualReviewRequest, current_user=Depends(require_admin)
):
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
    return FileResponse(
        path=media["path"],
        media_type=media.get("type") or "application/octet-stream",
        filename=media.get("name") or None,
    )


@app.post("/api/prepare-step-video")
async def prepare_step_video(
    req: PrepareStepVideoRequest, _current_user=Depends(require_admin)
):
    try:
        bundle = await prepare_reference_bundle(
            step_no=req.stepNo,
            description=req.description,
            video_data_url=req.videoDataUrl,
            max_frames=req.maxFrames,
            api_config=req.apiConfig,
        )
        return {"success": True, "data": bundle}
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
