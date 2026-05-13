import time
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from . import preparation
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
        ConfirmSegmentationRequest,
        EvaluationResultPayload,
        KeyMoment,
        PreparationJobResponse,
        RetryStepRequest,
        SegmentItem,
        SopData,
        SopStep,
        StepResultPayload,
    )
    from .scoring import (
        normalize_duration_limit,
        normalize_prerequisite_step_nos,
        normalize_step_type,
        post_process_evaluation_result,
    )
    from .storage import (
        add_history,
        add_sop,
        attach_media,
        authenticate_user,
        build_stats,
        create_evaluation_job,
        create_preparation_job,
        create_user,
        create_user_session,
        delete_history,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_preparation_job,
        get_sop,
        get_user_by_username,
        has_active_session,
        list_evaluation_jobs,
        list_draft_sops_for_admin,
        list_history,
        list_sop_steps,
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
        update_preparation_job,
        update_preparation_step_state,
        mark_preparation_job_cancelled,
        update_sop,
        update_user_status,
        write_confirmed_segments,
        delete_preparation_job,
    )
    from .video import (
        ensure_browser_playable_video,
        split_data_url,
    )
except ImportError:
    import preparation
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
        ConfirmSegmentationRequest,
        EvaluationResultPayload,
        KeyMoment,
        PreparationJobResponse,
        RetryStepRequest,
        SegmentItem,
        SopData,
        SopStep,
        StepResultPayload,
    )
    from scoring import (
        normalize_duration_limit,
        normalize_prerequisite_step_nos,
        normalize_step_type,
        post_process_evaluation_result,
    )
    from storage import (
        add_history,
        add_sop,
        attach_media,
        authenticate_user,
        build_stats,
        create_evaluation_job,
        create_preparation_job,
        create_user,
        create_user_session,
        delete_history,
        delete_sop,
        get_config,
        get_evaluation_job,
        get_history,
        get_media,
        get_preparation_job,
        get_sop,
        get_user_by_username,
        has_active_session,
        list_evaluation_jobs,
        list_draft_sops_for_admin,
        list_history,
        list_sop_steps,
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
        update_preparation_job,
        update_preparation_step_state,
        mark_preparation_job_cancelled,
        update_sop,
        update_user_status,
        write_confirmed_segments,
        delete_preparation_job,
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


class UpdateSopRequest(BaseModel):
    name: Optional[str] = None
    scene: Optional[str] = None
    steps: Optional[List[StepVideoInput]] = None
    workflowVideoDataUrl: str = ""
    workflowVideoMeta: Optional[StepVideoMeta] = None


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


def _dump_model(model):
    if model is None:
        return None
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return model


def _serialize_preparation_job(job):
    if not job:
        return None
    metadata = job.get("metadata") or {}
    return {
        "id": job.get("id"),
        "sopId": job.get("sopCode") or job.get("sop_id"),
        "sopDbId": job.get("sop_id"),
        "status": job.get("status") or "",
        "phase": job.get("phase"),
        "progressMessage": job.get("progress_message"),
        "errorMessage": job.get("error_message"),
        "metadata": metadata,
        "workflowMediaId": job.get("workflow_media_id"),
        "createdAt": str(job.get("created_at") or ""),
        "updatedAt": str(job.get("updated_at") or ""),
    }


def _build_draft_sop(req: CreateSopRequest, current_user):
    sop_id = f"sop-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"
    steps = []
    for index, step in enumerate(req.steps):
        steps.append(
            {
                "stepNo": index + 1,
                "description": (step.description or "").strip(),
                "stepType": normalize_step_type(step.stepType),
                "conditionText": (step.conditionText or "").strip(),
                "prerequisiteStepNos": normalize_prerequisite_step_nos(
                    step.prerequisiteStepNos, index + 1
                ),
                "minDurationSec": normalize_duration_limit(step.minDurationSec),
                "maxDurationSec": normalize_duration_limit(step.maxDurationSec),
                "referenceMode": "text",
                "referenceFrames": [],
                "analysisFrames": [],
                "referenceSummary": "",
                "referenceFeatures": None,
                "substeps": [],
                "roiHint": "",
                "aiUsed": False,
                "rawAIResult": None,
            }
        )
    sop = {
        "id": sop_id,
        "name": (req.name or "").strip(),
        "scene": (req.scene or "").strip() or "未填写",
        "stepCount": len(steps),
        "demoVideoCount": 0,
        "createTime": now_display(),
        "createdAtMs": int(time.time() * 1000),
        "status": "draft",
        "steps": steps,
    }
    add_sop(sop, created_by=current_user)
    return sop_id, sop


def _create_preparation_job_for_sop(sop_id, sop, req: CreateSopRequest, current_user):
    metadata = {
        "workflowVideoDataUrl": req.workflowVideoDataUrl,
        "workflowVideoMeta": _dump_model(req.workflowVideoMeta) or {},
        "sopCode": sop_id,
        "sopName": sop.get("name") or "",
        "stepsMeta": [
            {"stepNo": item["stepNo"], "description": item.get("description") or ""}
            for item in sop.get("steps") or []
        ],
        "stepStates": {
            str(item["stepNo"]): {"status": "pending", "retry_count": 0}
            for item in sop.get("steps") or []
        },
        "createdBy": current_user or {},
    }
    return create_preparation_job(sop_id, metadata=metadata)


# ── Startup / shutdown ─────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    start_worker()
    preparation.start_preparation_worker()


@app.on_event("shutdown")
async def on_shutdown():
    stop_worker()
    preparation.stop_preparation_worker()


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
    if _current_user.get("role") != "admin" and sop.get("status") != "published":
        raise HTTPException(status_code=404, detail="SOP 不存在")
    return {"success": True, "data": serialize_sop_detail(sop)}


@app.get("/api/admin/sops/drafts")
async def fetch_admin_draft_sops(current_user=Depends(require_admin)):
    return {
        "success": True,
        "data": {"drafts": list_draft_sops_for_admin(current_user.get("id"))},
    }


@app.put("/api/sops/{sop_id}")
async def update_sop_basic(sop_id: str, req: UpdateSopRequest, current_user=Depends(require_admin)):
    existing = get_sop(sop_id)
    if not existing:
        raise HTTPException(status_code=404, detail="SOP 不存在")

    has_video = bool((req.workflowVideoDataUrl or "").strip())
    if has_video:
        steps = req.steps or [
            StepVideoInput(description=item.get("description") or "")
            for item in existing.get("steps") or []
        ]
        validate_sop_step_inputs(steps)
        draft_req = CreateSopRequest(
            name=req.name or existing.get("name") or "",
            scene=req.scene if req.scene is not None else existing.get("scene"),
            steps=steps,
            workflowVideoDataUrl=req.workflowVideoDataUrl,
            workflowVideoMeta=req.workflowVideoMeta,
        )

        def apply_draft(current):
            updated_steps = []
            for index, step in enumerate(steps):
                original = (current.get("steps") or [{}] * len(steps))[index] if index < len(current.get("steps") or []) else {}
                updated_steps.append(
                    {
                        **original,
                        "stepNo": index + 1,
                        "description": (step.description or "").strip(),
                        "stepType": normalize_step_type(step.stepType),
                        "conditionText": (step.conditionText or "").strip(),
                        "prerequisiteStepNos": normalize_prerequisite_step_nos(
                            step.prerequisiteStepNos, index + 1
                        ),
                        "minDurationSec": normalize_duration_limit(step.minDurationSec),
                        "maxDurationSec": normalize_duration_limit(step.maxDurationSec),
                        "referenceMode": "text",
                        "referenceFrames": [],
                        "analysisFrames": [],
                        "referenceSummary": "",
                        "referenceFeatures": None,
                        "substeps": [],
                        "roiHint": "",
                        "aiUsed": False,
                        "rawAIResult": None,
                    }
                )
            return {
                **current,
                "name": draft_req.name,
                "scene": draft_req.scene or "未填写",
                "stepCount": len(updated_steps),
                "demoVideoCount": 0,
                "status": "draft",
                "steps": updated_steps,
            }

        updated = update_sop(sop_id, apply_draft)
        job_id = _create_preparation_job_for_sop(sop_id, updated, draft_req, current_user)
        return {"success": True, "data": {"sopId": sop_id, "jobId": job_id, "status": "queued"}}

    def apply_metadata(current):
        return {
            **current,
            "name": (req.name if req.name is not None else current.get("name")) or "",
            "scene": (req.scene if req.scene is not None else current.get("scene")) or "未填写",
        }

    updated = update_sop(sop_id, apply_metadata)
    return {"success": True, "data": serialize_sop_detail(updated)}


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
    metadata = {
        "workflowVideoDataUrl": req.videoDataUrl,
        "workflowVideoMeta": _dump_model(req.videoMeta) or {},
        "sopCode": sop_id,
        "sopName": sop.get("name") or "",
        "stepsMeta": [
            {
                "stepNo": step_no,
                "description": step_record.get("description") or "",
            }
        ],
        "stepStates": {str(step_no): {"status": "pending", "retry_count": 0}},
        "replaceStepNo": step_no,
        "createdBy": current_user or {},
    }
    job_id = create_preparation_job(sop_id, metadata=metadata)
    return {"success": True, "data": {"sopId": sop_id, "jobId": job_id, "status": "queued"}}


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
                    "referenceSummary": bundle["referenceSummary"],
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

    sop_id, sop = _build_draft_sop(req, current_user)
    job_id = _create_preparation_job_for_sop(sop_id, sop, req, current_user)
    return {
        "success": True,
        "data": {"sopId": sop_id, "jobId": job_id, "status": "queued"},
    }


@app.get("/api/sop-preparation-jobs/{job_id}", response_model=PreparationJobResponse)
async def fetch_preparation_job(job_id: int, _current_user=Depends(require_admin)):
    job = get_preparation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="预处理任务不存在")
    return {"success": True, "data": _serialize_preparation_job(job)}


