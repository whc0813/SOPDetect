import asyncio
import inspect
import time
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from backend import main, preparation
from backend.models import ConfirmSegmentationRequest, SegmentItem


def _fake_view(job_id: int, status: str = "processing_steps") -> dict:
    """构造一份满足 PreparationJobView schema 的最小返回值，用于 response_model 校验。"""
    return {
        "id": job_id,
        "sopId": f"sop-{job_id}",
        "status": status,
        "phase": None,
        "progressMessage": None,
        "errorMessage": None,
        "metadata": {},
        "workflowMediaId": None,
        "createdAt": "2026-05-13T00:00:00",
        "updatedAt": "2026-05-13T00:00:00",
    }


class PreparationWorkerTests(unittest.TestCase):
    def tearDown(self):
        preparation.stop_preparation_worker()

    def test_worker_can_start_and_stop(self):
        def fake_loop():
            time.sleep(0.2)

        with mock.patch("backend.preparation.storage.reset_stalled_preparation_jobs", return_value=0), mock.patch(
            "backend.preparation._worker_loop", side_effect=fake_loop
        ):
            preparation.start_preparation_worker()
            self.assertTrue(preparation.is_worker_running())
            preparation.stop_preparation_worker()
            self.assertFalse(preparation.is_worker_running())

    def test_confirm_segments_rejects_overlap_but_allows_gap(self):
        request = ConfirmSegmentationRequest(
            segments=[
                SegmentItem(stepNo=1, startSec=0, endSec=8),
                SegmentItem(stepNo=2, startSec=10, endSec=18),
            ]
        )
        preparation.validate_confirmed_segments(request.segments, step_count=2, duration_sec=20)

        bad = ConfirmSegmentationRequest(
            segments=[
                SegmentItem(stepNo=1, startSec=0, endSec=10),
                SegmentItem(stepNo=2, startSec=9, endSec=18),
            ]
        )
        with self.assertRaises(ValueError):
            preparation.validate_confirmed_segments(bad.segments, step_count=2, duration_sec=20)

    def test_processing_steps_runs_pending_steps_concurrently(self):
        calls = []

        async def fake_step(job, step, segment):
            calls.append(step["stepNo"])
            await asyncio.sleep(0.01)
            return {"stepSummary": "ok", "keyMoments": [], "usage": {}}

        job = {
            "id": 7,
            "sop_id": 3,
            "metadata": {
                "segments": [
                    {"stepNo": 1, "startSec": 0, "endSec": 5},
                    {"stepNo": 2, "startSec": 6, "endSec": 10},
                ],
                "stepsMeta": [
                    {"stepNo": 1, "description": "A"},
                    {"stepNo": 2, "description": "B"},
                ],
                "stepStates": {"1": {"status": "pending"}, "2": {"status": "pending"}},
            },
        }

        with mock.patch("backend.preparation._process_single_step", side_effect=fake_step), mock.patch(
            "backend.preparation.storage.update_sop_step_reference_bundle"
        ), mock.patch(
            "backend.preparation.storage.update_preparation_step_state"
        ), mock.patch(
            "backend.preparation.storage.get_preparation_job",
            return_value={"id": 7, "status": "processing_steps", "metadata": job["metadata"]},
        ), mock.patch("backend.preparation.storage.publish_prepared_sop") as publish, mock.patch(
            "backend.preparation._transition"
        ) as transition:
            asyncio.run(preparation._run_processing_steps(job))

        self.assertEqual(sorted(calls), [1, 2])
        publish.assert_called_once_with(3, 7)
        self.assertTrue(any(call.kwargs.get("status") == "completed" for call in transition.mock_calls))


class PreparationApiShapeTests(unittest.TestCase):
    def test_main_registers_preparation_routes_and_removes_dead_endpoint(self):
        paths = {route.path for route in main.app.routes}

        self.assertIn("/api/sop-preparation-jobs/{job_id}", paths)
        self.assertIn("/api/sop-preparation-jobs/{job_id}/confirm-segmentation", paths)
        self.assertIn("/api/sop-preparation-jobs/{job_id}/retry-step", paths)
        self.assertIn("/api/sop-preparation-jobs/{job_id}/retry-segmentation", paths)
        self.assertIn("/api/sop-preparation-jobs/{job_id}/cancel", paths)
        self.assertNotIn("/api/prepare-step-video", paths)

    def test_create_sop_uses_wrapped_response_with_sop_code_job_id(self):
        source = inspect.getsource(main.create_sop)

        self.assertIn('"success": True', source)
        self.assertIn('"data"', source)
        self.assertIn('"sopId"', source)
        self.assertIn('"jobId"', source)
        self.assertIn('"queued"', source)
        self.assertNotIn("response_model=CreateSopResponse", source)

    def test_user_cannot_fetch_draft_sop_detail(self):
        client = TestClient(main.app)
        draft = {"id": "sop-draft", "status": "draft", "steps": []}

        main.app.dependency_overrides[main.get_current_user] = lambda: {"id": 2, "role": "user"}
        with mock.patch("backend.main.get_sop", return_value=draft):
            resp = client.get("/api/sops/sop-draft")
        main.app.dependency_overrides.clear()

        self.assertEqual(resp.status_code, 404)


