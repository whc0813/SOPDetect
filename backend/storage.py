import hashlib
import hmac
import json
import mimetypes
import os
import shutil
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
SCHEMA_SQL_PATH = BASE_DIR / "mysql_schema.sql"

DEFAULT_CONFIG = {
    "apiKey": "",
    "baseURL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.5-plus",
    "fps": 6,
    "temperature": 0.1,
    "timeoutMs": 120000,
}

STEP_TYPE_VALUES = {"required", "optional", "conditional"}
DEFAULT_STEP_TYPE = "required"
DEFAULT_STEP_WEIGHT = 1.0


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


def _extract_token_usage(raw_result):
    payload = _json_loads(raw_result, None)
    if not isinstance(payload, dict):
        return None

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    def pick_number(*keys):
        for key in keys:
            value = usage.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except Exception:
                continue
        return None

    input_tokens = pick_number("prompt_tokens", "input_tokens", "promptTokens", "inputTokens")
    output_tokens = pick_number("completion_tokens", "output_tokens", "completionTokens", "outputTokens")
    total_tokens = pick_number("total_tokens", "totalTokens")
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
    }


def _safe_dir_name(value, fallback):
    text = str(value or "").strip()
    if not text:
        return fallback
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, "_")
    text = text.strip().rstrip(".")
    return text or fallback


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


def _load_schema_sql():
    if not SCHEMA_SQL_PATH.exists():
        raise RuntimeError(f"未找到数据库建表脚本: {SCHEMA_SQL_PATH}")
    sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    default_database = "sop_eval_system"
    target_database = MYSQL_SETTINGS["database"]
    if target_database and target_database != default_database:
        sql = sql.replace(
            f"CREATE DATABASE IF NOT EXISTS {default_database}",
            f"CREATE DATABASE IF NOT EXISTS {target_database}",
        )
        sql = sql.replace(f"USE {default_database}", f"USE {target_database}")
    return sql


def _split_sql_statements(sql_text):
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False

    for char in sql_text:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def _table_exists(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
            """,
            (MYSQL_SETTINGS["database"], table_name),
        )
        return cursor.fetchone() is not None


def _column_exists(connection, table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s AND column_name = %s
            LIMIT 1
            """,
            (MYSQL_SETTINGS["database"], table_name, column_name),
        )
        return cursor.fetchone() is not None


def _run_schema_migrations(connection):
    column_statements = {
        ("sop_steps", "step_type"): "ALTER TABLE sop_steps ADD COLUMN step_type ENUM('required', 'optional', 'conditional') NOT NULL DEFAULT 'required' AFTER description",
        ("sop_steps", "step_weight"): "ALTER TABLE sop_steps ADD COLUMN step_weight DECIMAL(4,1) NOT NULL DEFAULT 1.0 AFTER step_type",
        ("sop_steps", "condition_text"): "ALTER TABLE sop_steps ADD COLUMN condition_text TEXT NULL AFTER step_weight",
        ("sop_steps", "min_duration_sec"): "ALTER TABLE sop_steps ADD COLUMN min_duration_sec DECIMAL(8,3) NULL AFTER condition_text",
        ("sop_steps", "max_duration_sec"): "ALTER TABLE sop_steps ADD COLUMN max_duration_sec DECIMAL(8,3) NULL AFTER min_duration_sec",
        ("execution_step_results", "applicable"): "ALTER TABLE execution_step_results ADD COLUMN applicable TINYINT(1) NOT NULL DEFAULT 1 AFTER confidence",
        ("execution_step_results", "included_in_score"): "ALTER TABLE execution_step_results ADD COLUMN included_in_score TINYINT(1) NOT NULL DEFAULT 1 AFTER applicable",
        ("execution_step_results", "detected_start_sec"): "ALTER TABLE execution_step_results ADD COLUMN detected_start_sec DECIMAL(8,3) NULL AFTER prerequisite_violated",
        ("execution_step_results", "detected_end_sec"): "ALTER TABLE execution_step_results ADD COLUMN detected_end_sec DECIMAL(8,3) NULL AFTER detected_start_sec",
        ("execution_step_results", "step_weight_snapshot"): "ALTER TABLE execution_step_results ADD COLUMN step_weight_snapshot DECIMAL(4,1) NOT NULL DEFAULT 1.0 AFTER detected_end_sec",
        ("execution_step_results", "step_type_snapshot"): "ALTER TABLE execution_step_results ADD COLUMN step_type_snapshot VARCHAR(20) NOT NULL DEFAULT 'required' AFTER step_weight_snapshot",
        ("execution_step_results", "min_duration_sec_snapshot"): "ALTER TABLE execution_step_results ADD COLUMN min_duration_sec_snapshot DECIMAL(8,3) NULL AFTER step_type_snapshot",
        ("execution_step_results", "max_duration_sec_snapshot"): "ALTER TABLE execution_step_results ADD COLUMN max_duration_sec_snapshot DECIMAL(8,3) NULL AFTER min_duration_sec_snapshot",
        ("sops", "penalty_config"): "ALTER TABLE sops ADD COLUMN penalty_config JSON NULL AFTER demo_video_count",
    }

    for (table_name, column_name), statement in column_statements.items():
        if _table_exists(connection, table_name) and not _column_exists(connection, table_name, column_name):
            with connection.cursor() as cursor:
                cursor.execute(statement)

    drop_column_statements = {
        ("sop_steps", "risk_level"): "ALTER TABLE sop_steps DROP COLUMN risk_level",
        ("sop_steps", "time_anchor_type"): "ALTER TABLE sop_steps DROP COLUMN time_anchor_type",
        ("sop_steps", "time_window_start_sec"): "ALTER TABLE sop_steps DROP COLUMN time_window_start_sec",
        ("sop_steps", "time_window_end_sec"): "ALTER TABLE sop_steps DROP COLUMN time_window_end_sec",
        ("execution_step_results", "timing_status"): "ALTER TABLE execution_step_results DROP COLUMN timing_status",
        ("execution_step_results", "risk_level_snapshot"): "ALTER TABLE execution_step_results DROP COLUMN risk_level_snapshot",
    }

    for (table_name, column_name), statement in drop_column_statements.items():
        if _table_exists(connection, table_name) and _column_exists(connection, table_name, column_name):
            with connection.cursor() as cursor:
                cursor.execute(statement)

    if not _table_exists(connection, "sop_step_prerequisites"):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sop_step_prerequisites (
                  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                  sop_step_id BIGINT UNSIGNED NOT NULL,
                  prerequisite_step_no INT NOT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_sop_step_prerequisites_pair (sop_step_id, prerequisite_step_no),
                  KEY idx_sop_step_prerequisites_step (sop_step_id),
                  CONSTRAINT fk_sop_step_prerequisites_step
                    FOREIGN KEY (sop_step_id) REFERENCES sop_steps (id)
                    ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )


