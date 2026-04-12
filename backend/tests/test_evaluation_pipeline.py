import unittest
from unittest import mock

from backend import evaluation, prompt
from backend.models import KeyMoment, SopData, SopStep


def _build_test_sop():
    return SopData(
        name="手势顺序测试",
        scene="手势演示",
        stepCount=3,
        steps=[
            SopStep(
                stepNo=1,
                description="做出“1”手势",
                referenceFrames=["frame://one"],
                referenceSummary="伸出食指",
                roiHint="关注食指",
                substeps=[KeyMoment(title="形成手势1", timestampSec=1.0)],
            ),
            SopStep(
                stepNo=2,
                description="做出“2”手势",
                prerequisiteStepNos=[1],
                referenceFrames=["frame://two"],
                referenceSummary="伸出食指和中指",
                roiHint="关注食指和中指",
                substeps=[KeyMoment(title="形成手势2", timestampSec=3.0)],
            ),
            SopStep(
                stepNo=3,
                description="做出“3”手势",
                prerequisiteStepNos=[1, 2],
                referenceFrames=["frame://three"],
                referenceSummary="伸出三根手指",
                roiHint="关注三根手指",
                substeps=[KeyMoment(title="形成手势3", timestampSec=5.0)],
            ),
        ],
    )


class EvaluationPipelineRegressionTests(unittest.TestCase):
    def test_choose_analysis_fps_raises_sampling_density_for_fast_actions(self):
        self.assertEqual(evaluation.choose_analysis_fps(configured_fps=2, video_fps=30), 8.0)

    def test_ensure_step_segments_fills_missing_ranges_with_uniform_fallback(self):
        sop = _build_test_sop()
        segments = {
            1: {
                "stepNo": 1,
                "detected": True,
                "startSec": 1.2,
                "endSec": 2.4,
                "confidence": 0.95,
                "note": "model",
            }
        }

        with mock.patch(
            "backend.evaluation.build_user_segments",
            return_value=[
                {"stepNo": 1, "startSec": 0.0, "endSec": 2.0},
                {"stepNo": 2, "startSec": 2.0, "endSec": 4.0},
                {"stepNo": 3, "startSec": 4.0, "endSec": 6.0},
            ],
        ):
            hydrated = evaluation.ensure_step_segments(sop, segments, "demo.mp4")

        self.assertEqual(hydrated[1]["startSec"], 1.2)
        self.assertFalse(hydrated[2]["detected"])
        self.assertEqual(hydrated[2]["startSec"], 2.0)
        self.assertEqual(hydrated[3]["endSec"], 6.0)

    def test_apply_global_validation_overrides_merges_order_flags_back_to_steps(self):
        step_results = [
            {
                "stepNo": 1,
                "description": "做出“1”手势",
                "passed": True,
                "score": 100,
                "confidence": 1.0,
                "applicable": True,
                "issueType": "正常",
                "completionLevel": "完整",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 1.2,
                "detectedEndSec": 2.4,
                "evidence": "动作正确",
            },
            {
                "stepNo": 2,
                "description": "做出“2”手势",
                "passed": True,
                "score": 100,
                "confidence": 0.98,
                "applicable": True,
                "issueType": "正常",
                "completionLevel": "完整",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 5.5,
                "detectedEndSec": 7.0,
                "evidence": "动作正确",
            },
        ]
        global_result = {
            "stepOverrides": [
                {
                    "stepNo": 2,
                    "orderIssue": True,
                    "prerequisiteViolated": False,
                    "issueType": "延后执行",
                    "detectedStartSec": 5.5,
                    "detectedEndSec": 7.0,
                    "evidenceNote": "该步骤出现在步骤3之后，应判定为顺序异常。",
                }
            ]
        }

        merged = evaluation.apply_global_validation_overrides(step_results, global_result)

        self.assertTrue(merged[1]["orderIssue"])
        self.assertEqual(merged[1]["issueType"], "延后执行")
        self.assertIn("顺序异常", merged[1]["evidence"])

    def test_global_validation_content_prefers_step_detected_range_over_stage1_segment(self):
        sop = _build_test_sop()
        step_results = [
            {
                "stepNo": 1,
                "description": "做出“1”手势",
                "passed": True,
                "score": 100,
                "issueType": "正常",
                "orderIssue": False,
                "detectedStartSec": 1.2,
                "detectedEndSec": 2.4,
                "evidence": "动作正确",
            }
        ]
        segments = {
            1: {
                "stepNo": 1,
                "detected": True,
                "startSec": 0.0,
                "endSec": 0.5,
                "confidence": 0.1,
                "note": "bad-segment",
            }
        }

        content = prompt.build_global_validation_content(sop, step_results, segments)

        self.assertIn("1.2s~2.4s", content)
        self.assertNotIn("0.0s~0.5s", content)

    def test_temporal_segmentation_blocks_include_text_clues_and_no_reference_frames(self):
        # Stage 1 只需定位时序，文字线索（参考摘要、ROI）已足够，省去参考帧以节省 token
        sop = _build_test_sop()

        blocks = prompt.build_temporal_segmentation_blocks(sop, "data:video/mp4;base64,ZmFrZQ==", 6)
        all_text = "\n".join(
            item.get("text", "")
            for item in blocks
            if isinstance(item, dict) and item.get("type") == "text"
        )

        self.assertIn("参考摘要", all_text)
        self.assertIn("ROI", all_text)
        # 不再发送参考图，仅依赖文字线索
        self.assertFalse(any(item.get("type") == "image_url" for item in blocks))

    def test_per_step_evaluation_blocks_include_user_focus_frames(self):
        step = _build_test_sop().steps[2]

        blocks = prompt.build_per_step_evaluation_blocks(
            step,
            {"detected": True, "startSec": 3.0, "endSec": 4.2},
            "data:video/mp4;base64,ZmFrZQ==",
            6,
            user_focus_frames=["frame://u1", "frame://u2"],
            user_focus_timestamps=[3.1, 3.8],
        )
        all_text = "\n".join(
            item.get("text", "")
            for item in blocks
            if isinstance(item, dict) and item.get("type") == "text"
        )

        self.assertIn("用户视频关键帧", all_text)
        self.assertGreaterEqual(
            sum(1 for item in blocks if item.get("type") == "image_url"),
            len(step.referenceFrames) + 2,
        )

    def test_per_step_evaluation_system_prompt_treats_segment_as_search_window(self):
        system_prompt = prompt.build_per_step_evaluation_system_prompt()

        self.assertIn("候选时间窗", system_prompt)
        self.assertIn("局部片段", system_prompt)
        self.assertIn("不要因为", system_prompt)
        self.assertIn("不要使用 mm:ss", system_prompt)
        self.assertIn("绝不能判成“缺失”", system_prompt)

    def test_per_step_evaluation_blocks_include_video_duration_guardrail(self):
        step = _build_test_sop().steps[2]

        blocks = prompt.build_per_step_evaluation_blocks(
            step,
            {"detected": True, "startSec": 3.0, "endSec": 4.2},
            "data:video/mp4;base64,ZmFrZQ==",
            6,
            user_focus_frames=["frame://u1", "frame://u2"],
            user_focus_timestamps=[3.1, 3.8],
            user_video_duration=7.0,
        )
        all_text = "\n".join(
            item.get("text", "")
            for item in blocks
            if isinstance(item, dict) and item.get("type") == "text"
        )

        self.assertIn("总时长：7.0s", all_text)
        self.assertIn("不要写出超过", all_text)
        self.assertNotIn("用户关键帧 1@", all_text)

    def test_batch_step_evaluation_blocks_attach_one_video_for_all_steps(self):
        sop = _build_test_sop()
        segments = {
            1: {"stepNo": 1, "detected": True, "startSec": 1.0, "endSec": 2.0},
            2: {"stepNo": 2, "detected": True, "startSec": 3.0, "endSec": 4.0},
            3: {"stepNo": 3, "detected": True, "startSec": 5.0, "endSec": 6.0},
        }

        blocks = prompt.build_batch_step_evaluation_blocks(
            sop,
            segments,
            "data:video/mp4;base64,ZmFrZQ==",
            6,
            user_video_duration=7.0,
        )
        all_text = "\n".join(
            item.get("text", "")
            for item in blocks
            if isinstance(item, dict) and item.get("type") == "text"
        )

        self.assertIn("7.0s", all_text)
        self.assertIn("1.0s - 2.0s", all_text)
        self.assertEqual(sum(1 for item in blocks if item.get("type") == "video_url"), 1)
        self.assertNotIn("鐢ㄦ埛瑙嗛鍏抽敭甯", all_text)

    def test_batch_step_evaluation_system_prompt_mentions_batch_scope(self):
        system_prompt = prompt.build_batch_step_evaluation_system_prompt()

        self.assertIn("stepResults", system_prompt)
        self.assertIn("stepNo", system_prompt)
        self.assertIn("mm:ss", system_prompt)
        self.assertIn(
            "stepResults",
            prompt.build_batch_step_evaluation_schema(3)["json_schema"]["schema"]["required"],
        )

    def test_run_per_step_evaluation_batch_calls_model_once_and_returns_all_steps(self):
        sop = _build_test_sop()
        segments = {
            1: {"stepNo": 1, "detected": True, "startSec": 1.0, "endSec": 2.0},
            2: {"stepNo": 2, "detected": True, "startSec": 3.0, "endSec": 4.0},
            3: {"stepNo": 3, "detected": True, "startSec": 5.0, "endSec": 6.0},
        }
        raw_json = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"stepResults":['
                            '{"stepNo":1,"passed":true,"score":100,"confidence":1.0,"applicable":true,'
                            '"issueType":"姝ｅ父","completionLevel":"瀹屾暣","orderIssue":false,'
                            '"prerequisiteViolated":false,"detectedStartSec":1.1,"detectedEndSec":1.9,"evidence":"ok1"},'
                            '{"stepNo":2,"passed":true,"score":90,"confidence":0.9,"applicable":true,'
                            '"issueType":"姝ｅ父","completionLevel":"瀹屾暣","orderIssue":false,'
                            '"prerequisiteViolated":false,"detectedStartSec":3.2,"detectedEndSec":3.9,"evidence":"ok2"},'
                            '{"stepNo":3,"passed":false,"score":60,"confidence":0.8,"applicable":true,'
                            '"issueType":"杩囨棭鎵ц","completionLevel":"瀹屾暣","orderIssue":true,'
                            '"prerequisiteViolated":false,"detectedStartSec":0.6,"detectedEndSec":1.8,"evidence":"ok3"}'
                            ']}'
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        }

        with mock.patch(
            "backend.evaluation.read_video_meta",
            return_value={"durationSec": 6.0, "fps": 30.0, "frameCount": 180},
        ), mock.patch(
            "backend.evaluation.call_chat_completion",
            new=mock.AsyncMock(return_value=raw_json),
        ) as call_mock:
            results = evaluation.asyncio.run(
                evaluation.run_per_step_evaluation_batch(
                    evaluation.ApiConfig(apiKey="k"),
                    sop,
                    segments,
                    "demo-path.mp4",
                    "data:video/mp4;base64,ZmFrZQ==",
                    6,
                )
            )

        self.assertEqual(call_mock.await_count, 1)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["description"], sop.steps[0].description)
        self.assertEqual(results[2]["issueType"], "杩囨棭鎵ц")
        self.assertIn("_batchPayloadPreview", results[0])
        self.assertNotIn("_batchPayloadPreview", results[1])

    def test_run_per_step_evaluation_batch_skips_focus_frame_extraction(self):
        sop = _build_test_sop()
        segments = {
            1: {"stepNo": 1, "detected": True, "startSec": 1.0, "endSec": 2.0},
            2: {"stepNo": 2, "detected": True, "startSec": 3.0, "endSec": 4.0},
            3: {"stepNo": 3, "detected": True, "startSec": 5.0, "endSec": 6.0},
        }
        raw_json = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"stepResults":['
                            '{"stepNo":1,"passed":true,"score":100,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":1.0,"detectedEndSec":2.0,"evidence":"ok"},',
                            '{"stepNo":2,"passed":true,"score":100,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":3.0,"detectedEndSec":4.0,"evidence":"ok"},',
                            '{"stepNo":3,"passed":true,"score":100,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":5.0,"detectedEndSec":6.0,"evidence":"ok"}'
                            ']}'
                        )
                    }
                }
            ]
        }

        with mock.patch(
            "backend.evaluation.extract_analysis_samples",
            return_value=([3.1, 3.6], ["frame://u1", "frame://u2"]),
        ) as extract_mock, mock.patch(
            "backend.evaluation.read_video_meta",
            return_value={"durationSec": 6.0, "fps": 30.0, "frameCount": 180},
        ), mock.patch(
            "backend.evaluation.call_chat_completion",
            new=mock.AsyncMock(return_value=raw_json),
        ):
            results = evaluation.asyncio.run(
                evaluation.run_per_step_evaluation_batch(
                    evaluation.ApiConfig(apiKey="k"),
                    sop,
                    segments,
                    "demo-path.mp4",
                    "data:video/mp4;base64,ZmFrZQ==",
                    6,
                )
            )

        self.assertEqual(len(results), 3)
        self.assertEqual(extract_mock.call_count, 0)

    def test_run_per_step_evaluation_batch_fills_missing_steps_when_model_omits_one(self):
        sop = _build_test_sop()
        segments = {
            1: {"stepNo": 1, "detected": True, "startSec": 1.0, "endSec": 2.0},
            2: {"stepNo": 2, "detected": True, "startSec": 3.0, "endSec": 4.0},
            3: {"stepNo": 3, "detected": True, "startSec": 5.0, "endSec": 6.0},
        }
        raw_json = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"stepResults":['
                            '{"stepNo":1,"passed":true,"score":100,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":1.0,"detectedEndSec":2.0,"evidence":"ok"},',
                            '{"stepNo":3,"passed":true,"score":95,"confidence":0.9,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":5.0,"detectedEndSec":6.0,"evidence":"ok"}'
                            ']}'
                        )
                    }
                }
            ]
        }

        with mock.patch(
            "backend.evaluation.read_video_meta",
            return_value={"durationSec": 6.0, "fps": 30.0, "frameCount": 180},
        ), mock.patch(
            "backend.evaluation.call_chat_completion",
            new=mock.AsyncMock(return_value=raw_json),
        ):
            results = evaluation.asyncio.run(
                evaluation.run_per_step_evaluation_batch(
                    evaluation.ApiConfig(apiKey="k"),
                    sop,
                    segments,
                    "demo-path.mp4",
                    "data:video/mp4;base64,ZmFrZQ==",
                    6,
                )
            )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[1]["stepNo"], 2)
        self.assertFalse(results[1]["passed"])
        self.assertEqual(results[1]["score"], 0)
        self.assertEqual(results[1]["issueType"], "证据不足")

    def test_sanitize_step_result_clamps_range_and_strips_impossible_timestamps(self):
        result = {
            "stepNo": 3,
            "description": "做出“3”手势",
            "passed": False,
            "score": 0,
            "confidence": 0.8,
            "applicable": True,
            "issueType": "动作错误",
            "completionLevel": "未完成",
            "orderIssue": False,
            "prerequisiteViolated": False,
            "detectedStartSec": 9.0,
            "detectedEndSec": 20.0,
            "evidence": "在用户视频中，0:09-0:20期间做出4手势，0:21-0:58期间保持2手势。",
        }

        cleaned = evaluation.sanitize_step_result(result, 7.0)

        self.assertEqual(cleaned["detectedStartSec"], 7.0)
        self.assertEqual(cleaned["detectedEndSec"], 7.0)
        self.assertNotIn("0:09", cleaned["evidence"])
        self.assertNotIn("0:58", cleaned["evidence"])
        self.assertIn("候选时间窗", cleaned["evidence"])

    def test_reconcile_order_issue_from_evidence_promotes_missing_to_early_execution(self):
        step = _build_test_sop().steps[2]
        result = {
            "stepNo": 3,
            "description": "做出“3”手势",
            "passed": False,
            "score": 0,
            "confidence": 1.0,
            "applicable": True,
            "issueType": "缺失",
            "completionLevel": "未完成",
            "orderIssue": False,
            "prerequisiteViolated": False,
            "detectedStartSec": 0.0,
            "detectedEndSec": 0.0,
            "evidence": (
                "用户视频中依次展示了握拳、伸出三指（0.6s-1.8s）、伸出一指（2.1s-3.6s）和伸出两指（3.9s-5.3s）的动作。"
                "虽然视频早期出现了三指手势，但根据SOP逻辑，该三指动作发生在步骤1和2之前或期间，属于错误时序。"
            ),
        }

        cleaned = evaluation.reconcile_order_issue_from_evidence(step, result, 7.0)

        self.assertEqual(cleaned["issueType"], "过早执行")
        self.assertTrue(cleaned["orderIssue"])
        self.assertEqual(cleaned["detectedStartSec"], 0.6)
        self.assertEqual(cleaned["detectedEndSec"], 1.8)
        self.assertIn("后端已根据证据改判为顺序问题", cleaned["evidence"])

    def test_run_multistage_evaluation_aggregates_token_usage_from_all_model_calls(self):
        sop = _build_test_sop()
        segments = {
            1: {"stepNo": 1, "detected": True, "startSec": 1.0, "endSec": 2.0, "confidence": 0.9, "note": ""},
            2: {"stepNo": 2, "detected": True, "startSec": 3.0, "endSec": 4.0, "confidence": 0.9, "note": ""},
            3: {"stepNo": 3, "detected": True, "startSec": 5.0, "endSec": 6.0, "confidence": 0.9, "note": ""},
        }
        step_results = [
            {
                "stepNo": 1,
                "description": "做出“1”手势",
                "passed": True,
                "score": 100,
                "confidence": 1.0,
                "applicable": True,
                "issueType": "正常",
                "completionLevel": "完整",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 1.0,
                "detectedEndSec": 2.0,
                "evidence": "ok",
                "_payloadPreview": {"stage": "stage2", "stepNo": 1},
                "_rawModelResult": {
                    "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
                },
            },
            {
                "stepNo": 2,
                "description": "做出“2”手势",
                "passed": True,
                "score": 100,
                "confidence": 1.0,
                "applicable": True,
                "issueType": "正常",
                "completionLevel": "完整",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 3.0,
                "detectedEndSec": 4.0,
                "evidence": "ok",
                "_payloadPreview": {"stage": "stage2", "stepNo": 2},
                "_rawModelResult": {
                    "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14}
                },
            },
            {
                "stepNo": 3,
                "description": "做出“3”手势",
                "passed": False,
                "score": 60,
                "confidence": 1.0,
                "applicable": True,
                "issueType": "过早执行",
                "completionLevel": "完整",
                "orderIssue": True,
                "prerequisiteViolated": True,
                "detectedStartSec": 5.0,
                "detectedEndSec": 6.0,
                "evidence": "order issue",
                "_payloadPreview": {"stage": "stage2", "stepNo": 3},
                "_rawModelResult": {
                    "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}
                },
            },
        ]
        global_result = {
            "passed": False,
            "score": 60,
            "feedback": "全局判断",
            "issues": ["顺序错误"],
            "sequenceAssessment": "明显顺序错误",
            "prerequisiteViolated": True,
            "stepOverrides": [],
            "_payloadPreview": {"stage": "stage3"},
            "_rawModelResult": {
                "usage": {"prompt_tokens": 13, "completion_tokens": 5, "total_tokens": 18}
            },
        }

        with mock.patch(
            "backend.evaluation.run_temporal_segmentation",
            return_value=(
                segments,
                7.0,
                {
                    "payloadPreview": {"stage": "stage1"},
                    "rawModelResult": {
                        "usage": {"prompt_tokens": 9, "completion_tokens": 1, "total_tokens": 10}
                    },
                },
            ),
        ), mock.patch(
            "backend.evaluation.ensure_step_segments",
            return_value=segments,
        ), mock.patch(
            "backend.evaluation.run_per_step_evaluation_batch",
            return_value=step_results,
        ), mock.patch(
            "backend.evaluation.run_global_validation",
            return_value=global_result,
        ), mock.patch(
            "backend.evaluation.post_process_evaluation_result",
            side_effect=lambda _sop, merged, penalty_config=None: merged,
        ):
            result, normalized_segments, detected_duration = evaluation.asyncio.run(
                evaluation._run_multistage_evaluation(
                    evaluation.ApiConfig(apiKey="k"),
                    sop,
                    "demo.mp4",
                    "data:video/mp4;base64,ZmFrZQ==",
                    6.0,
                )
            )

        self.assertEqual(normalized_segments, segments)
        self.assertEqual(detected_duration, 7.0)
        self.assertEqual(
            result["rawModelResult"]["usage"],
            {"prompt_tokens": 55, "completion_tokens": 15, "total_tokens": 70},
        )
        self.assertEqual(len(result["payloadPreview"]["stages"]), 5)

    def test_build_multistage_model_trace_keeps_media_preview(self):
        payload_preview, raw_model_result = evaluation.build_multistage_model_trace(
            [
                {
                    "stage": "stage2_step_eval",
                    "stepNo": 2,
                    "payloadPreview": {
                        "messages": [
                            {"role": "system", "content": "系统提示词"},
                        ]
                    },
                    "mediaPreview": {
                        "images": [{"url": "data:image/png;base64,abc"}],
                        "videos": [{"label": "整段用户视频"}],
                    },
                    "rawModelResult": {
                        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
                    },
                }
            ]
        )

        self.assertEqual(payload_preview["stages"][0]["mediaPreview"]["images"][0]["url"], "data:image/png;base64,abc")
        self.assertEqual(payload_preview["stages"][0]["mediaPreview"]["videos"][0]["label"], "整段用户视频")
        self.assertEqual(
            raw_model_result["usage"],
            {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        )

    def test_run_multistage_evaluation_persists_stage1_fallback_trace_when_segmentation_fails(self):
        sop = _build_test_sop()
        step_results = [
            {
                "stepNo": 1,
                "description": "步骤1",
                "passed": True,
                "score": 100,
                "confidence": 1.0,
                "applicable": True,
                "issueType": "姝ｅ父",
                "completionLevel": "瀹屾暣",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 0.0,
                "detectedEndSec": 1.0,
                "evidence": "ok",
                "_payloadPreview": {"messages": []},
                "_rawModelResult": {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
            }
        ]
        global_result = {
            "passed": True,
            "score": 100,
            "feedback": "ok",
            "issues": [],
            "sequenceAssessment": "椤哄簭姝ｇ‘",
            "prerequisiteViolated": False,
            "stepOverrides": [],
            "_payloadPreview": {"messages": []},
            "_rawModelResult": {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
        }

        with mock.patch(
            "backend.evaluation.run_temporal_segmentation",
            return_value=({}, None, None),
        ), mock.patch(
            "backend.evaluation.ensure_step_segments",
            return_value={1: {"stepNo": 1, "detected": False, "startSec": 0.0, "endSec": 1.0, "confidence": 0.0, "note": "fallback"}},
        ), mock.patch(
            "backend.evaluation.run_per_step_evaluation_batch",
            return_value=step_results,
        ), mock.patch(
            "backend.evaluation.run_global_validation",
            return_value=global_result,
        ), mock.patch(
            "backend.evaluation.post_process_evaluation_result",
            side_effect=lambda _sop, merged, penalty_config=None: merged,
        ):
            result, _normalized_segments, _detected_duration = evaluation.asyncio.run(
                evaluation._run_multistage_evaluation(
                    evaluation.ApiConfig(apiKey="k"),
                    sop,
                    "demo.mp4",
                    "data:video/mp4;base64,ZmFrZQ==",
                    6.0,
                )
            )

        self.assertEqual(result["payloadPreview"]["stages"][0]["stage"], "stage1_segmentation")
        self.assertEqual(
            result["payloadPreview"]["stages"][0]["payload"]["fallbackNote"],
            "阶段1时序定位失败，系统已回退为兜底分段继续后续评测。",
        )


if __name__ == "__main__":
    unittest.main()
