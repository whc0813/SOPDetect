import unittest

from backend import storage


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._results = []

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split())
        self.executed.append((normalized_sql, tuple(params or ())))

        if "FROM sop_executions e" in normalized_sql and "JOIN sops s ON s.id = e.sop_id" in normalized_sql:
            self._results = [
                {
                    "id": 1,
                    "execution_code": "history-1",
                    "sop_id": 10,
                    "user_id": 3,
                    "uploaded_video_media_id": 100,
                    "finish_time": "2026-04-12 10:00:00",
                    "score": 92.5,
                    "ai_status": "passed",
                    "feedback": "模型反馈",
                    "sequence_assessment": "顺序正常",
                    "prerequisite_violated": 0,
                    "payload_preview": '{"mode":"multistage"}',
                    "raw_model_result": '{"usage":{"total_tokens":321}}',
                    "created_at": "2026-04-12 09:59:00",
                    "sop_code": "sop-10",
                    "task_name": "洗手流程",
                    "scene": "实验室",
                    "user_name": "tester",
                    "user_display_name": "测试员",
                }
            ]
        elif "SELECT e.id, e.feedback, e.sequence_assessment, e.payload_preview, e.raw_model_result" in normalized_sql:
            self._results = [
                {
                    "id": 1,
                    "feedback": "模型反馈",
                    "sequence_assessment": "顺序正常",
                    "payload_preview": '{"mode":"multistage"}',
                    "raw_model_result": '{"usage":{"total_tokens":321}}',
                }
            ]
        else:
            self._results = []

    def fetchall(self):
        return list(self._results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj


class HistoryQueryOptimizationTests(unittest.TestCase):
    def test_build_history_records_sorts_without_loading_large_detail_columns(self):
        connection = _FakeConnection()

        records = storage._build_history_records(connection)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["detail"]["feedback"], "模型反馈")
        self.assertEqual(records[0]["detail"]["tokenUsage"]["totalTokens"], 321)

        first_sql = connection.cursor_obj.executed[0][0]
        self.assertNotIn("e.feedback", first_sql)
        self.assertNotIn("e.sequence_assessment", first_sql)
        self.assertNotIn("e.payload_preview", first_sql)
        self.assertNotIn("e.raw_model_result", first_sql)

        self.assertTrue(
            any(
                "SELECT e.id, e.feedback, e.sequence_assessment, e.payload_preview, e.raw_model_result" in sql
                for sql, _params in connection.cursor_obj.executed
            ),
            "history details should be loaded in a separate query after sorting",
        )


if __name__ == "__main__":
    unittest.main()