def _normalize_step_type(value):
    text = str(value or "").strip().lower()
    return text if text in STEP_TYPE_VALUES else DEFAULT_STEP_TYPE


def _normalize_step_weight(value):
    try:
        weight = round(float(value), 1)
    except Exception:
        return DEFAULT_STEP_WEIGHT
    return min(5.0, max(0.5, weight))


def _normalize_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 3)
    except Exception:
        return None


def _normalize_duration_limit(value):
    number = _normalize_optional_float(value)
    if number is None or number <= 0:
        return None
    return number


def _normalize_prerequisite_step_nos(values, current_step_no=None):
    items = []
    for raw in values or []:
        try:
            step_no = int(raw)
        except Exception:
            continue
        if step_no <= 0:
            continue
        if current_step_no is not None and step_no >= int(current_step_no):
            continue
        if step_no not in items:
            items.append(step_no)
    return sorted(items)


def _normalize_step_record(step):
    step_no = int(step.get("stepNo") or 0)
    return {
        **step,
        "stepType": _normalize_step_type(step.get("stepType")),
        "stepWeight": _normalize_step_weight(step.get("stepWeight")),
        "conditionText": (step.get("conditionText") or "").strip(),
        "prerequisiteStepNos": _normalize_prerequisite_step_nos(step.get("prerequisiteStepNos"), step_no or None),
        "minDurationSec": _normalize_duration_limit(step.get("minDurationSec")),
        "maxDurationSec": _normalize_duration_limit(step.get("maxDurationSec")),
    }

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
        connection = _mysql_connection(database=None)
        try:
            with connection.cursor() as cursor:
                for statement in _split_sql_statements(_load_schema_sql()):
                    cursor.execute(statement)
            _run_schema_migrations(connection)
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


def _fetch_user_by_id(connection, user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, password_hash, display_name, role, status
            FROM users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cursor.fetchone()


def _password_matches(password, stored_hash):
    if not stored_hash:
        return False
    if stored_hash == password:
        return True
    if stored_hash == hashlib.sha256(password.encode("utf-8")).hexdigest():
        return True
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$", 3)
        if len(parts) != 4:
            return False
        _, iterations_raw, salt, expected_hash = parts
        try:
            iterations = int(iterations_raw)
        except (TypeError, ValueError):
            return False
        derived_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(derived_hash, expected_hash)
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


def get_user_by_username(username):
    if not username:
        return None
    with _get_connection() as connection:
        user = _fetch_user_by_name(connection, username)
        if not user:
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "displayName": user["display_name"],
            "status": user["status"],
        }


def get_user_by_id(user_id):
    if not user_id:
        return None
    with _get_connection() as connection:
        user = _fetch_user_by_id(connection, user_id)
        if not user or user.get("status") != "active":
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "displayName": user["display_name"],
            "status": user["status"],
        }


def has_active_session(user_id):
    if not user_id:
        return False
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM user_login_sessions
                WHERE user_id = %s AND status = 'active'
                LIMIT 1
                """,
                (user_id,),
            )
            has_session = cursor.fetchone() is not None
            if has_session:
                cursor.execute(
                    """
                    UPDATE user_login_sessions
                    SET status = 'revoked',
                        revoked_at = NOW()
                    WHERE user_id = %s AND status = 'active'
                    """,
                    (user_id,),
                )
        connection.commit()
    return False


def create_user_session(user_id, session_token):
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_login_sessions (user_id, session_token, status)
                VALUES (%s, %s, 'active')
                """,
                (user_id, session_token),
            )
        connection.commit()