@app.post("/api/sop-preparation-jobs/{job_id}/confirm-segmentation", response_model=PreparationJobResponse)
async def confirm_preparation_segmentation(
    job_id: int,
    req: ConfirmSegmentationRequest,
    _current_user=Depends(require_admin),
):
    job = get_preparation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="预处理任务不存在")
    if job.get("status") not in ("awaiting_confirmation", "failed"):
        raise HTTPException(status_code=409, detail="当前状态不能确认分段")
    # 仅时序分割失败的 Job 可以手动卡边界兜底；processing_steps 阶段失败需先重试或取消
    if job.get("status") == "failed" and job.get("phase") == "processing_steps":
        raise HTTPException(status_code=409, detail="处理阶段失败请重试失败步骤或取消任务")
    metadata = job.get("metadata") or {}
    replace_step_no = metadata.get("replaceStepNo")
    if replace_step_no:
        target_no = int(replace_step_no)
        expected_step_nos = {target_no}
        step_count = 1
    else:
        sop_steps = list_sop_steps(job["sop_id"])
        if not sop_steps:
            raise HTTPException(status_code=400, detail="SOP 步骤数据缺失，无法校验分段")
        step_count = len(sop_steps)
        expected_step_nos = {int(row["step_no"]) for row in sop_steps}
    duration_sec = metadata.get("duration_sec") or metadata.get("durationSec") or 0
    try:
        segments = preparation.validate_confirmed_segments(
            req.segments,
            step_count,
            duration_sec,
            expected_step_nos=expected_step_nos,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    actual_step_nos = {int(item["stepNo"]) for item in segments}
    if actual_step_nos != expected_step_nos:
        missing = sorted(expected_step_nos - actual_step_nos)
        extra = sorted(actual_step_nos - expected_step_nos)
        details = []
        if missing:
            details.append(f"缺少步骤 {missing}")
        if extra:
            details.append(f"多余步骤 {extra}")
        raise HTTPException(status_code=400, detail="；".join(details))

    write_confirmed_segments(job["sop_id"], segments)
    step_states = {
        str(item["stepNo"]): {
            **((metadata.get("stepStates") or {}).get(str(item["stepNo"])) or {}),
            "status": "pending",
        }
        for item in segments
    }
    update_preparation_job(
        job_id,
        status="processing_steps",
        phase="processing_steps",
        progress_message="正在并发处理各步骤关键帧",
        error_message="",
        metadata_patch={"segments": segments, "stepStates": step_states},
    )
    return {"success": True, "data": _serialize_preparation_job(get_preparation_job(job_id))}


@app.post("/api/sop-preparation-jobs/{job_id}/retry-step", response_model=PreparationJobResponse)
async def retry_preparation_step(
    job_id: int,
    req: RetryStepRequest,
    _current_user=Depends(require_admin),
):
    job = get_preparation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="预处理任务不存在")
    metadata = job.get("metadata") or {}
    states = dict(metadata.get("stepStates") or {})
    key = str(req.stepNo)
    current = states.get(key)
    if current is None:
        raise HTTPException(status_code=404, detail=f"步骤 {req.stepNo} 不在此预处理任务中")
    if current.get("status") != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"步骤 {req.stepNo} 当前状态为 {current.get('status') or 'unknown'}，仅支持失败步骤重试",
        )
    states[key] = {
        **current,
        "status": "pending",
        "retry_count": int(current.get("retry_count") or 0) + 1,
        "error": "",
    }
    update_preparation_job(
        job_id,
        status="processing_steps",
        phase="processing_steps",
        progress_message=f"正在重试步骤 {req.stepNo}",
        error_message="",
        metadata_patch={"stepStates": states},
    )
    return {"success": True, "data": _serialize_preparation_job(get_preparation_job(job_id))}


