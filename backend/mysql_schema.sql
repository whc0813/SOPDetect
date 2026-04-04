CREATE DATABASE IF NOT EXISTS sop_eval_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE sop_eval_system;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_login_sessions (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  session_token VARCHAR(128) NOT NULL,
  status ENUM('active', 'revoked') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revoked_at DATETIME NULL,
  UNIQUE KEY uk_user_login_sessions_token (session_token),
  KEY idx_user_login_sessions_user_status (user_id, status),
  CONSTRAINT fk_user_login_sessions_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sops (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  sop_code VARCHAR(50) NOT NULL,
  name VARCHAR(200) NOT NULL,
  scene VARCHAR(200) NULL,
  description TEXT NULL,
  step_count INT NOT NULL DEFAULT 0,
  demo_video_count INT NOT NULL DEFAULT 0,
  penalty_config JSON NULL,
  status ENUM('draft', 'published', 'archived') NOT NULL DEFAULT 'published',
  created_by BIGINT UNSIGNED NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_sops_code (sop_code),
  KEY idx_sops_status_created (status, created_at),
  CONSTRAINT fk_sops_created_by
    FOREIGN KEY (created_by) REFERENCES users (id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sop_steps (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  sop_id BIGINT UNSIGNED NOT NULL,
  step_no INT NOT NULL,
  description TEXT NOT NULL,
  step_type ENUM('required', 'optional', 'conditional') NOT NULL DEFAULT 'required',
  step_weight DECIMAL(4,1) NOT NULL DEFAULT 1.0,
  condition_text TEXT NULL,
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS media_files (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  media_code VARCHAR(64) NOT NULL,
  owner_role ENUM('admin', 'user') NOT NULL,
  business_type ENUM('sop_step_demo', 'execution_upload', 'evaluation_job_upload', 'other') NOT NULL,
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS execution_step_results (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  execution_id BIGINT UNSIGNED NOT NULL,
  sop_step_id BIGINT UNSIGNED NULL,
  step_no INT NOT NULL,
  description TEXT NOT NULL,
  passed TINYINT(1) NOT NULL,
  score DECIMAL(5,2) NOT NULL,
  confidence DECIMAL(5,2) NOT NULL,
  applicable TINYINT(1) NOT NULL DEFAULT 1,
  included_in_score TINYINT(1) NOT NULL DEFAULT 1,
  issue_type VARCHAR(100) NULL,
  completion_level VARCHAR(100) NULL,
  order_issue TINYINT(1) NOT NULL DEFAULT 0,
  prerequisite_violated TINYINT(1) NOT NULL DEFAULT 0,
  detected_start_sec DECIMAL(8,3) NULL,
  detected_end_sec DECIMAL(8,3) NULL,
  step_weight_snapshot DECIMAL(4,1) NOT NULL DEFAULT 1.0,
  step_type_snapshot VARCHAR(20) NOT NULL DEFAULT 'required',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation_jobs (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  job_code VARCHAR(64) NOT NULL,
  sop_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NULL,
  uploaded_video_media_id BIGINT UNSIGNED NULL,
  status ENUM('queued', 'processing', 'succeeded', 'failed') NOT NULL DEFAULT 'queued',
  stage VARCHAR(50) NOT NULL DEFAULT 'submitted',
  progress_percent INT NOT NULL DEFAULT 0,
  retry_count INT NOT NULL DEFAULT 0,
  max_retry_count INT NOT NULL DEFAULT 3,
  failure_reason VARCHAR(255) NULL,
  failure_detail TEXT NULL,
  result_execution_id BIGINT UNSIGNED NULL,
  queue_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  start_at DATETIME NULL,
  finish_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_evaluation_jobs_code (job_code),
  KEY idx_evaluation_jobs_user_status (user_id, status, created_at),
  KEY idx_evaluation_jobs_status_created (status, created_at),
  CONSTRAINT fk_evaluation_jobs_sop
    FOREIGN KEY (sop_id) REFERENCES sops (id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_jobs_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE SET NULL,
  CONSTRAINT fk_evaluation_jobs_video
    FOREIGN KEY (uploaded_video_media_id) REFERENCES media_files (id)
    ON DELETE SET NULL,
  CONSTRAINT fk_evaluation_jobs_execution
    FOREIGN KEY (result_execution_id) REFERENCES sop_executions (id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS evaluation_job_logs (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  level ENUM('info', 'warning', 'error') NOT NULL DEFAULT 'info',
  stage VARCHAR(50) NOT NULL DEFAULT 'submitted',
  message VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_evaluation_job_logs_job (job_id, created_at),
  CONSTRAINT fk_evaluation_job_logs_job
    FOREIGN KEY (job_id) REFERENCES evaluation_jobs (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