def is_user_session_active(user_id, session_token):
    if not user_id or not session_token:
        return False
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM user_login_sessions
                WHERE user_id = %s AND session_token = %s AND status = 'active'
                LIMIT 1
                """,
                (user_id, session_token),
            )
            return cursor.fetchone() is not None


def revoke_user_session(user_id, session_token):
    if not user_id or not session_token:
        return
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_login_sessions
                SET status = 'revoked',
                    revoked_at = NOW()
                WHERE user_id = %s AND session_token = %s AND status = 'active'
                """,
                (user_id, session_token),
            )
        connection.commit()


def revoke_all_user_sessions(user_id):
    if not user_id:
        return
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_login_sessions
                SET status = 'revoked',
                    revoked_at = NOW()
                WHERE user_id = %s AND status = 'active'
                """,
                (user_id,),
            )
        connection.commit()


def create_user(username, password, display_name, role="user"):
    username = (username or "").strip()
    password = (password or "").strip()
    display_name = (display_name or "").strip()
    role = (role or "user").strip() or "user"

    if not username:
        raise ValueError("用户名不能为空")
    if not password:
        raise ValueError("密码不能为空")
    if len(username) < 3 or len(username) > 50:
        raise ValueError("用户名长度需在 3 到 50 个字符之间")
    if len(password) < 6:
        raise ValueError("密码长度不能少于 6 位")
    if role not in ("admin", "user"):
        raise ValueError("用户角色不合法")

    final_display_name = display_name or username
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    with _get_connection() as connection:
        existing = _fetch_user_by_name(connection, username)
        if existing:
            raise ValueError("用户名已存在")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, display_name, role, status)
                VALUES (%s, %s, %s, %s, 'active')
                """,
                (username, password_hash, final_display_name, role),
            )
            user_id = cursor.lastrowid
        connection.commit()

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "displayName": final_display_name,
        "status": "active",
    }


