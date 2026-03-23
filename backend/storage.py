import json
import mimetypes
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "db.json"
DB_LOCK = threading.Lock()

DEFAULT_CONFIG = {
    "apiKey": "",
    "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.5-plus",
    "fps": 2,
    "temperature": 0.1,
    "timeoutMs": 120000,
}


def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def default_db():
    return {
        "config": dict(DEFAULT_CONFIG),
        "sops": [],
        "history": [],
        "media": {},
    }


def now_display():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_db():
    ensure_storage()
    with DB_LOCK:
        if not DB_PATH.exists():
            data = default_db()
            DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data

        try:
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = default_db()

        data.setdefault("config", dict(DEFAULT_CONFIG))
        data.setdefault("sops", [])
        data.setdefault("history", [])
        data.setdefault("media", {})
        return data


def save_db(data):
    ensure_storage()
    with DB_LOCK:
        DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_config():
    data = load_db()
    config = dict(DEFAULT_CONFIG)
    config.update(data.get("config") or {})
    return config


def set_config(config):
    data = load_db()
    merged = dict(DEFAULT_CONFIG)
    merged.update(config or {})
    data["config"] = merged
    save_db(data)
    return merged


def list_sops():
    data = load_db()
    items = data.get("sops") or []
    return sorted(items, key=lambda item: item.get("createdAtMs", 0), reverse=True)


def get_sop(sop_id):
    for item in list_sops():
        if item.get("id") == sop_id:
            return item
    return None


def add_sop(sop):
    data = load_db()
    sops = data.setdefault("sops", [])
    sops.insert(0, sop)
    save_db(data)
    return sop


def update_sop(sop_id, updater):
    data = load_db()
    sops = data.setdefault("sops", [])
    for index, item in enumerate(sops):
        if item.get("id") != sop_id:
            continue
        updated = updater(item)
        sops[index] = updated
        save_db(data)
        return updated
    return None


def delete_sop(sop_id):
    data = load_db()
    sops = data.setdefault("sops", [])
    before = len(sops)
    data["sops"] = [item for item in sops if item.get("id") != sop_id]
    changed = len(data["sops"]) != before
    if changed:
        save_db(data)
    return changed


def list_history():
    data = load_db()
    items = data.get("history") or []
    return sorted(items, key=lambda item: item.get("createdAtMs", 0), reverse=True)


def get_history(record_id):
    for item in list_history():
        if str(item.get("id")) == str(record_id):
            return item
    return None


def add_history(record):
    data = load_db()
    history = data.setdefault("history", [])
    history.insert(0, record)
    save_db(data)
    return record


def update_manual_review(record_id, review):
    data = load_db()
    history = data.setdefault("history", [])
    for index, item in enumerate(history):
        if str(item.get("id")) != str(record_id):
            continue
        history[index] = {**item, "manualReview": review}
        save_db(data)
        return history[index]
    return None


def attach_media(data, binary, mime_type, original_name="", size=None, last_modified=None):
    ensure_storage()
    media_id = f"media-{uuid.uuid4().hex}"
    guessed_suffix = Path(original_name or "").suffix
    fallback_suffix = mimetypes.guess_extension(mime_type or "") or ".bin"
    suffix = guessed_suffix or fallback_suffix
    filename = f"{media_id}{suffix}"
    path = MEDIA_DIR / filename
    path.write_bytes(binary)

    media = {
        "mediaId": media_id,
        "name": original_name or filename,
        "type": mime_type or "application/octet-stream",
        "size": int(size if size is not None else len(binary)),
        "lastModified": last_modified,
        "path": str(path),
    }
    data.setdefault("media", {})[media_id] = media
    return media


def get_media(media_id):
    data = load_db()
    media = (data.get("media") or {}).get(media_id)
    if not media:
        return None

    path = media.get("path")
    if not path or not os.path.exists(path):
        return None
    return media


def serialize_media_reference(media_ref):
    if not media_ref or not isinstance(media_ref, dict):
        return None

    media_id = media_ref.get("mediaId") or ""
    return {
        "name": media_ref.get("name") or "",
        "type": media_ref.get("type") or "",
        "size": media_ref.get("size"),
        "lastModified": media_ref.get("lastModified"),
        "mediaId": media_id,
        "url": f"/api/media/{media_id}" if media_id else "",
    }


