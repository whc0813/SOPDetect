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

        if "FROM sop_executions WHERE execution_code = %s" in normalized_sql:
            self._fetchone = {"id": 9, "uploaded_video_media_id": 19}
            self._results = []
        elif "SELECT storage_path FROM media_files WHERE related_execution_id = %s" in normalized_sql:
            self._fetchone = None
            self._results = [{"storage_path": "upload-a.mp4"}]
        else:
            self._fetchone = None
            self._results = []

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


class DeleteHistoryTests(unittest.TestCase):
    def test_delete_history_removes_execution_media_and_record(self):
        connection = _FakeConnection()

        with mock.patch("backend.storage._get_connection", return_value=connection), mock.patch(
            "backend.storage._delete_files"
        ) as delete_files:
            result = storage.delete_history("history-9")

        self.assertTrue(result)
        self.assertTrue(connection.committed)
        delete_files.assert_called_once_with(["upload-a.mp4"])

        executed_sql = [sql for sql, _params in connection.cursor_obj.executed]
        self.assertTrue(
            any("DELETE FROM media_files WHERE related_execution_id = %s" in sql for sql in executed_sql),
            "delete_history should remove uploaded media rows before deleting the execution",
        )
        self.assertTrue(
            any("DELETE FROM sop_executions WHERE id = %s" in sql for sql in executed_sql),
            "delete_history should remove the execution record",
        )


if __name__ == "__main__":
    unittest.main()