def list_users():
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, role, status, last_login_at, created_at, updated_at
                FROM users
                ORDER BY role ASC, created_at ASC, id ASC
                """
            )
            rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "username": row["username"],
            "displayName": row["display_name"],
            "role": row["role"],
            "status": row["status"],
            "lastLoginAt": _parse_datetime(row.get("last_login_at")),
            "createdAt": _parse_datetime(row.get("created_at")),
            "updatedAt": _parse_datetime(row.get("updated_at")),
        }
        for row in rows
    ]


def update_user_status(user_id, status):
    status = (status or "").strip()
    if status not in ("active", "disabled"):
        raise ValueError("用户状态不合法")

    with _get_connection() as connection:
        user = _fetch_user_by_id(connection, user_id)
        if not user:
            return None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET status = %s
                WHERE id = %s
                """,
                (status, user_id),
            )
        connection.commit()

    return get_user_by_id(user_id) or {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "displayName": user["display_name"],
        "status": status,
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
    prerequisite_map = {}

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

            cursor.execute(
                f"""
                SELECT *
                FROM sop_step_prerequisites
                WHERE sop_step_id IN ({step_placeholders})
                ORDER BY sop_step_id ASC, prerequisite_step_no ASC
                """,
                step_ids,
            )
            for row in cursor.fetchall():
                prerequisite_map.setdefault(row["sop_step_id"], []).append(int(row.get("prerequisite_step_no") or 0))

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
        normalized_step = _normalize_step_record(
            {
                "stepNo": int(step.get("step_no") or 0),
                "stepType": step.get("step_type"),
                "stepWeight": step.get("step_weight"),
                "conditionText": step.get("condition_text"),
                "prerequisiteStepNos": prerequisite_map.get(step["id"], []),
                "minDurationSec": step.get("min_duration_sec"),
                "maxDurationSec": step.get("max_duration_sec"),
            }
        )

        steps_by_sop.setdefault(step["sop_id"], []).append(
            {
                "stepNo": normalized_step["stepNo"],
                "description": step.get("description") or "",
                "videoMeta": demo_video,
                "demoVideo": demo_video,
                "stepType": normalized_step["stepType"],
                "stepWeight": normalized_step["stepWeight"],
                "conditionText": normalized_step["conditionText"],
                "prerequisiteStepNos": normalized_step["prerequisiteStepNos"],
                "minDurationSec": normalized_step["minDurationSec"],
                "maxDurationSec": normalized_step["maxDurationSec"],
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
    step = _normalize_step_record(step)
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

        for prerequisite_step_no in step.get("prerequisiteStepNos") or []:
            cursor.execute(
                """
                INSERT INTO sop_step_prerequisites (sop_step_id, prerequisite_step_no)
                VALUES (%s, %s)
                """,
                (step_id, prerequisite_step_no),
            )


def _upsert_sop_content(connection, sop_data, created_by_id=None):
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
                    status = %s,
                    created_by = COALESCE(created_by, %s)
                WHERE id = %s
                """,
                (
                    sop_data.get("name") or "",
                    sop_data.get("scene") or "",
                    sop_data.get("description") or "",
                    sop_data.get("stepCount") or len(steps),
                    demo_video_count,
                    sop_data.get("status") or "published",
                    created_by_id,
                    sop_row["id"],
                ),
            )
            sop_id = sop_row["id"]
            cursor.execute("DELETE FROM sop_steps WHERE sop_id = %s", (sop_id,))
        else:
            cursor.execute(
                """
                INSERT INTO sops (sop_code, name, scene, description, step_count, demo_video_count, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sop_data["id"],
                    sop_data.get("name") or "",
                    sop_data.get("scene") or "",
                    sop_data.get("description") or "",
                    sop_data.get("stepCount") or len(steps),
                    demo_video_count,
                    sop_data.get("status") or "published",
                    created_by_id,
                ),
            )
            sop_id = cursor.lastrowid

    for step in steps:
        step = _normalize_step_record(step)
        reference_features = step.get("referenceFeatures") or {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sop_steps (
                  sop_id, step_no, description, step_type, step_weight, condition_text,
                  min_duration_sec, max_duration_sec, reference_mode,
                  reference_summary, roi_hint, ai_used, reference_duration_sec, reference_fps,
                  reference_frame_count, raw_ai_result
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sop_id,
                    step.get("stepNo") or 0,
                    step.get("description") or "",
                    step.get("stepType") or DEFAULT_STEP_TYPE,
                    step.get("stepWeight") or DEFAULT_STEP_WEIGHT,
                    step.get("conditionText") or "",
                    step.get("minDurationSec"),
                    step.get("maxDurationSec"),
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


def add_sop(sop, created_by=None):
    with _get_connection() as connection:
        _upsert_sop_content(connection, sop, created_by_id=(created_by or {}).get("id"))
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


def _delete_dirs(paths):
    unique_dirs = []
    seen = set()
    for path in paths:
        text = str(path or "").strip()
        if not text:
            continue
        normalized = os.path.normcase(os.path.normpath(text))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_dirs.append(text)

    unique_dirs.sort(key=lambda item: len(Path(item).parts), reverse=True)
    for path in unique_dirs:
        try:
            if path and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def delete_sop(sop_id):
    with _get_connection() as connection:
        sop_row = _fetch_sop_row_by_code(connection, sop_id)
        if not sop_row:
            return False

        media_paths = []
        step_ids = []
        cleanup_dirs = [
            str(ADMIN_MEDIA_DIR / "sop_step_demo" / sop_id),
        ]
        if USER_MEDIA_DIR.exists():
            for user_dir in USER_MEDIA_DIR.iterdir():
                if user_dir.is_dir():
                    cleanup_dirs.append(str(user_dir / sop_id))

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sop_executions WHERE sop_id = %s", (sop_row["id"],))
            execution_ids = [row["id"] for row in cursor.fetchall()]
            cursor.execute("SELECT id FROM sop_steps WHERE sop_id = %s", (sop_row["id"],))
            step_ids = [row["id"] for row in cursor.fetchall()]

            media_filters = ["related_sop_id = %s"]
            media_params = [sop_row["id"]]

            if step_ids:
                step_placeholders = ", ".join(["%s"] * len(step_ids))
                media_filters.append(f"related_step_id IN ({step_placeholders})")
                media_params.extend(step_ids)

            if execution_ids:
                execution_placeholders = ", ".join(["%s"] * len(execution_ids))
                media_filters.append(f"related_execution_id IN ({execution_placeholders})")
                media_params.extend(execution_ids)

            cursor.execute(
                f"""
                SELECT storage_path
                FROM media_files
                WHERE {" OR ".join(media_filters)}
                """,
                media_params,
            )
            media_paths = [row["storage_path"] for row in cursor.fetchall()]

            cursor.execute(
                f"DELETE FROM media_files WHERE {' OR '.join(media_filters)}",
                media_params,
            )

            if execution_ids:
                cursor.execute(
                    "DELETE FROM sop_executions WHERE sop_id = %s",
                    (sop_row["id"],),
                )

            cursor.execute("DELETE FROM evaluation_jobs WHERE sop_id = %s", (sop_row["id"],))
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'evaluation_tasks'
                """,
                (MYSQL_SETTINGS["database"],),
            )
            legacy_tasks_exists = int((cursor.fetchone() or {}).get("count") or 0) > 0
            if legacy_tasks_exists:
                cursor.execute("DELETE FROM evaluation_tasks WHERE sop_id = %s", (sop_row["id"],))
            cursor.execute("DELETE FROM sops WHERE id = %s", (sop_row["id"],))

        connection.commit()
        _delete_files(media_paths)
        _delete_dirs(cleanup_dirs)
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
    uploaded_by_name = ""
    if isinstance(uploaded_by, dict):
        uploaded_by_name = uploaded_by.get("username") or uploaded_by.get("displayName") or ""
    elif isinstance(uploaded_by, str):
        uploaded_by_name = uploaded_by

    base_dir = ADMIN_MEDIA_DIR if owner_role == "admin" else USER_MEDIA_DIR
    if owner_role == "admin" and business_type == "sop_step_demo":
        sub_dir = base_dir / "sop_step_demo" / (related_sop_id or "unassigned") / (
            f"step_{related_step_no}" if related_step_no else "step_unknown"
        )
    elif owner_role == "user" and business_type in {"execution_upload", "evaluation_job_upload"}:
        user_dir = _safe_dir_name(uploaded_by_name, "unknown_user")
        sop_dir = _safe_dir_name(related_sop_id, "unknown_sop")
        sub_dir = base_dir / user_dir / sop_dir
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

        if isinstance(uploaded_by, dict):
            uploaded_by_id = uploaded_by.get("id")
        elif isinstance(uploaded_by, int):
            uploaded_by_id = uploaded_by
        else:
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


def get_media(media_id, current_user=None):
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

    if current_user and current_user.get("role") != "admin":
        allow_access = False
        if row.get("owner_role") == "admin" and row.get("business_type") == "sop_step_demo":
            allow_access = True
        elif row.get("uploaded_by") == current_user.get("id"):
            allow_access = True
        elif row.get("related_execution_id"):
            with _get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT user_id
                        FROM sop_executions
                        WHERE id = %s
                        LIMIT 1
                        """,
                        (row.get("related_execution_id"),),
                    )
                    execution_row = cursor.fetchone()
            allow_access = execution_row and execution_row.get("user_id") == current_user.get("id")
        if not allow_access:
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


def _parse_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _fetch_evaluation_job_rows(connection, job_codes=None, current_user=None, status=None, limit=None):
    sql = """
        SELECT j.id, j.job_code, j.sop_id, j.user_id, j.uploaded_video_media_id, j.status, j.stage,
               j.progress_percent, j.retry_count, j.max_retry_count, j.failure_reason, j.failure_detail,
               j.result_execution_id, j.queue_at, j.start_at, j.finish_at, j.created_at, j.updated_at,
               s.sop_code, s.name AS task_name, s.scene,
               u.username AS user_name, u.display_name AS user_display_name,
               mf.media_code AS uploaded_video_code, mf.original_name AS uploaded_video_name,
               mf.mime_type AS uploaded_video_type, mf.file_size AS uploaded_video_size,
               mf.last_modified_ms AS uploaded_video_last_modified,
               e.execution_code AS result_record_code
        FROM evaluation_jobs j
        JOIN sops s ON s.id = j.sop_id
        LEFT JOIN users u ON u.id = j.user_id
        LEFT JOIN media_files mf ON mf.id = j.uploaded_video_media_id
        LEFT JOIN sop_executions e ON e.id = j.result_execution_id
    """
    params = []
    conditions = []
    if job_codes:
        placeholders = ", ".join(["%s"] * len(job_codes))
        conditions.append(f"j.job_code IN ({placeholders})")
        params.extend(job_codes)
    if status:
        conditions.append("j.status = %s")
        params.append(status)
    if current_user and current_user.get("role") != "admin":
        conditions.append("j.user_id = %s")
        params.append(current_user.get("id"))
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY j.created_at DESC"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _build_evaluation_job_records(connection, job_codes=None, current_user=None, status=None, limit=None):
    rows = _fetch_evaluation_job_rows(
        connection,
        job_codes=job_codes,
        current_user=current_user,
        status=status,
        limit=limit,
    )
    if not rows:
        return []

    job_ids = [row["id"] for row in rows]
    placeholders = ", ".join(["%s"] * len(job_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT job_id, level, stage, message, created_at
            FROM evaluation_job_logs
            WHERE job_id IN ({placeholders})
            ORDER BY created_at ASC, id ASC
            """,
            job_ids,
        )
        log_rows = cursor.fetchall()

    logs_map = {}
    for row in log_rows:
        logs_map.setdefault(row["job_id"], []).append(
            {
                "time": _parse_datetime(row.get("created_at")),
                "level": row.get("level") or "info",
                "stage": row.get("stage") or "",
                "message": row.get("message") or "",
            }
        )

    records = []
    for row in rows:
        uploaded_video = None
        if row.get("uploaded_video_code"):
            uploaded_video = {
                "mediaId": row.get("uploaded_video_code") or "",
                "name": row.get("uploaded_video_name") or "",
                "type": row.get("uploaded_video_type") or "",
                "size": row.get("uploaded_video_size"),
                "lastModified": row.get("uploaded_video_last_modified"),
            }

        records.append(
            {
                "id": row.get("job_code") or "",
                "taskId": row.get("sop_code") or "",
                "taskName": row.get("task_name") or "",
                "scene": row.get("scene") or "",
                "userId": row.get("user_id"),
                "userName": row.get("user_name") or "",
                "userDisplayName": row.get("user_display_name") or row.get("user_name") or "",
                "status": row.get("status") or "queued",
                "stage": row.get("stage") or "submitted",
                "progressPercent": _parse_int(row.get("progress_percent"), 0),
                "retryCount": _parse_int(row.get("retry_count"), 0),
                "maxRetryCount": _parse_int(row.get("max_retry_count"), 3),
                "failureReason": row.get("failure_reason") or "",
                "failureDetail": row.get("failure_detail") or "",
                "resultRecordId": row.get("result_record_code") or "",
                "queueTime": _parse_datetime(row.get("queue_at")),
                "startTime": _parse_datetime(row.get("start_at")),
                "finishTime": _parse_datetime(row.get("finish_at")),
                "createdAt": _parse_datetime(row.get("created_at")),
                "updatedAt": _parse_datetime(row.get("updated_at")),
                "uploadedVideo": serialize_uploaded_video(uploaded_video),
                "logs": logs_map.get(row["id"], []),
            }
        )
    return records


def _append_job_log(connection, job_db_id, level, stage, message):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO evaluation_job_logs (job_id, level, stage, message)
            VALUES (%s, %s, %s, %s)
            """,
            (job_db_id, level or "info", stage or "submitted", (message or "").strip() or "系统已记录任务状态"),
        )


def list_evaluation_jobs(current_user=None, status=None, limit=100):
    with _get_connection() as connection:
        return _build_evaluation_job_records(connection, current_user=current_user, status=status, limit=limit)


def get_evaluation_job(job_id, current_user=None):
    with _get_connection() as connection:
        records = _build_evaluation_job_records(connection, [job_id], current_user=current_user)
        return records[0] if records else None


def create_evaluation_job(sop_id, uploaded_video, current_user=None, retry_count=0):
    with _get_connection() as connection:
        sop_row = _fetch_sop_row_by_code(connection, sop_id)
        if not sop_row:
            raise ValueError("SOP not found")

        uploaded_video_db_id = None
        uploaded_video_code = (uploaded_video or {}).get("mediaId")
        if uploaded_video_code:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM media_files WHERE media_code = %s LIMIT 1", (uploaded_video_code,))
                media_row = cursor.fetchone()
                uploaded_video_db_id = media_row["id"] if media_row else None

        job_code = f"job-{uuid.uuid4().hex}"
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO evaluation_jobs (
                  job_code, sop_id, user_id, uploaded_video_media_id, status, stage, progress_percent,
                  retry_count, max_retry_count, queue_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job_code,
                    sop_row["id"],
                    current_user.get("id") if current_user else None,
                    uploaded_video_db_id,
                    "queued",
                    "submitted",
                    0,
                    max(0, int(retry_count or 0)),
                    3,
                    datetime.now(),
                ),
            )
            job_db_id = cursor.lastrowid
        _append_job_log(connection, job_db_id, "info", "submitted", "评测任务已创建")
        _append_job_log(connection, job_db_id, "info", "waiting", "任务已进入评测队列，等待处理")
        connection.commit()
    return get_evaluation_job(job_code, current_user=current_user)


def append_evaluation_job_log(job_id, level="info", stage="submitted", message=""):
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM evaluation_jobs WHERE job_code = %s LIMIT 1", (job_id,))
            row = cursor.fetchone()
            if not row:
                return False
        _append_job_log(connection, row["id"], level, stage, message)
        connection.commit()
    return True


def update_evaluation_job(
    job_id,
    *,
    status=None,
    stage=None,
    progress_percent=None,
    failure_reason=None,
    failure_detail=None,
    result_record_id=None,
    start_time=None,
    finish_time=None,
):
    fields = []
    params = []
    if status is not None:
        fields.append("status = %s")
        params.append(status)
    if stage is not None:
        fields.append("stage = %s")
        params.append(stage)
    if progress_percent is not None:
        fields.append("progress_percent = %s")
        params.append(max(0, min(100, int(progress_percent))))
    if failure_reason is not None:
        fields.append("failure_reason = %s")
        params.append(failure_reason)
    if failure_detail is not None:
        fields.append("failure_detail = %s")
        params.append(failure_detail)
    if start_time is not None:
        fields.append("start_at = %s")
        params.append(start_time)
    if finish_time is not None:
        fields.append("finish_at = %s")
        params.append(finish_time)
    if result_record_id is not None:
        fields.append(
            "result_execution_id = (SELECT id FROM sop_executions WHERE execution_code = %s LIMIT 1)"
        )
        params.append(result_record_id)

    if not fields:
        return get_evaluation_job(job_id)

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE evaluation_jobs
                SET {", ".join(fields)}
                WHERE job_code = %s
                """,
                [*params, job_id],
            )
        connection.commit()
    return get_evaluation_job(job_id)


def claim_next_evaluation_job():
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, job_code
                FROM evaluation_jobs
                WHERE status = 'queued'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute(
                """
                UPDATE evaluation_jobs
                SET status = 'processing',
                    stage = 'preparing_video',
                    progress_percent = 10,
                    start_at = %s
                WHERE id = %s AND status = 'queued'
                """,
                (datetime.now(), row["id"]),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
        _append_job_log(connection, row["id"], "info", "preparing_video", "任务已开始处理")
        connection.commit()
        return _build_evaluation_job_records(connection, [row["job_code"]])[0]


def retry_evaluation_job(job_id, current_user=None):
    with _get_connection() as connection:
        records = _build_evaluation_job_records(connection, [job_id], current_user=current_user)
        if not records:
            return None
        source = records[0]
        if source.get("status") != "failed":
            raise ValueError("Only failed jobs can be retried")
    source_video = source.get("uploadedVideo") or {}
    return create_evaluation_job(
        source.get("taskId"),
        {"mediaId": source_video.get("mediaId")},
        current_user=current_user,
        retry_count=(source.get("retryCount") or 0) + 1,
    )


def _fetch_history_rows(
    connection,
    execution_codes=None,
    current_user=None,
    keyword=None,
    ai_status=None,
    review_status=None,
    sort_order="desc",
):
    sql = """
        SELECT e.id, e.execution_code, e.sop_id, e.user_id, e.uploaded_video_media_id, e.finish_time,
               e.score, e.ai_status, e.prerequisite_violated, e.created_at,
               s.sop_code, s.name AS task_name, s.scene,
               u.username AS user_name, u.display_name AS user_display_name
        FROM sop_executions e
        JOIN sops s ON s.id = e.sop_id
        LEFT JOIN users u ON u.id = e.user_id
    """
    params = []
    conditions = []
    if execution_codes:
        placeholders = ", ".join(["%s"] * len(execution_codes))
        conditions.append(f"e.execution_code IN ({placeholders})")
        params.extend(execution_codes)
    if current_user and current_user.get("role") != "admin":
        conditions.append("e.user_id = %s")
        params.append(current_user.get("id"))
    if keyword:
        conditions.append("s.name LIKE %s")
        params.append(f"%{keyword}%")
    if ai_status:
        conditions.append("e.ai_status = %s")
        params.append(ai_status)
    if review_status == "pending":
        conditions.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM manual_reviews mr2
                WHERE mr2.execution_id = e.id
                  AND COALESCE(TRIM(mr2.review_status), '') <> ''
            )
            """
        )
    elif review_status:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM manual_reviews mr2
                WHERE mr2.execution_id = e.id
                  AND mr2.review_status = %s
            )
            """
        )
        params.append(review_status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    final_sort_order = "ASC" if str(sort_order).lower() == "asc" else "DESC"
    sql += f" ORDER BY e.finish_time {final_sort_order}, e.created_at {final_sort_order}"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _fetch_history_detail_rows(connection, execution_ids):
    if not execution_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(execution_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT e.id, e.feedback, e.sequence_assessment, e.payload_preview, e.raw_model_result
            FROM sop_executions e
            WHERE e.id IN ({placeholders})
            """,
            execution_ids,
        )
        return {row["id"]: row for row in cursor.fetchall()}


