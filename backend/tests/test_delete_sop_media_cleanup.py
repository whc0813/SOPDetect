import unittest
from unittest import mock

from backend import storage


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._results = []
        self._fetchone = None

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split())
        self.executed.append((normalized_sql, tuple(params or ())))

        if "SELECT id FROM sop_executions WHERE sop_id = %s" in normalized_sql:
            self._results = []
            self._fetchone = None
        elif "SELECT id FROM sop_steps WHERE sop_id = %s" in normalized_sql:
            self._results = [{"id": 11}, {"id": 12}]
            self._fetchone = None
        elif "SELECT storage_path FROM media_files WHERE related_sop_id = %s OR related_step_id IN" in normalized_sql:
            self._results = [{"storage_path": "demo-a.mp4"}, {"storage_path": "demo-b.mp4"}]
            self._fetchone = None
        else:
            self._results = []
            self._fetchone = {"count": 0} if "SELECT COUNT(*) AS count" in normalized_sql else None

    def fetchall(self):
        return list(self._results)

    def fetchone(self):
        return self._fetchone

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.cursor_obj = _FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DeleteSopMediaCleanupTests(unittest.TestCase):
    def test_delete_sop_removes_step_demo_media_by_step_id(self):
        connection = _FakeConnection()

        fake_user_media_dir = mock.Mock()
        fake_user_media_dir.exists.return_value = False

        with mock.patch("backend.storage._get_connection", return_value=connection), mock.patch(
            "backend.storage._fetch_sop_row_by_code", return_value={"id": 7}
        ), mock.patch("backend.storage._delete_files") as delete_files, mock.patch(
            "backend.storage._delete_dirs"
        ) as delete_dirs, mock.patch("backend.storage.USER_MEDIA_DIR", fake_user_media_dir):
            result = storage.delete_sop("sop-7")

        self.assertTrue(result)
        self.assertTrue(connection.committed)
        delete_files.assert_called_once_with(["demo-a.mp4", "demo-b.mp4"])
        delete_dirs.assert_called_once()

        executed_sql = [sql for sql, _params in connection.cursor_obj.executed]
        self.assertTrue(
            any("SELECT id FROM sop_steps WHERE sop_id = %s" in sql for sql in executed_sql),
            "delete_sop should load step ids before removing media",
        )
        self.assertTrue(
            any("related_step_id IN" in sql for sql in executed_sql),
            "delete_sop should remove sop_step_demo media by related_step_id",
        )


if __name__ == "__main__":
    unittest.main()
