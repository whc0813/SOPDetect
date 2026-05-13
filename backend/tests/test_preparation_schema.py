import inspect
import unittest

from backend import storage


class PreparationSchemaTests(unittest.TestCase):
    def test_schema_declares_preparation_jobs_and_time_window_columns(self):
        schema = storage.SCHEMA_SQL_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS `sop_preparation_jobs`", schema)
        self.assertIn("`active_job_id` bigint unsigned DEFAULT NULL", schema)
        self.assertIn("`time_window_start_sec` decimal(8,3) DEFAULT NULL", schema)
        self.assertIn("`time_window_end_sec` decimal(8,3) DEFAULT NULL", schema)
        self.assertIn("`segmentation_source` varchar(16)", schema)
        self.assertIn("CONSTRAINT `fk_prep_job_sop`", schema)

    def test_migration_adds_time_window_columns_without_dropping_them(self):
        source = inspect.getsource(storage._run_schema_migrations)

        self.assertIn("ALTER TABLE sop_steps ADD COLUMN time_window_start_sec", source)
        self.assertIn("ALTER TABLE sop_steps ADD COLUMN time_window_end_sec", source)
        self.assertIn("ALTER TABLE sop_steps ADD COLUMN segmentation_source", source)
        self.assertNotIn("DROP COLUMN time_window_start_sec", source)
        self.assertNotIn("DROP COLUMN time_window_end_sec", source)

    def test_storage_exposes_preparation_job_operations(self):
        for name in [
            "create_preparation_job",
            "get_preparation_job",
            "update_preparation_job",
            "pick_preparation_job",
            "delete_preparation_job",
            "list_draft_sops_for_admin",
            "write_confirmed_segments",
            "publish_prepared_sop",
        ]:
            self.assertTrue(hasattr(storage, name), name)


if __name__ == "__main__":
    unittest.main()