def _build_history_records(
    connection,
    execution_codes=None,
    current_user=None,
    keyword=None,
    ai_status=None,
    review_status=None,
    sort_order="desc",
):
    rows = _fetch_history_rows(
        connection,
        execution_codes,
        current_user=current_user,
        keyword=keyword,
        ai_status=ai_status,
        review_status=review_status,
        sort_order=sort_order,
    )
    if not rows:
        return []

    execution_ids = [row["id"] for row in rows]
    detail_rows = _fetch_history_detail_rows(connection, execution_ids)
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
                "applicable": bool(row.get("applicable")) if row.get("applicable") is not None else True,
                "includedInScore": bool(row.get("included_in_score")) if row.get("included_in_score") is not None else True,
                "issueType": row.get("issue_type") or "",
                "completionLevel": row.get("completion_level") or "",
                "orderIssue": bool(row.get("order_issue")),
                "prerequisiteViolated": bool(row.get("prerequisite_violated")),
                "detectedStartSec": float(row.get("detected_start_sec")) if row.get("detected_start_sec") is not None else None,
                "detectedEndSec": float(row.get("detected_end_sec")) if row.get("detected_end_sec") is not None else None,
                "stepWeight": _normalize_step_weight(row.get("step_weight_snapshot")),
                "stepType": _normalize_step_type(row.get("step_type_snapshot")),
                "minDurationSec": _normalize_duration_limit(row.get("min_duration_sec_snapshot")),
                "maxDurationSec": _normalize_duration_limit(row.get("max_duration_sec_snapshot")),
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
        detail_row = detail_rows.get(row["id"], {})
        records.append(
            {
                "id": row.get("execution_code"),
                "createdAtMs": int(row["created_at"].timestamp() * 1000) if isinstance(row.get("created_at"), datetime) else 0,
                "taskId": row.get("sop_code") or "",
                "taskName": row.get("task_name") or "",
                "scene": row.get("scene") or "",
                "userId": row.get("user_id"),
                "userName": row.get("user_name") or "",
                "userDisplayName": row.get("user_display_name") or row.get("user_name") or "",
                "finishTime": _parse_datetime(row.get("finish_time")),
                "score": float(row.get("score")) if row.get("score") is not None else None,
                "status": row.get("ai_status") or "failed",
                "manualReview": review_map.get(row["id"]),
                "detail": {
                    "feedback": detail_row.get("feedback") or "",
                    "issues": issues_map.get(row["id"], []),
                    "sequenceAssessment": detail_row.get("sequence_assessment") or "",
                    "prerequisiteViolated": bool(row.get("prerequisite_violated")),
                    "stepResults": step_results_map.get(row["id"], []),
                    "sopSteps": sop_steps_map.get(row["sop_id"], []),
                    "uploadedVideo": media_map.get(row["id"]),
                    "tokenUsage": _extract_token_usage(detail_row.get("raw_model_result")),
                    "payloadPreview": _json_loads(detail_row.get("payload_preview"), None),
                    "rawModelResult": _json_loads(detail_row.get("raw_model_result"), None),
                },
            }
        )
    return records


