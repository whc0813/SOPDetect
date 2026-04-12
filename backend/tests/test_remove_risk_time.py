import unittest
from unittest import mock

from backend import main, storage


class RemoveRiskTimeTests(unittest.TestCase):
    def test_post_process_result_drops_risk_and_timing_fields(self):
        sop = main.SopData(
            name="测试SOP",
            stepCount=1,
            steps=[
                main.SopStep(
                    stepNo=1,
                    description="步骤一",
                    stepType="required",
                    stepWeight=1.0,
                    prerequisiteStepNos=[],
                )
            ],
        )

        evaluation = {
            "passed": True,
            "score": 95,
            "feedback": "模型反馈",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "步骤一",
                    "passed": True,
                    "score": 95,
                    "confidence": 0.9,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 1.0,
                    "detectedEndSec": 2.0,
                    "timingStatus": "within_window",
                    "evidence": "证据",
                }
            ],
        }

        result = main.post_process_evaluation_result(sop, evaluation)

        self.assertNotIn("riskLevel", result["stepResults"][0])
        self.assertNotIn("timingStatus", result["stepResults"][0])
        self.assertNotIn("风险等级", result["feedback"])
        self.assertNotIn("时间约束", result["feedback"])

    def test_serialize_sop_summary_drops_risk_and_time_constraint(self):
        sop = {
            "id": "sop-1",
            "name": "测试SOP",
            "scene": "实验室",
            "stepCount": 1,
            "steps": [
                {
                    "stepNo": 1,
                    "description": "步骤一",
                    "stepType": "required",
                    "stepWeight": 1.0,
                    "riskLevel": "critical",
                    "conditionText": "",
                    "prerequisiteStepNos": [],
                    "timeConstraint": {"anchorType": "flow_start", "startSec": 0, "endSec": 3},
                }
            ],
        }

        result = storage.serialize_sop_summary(sop)

        self.assertNotIn("riskLevel", result["steps"][0])
        self.assertNotIn("timeConstraint", result["steps"][0])

    def test_build_stats_drops_risk_and_timing_stats(self):
        history = [
            {
                "id": "history-1",
                "taskId": "sop-1",
                "taskName": "测试SOP",
                "scene": "实验室",
                "status": "passed",
                "score": 90,
                "manualReview": None,
                "detail": {
                    "stepResults": [
                        {
                            "stepNo": 1,
                            "description": "步骤一",
                            "passed": True,
                            "issueType": "正常",
                            "timingStatus": "within_window",
                            "riskLevel": "high",
                        }
                    ]
                },
            }
        ]

        with mock.patch("backend.storage.list_sops", return_value=[{"id": "sop-1"}]), mock.patch(
            "backend.storage.list_history", return_value=history
        ):
            result = storage.build_stats()

        self.assertIn("issueTypeStats", result)
        self.assertNotIn("highRiskStepStats", result)
        self.assertNotIn("timingStatusStats", result)
        self.assertNotIn("riskLevelStats", result)


if __name__ == "__main__":
    unittest.main()