@app.post("/api/sop-preparation-jobs/{job_id}/retry-segmentation", response_model=PreparationJobResponse)
async def retry_preparation_segmentation(job_id: int, _current_user=Depends(require_admin)):
    job = get_preparation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="预处理任务不存在")
    if job.get("status") != "failed":
        raise HTTPException(
            status_code=409,
            detail=f"当前状态 {job.get('status')} 不支持重试分段",
        )
    update_preparation_job(
        job_id,
        status="queued",
        phase="queued",
        progress_message="已重新进入时序分割队列",
        error_message="",
    )
    return {"success": True, "data": _serialize_preparation_job(get_preparation_job(job_id))}


@app.post("/api/sop-preparation-jobs/{job_id}/cancel")
async def cancel_preparation_job(job_id: int, _current_user=Depends(require_admin)):
    job = get_preparation_job(job_id)
    if not job:
        return {"success": True}
    sop = get_sop(job.get("sopCode") or "")
    if sop and sop.get("status") != "draft":
        raise HTTPException(status_code=400, detail="只能取消草稿 SOP 的预处理任务")
    # 软删：先标记 cancelled，让 worker 在每次写库前自行退出，再做真正清理。
    mark_preparation_job_cancelled(job_id)
    sop_code = job.get("sopCode")
    delete_preparation_job(job_id)
    if sop_code:
        delete_sop(sop_code)
    return {"success": True}


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
    if not sop_record or sop_record.get("status") != "published":
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
    if not sop or sop.get("status") != "published":
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


@app.delete("/api/history/{record_id}")
async def remove_history(record_id: str, _current_user=Depends(require_admin)):
    if not delete_history(record_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True}


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