def list_history(current_user=None, keyword=None, ai_status=None, review_status=None, sort_order="desc"):
    with _get_connection() as connection:
        return _build_history_records(
            connection,
            current_user=current_user,
            keyword=keyword,
            ai_status=ai_status,
            review_status=review_status,
            sort_order=sort_order,
        )


def get_history(record_id, current_user=None):
    with _get_connection() as connection:
        records = _build_history_records(connection, [record_id], current_user=current_user)
        return records[0] if records else None


def add_history(record, current_user=None):
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
                    current_user.get("id") if current_user else None,
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
                      execution_id, sop_step_id, step_no, description, passed, score, confidence, applicable,
                      included_in_score, issue_type, completion_level, order_issue, prerequisite_violated,
                      detected_start_sec, detected_end_sec, step_weight_snapshot, step_type_snapshot,
                      min_duration_sec_snapshot, max_duration_sec_snapshot, evidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        execution_id,
                        step_rows.get(int(item.get("stepNo") or 0)),
                        item.get("stepNo") or 0,
                        item.get("description") or "",
                        1 if item.get("passed") else 0,
                        item.get("score") or 0,
                        item.get("confidence") or 0,
                        1 if item.get("applicable", True) else 0,
                        1 if item.get("includedInScore", True) else 0,
                        item.get("issueType") or "",
                        item.get("completionLevel") or "",
                        1 if item.get("orderIssue") else 0,
                        1 if item.get("prerequisiteViolated") else 0,
                        item.get("detectedStartSec"),
                        item.get("detectedEndSec"),
                        _normalize_step_weight(item.get("stepWeight")),
                        _normalize_step_type(item.get("stepType")),
                        _normalize_duration_limit(item.get("minDurationSec")),
                        _normalize_duration_limit(item.get("maxDurationSec")),
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
    return get_history(record.get("id"), current_user=current_user)


