import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

try:
    from .storage import get_user_by_id, is_user_session_active
except ImportError:
    from storage import get_user_by_id, is_user_session_active

TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "sop-eval-dev-secret")
TOKEN_EXPIRES_IN = int(os.getenv("AUTH_TOKEN_EXPIRES_IN", "28800"))


# ── Auth-related Pydantic models ───────────────────────────────

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


# ── Token helpers ──────────────────────────────────────────────

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
    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256
    ).digest()
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
