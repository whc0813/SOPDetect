CREATE DATABASE IF NOT EXISTS sop_eval_system
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE sop_eval_system;

CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `display_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('admin','user') COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('active','disabled') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `last_login_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`),
  KEY `idx_users_role_status` (`role`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_login_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `session_token` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` enum('active','revoked') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `revoked_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_login_sessions_token` (`session_token`),
  KEY `idx_user_login_sessions_user_status` (`user_id`,`status`),
  CONSTRAINT `fk_user_login_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_configs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `config_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'default',
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'dashscope',
  `base_url` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `api_key_encrypted` text COLLATE utf8mb4_unicode_ci,
  `fps` decimal(4,2) NOT NULL DEFAULT '2.00',
  `temperature` decimal(3,2) NOT NULL DEFAULT '0.10',
  `timeout_ms` int NOT NULL DEFAULT '120000',
  `is_default` tinyint(1) NOT NULL DEFAULT '1',
  `created_by` bigint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ai_configs_name` (`config_name`),
  KEY `idx_ai_configs_default` (`is_default`),
  KEY `fk_ai_configs_created_by` (`created_by`),
  CONSTRAINT `fk_ai_configs_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sops` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `sop_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scene` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `step_count` int NOT NULL DEFAULT '0',
  `demo_video_count` int NOT NULL DEFAULT '0',
  `status` enum('draft','published','archived') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'published',
  `created_by` bigint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sops_code` (`sop_code`),
  KEY `idx_sops_status_created` (`status`,`created_at`),
  KEY `fk_sops_created_by` (`created_by`),
  CONSTRAINT `fk_sops_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sop_steps` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `sop_id` bigint unsigned NOT NULL,
  `step_no` int NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `step_type` enum('required','optional','conditional') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'required',
  `condition_text` text COLLATE utf8mb4_unicode_ci,
  `min_duration_sec` decimal(8,3) DEFAULT NULL,
  `max_duration_sec` decimal(8,3) DEFAULT NULL,
  `reference_mode` enum('text','video') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'text',
  `reference_summary` text COLLATE utf8mb4_unicode_ci,
  `roi_hint` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ai_used` tinyint(1) NOT NULL DEFAULT '0',
  `reference_duration_sec` decimal(8,3) DEFAULT NULL,
  `reference_fps` decimal(6,3) DEFAULT NULL,
  `reference_frame_count` int DEFAULT NULL,
  `raw_ai_result` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sop_steps_no` (`sop_id`,`step_no`),
  KEY `idx_sop_steps_sop` (`sop_id`),
  CONSTRAINT `fk_sop_steps_sop` FOREIGN KEY (`sop_id`) REFERENCES `sops` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `media_files` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `media_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner_role` enum('admin','user') COLLATE utf8mb4_unicode_ci NOT NULL,
  `business_type` enum('sop_step_demo','execution_upload','evaluation_job_upload','other') COLLATE utf8mb4_unicode_ci NOT NULL,
  `related_sop_id` bigint unsigned DEFAULT NULL,
  `related_step_id` bigint unsigned DEFAULT NULL,
  `related_execution_id` bigint unsigned DEFAULT NULL,
  `original_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stored_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_ext` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_size` bigint unsigned NOT NULL,
  `storage_disk` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'local',
  `storage_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `access_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_modified_ms` bigint DEFAULT NULL,
  `uploaded_by` bigint unsigned DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_media_files_code` (`media_code`),
  KEY `idx_media_owner_business` (`owner_role`,`business_type`),
  KEY `idx_media_sop_step` (`related_sop_id`,`related_step_id`),
  KEY `idx_media_execution` (`related_execution_id`),
  KEY `fk_media_related_step` (`related_step_id`),
  KEY `fk_media_uploaded_by` (`uploaded_by`),
  CONSTRAINT `fk_media_related_sop` FOREIGN KEY (`related_sop_id`) REFERENCES `sops` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_media_related_step` FOREIGN KEY (`related_step_id`) REFERENCES `sop_steps` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_media_uploaded_by` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sop_step_keyframes` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `sop_step_id` bigint unsigned NOT NULL,
  `frame_type` enum('reference','analysis') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'reference',
  `sort_order` int NOT NULL,
  `timestamp_sec` decimal(8,3) DEFAULT NULL,
  `image_data` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sop_step_keyframes_order` (`sop_step_id`,`frame_type`,`sort_order`),
  KEY `idx_sop_step_keyframes_step` (`sop_step_id`),
  CONSTRAINT `fk_sop_step_keyframes_step` FOREIGN KEY (`sop_step_id`) REFERENCES `sop_steps` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sop_step_substeps` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `sop_step_id` bigint unsigned NOT NULL,
  `sort_order` int NOT NULL,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `timestamp_sec` decimal(8,3) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sop_step_substeps_order` (`sop_step_id`,`sort_order`),
  KEY `idx_sop_step_substeps_step` (`sop_step_id`),
  CONSTRAINT `fk_sop_step_substeps_step` FOREIGN KEY (`sop_step_id`) REFERENCES `sop_steps` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sop_step_prerequisites` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `sop_step_id` bigint unsigned NOT NULL,
  `prerequisite_step_no` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sop_step_prerequisites_pair` (`sop_step_id`,`prerequisite_step_no`),
  KEY `idx_sop_step_prerequisites_step` (`sop_step_id`),
  CONSTRAINT `fk_sop_step_prerequisites_step` FOREIGN KEY (`sop_step_id`) REFERENCES `sop_steps` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sop_executions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `execution_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sop_id` bigint unsigned NOT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `uploaded_video_media_id` bigint unsigned DEFAULT NULL,
  `finish_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ai_status` enum('passed','failed') COLLATE utf8mb4_unicode_ci NOT NULL,
  `feedback` text COLLATE utf8mb4_unicode_ci,
  `sequence_assessment` text COLLATE utf8mb4_unicode_ci,
  `prerequisite_violated` tinyint(1) NOT NULL DEFAULT '0',
  `payload_preview` json DEFAULT NULL,
  `raw_model_result` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sop_executions_code` (`execution_code`),
  KEY `idx_sop_executions_sop` (`sop_id`),
  KEY `idx_sop_executions_user` (`user_id`),
  KEY `idx_sop_executions_status_time` (`ai_status`,`finish_time`),
  KEY `fk_sop_executions_video` (`uploaded_video_media_id`),
  CONSTRAINT `fk_sop_executions_sop` FOREIGN KEY (`sop_id`) REFERENCES `sops` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sop_executions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_sop_executions_video` FOREIGN KEY (`uploaded_video_media_id`) REFERENCES `media_files` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `execution_issues` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `execution_id` bigint unsigned NOT NULL,
  `issue_text` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sort_order` int NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_execution_issues_execution` (`execution_id`),
  CONSTRAINT `fk_execution_issues_execution` FOREIGN KEY (`execution_id`) REFERENCES `sop_executions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `execution_step_results` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `execution_id` bigint unsigned NOT NULL,
  `sop_step_id` bigint unsigned DEFAULT NULL,
  `step_no` int NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `passed` tinyint(1) NOT NULL,
  `confidence` decimal(5,2) NOT NULL,
  `applicable` tinyint(1) NOT NULL DEFAULT '1',
  `included_in_score` tinyint(1) NOT NULL DEFAULT '1',
  `issue_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `completion_level` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_issue` tinyint(1) NOT NULL DEFAULT '0',
  `prerequisite_violated` tinyint(1) NOT NULL DEFAULT '0',
  `detected_start_sec` decimal(8,3) DEFAULT NULL,
  `detected_end_sec` decimal(8,3) DEFAULT NULL,
  `step_type_snapshot` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'required',
  `min_duration_sec_snapshot` decimal(8,3) DEFAULT NULL,
  `max_duration_sec_snapshot` decimal(8,3) DEFAULT NULL,
  `evidence` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_execution_step_results_no` (`execution_id`,`step_no`),
  KEY `idx_execution_step_results_step` (`sop_step_id`),
  CONSTRAINT `fk_execution_step_results_execution` FOREIGN KEY (`execution_id`) REFERENCES `sop_executions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_execution_step_results_sop_step` FOREIGN KEY (`sop_step_id`) REFERENCES `sop_steps` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `manual_reviews` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `execution_id` bigint unsigned NOT NULL,
  `review_status` enum('approved','rejected','needs_attention') COLLATE utf8mb4_unicode_ci NOT NULL,
  `review_note` text COLLATE utf8mb4_unicode_ci,
  `reviewer_id` bigint unsigned DEFAULT NULL,
  `review_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_manual_reviews_execution` (`execution_id`),
  KEY `idx_manual_reviews_status_time` (`review_status`,`review_time`),
  KEY `fk_manual_reviews_reviewer` (`reviewer_id`),
  CONSTRAINT `fk_manual_reviews_execution` FOREIGN KEY (`execution_id`) REFERENCES `sop_executions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_manual_reviews_reviewer` FOREIGN KEY (`reviewer_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `evaluation_jobs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `job_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sop_id` bigint unsigned NOT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `uploaded_video_media_id` bigint unsigned DEFAULT NULL,
  `status` enum('queued','processing','succeeded','failed') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'queued',
  `stage` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'submitted',
  `progress_percent` int NOT NULL DEFAULT '0',
  `retry_count` int NOT NULL DEFAULT '0',
  `max_retry_count` int NOT NULL DEFAULT '3',
  `failure_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `failure_detail` text COLLATE utf8mb4_unicode_ci,
  `result_execution_id` bigint unsigned DEFAULT NULL,
  `queue_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `start_at` datetime DEFAULT NULL,
  `finish_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_evaluation_jobs_code` (`job_code`),
  KEY `idx_evaluation_jobs_user_status` (`user_id`,`status`,`created_at`),
  KEY `idx_evaluation_jobs_status_created` (`status`,`created_at`),
  KEY `fk_evaluation_jobs_sop` (`sop_id`),
  KEY `fk_evaluation_jobs_video` (`uploaded_video_media_id`),
  KEY `fk_evaluation_jobs_execution` (`result_execution_id`),
  CONSTRAINT `fk_evaluation_jobs_execution` FOREIGN KEY (`result_execution_id`) REFERENCES `sop_executions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_evaluation_jobs_sop` FOREIGN KEY (`sop_id`) REFERENCES `sops` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_evaluation_jobs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_evaluation_jobs_video` FOREIGN KEY (`uploaded_video_media_id`) REFERENCES `media_files` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `evaluation_job_logs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `job_id` bigint unsigned NOT NULL,
  `level` enum('info','warning','error') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'info',
  `stage` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'submitted',
  `message` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_evaluation_job_logs_job` (`job_id`,`created_at`),
  CONSTRAINT `fk_evaluation_job_logs_job` FOREIGN KEY (`job_id`) REFERENCES `evaluation_jobs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `evaluation_tasks` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `task_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sop_id` bigint unsigned NOT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `uploaded_video_media_id` bigint unsigned DEFAULT NULL,
  `status` enum('queued','processing','completed','failed') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'queued',
  `progress` int NOT NULL DEFAULT '0',
  `current_stage` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `failure_reason` text COLLATE utf8mb4_unicode_ci,
  `retry_count` int NOT NULL DEFAULT '0',
  `result_payload` json DEFAULT NULL,
  `log_entries` json DEFAULT NULL,
  `history_execution_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_evaluation_tasks_code` (`task_code`),
  KEY `idx_evaluation_tasks_status_created` (`status`,`created_at`),
  KEY `idx_evaluation_tasks_sop` (`sop_id`),
  KEY `fk_evaluation_tasks_user` (`user_id`),
  KEY `fk_evaluation_tasks_video` (`uploaded_video_media_id`),
  CONSTRAINT `fk_evaluation_tasks_sop` FOREIGN KEY (`sop_id`) REFERENCES `sops` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_evaluation_tasks_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_evaluation_tasks_video` FOREIGN KEY (`uploaded_video_media_id`) REFERENCES `media_files` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