class PreparationGuardEndpointTests(unittest.TestCase):
    """Critical/Important 修复回归：状态守卫与取消行为。"""

    def setUp(self):
        self.client = TestClient(main.app)
        main.app.dependency_overrides[main.require_admin] = lambda: {"id": 1, "role": "admin"}

    def tearDown(self):
        main.app.dependency_overrides.clear()
    def test_retry_step_rejects_non_failed_step(self):
        job = {
            "id": 1,
            "sop_id": 9,
            "sopCode": "sop-1",
            "status": "processing_steps",
            "metadata": {"stepStates": {"1": {"status": "completed"}}},
        }
        with mock.patch("backend.main.get_preparation_job", return_value=job):
            resp = self.client.post(
                "/api/sop-preparation-jobs/1/retry-step",
                json={"stepNo": 1},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("仅支持失败步骤重试", resp.json()["detail"])

    def test_retry_step_accepts_failed_step(self):
        job = {
            "id": 2,
            "sop_id": 9,
            "sopCode": "sop-1",
            "status": "failed",
            "metadata": {"stepStates": {"1": {"status": "failed", "retry_count": 0}}},
        }
        captured = {}

        def fake_update(*args, **kwargs):
            captured.update(kwargs)

        with mock.patch("backend.main.get_preparation_job", return_value=job), mock.patch(
            "backend.main.update_preparation_job", side_effect=fake_update
        ), mock.patch("backend.main._serialize_preparation_job", return_value=_fake_view(2)):
            resp = self.client.post(
                "/api/sop-preparation-jobs/2/retry-step",
                json={"stepNo": 1},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(captured.get("status"), "processing_steps")

    def test_retry_segmentation_requires_failed_status(self):
        job = {"id": 3, "status": "awaiting_confirmation"}
        with mock.patch("backend.main.get_preparation_job", return_value=job):
            resp = self.client.post("/api/sop-preparation-jobs/3/retry-segmentation")
        self.assertEqual(resp.status_code, 409)

    def test_confirm_segmentation_rejects_wrong_status_with_409(self):
        job = {"id": 4, "sop_id": 7, "status": "processing_steps", "metadata": {}}
        body = {"segments": [{"stepNo": 1, "startSec": 0, "endSec": 5}]}
        with mock.patch("backend.main.get_preparation_job", return_value=job):
            resp = self.client.post(
                "/api/sop-preparation-jobs/4/confirm-segmentation", json=body
            )
        self.assertEqual(resp.status_code, 409)

    def test_confirm_segmentation_uses_sop_steps_for_validation(self):
        job = {
            "id": 5,
            "sop_id": 11,
            "status": "awaiting_confirmation",
            "metadata": {"duration_sec": 20.0, "stepStates": {}},  # 没有 stepsMeta
        }
        sop_steps = [{"step_no": 1, "description": "A"}, {"step_no": 2, "description": "B"}]
        body = {
            "segments": [
                {"stepNo": 1, "startSec": 0, "endSec": 8},
                {"stepNo": 2, "startSec": 10, "endSec": 18},
            ]
        }
        with mock.patch("backend.main.get_preparation_job", return_value=job), mock.patch(
            "backend.main.list_sop_steps", return_value=sop_steps
        ), mock.patch("backend.main.write_confirmed_segments"), mock.patch(
            "backend.main.update_preparation_job"
        ), mock.patch("backend.main._serialize_preparation_job", return_value=_fake_view(5)):
            resp = self.client.post(
                "/api/sop-preparation-jobs/5/confirm-segmentation", json=body
            )
        self.assertEqual(resp.status_code, 200)

    def test_cancel_soft_marks_job_before_deleting(self):
        job = {
            "id": 6,
            "sop_id": 13,
            "sopCode": "sop-13",
            "status": "processing_steps",
            "metadata": {},
        }
        sop = {"id": "sop-13", "status": "draft"}
        order = []
        with mock.patch("backend.main.get_preparation_job", return_value=job), mock.patch(
            "backend.main.get_sop", return_value=sop
        ), mock.patch(
            "backend.main.mark_preparation_job_cancelled",
            side_effect=lambda jid: order.append(("mark", jid)),
        ), mock.patch(
            "backend.main.delete_preparation_job",
            side_effect=lambda jid: order.append(("del_job", jid)),
        ), mock.patch(
            "backend.main.delete_sop",
            side_effect=lambda code: order.append(("del_sop", code)) or True,
        ):
            resp = self.client.post("/api/sop-preparation-jobs/6/cancel")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            order,
            [("mark", 6), ("del_job", 6), ("del_sop", "sop-13")],
        )

    def test_worker_skips_writes_after_cancel(self):
        """C-4/I-1：worker 在写库前重检 status=cancelled 时应当退出。"""

        async def runner():
            with mock.patch(
                "backend.preparation.storage.get_preparation_job",
                return_value={"id": 7, "status": "cancelled"},
            ):
                self.assertTrue(preparation._job_was_cancelled(7))

        asyncio.run(runner())

    def test_single_step_replace_skips_segmenting(self):
        """I-5：replaceStepNo 走轻量分支，不调用模型时序分割。"""
        captured_transitions = []

        def fake_transition(job_id, **kwargs):
            captured_transitions.append(kwargs.get("status"))

        with mock.patch(
            "backend.preparation._prepare_workflow_video",
            return_value=("data:video/mp4;base64,AAAA", 12.0, {"mediaId": "m-1"}),
        ), mock.patch(
            "backend.preparation.segment_workflow_video",
            side_effect=AssertionError("单步骤替换不应调用整体时序分割"),
        ), mock.patch(
            "backend.preparation.storage.get_preparation_job",
            return_value={"id": 9, "status": "queued", "metadata": {}},
        ), mock.patch(
            "backend.preparation._transition", side_effect=fake_transition
        ):
            asyncio.run(
                preparation._run_segmenting_stage(
                    {
                        "id": 9,
                        "sop_id": 4,
                        "metadata": {
                            "workflowVideoDataUrl": "data:video/mp4;base64,AAAA",
                            "replaceStepNo": 2,
                            "stepsMeta": [{"stepNo": 2, "description": "B"}],
                        },
                    }
                )
            )
        # 应当从 preparing 直接跳到 awaiting_confirmation，不经过 segmenting
        self.assertIn("preparing", captured_transitions)
        self.assertIn("awaiting_confirmation", captured_transitions)
        self.assertNotIn("segmenting", captured_transitions)

    def test_confirm_segmentation_accepts_single_step_replace(self):
        """I-5：单步骤替换 confirm 只需校验目标步骤，不要求覆盖全部 sop_steps。"""
        job = {
            "id": 10,
            "sop_id": 4,
            "sopCode": "sop-4",
            "status": "awaiting_confirmation",
            "metadata": {
                "duration_sec": 12.0,
                "replaceStepNo": 2,
                "stepStates": {"2": {"status": "pending"}},
            },
        }
        body = {"segments": [{"stepNo": 2, "startSec": 0, "endSec": 8}]}
        with mock.patch("backend.main.get_preparation_job", return_value=job), mock.patch(
            "backend.main.list_sop_steps"
        ) as list_steps, mock.patch("backend.main.write_confirmed_segments"), mock.patch(
            "backend.main.update_preparation_job"
        ), mock.patch("backend.main._serialize_preparation_job", return_value=_fake_view(10)):
            resp = self.client.post(
                "/api/sop-preparation-jobs/10/confirm-segmentation", json=body
            )
        self.assertEqual(resp.status_code, 200)
        # 单步骤替换不应去 DB 读全部 sop_steps
        list_steps.assert_not_called()

    def test_worker_step_state_uses_atomic_update(self):
        """C-4 防 race：每步状态走 update_preparation_step_state 而非全量 patch。"""
        calls = []

        async def fake_step(job, step, segment):
            await asyncio.sleep(0)
            return {"stepSummary": "ok", "keyMoments": [], "usage": {}}

        job = {
            "id": 8,
            "sop_id": 5,
            "metadata": {
                "segments": [
                    {"stepNo": 1, "startSec": 0, "endSec": 5},
                    {"stepNo": 2, "startSec": 5, "endSec": 10},
                ],
                "stepsMeta": [
                    {"stepNo": 1, "description": "A"},
                    {"stepNo": 2, "description": "B"},
                ],
                "stepStates": {"1": {"status": "pending"}, "2": {"status": "pending"}},
            },
        }
        with mock.patch("backend.preparation._process_single_step", side_effect=fake_step), mock.patch(
            "backend.preparation.storage.update_sop_step_reference_bundle"
        ), mock.patch(
            "backend.preparation.storage.update_preparation_step_state",
            side_effect=lambda jid, sn, patch: calls.append((sn, patch.get("status"))),
        ), mock.patch(
            "backend.preparation.storage.publish_prepared_sop"
        ), mock.patch(
            "backend.preparation.storage.get_preparation_job",
            return_value={"id": 8, "status": "processing_steps", "metadata": job["metadata"]},
        ), mock.patch("backend.preparation._transition"):
            asyncio.run(preparation._run_processing_steps(job))

        # 每步骤应该都有 processing + completed 两次写入，且全部走原子接口
        per_step = {}
        for step_no, status in calls:
            per_step.setdefault(step_no, []).append(status)
        self.assertEqual(sorted(per_step.keys()), [1, 2])
        for step_no, history in per_step.items():
            self.assertIn("processing", history)
            self.assertIn("completed", history)


if __name__ == "__main__":
    unittest.main()
