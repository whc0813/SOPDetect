import hashlib
import json
import mimetypes
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
ADMIN_MEDIA_DIR = MEDIA_DIR / "Admin"
USER_MEDIA_DIR = MEDIA_DIR / "User"
DB_LOCK = threading.Lock()
SCHEMA_LOCK = threading.Lock()
SCHEMA_READY = False
ENV_PATH = BASE_DIR / ".env"

DEFAULT_CONFIG = {
    "apiKey": "",
    "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.5-plus",
    "fps": 2,
    "temperature": 0.1,
    "timeoutMs": 120000,
}


def _load_env_file():
    if not ENV_PATH.exists():
        return
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

MYSQL_SETTINGS = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "sop_eval_system"),
    "charset": "utf8mb4",
}

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      username VARCHAR(50) NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      display_name VARCHAR(100) NOT NULL,
      role ENUM('admin', 'user') NOT NULL,
      status ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
      last_login_at DATETIME NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_users_username (username),
      KEY idx_users_role_status (role, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_configs (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      config_name VARCHAR(100) NOT NULL DEFAULT 'default',
      provider VARCHAR(50) NOT NULL DEFAULT 'dashscope',
      base_url VARCHAR(255) NOT NULL,
      model_name VARCHAR(100) NOT NULL,
      api_key_encrypted TEXT NULL,
      fps DECIMAL(4,2) NOT NULL DEFAULT 2.00,
      temperature DECIMAL(3,2) NOT NULL DEFAULT 0.10,
      timeout_ms INT NOT NULL DEFAULT 120000,
      is_default TINYINT(1) NOT NULL DEFAULT 1,
      created_by BIGINT UNSIGNED NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_ai_configs_name (config_name),
      KEY idx_ai_configs_default (is_default),
      CONSTRAINT fk_ai_configs_created_by
        FOREIGN KEY (created_by) REFERENCES users (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sops (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      sop_code VARCHAR(50) NOT NULL,
      name VARCHAR(200) NOT NULL,
      scene VARCHAR(200) NULL,
      description TEXT NULL,
      step_count INT NOT NULL DEFAULT 0,
      demo_video_count INT NOT NULL DEFAULT 0,
      status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'published',
      created_by BIGINT UNSIGNED NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_sops_code (sop_code),
      KEY idx_sops_status_created (status, created_at),
      CONSTRAINT fk_sops_created_by
        FOREIGN KEY (created_by) REFERENCES users (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sop_steps (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      sop_id BIGINT UNSIGNED NOT NULL,
      step_no INT NOT NULL,
      description TEXT NOT NULL,
      reference_mode ENUM('text', 'video') NOT NULL DEFAULT 'text',
      reference_summary TEXT NULL,
      roi_hint VARCHAR(255) NULL,
      ai_used TINYINT(1) NOT NULL DEFAULT 0,
      reference_duration_sec DECIMAL(8,3) NULL,
      reference_fps DECIMAL(6,3) NULL,
      reference_frame_count INT NULL,
      raw_ai_result JSON NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_sop_steps_no (sop_id, step_no),
      KEY idx_sop_steps_sop (sop_id),
      CONSTRAINT fk_sop_steps_sop
        FOREIGN KEY (sop_id) REFERENCES sops (id)
        ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS media_files (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      media_code VARCHAR(64) NOT NULL,
      owner_role ENUM('admin', 'user') NOT NULL,
      business_type ENUM('sop_step_demo', 'execution_upload', 'other') NOT NULL,
      related_sop_id BIGINT UNSIGNED NULL,
      related_step_id BIGINT UNSIGNED NULL,
      related_execution_id BIGINT UNSIGNED NULL,
      original_name VARCHAR(255) NOT NULL,
      stored_name VARCHAR(255) NOT NULL,
      file_ext VARCHAR(20) NULL,
      mime_type VARCHAR(100) NOT NULL,
      file_size BIGINT UNSIGNED NOT NULL,
      storage_disk VARCHAR(50) NOT NULL DEFAULT 'local',
      storage_path VARCHAR(500) NOT NULL,
      access_url VARCHAR(500) NULL,
      last_modified_ms BIGINT NULL,
      uploaded_by BIGINT UNSIGNED NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uk_media_files_code (media_code),
      KEY idx_media_owner_business (owner_role, business_type),
      KEY idx_media_sop_step (related_sop_id, related_step_id),
      KEY idx_media_execution (related_execution_id),
      CONSTRAINT fk_media_related_sop
        FOREIGN KEY (related_sop_id) REFERENCES sops (id)
        ON DELETE SET NULL,
      CONSTRAINT fk_media_related_step
        FOREIGN KEY (related_step_id) REFERENCES sop_steps (id)
        ON DELETE SET NULL,
      CONSTRAINT fk_media_uploaded_by
        FOREIGN KEY (uploaded_by) REFERENCES users (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sop_step_keyframes (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      sop_step_id BIGINT UNSIGNED NOT NULL,
      frame_type ENUM('reference', 'analysis') NOT NULL DEFAULT 'reference',
      sort_order INT NOT NULL,
      timestamp_sec DECIMAL(8,3) NULL,
      image_data LONGTEXT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uk_sop_step_keyframes_order (sop_step_id, frame_type, sort_order),
      KEY idx_sop_step_keyframes_step (sop_step_id),
      CONSTRAINT fk_sop_step_keyframes_step
        FOREIGN KEY (sop_step_id) REFERENCES sop_steps (id)
        ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sop_step_substeps (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      sop_step_id BIGINT UNSIGNED NOT NULL,
      sort_order INT NOT NULL,
      title VARCHAR(200) NOT NULL,
      timestamp_sec DECIMAL(8,3) NOT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uk_sop_step_substeps_order (sop_step_id, sort_order),
      KEY idx_sop_step_substeps_step (sop_step_id),
      CONSTRAINT fk_sop_step_substeps_step
        FOREIGN KEY (sop_step_id) REFERENCES sop_steps (id)
        ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS sop_executions (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      execution_code VARCHAR(64) NOT NULL,
      sop_id BIGINT UNSIGNED NOT NULL,
      user_id BIGINT UNSIGNED NULL,
      uploaded_video_media_id BIGINT UNSIGNED NULL,
      finish_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      score DECIMAL(5,2) NULL,
      ai_status ENUM('passed', 'failed') NOT NULL,
      feedback TEXT NULL,
      sequence_assessment TEXT NULL,
      prerequisite_violated TINYINT(1) NOT NULL DEFAULT 0,
      payload_preview JSON NULL,
      raw_model_result JSON NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_sop_executions_code (execution_code),
      KEY idx_sop_executions_sop (sop_id),
      KEY idx_sop_executions_user (user_id),
      KEY idx_sop_executions_status_time (ai_status, finish_time),
      CONSTRAINT fk_sop_executions_sop
        FOREIGN KEY (sop_id) REFERENCES sops (id)
        ON DELETE RESTRICT,
      CONSTRAINT fk_sop_executions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL,
      CONSTRAINT fk_sop_executions_video
        FOREIGN KEY (uploaded_video_media_id) REFERENCES media_files (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_issues (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      execution_id BIGINT UNSIGNED NOT NULL,
      issue_text VARCHAR(255) NOT NULL,
      sort_order INT NOT NULL DEFAULT 1,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      KEY idx_execution_issues_execution (execution_id),
      CONSTRAINT fk_execution_issues_execution
        FOREIGN KEY (execution_id) REFERENCES sop_executions (id)
        ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS execution_step_results (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      execution_id BIGINT UNSIGNED NOT NULL,
      sop_step_id BIGINT UNSIGNED NULL,
      step_no INT NOT NULL,
      description TEXT NOT NULL,
      passed TINYINT(1) NOT NULL,
      score DECIMAL(5,2) NOT NULL,
      confidence DECIMAL(5,2) NOT NULL,
      issue_type VARCHAR(100) NULL,
      completion_level VARCHAR(100) NULL,
      order_issue TINYINT(1) NOT NULL DEFAULT 0,
      prerequisite_violated TINYINT(1) NOT NULL DEFAULT 0,
      evidence TEXT NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE KEY uk_execution_step_results_no (execution_id, step_no),
      KEY idx_execution_step_results_step (sop_step_id),
      CONSTRAINT fk_execution_step_results_execution
        FOREIGN KEY (execution_id) REFERENCES sop_executions (id)
        ON DELETE CASCADE,
      CONSTRAINT fk_execution_step_results_sop_step
        FOREIGN KEY (sop_step_id) REFERENCES sop_steps (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS manual_reviews (
      id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
      execution_id BIGINT UNSIGNED NOT NULL,
      review_status ENUM('approved', 'rejected', 'needs_attention') NOT NULL,
      review_note TEXT NULL,
      reviewer_id BIGINT UNSIGNED NULL,
      review_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uk_manual_reviews_execution (execution_id),
      KEY idx_manual_reviews_status_time (review_status, review_time),
      CONSTRAINT fk_manual_reviews_execution
        FOREIGN KEY (execution_id) REFERENCES sop_executions (id)
        ON DELETE CASCADE,
      CONSTRAINT fk_manual_reviews_reviewer
        FOREIGN KEY (reviewer_id) REFERENCES users (id)
        ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    ADMIN_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    USER_MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def now_display():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(value):
    return json.dumps(value, ensure_ascii=False) if value is not None else None


def _json_loads(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _parse_datetime(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _mysql_connection(database=None, autocommit=False):
    settings = dict(MYSQL_SETTINGS)
    if database is not None:
        settings["database"] = database
    try:
        return pymysql.connect(
            host=settings["host"],
            port=settings["port"],
            user=settings["user"],
            password=settings["password"],
            database=settings.get("database"),
            charset=settings["charset"],
            cursorclass=DictCursor,
            autocommit=autocommit,
        )
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            f"MySQL 连接失败，请检查 backend/.env 配置与数据库权限：{exc}"
        ) from exc


def _ensure_database():
    try:
        connection = pymysql.connect(
            host=MYSQL_SETTINGS["host"],
            port=MYSQL_SETTINGS["port"],
            user=MYSQL_SETTINGS["user"],
            password=MYSQL_SETTINGS["password"],
            charset=MYSQL_SETTINGS["charset"],
            cursorclass=DictCursor,
            autocommit=True,
        )
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            f"MySQL 连接失败，请检查 backend/.env 配置与数据库权限：{exc}"
        ) from exc
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_SETTINGS['database']}` "
                "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
            )
    finally:
        connection.close()


def _ensure_seed_data(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS count FROM users")
        if int(cursor.fetchone()["count"]) == 0:
            cursor.executemany(
                """
                INSERT INTO users (username, password_hash, display_name, role)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    ("admin", "admin", "管理员", "admin"),
                    ("user", "user", "操作用户", "user"),
                ],
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = CASE username
                    WHEN 'admin' THEN 'admin'
                    WHEN 'user' THEN 'user'
                    ELSE password_hash
                END
                WHERE username IN ('admin', 'user')
                  AND password_hash = 'replace_with_bcrypt_hash'
                """
            )

        cursor.execute("SELECT COUNT(*) AS count FROM ai_configs")
        if int(cursor.fetchone()["count"]) == 0:
            cursor.execute(
                """
                INSERT INTO ai_configs (
                  config_name, provider, base_url, model_name, api_key_encrypted, fps, temperature, timeout_ms, is_default
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "default",
                    "dashscope",
                    DEFAULT_CONFIG["baseURL"],
                    DEFAULT_CONFIG["model"],
                    DEFAULT_CONFIG["apiKey"],
                    DEFAULT_CONFIG["fps"],
                    DEFAULT_CONFIG["temperature"],
                    DEFAULT_CONFIG["timeoutMs"],
                    1,
                ),
            )


def ensure_schema():
    global SCHEMA_READY
    if SCHEMA_READY:
        return

    with SCHEMA_LOCK:
        if SCHEMA_READY:
            return

        ensure_storage()
        _ensure_database()
        connection = _mysql_connection()
        try:
            with connection.cursor() as cursor:
                for statement in SCHEMA_STATEMENTS:
                    cursor.execute(statement)
            _ensure_seed_data(connection)
            connection.commit()
            SCHEMA_READY = True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _get_connection():
    ensure_schema()
    return _mysql_connection()


def _fetch_user_by_name(connection, username):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, password_hash, display_name, role, status
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (username,),
        )
        return cursor.fetchone()


def _password_matches(password, stored_hash):
    if not stored_hash:
        return False
    if stored_hash == password:
        return True
    if stored_hash == hashlib.sha256(password.encode("utf-8")).hexdigest():
        return True
    return False


def authenticate_user(username, password):
    with _get_connection() as connection:
        user = _fetch_user_by_name(connection, username)
        if not user or user.get("status") != "active":
            return None
        if not _password_matches(password, user.get("password_hash") or ""):
            return None

        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user["id"],))
        connection.commit()
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "displayName": user["display_name"],
        }


def load_db():
    ensure_schema()
    return {}


def save_db(_data):
    ensure_schema()
    return None


def _resolve_user_id(connection, name):
    if not name:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s OR display_name = %s
            LIMIT 1
            """,
            (name, name),
        )
        row = cursor.fetchone()
        return row["id"] if row else None


def _fetch_default_config_row(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM ai_configs
            ORDER BY is_default DESC, id ASC
            LIMIT 1
            """
        )
        return cursor.fetchone()


def get_config():
    with _get_connection() as connection:
        row = _fetch_default_config_row(connection)
        if not row:
            return dict(DEFAULT_CONFIG)
        return {
            "apiKey": row.get("api_key_encrypted") or "",
            "baseURL": row.get("base_url") or DEFAULT_CONFIG["baseURL"],
            "model": row.get("model_name") or DEFAULT_CONFIG["model"],
            "fps": float(row.get("fps") or DEFAULT_CONFIG["fps"]),
            "temperature": float(row.get("temperature") or DEFAULT_CONFIG["temperature"]),
            "timeoutMs": int(row.get("timeout_ms") or DEFAULT_CONFIG["timeoutMs"]),
        }


def set_config(config):
    merged = dict(DEFAULT_CONFIG)
    merged.update(config or {})

    with _get_connection() as connection:
        row = _fetch_default_config_row(connection)
        with connection.cursor() as cursor:
            if row:
                cursor.execute(
                    """
                    UPDATE ai_configs
                    SET provider = %s,
                        base_url = %s,
                        model_name = %s,
                        api_key_encrypted = %s,
                        fps = %s,
                        temperature = %s,
                        timeout_ms = %s,
                        is_default = 1
                    WHERE id = %s
                    """,
                    (
                        "dashscope",
                        merged["baseURL"],
                        merged["model"],
                        merged["apiKey"],
                        merged["fps"],
                        merged["temperature"],
                        merged["timeoutMs"],
                        row["id"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO ai_configs (
                      config_name, provider, base_url, model_name, api_key_encrypted, fps, temperature, timeout_ms, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "default",
                        "dashscope",
                        merged["baseURL"],
                        merged["model"],
                        merged["apiKey"],
                        merged["fps"],
                        merged["temperature"],
                        merged["timeoutMs"],
                        1,
                    ),
                )
        connection.commit()

    return merged


def _fetch_sop_base_rows(connection, sop_codes=None):
    sql = """
        SELECT s.id, s.sop_code, s.name, s.scene, s.description, s.step_count, s.demo_video_count,
               s.status, s.created_at, s.updated_at
        FROM sops s
    """
    params = []
    if sop_codes:
        placeholders = ", ".join(["%s"] * len(sop_codes))
        sql += f" WHERE s.sop_code IN ({placeholders})"
        params.extend(sop_codes)
    sql += " ORDER BY s.created_at DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _media_row_to_api(media_row):
    if not media_row:
        return None
    return {
        "mediaId": media_row.get("media_code") or "",
        "name": media_row.get("original_name") or "",
        "type": media_row.get("mime_type") or "",
        "size": media_row.get("file_size"),
        "lastModified": media_row.get("last_modified_ms"),
        "path": media_row.get("storage_path") or "",
    }


def _fetch_media_for_steps(connection, step_ids):
    if not step_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(step_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM media_files
            WHERE related_step_id IN ({placeholders})
            ORDER BY id DESC
            """,
            step_ids,
        )
        rows = cursor.fetchall()

    media_map = {}
    for row in rows:
        step_id = row.get("related_step_id")
        if step_id and step_id not in media_map:
            media_map[step_id] = row
    return media_map


def _build_sop_records(connection, sop_codes=None):
    sop_rows = _fetch_sop_base_rows(connection, sop_codes)
    if not sop_rows:
        return []

    sop_ids = [row["id"] for row in sop_rows]
    placeholders = ", ".join(["%s"] * len(sop_ids))

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM sop_steps
            WHERE sop_id IN ({placeholders})
            ORDER BY sop_id ASC, step_no ASC
            """,
            sop_ids,
        )
        step_rows = cursor.fetchall()

    step_ids = [row["id"] for row in step_rows]
    media_map = _fetch_media_for_steps(connection, step_ids)
    keyframe_map = {}
    substep_map = {}

    if step_ids:
        step_placeholders = ", ".join(["%s"] * len(step_ids))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM sop_step_keyframes
                WHERE sop_step_id IN ({step_placeholders})
                ORDER BY sop_step_id ASC, frame_type ASC, sort_order ASC
                """,
                step_ids,
            )
            for row in cursor.fetchall():
                keyframe_map.setdefault(row["sop_step_id"], []).append(row)

            cursor.execute(
                f"""
                SELECT *
                FROM sop_step_substeps
                WHERE sop_step_id IN ({step_placeholders})
                ORDER BY sop_step_id ASC, sort_order ASC
                """,
                step_ids,
            )
            for row in cursor.fetchall():
                substep_map.setdefault(row["sop_step_id"], []).append(row)

    steps_by_sop = {}
    for step in step_rows:
        frames = keyframe_map.get(step["id"], [])
        reference_frames = [item.get("image_data") or "" for item in frames if item.get("frame_type") == "reference"]
        analysis_frames = [item.get("image_data") or "" for item in frames if item.get("frame_type") == "analysis"]
        sample_timestamps = [
            float(item.get("timestamp_sec"))
            for item in frames
            if item.get("frame_type") == "reference" and item.get("timestamp_sec") is not None
        ]
        media_row = media_map.get(step["id"])
        demo_video = _media_row_to_api(media_row)

        steps_by_sop.setdefault(step["sop_id"], []).append(
            {
                "stepNo": int(step.get("step_no") or 0),
                "description": step.get("description") or "",
                "videoMeta": demo_video,
                "demoVideo": demo_video,
                "referenceMode": step.get("reference_mode") or ("video" if reference_frames else "text"),
                "referenceFrames": reference_frames,
                "analysisFrames": analysis_frames,
                "referenceSummary": step.get("reference_summary") or "",
                "referenceFeatures": {
                    "durationSec": float(step.get("reference_duration_sec") or 0),
                    "fps": float(step.get("reference_fps") or 0),
                    "frameCount": int(step.get("reference_frame_count") or 0),
                    "sampleTimestamps": sample_timestamps,
                },
                "substeps": [
                    {
                        "title": item.get("title") or "",
                        "timestampSec": float(item.get("timestamp_sec") or 0),
                    }
                    for item in substep_map.get(step["id"], [])
                ],
                "roiHint": step.get("roi_hint") or "",
                "aiUsed": bool(step.get("ai_used")),
                "rawAIResult": _json_loads(step.get("raw_ai_result"), None),
            }
        )

    records = []
    for row in sop_rows:
        steps = steps_by_sop.get(row["id"], [])
        records.append(
            {
                "id": row.get("sop_code"),
                "name": row.get("name") or "",
                "scene": row.get("scene") or "未填写",
                "description": row.get("description") or "",
                "stepCount": int(row.get("step_count") or len(steps)),
                "demoVideoCount": int(row.get("demo_video_count") or sum(1 for item in steps if item.get("demoVideo"))),
                "createTime": _parse_datetime(row.get("created_at")),
                "createdAtMs": int(row["created_at"].timestamp() * 1000) if isinstance(row.get("created_at"), datetime) else 0,
                "steps": steps,
            }
        )
    return records


def list_sops():
    with _get_connection() as connection:
        return _build_sop_records(connection)


def get_sop(sop_id):
    with _get_connection() as connection:
        records = _build_sop_records(connection, [sop_id])
        return records[0] if records else None


def _fetch_sop_row_by_code(connection, sop_code):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM sops WHERE sop_code = %s LIMIT 1", (sop_code,))
        return cursor.fetchone()


def _fetch_step_row(connection, sop_id, step_no):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM sop_steps
            WHERE sop_id = %s AND step_no = %s
            LIMIT 1
            """,
            (sop_id, step_no),
        )
        return cursor.fetchone()


def _insert_step_children(connection, step_id, step):
    reference_frames = step.get("referenceFrames") or []
    analysis_frames = step.get("analysisFrames") or []
    reference_timestamps = ((step.get("referenceFeatures") or {}).get("sampleTimestamps")) or []

    with connection.cursor() as cursor:
        for index, frame in enumerate(reference_frames):
            timestamp = reference_timestamps[index] if index < len(reference_timestamps) else None
            cursor.execute(
                """
                INSERT INTO sop_step_keyframes (sop_step_id, frame_type, sort_order, timestamp_sec, image_data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (step_id, "reference", index + 1, timestamp, frame),
            )

        for index, frame in enumerate(analysis_frames):
            cursor.execute(
                """
                INSERT INTO sop_step_keyframes (sop_step_id, frame_type, sort_order, timestamp_sec, image_data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (step_id, "analysis", index + 1, None, frame),
            )

        for index, item in enumerate(step.get("substeps") or []):
            cursor.execute(
                """
                INSERT INTO sop_step_substeps (sop_step_id, sort_order, title, timestamp_sec)
                VALUES (%s, %s, %s, %s)
                """,
                (step_id, index + 1, item.get("title") or "", item.get("timestampSec") or 0),
            )


def _upsert_sop_content(connection, sop_data):
    sop_row = _fetch_sop_row_by_code(connection, sop_data["id"])
    steps = sop_data.get("steps") or []
    demo_video_count = sum(1 for item in steps if item.get("demoVideo"))

    with connection.cursor() as cursor:
        if sop_row:
            cursor.execute(
                """
                UPDATE sops
                SET name = %s,
                    scene = %s,
                    description = %s,
                    step_count = %s,
                    demo_video_count = %s,
                    status = %s
                WHERE id = %s
                """,
                (
                    sop_data.get("name") or "",
                    sop_data.get("scene") or "",
                    sop_data.get("description") or "",
                    sop_data.get("stepCount") or len(steps),
                    demo_video_count,
                    sop_data.get("status") or "published",
                    sop_row["id"],
                ),
            )
            sop_id = sop_row["id"]
            cursor.execute("DELETE FROM sop_steps WHERE sop_id = %s", (sop_id,))
        else:
            cursor.execute(
                """
                INSERT INTO sops (sop_code, name, scene, description, step_count, demo_video_count, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sop_data["id"],
                    sop_data.get("name") or "",
                    sop_data.get("scene") or "",
                    sop_data.get("description") or "",
                    sop_data.get("stepCount") or len(steps),
                    demo_video_count,
                    sop_data.get("status") or "published",
                ),
            )
            sop_id = cursor.lastrowid

    for step in steps:
        reference_features = step.get("referenceFeatures") or {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sop_steps (
                  sop_id, step_no, description, reference_mode, reference_summary, roi_hint, ai_used,
                  reference_duration_sec, reference_fps, reference_frame_count, raw_ai_result
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sop_id,
                    step.get("stepNo") or 0,
                    step.get("description") or "",
                    step.get("referenceMode") or ("video" if step.get("referenceFrames") else "text"),
                    step.get("referenceSummary") or "",
                    step.get("roiHint") or "",
                    1 if step.get("aiUsed") else 0,
                    reference_features.get("durationSec"),
                    reference_features.get("fps"),
                    reference_features.get("frameCount"),
                    _json_dumps(step.get("rawAIResult")),
                ),
            )
            step_id = cursor.lastrowid

        _insert_step_children(connection, step_id, step)

        demo_video = step.get("demoVideo")
        if demo_video and demo_video.get("mediaId"):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE media_files
                    SET owner_role = 'admin',
                        business_type = 'sop_step_demo',
                        related_sop_id = %s,
                        related_step_id = %s
                    WHERE media_code = %s
                    """,
                    (sop_id, step_id, demo_video.get("mediaId")),
                )


def add_sop(sop):
    with _get_connection() as connection:
        _upsert_sop_content(connection, sop)
        connection.commit()
    return get_sop(sop.get("id"))


def update_sop(sop_id, updater):
    with _get_connection() as connection:
        current_records = _build_sop_records(connection, [sop_id])
        if not current_records:
            return None
        updated = updater(current_records[0])
        _upsert_sop_content(connection, updated)
        connection.commit()
    return get_sop(sop_id)


def _delete_files(paths):
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def delete_sop(sop_id):
    with _get_connection() as connection:
        sop_row = _fetch_sop_row_by_code(connection, sop_id)
        if not sop_row:
            return False

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sop_executions WHERE sop_id = %s", (sop_row["id"],))
            execution_ids = [row["id"] for row in cursor.fetchall()]

            if execution_ids:
                placeholders = ", ".join(["%s"] * len(execution_ids))
                cursor.execute(
                    f"""
                    SELECT storage_path
                    FROM media_files
                    WHERE related_sop_id = %s OR related_execution_id IN ({placeholders})
                    """,
                    [sop_row["id"], *execution_ids],
                )
            else:
                cursor.execute(
                    "SELECT storage_path FROM media_files WHERE related_sop_id = %s",
                    (sop_row["id"],),
                )
            media_paths = [row["storage_path"] for row in cursor.fetchall()]

            if execution_ids:
                placeholders = ", ".join(["%s"] * len(execution_ids))
                cursor.execute(
                    f"DELETE FROM media_files WHERE related_sop_id = %s OR related_execution_id IN ({placeholders})",
                    [sop_row["id"], *execution_ids],
                )
                cursor.execute("DELETE FROM sop_executions WHERE sop_id = %s", (sop_row["id"],))
            else:
                cursor.execute("DELETE FROM media_files WHERE related_sop_id = %s", (sop_row["id"],))

            cursor.execute("DELETE FROM sops WHERE id = %s", (sop_row["id"],))

        connection.commit()
        _delete_files(media_paths)
        return True


def attach_media(
    _data,
    binary,
    mime_type,
    original_name="",
    size=None,
    last_modified=None,
    owner_role="user",
    business_type="other",
    related_sop_id=None,
    related_step_no=None,
    related_execution_id=None,
    uploaded_by=None,
):
    ensure_storage()
    media_code = f"media-{uuid.uuid4().hex}"
    guessed_suffix = Path(original_name or "").suffix
    fallback_suffix = mimetypes.guess_extension(mime_type or "") or ".bin"
    suffix = guessed_suffix or fallback_suffix
    stored_name = f"{media_code}{suffix}"

    base_dir = ADMIN_MEDIA_DIR if owner_role == "admin" else USER_MEDIA_DIR
    if owner_role == "admin" and business_type == "sop_step_demo":
        sub_dir = base_dir / "sop_step_demo" / (related_sop_id or "unassigned") / (
            f"step_{related_step_no}" if related_step_no else "step_unknown"
        )
    elif owner_role == "user" and business_type == "execution_upload":
        sub_dir = base_dir / "execution_upload" / (related_execution_id or "pending")
    else:
        sub_dir = base_dir / "other"

    sub_dir.mkdir(parents=True, exist_ok=True)
    path = sub_dir / stored_name
    path.write_bytes(binary)

    with _get_connection() as connection:
        sop_row = _fetch_sop_row_by_code(connection, related_sop_id) if related_sop_id else None
        step_row = (
            _fetch_step_row(connection, sop_row["id"], related_step_no)
            if sop_row and related_step_no is not None
            else None
        )
        execution_db_id = None
        if related_execution_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM sop_executions WHERE execution_code = %s LIMIT 1",
                    (related_execution_id,),
                )
                row = cursor.fetchone()
                execution_db_id = row["id"] if row else None

        uploaded_by_id = _resolve_user_id(connection, uploaded_by)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO media_files (
                  media_code, owner_role, business_type, related_sop_id, related_step_id, related_execution_id,
                  original_name, stored_name, file_ext, mime_type, file_size, storage_disk, storage_path,
                  access_url, last_modified_ms, uploaded_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    media_code,
                    owner_role,
                    business_type,
                    sop_row["id"] if sop_row else None,
                    step_row["id"] if step_row else None,
                    execution_db_id,
                    original_name or stored_name,
                    stored_name,
                    suffix,
                    mime_type or "application/octet-stream",
                    int(size if size is not None else len(binary)),
                    "local",
                    str(path),
                    None,
                    last_modified,
                    uploaded_by_id,
                ),
            )
        connection.commit()

    return {
        "mediaId": media_code,
        "name": original_name or stored_name,
        "type": mime_type or "application/octet-stream",
        "size": int(size if size is not None else len(binary)),
        "lastModified": last_modified,
        "path": str(path),
    }


def get_media(media_id):
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM media_files
                WHERE media_code = %s
                LIMIT 1
                """,
                (media_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None

    path = row.get("storage_path")
    if not path or not os.path.exists(path):
        return None
    return {
        "mediaId": row.get("media_code") or "",
        "name": row.get("original_name") or "",
        "type": row.get("mime_type") or "",
        "size": row.get("file_size"),
        "lastModified": row.get("last_modified_ms"),
        "path": path,
    }


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


def _fetch_history_rows(connection, execution_codes=None):
    sql = """
        SELECT e.id, e.execution_code, e.sop_id, e.user_id, e.uploaded_video_media_id, e.finish_time,
               e.score, e.ai_status, e.feedback, e.sequence_assessment, e.prerequisite_violated,
               e.payload_preview, e.raw_model_result, e.created_at,
               s.sop_code, s.name AS task_name, s.scene
        FROM sop_executions e
        JOIN sops s ON s.id = e.sop_id
    """
    params = []
    if execution_codes:
        placeholders = ", ".join(["%s"] * len(execution_codes))
        sql += f" WHERE e.execution_code IN ({placeholders})"
        params.extend(execution_codes)
    sql += " ORDER BY e.created_at DESC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _build_history_records(connection, execution_codes=None):
    rows = _fetch_history_rows(connection, execution_codes)
    if not rows:
        return []

    execution_ids = [row["id"] for row in rows]
    execution_placeholders = ", ".join(["%s"] * len(execution_ids))
    sop_ids = sorted({row["sop_id"] for row in rows})
    sop_placeholders = ", ".join(["%s"] * len(sop_ids))

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT *
            FROM execution_issues
            WHERE execution_id IN ({execution_placeholders})
            ORDER BY execution_id ASC, sort_order ASC
            """,
            execution_ids,
        )
        issues_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT *
            FROM execution_step_results
            WHERE execution_id IN ({execution_placeholders})
            ORDER BY execution_id ASC, step_no ASC
            """,
            execution_ids,
        )
        step_result_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT mr.*, u.display_name AS reviewer_name
            FROM manual_reviews mr
            LEFT JOIN users u ON u.id = mr.reviewer_id
            WHERE mr.execution_id IN ({execution_placeholders})
            """,
            execution_ids,
        )
        review_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT *
            FROM media_files
            WHERE related_execution_id IN ({execution_placeholders})
            ORDER BY id DESC
            """,
            execution_ids,
        )
        media_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT st.sop_id, st.step_no, st.description, mf.original_name AS video_name
            FROM sop_steps st
            LEFT JOIN media_files mf ON mf.related_step_id = st.id
            WHERE st.sop_id IN ({sop_placeholders})
            ORDER BY st.sop_id ASC, st.step_no ASC
            """,
            sop_ids,
        )
        sop_step_rows = cursor.fetchall()

    issues_map = {}
    for row in issues_rows:
        issues_map.setdefault(row["execution_id"], []).append(row["issue_text"])

    step_results_map = {}
    for row in step_result_rows:
        step_results_map.setdefault(row["execution_id"], []).append(
            {
                "stepNo": int(row.get("step_no") or 0),
                "description": row.get("description") or "",
                "passed": bool(row.get("passed")),
                "score": float(row.get("score") or 0),
                "confidence": float(row.get("confidence") or 0),
                "issueType": row.get("issue_type") or "",
                "completionLevel": row.get("completion_level") or "",
                "orderIssue": bool(row.get("order_issue")),
                "prerequisiteViolated": bool(row.get("prerequisite_violated")),
                "evidence": row.get("evidence") or "",
            }
        )

    review_map = {}
    for row in review_rows:
        review_map[row["execution_id"]] = {
            "status": row.get("review_status") or "",
            "note": row.get("review_note") or "",
            "reviewer": row.get("reviewer_name") or "",
            "reviewTime": _parse_datetime(row.get("review_time")),
        }

    media_map = {}
    for row in media_rows:
        execution_id = row.get("related_execution_id")
        if execution_id and execution_id not in media_map:
            media_map[execution_id] = _media_row_to_api(row)

    sop_steps_map = {}
    for row in sop_step_rows:
        sop_steps_map.setdefault(row["sop_id"], []).append(
            {
                "stepNo": int(row.get("step_no") or 0),
                "description": row.get("description") or "",
                "videoName": row.get("video_name") or "",
            }
        )

    records = []
    for row in rows:
        records.append(
            {
                "id": row.get("execution_code"),
                "createdAtMs": int(row["created_at"].timestamp() * 1000) if isinstance(row.get("created_at"), datetime) else 0,
                "taskId": row.get("sop_code") or "",
                "taskName": row.get("task_name") or "",
                "scene": row.get("scene") or "",
                "finishTime": _parse_datetime(row.get("finish_time")),
                "score": float(row.get("score")) if row.get("score") is not None else None,
                "status": row.get("ai_status") or "failed",
                "manualReview": review_map.get(row["id"]),
                "detail": {
                    "feedback": row.get("feedback") or "",
                    "issues": issues_map.get(row["id"], []),
                    "sequenceAssessment": row.get("sequence_assessment") or "",
                    "prerequisiteViolated": bool(row.get("prerequisite_violated")),
                    "stepResults": step_results_map.get(row["id"], []),
                    "sopSteps": sop_steps_map.get(row["sop_id"], []),
                    "uploadedVideo": media_map.get(row["id"]),
                    "payloadPreview": _json_loads(row.get("payload_preview"), None),
                    "rawModelResult": _json_loads(row.get("raw_model_result"), None),
                },
            }
        )
    return records


def list_history():
    with _get_connection() as connection:
        return _build_history_records(connection)


def get_history(record_id):
    with _get_connection() as connection:
        records = _build_history_records(connection, [record_id])
        return records[0] if records else None


def add_history(record):
    with _get_connection() as connection:
        sop_row = _fetch_sop_row_by_code(connection, record.get("taskId"))
        if not sop_row:
            raise ValueError("SOP not found")

        uploaded_video_code = ((record.get("detail") or {}).get("uploadedVideo") or {}).get("mediaId")
        uploaded_video_db_id = None
        if uploaded_video_code:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM media_files WHERE media_code = %s LIMIT 1", (uploaded_video_code,))
                media_row = cursor.fetchone()
                uploaded_video_db_id = media_row["id"] if media_row else None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sop_executions (
                  execution_code, sop_id, user_id, uploaded_video_media_id, finish_time, score, ai_status,
                  feedback, sequence_assessment, prerequisite_violated, payload_preview, raw_model_result
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.get("id"),
                    sop_row["id"],
                    None,
                    uploaded_video_db_id,
                    datetime.now(),
                    record.get("score"),
                    record.get("status") or "failed",
                    (record.get("detail") or {}).get("feedback") or "",
                    (record.get("detail") or {}).get("sequenceAssessment") or "",
                    1 if (record.get("detail") or {}).get("prerequisiteViolated") else 0,
                    _json_dumps((record.get("detail") or {}).get("payloadPreview")),
                    _json_dumps((record.get("detail") or {}).get("rawModelResult")),
                ),
            )
            execution_id = cursor.lastrowid

        for index, issue_text in enumerate((record.get("detail") or {}).get("issues") or []):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_issues (execution_id, issue_text, sort_order)
                    VALUES (%s, %s, %s)
                    """,
                    (execution_id, issue_text, index + 1),
                )

        step_rows = {}
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, step_no FROM sop_steps WHERE sop_id = %s", (sop_row["id"],))
            for row in cursor.fetchall():
                step_rows[int(row["step_no"])] = row["id"]

        for item in (record.get("detail") or {}).get("stepResults") or []:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO execution_step_results (
                      execution_id, sop_step_id, step_no, description, passed, score, confidence, issue_type,
                      completion_level, order_issue, prerequisite_violated, evidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        execution_id,
                        step_rows.get(int(item.get("stepNo") or 0)),
                        item.get("stepNo") or 0,
                        item.get("description") or "",
                        1 if item.get("passed") else 0,
                        item.get("score") or 0,
                        item.get("confidence") or 0,
                        item.get("issueType") or "",
                        item.get("completionLevel") or "",
                        1 if item.get("orderIssue") else 0,
                        1 if item.get("prerequisiteViolated") else 0,
                        item.get("evidence") or "",
                    ),
                )

        if uploaded_video_code:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE media_files
                    SET owner_role = 'user',
                        business_type = 'execution_upload',
                        related_execution_id = %s,
                        related_sop_id = %s
                    WHERE media_code = %s
                    """,
                    (execution_id, sop_row["id"], uploaded_video_code),
                )

        connection.commit()
    return get_history(record.get("id"))


def update_manual_review(record_id, review):
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sop_executions WHERE execution_code = %s LIMIT 1", (record_id,))
            execution_row = cursor.fetchone()
            if not execution_row:
                return None

        reviewer_id = _resolve_user_id(connection, review.get("reviewer"))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO manual_reviews (execution_id, review_status, review_note, reviewer_id, review_time)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  review_status = VALUES(review_status),
                  review_note = VALUES(review_note),
                  reviewer_id = VALUES(reviewer_id),
                  review_time = VALUES(review_time)
                """,
                (
                    execution_row["id"],
                    review.get("status") or "needs_attention",
                    review.get("note") or "",
                    reviewer_id,
                    datetime.now(),
                ),
            )
        connection.commit()
    return get_history(record_id)


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
        "demoVideoCount": sop.get("demoVideoCount") or len([item for item in (sop.get("steps") or []) if item.get("demoVideo")]),
        "createTime": sop.get("createTime") or "",
        "steps": [
            {
                "stepNo": step.get("stepNo"),
                "description": step.get("description") or "",
                "videoMeta": serialize_media_reference(step.get("demoVideo")),
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
            "videoMeta": serialize_media_reference(step.get("demoVideo")),
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
            "taskName": record.get("taskName") or "未命名SOP",
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