def serialize_uploaded_video(uploaded_video):
    return serialize_media_reference(uploaded_video)


def serialize_history(record):
    detail = dict(record.get("detail") or {})
    detail["uploadedVideo"] = serialize_uploaded_video(detail.get("uploadedVideo"))
    manual_review = record.get("manualReview")
    return {
        **record,
        "detail": detail,
        "manualReview": manual_review if manual_review else None,
    }


def serialize_sop_summary(sop):
    return {
        "id": sop.get("id"),
        "name": sop.get("name") or "",
        "scene": sop.get("scene") or "未填写",
        "stepCount": sop.get("stepCount") or len(sop.get("steps") or []),
        "demoVideoCount": sop.get("demoVideoCount") or len(sop.get("steps") or []),
        "createTime": sop.get("createTime") or "",
        "steps": [
            {
                "stepNo": step.get("stepNo"),
                "description": step.get("description") or "",
                "videoMeta": step.get("videoMeta"),
                "demoVideo": serialize_media_reference(step.get("demoVideo")),
                "referenceMode": step.get("referenceMode") or ("video" if step.get("referenceFrames") else "text"),
                "referenceSummary": step.get("referenceSummary") or "",
                "referenceFeatures": step.get("referenceFeatures"),
                "substeps": step.get("substeps") or [],
                "roiHint": step.get("roiHint") or "",
                "aiUsed": bool(step.get("aiUsed")),
            }
            for step in (sop.get("steps") or [])
        ],
    }


def serialize_sop_detail(sop):
    summary = serialize_sop_summary(sop)
    summary["steps"] = [
        {
            **step,
            "demoVideo": serialize_media_reference(step.get("demoVideo")),
            "referenceFrames": step.get("referenceFrames") or [],
            "analysisFrames": step.get("analysisFrames") or [],
            "rawAIResult": step.get("rawAIResult"),
        }
        for step in (sop.get("steps") or [])
    ]
    return summary


def build_stats():
    sops = list_sops()
    history = list_history()
    total_executions = len(history)
    passed_count = sum(1 for item in history if item.get("status") == "passed")
    pending_review_count = sum(1 for item in history if not (item.get("manualReview") or {}).get("status"))

    bucket = {}
    for record in history:
        key = record.get("taskId") or record.get("taskName") or f"unknown-{record.get('id')}"
        item = bucket.get(key) or {
            "taskId": record.get("taskId") or "",
            "taskName": record.get("taskName") or "未命名 SOP",
            "scene": record.get("scene") or "未填写",
            "totalCount": 0,
            "passedCount": 0,
            "pendingReviewCount": 0,
            "scoreSum": 0,
            "scoreCount": 0,
        }
        item["totalCount"] += 1
        if record.get("status") == "passed":
            item["passedCount"] += 1
        if not (record.get("manualReview") or {}).get("status"):
            item["pendingReviewCount"] += 1
        try:
            score = float(record.get("score"))
        except Exception:
            score = None
        if score is not None:
            item["scoreSum"] += score
            item["scoreCount"] += 1
        bucket[key] = item

    sop_stats_list = []
    for item in bucket.values():
        total = item["totalCount"]
        sop_stats_list.append(
            {
                "taskId": item["taskId"],
                "taskName": item["taskName"],
                "scene": item["scene"],
                "totalCount": total,
                "passedCount": item["passedCount"],
                "pendingReviewCount": item["pendingReviewCount"],
                "passRate": (item["passedCount"] / total * 100) if total else 0,
                "averageScore": (item["scoreSum"] / item["scoreCount"]) if item["scoreCount"] else None,
            }
        )

    sop_stats_list.sort(key=lambda item: item["totalCount"], reverse=True)
    return {
        "summaryStats": {
            "totalSops": len(sops),
            "totalExecutions": total_executions,
            "pendingReviewCount": pending_review_count,
            "passRate": (passed_count / total_executions * 100) if total_executions else 0,
        },
        "sopStatsList": sop_stats_list,
    }