def update_manual_review(record_id, review, current_user=None):
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sop_executions WHERE execution_code = %s LIMIT 1", (record_id,))
            execution_row = cursor.fetchone()
            if not execution_row:
                return None

        reviewer_id = (current_user or {}).get("id") or _resolve_user_id(connection, review.get("reviewer"))
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
    return get_history(record_id, current_user=current_user)


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
                "stepType": _normalize_step_type(step.get("stepType")),
                "stepWeight": _normalize_step_weight(step.get("stepWeight")),
                "conditionText": (step.get("conditionText") or "").strip(),
                "prerequisiteStepNos": _normalize_prerequisite_step_nos(step.get("prerequisiteStepNos"), step.get("stepNo")),
                "minDurationSec": _normalize_duration_limit(step.get("minDurationSec")),
                "maxDurationSec": _normalize_duration_limit(step.get("maxDurationSec")),
                "referenceMode": step.get("referenceMode") or ("video" if step.get("referenceFrames") else "text"),
                "referenceSummary": step.get("referenceSummary") or "",
                "referenceFeatures": step.get("referenceFeatures"),
                "substeps": step.get("substeps") or [],
                "roiHint": step.get("roiHint") or "",
                "aiUsed": bool(step.get("aiUsed")),
                "tokenUsage": _extract_token_usage(step.get("rawAIResult")),
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
            "tokenUsage": _extract_token_usage(step.get("rawAIResult")),
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

    issue_bucket = {}
    for record in history:
        for step in (record.get("detail") or {}).get("stepResults") or []:
            issue_type = (step.get("issueType") or "").strip()
            if not issue_type or issue_type == "正常":
                continue
            issue_bucket[issue_type] = issue_bucket.get(issue_type, 0) + 1

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
    issue_type_stats = [
        {"issueType": issue_type, "count": count}
        for issue_type, count in sorted(issue_bucket.items(), key=lambda item: item[1], reverse=True)
    ]

    return {
        "summaryStats": {
            "totalSops": len(sops),
            "totalExecutions": total_executions,
            "pendingReviewCount": pending_review_count,
            "passRate": (passed_count / total_executions * 100) if total_executions else 0,
        },
        "sopStatsList": sop_stats_list,
        "issueTypeStats": issue_type_stats,
    }
