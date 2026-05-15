import unittest
import json
from unittest import mock

from backend import evaluation, main, models, prompt, scoring
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


def _build_many_step_sop(step_count=12):
    return SopData(
        name="长流程测试",
        scene="批量评估",
        stepCount=step_count,
        steps=[
            SopStep(
                stepNo=index,
                description=f"完成步骤 {index}",
                referenceFrames=[f"frame://{index}"],
                referenceSummary=f"步骤 {index} 正确动作",
                roiHint=f"关注区域 {index}",
            )
            for index in range(1, step_count + 1)
        ],
    )


def _raw_step_eval_json(step_nos):
    step_results = [
        {
            "stepNo": step_no,
            "passed": True,
            "confidence": 1.0,
            "applicable": True,
            "issueType": "正常",
            "orderIssue": False,
            "prerequisiteViolated": False,
            "detectedStartSec": float(step_no),
            "detectedEndSec": float(step_no) + 0.5,
            "repeatedExecution": False,
            "detectedOccurrences": [],
            "reasoning": "ok",
            "evidence": "ok",
        }
        for step_no in step_nos
    ]
    return {"choices": [{"message": {"content": json.dumps({"stepResults": step_results}, ensure_ascii=False)}}]}


class EvaluationPipelineRegressionTests(unittest.TestCase):
    def test_issue_type_values_are_simplified(self):
        self.assertEqual(
            models.ISSUE_TYPE_VALUES,
            ["正常", "缺失", "动作不规范", "顺序问题", "重复操作", "证据不足"],
        )

    def test_legacy_issue_types_normalize_to_simplified_values(self):
        self.assertEqual(scoring.normalize_issue_type("部分完成"), "动作不规范")
        self.assertEqual(scoring.normalize_issue_type("动作错误"), "动作不规范")
        self.assertEqual(scoring.normalize_issue_type("顺序颠倒"), "顺序问题")
        self.assertEqual(scoring.normalize_issue_type("过早执行"), "顺序问题")
        self.assertEqual(scoring.normalize_issue_type("延后执行"), "顺序问题")
        self.assertEqual(scoring.normalize_issue_type("前置条件缺失"), "顺序问题")
        self.assertEqual(scoring.normalize_issue_type("过快完成"), "正常")
        self.assertEqual(scoring.normalize_issue_type("超时完成"), "正常")

    def test_response_schemas_do_not_request_numeric_scores(self):
        schema_text = str(prompt.build_response_schema(1))
        batch_schema_text = str(prompt.build_batch_step_evaluation_schema(1))
        global_schema_text = str(prompt.build_global_validation_schema())

        self.assertNotIn("score", schema_text)
        self.assertNotIn("score", batch_schema_text)
        self.assertNotIn("score", global_schema_text)

    def test_response_schemas_do_not_request_completion_level(self):
        schema_text = str(prompt.build_response_schema(1))
        per_step_schema_text = str(prompt.build_per_step_evaluation_schema())
        batch_schema_text = str(prompt.build_batch_step_evaluation_schema(1))

        self.assertNotIn("completionLevel", schema_text)
        self.assertNotIn("completionLevel", per_step_schema_text)
        self.assertNotIn("completionLevel", batch_schema_text)

    def test_prompt_blocks_do_not_include_step_weight(self):
        sop = _build_test_sop()
        all_step_blocks = prompt.build_content_blocks(sop, "data:video/mp4;base64,user", 2)
        per_step_blocks = prompt.build_per_step_evaluation_blocks(
            sop.steps[0],
            {"detected": True, "startSec": 1.0, "endSec": 2.0},
            "data:video/mp4;base64,user",
            2,
        )
        batch_blocks = prompt.build_batch_step_evaluation_blocks(
            sop,
            {1: {"startSec": 1.0, "endSec": 2.0}},
            "data:video/mp4;base64,user",
            2,
        )
        text = "\n".join(
            block.get("text", "")
            for block in [*all_step_blocks, *per_step_blocks, *batch_blocks]
            if block.get("type") == "text"
        )

        self.assertNotIn("步骤权重", text)
        self.assertNotIn("权重", text)

    def test_post_process_ignores_min_duration_limit(self):
        sop = SopData(
            name="计时测试",
            stepCount=1,
            steps=[
                SopStep(
                    stepNo=1,
                    description="擦拭消毒至少 3 秒",
                )
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "擦拭消毒至少 3 秒",
                    "passed": True,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 1.0,
                    "detectedEndSec": 2.0,
                    "evidence": "动作完整但持续时间较短",
                }
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        self.assertEqual(result["stepResults"][0]["issueType"], "正常")
        self.assertTrue(result["stepResults"][0]["passed"])
        self.assertTrue(result["passed"])
        self.assertNotIn("score", result["stepResults"][0])
        self.assertNotIn("最短耗时", result["stepResults"][0]["evidence"])
        self.assertEqual(result["issues"], [])

    def test_post_process_ignores_max_duration_limit(self):
        sop = SopData(
            name="计时测试",
            stepCount=1,
            steps=[
                SopStep(
                    stepNo=1,
                    description="拧紧螺丝需在 2 秒内完成",
                )
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "拧紧螺丝需在 2 秒内完成",
                    "passed": True,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 1.0,
                    "detectedEndSec": 4.5,
                    "evidence": "动作完整但耗时较长",
                }
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        self.assertEqual(result["stepResults"][0]["issueType"], "正常")
        self.assertTrue(result["stepResults"][0]["passed"])
        self.assertTrue(result["passed"])
        self.assertNotIn("score", result["stepResults"][0])
        self.assertNotIn("最长耗时", result["stepResults"][0]["evidence"])
        self.assertEqual(result["issues"], [])

    def test_post_process_keeps_normal_step_without_duration_limits(self):
        sop = SopData(
            name="计时测试",
            stepCount=1,
            steps=[SopStep(stepNo=1, description="普通步骤")],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "普通步骤",
                    "passed": True,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 1.0,
                    "detectedEndSec": 10.0,
                    "evidence": "动作完整",
                }
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        self.assertEqual(result["stepResults"][0]["issueType"], "正常")
        self.assertTrue(result["stepResults"][0]["passed"])
        self.assertTrue(result["passed"])
        self.assertNotIn("score", result["stepResults"][0])

    def test_validate_sop_step_ignores_duration_range(self):
        step = main.StepVideoInput(
            description="计时步骤",
        )

        main.validate_sop_step_inputs([step])

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
        self.assertEqual(merged[1]["issueType"], "顺序问题")
        self.assertIn("顺序异常", merged[1]["evidence"])

    def test_apply_global_validation_overrides_accepts_legacy_step_id_and_string_flags(self):
        step_results = [
            {
                "stepNo": 10,
                "description": "扣合电池排线",
                "passed": True,
                "confidence": 0.98,
                "applicable": True,
                "issueType": "正常",
                "completionLevel": "完整",
                "orderIssue": False,
                "prerequisiteViolated": False,
                "detectedStartSec": 33.9,
                "detectedEndSec": 37.7,
                "evidence": "动作正确",
            }
        ]
        global_result = {
            "stepOverrides": [
                {
                    "stepId": 10,
                    "issueType": "顺序问题",
                    "orderIssue": "抢先执行",
                    "prerequisiteViolated": "true",
                    "evidenceNote": "步骤10在步骤9尚未完全结束时即已开始并完成。",
                }
            ]
        }

        merged = evaluation.apply_global_validation_overrides(step_results, global_result)

        self.assertTrue(merged[0]["orderIssue"])
        self.assertTrue(merged[0]["prerequisiteViolated"])
        self.assertEqual(merged[0]["issueType"], "顺序问题")
        self.assertIn("步骤9尚未完全结束", merged[0]["evidence"])

    def test_post_process_marks_default_sequence_overlap_as_order_issue_and_fails_result(self):
        sop = SopData(
            name="组装手机",
            stepCount=2,
            steps=[
                SopStep(stepNo=9, description="安装振动马达及扬声器盖板"),
                SopStep(stepNo=10, description="扣合电池排线"),
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 9,
                    "description": "安装振动马达及扬声器盖板",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 32.0,
                    "detectedEndSec": 40.6,
                    "evidence": "底部组件安装完成",
                },
                {
                    "stepNo": 10,
                    "description": "扣合电池排线",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 33.9,
                    "detectedEndSec": 37.7,
                    "evidence": "电池排线已扣合",
                },
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        step10 = result["stepResults"][1]
        self.assertFalse(result["passed"])
        self.assertFalse(step10["passed"])
        self.assertTrue(step10["orderIssue"])
        self.assertFalse(step10["prerequisiteViolated"])
        self.assertEqual(step10["issueType"], "顺序问题")
        self.assertFalse(step10["passed"])
        self.assertNotIn("score", step10)
        self.assertIn("步骤 10 顺序问题", result["issues"])
        self.assertEqual(result["sequenceAssessment"], "轻微顺序偏差")

    def test_post_process_keeps_normal_default_sequence_as_passed(self):
        sop = SopData(
            name="线性流程",
            stepCount=2,
            steps=[
                SopStep(stepNo=1, description="第一步"),
                SopStep(stepNo=2, description="第二步"),
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "第一步",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 1.0,
                    "detectedEndSec": 2.0,
                    "evidence": "ok1",
                },
                {
                    "stepNo": 2,
                    "description": "第二步",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 2.0,
                    "detectedEndSec": 3.0,
                    "evidence": "ok2",
                },
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        self.assertTrue(result["passed"])
        self.assertEqual(result["sequenceAssessment"], "顺序正确")
        self.assertEqual(result["issues"], [])

    def test_explicit_prerequisite_violation_keeps_prerequisite_issue_priority(self):
        sop = SopData(
            name="前置优先",
            stepCount=2,
            steps=[
                SopStep(stepNo=1, description="第一步"),
                SopStep(stepNo=2, description="第二步", prerequisiteStepNos=[1]),
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "第一步",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 5.0,
                    "detectedEndSec": 6.0,
                    "evidence": "ok1",
                },
                {
                    "stepNo": 2,
                    "description": "第二步",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 3.0,
                    "detectedEndSec": 4.0,
                    "evidence": "ok2",
                },
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        step2 = result["stepResults"][1]
        self.assertFalse(result["passed"])
        self.assertFalse(step2["passed"])
        self.assertTrue(step2["orderIssue"])
        self.assertTrue(step2["prerequisiteViolated"])
        self.assertEqual(step2["issueType"], "顺序问题")

    def test_missing_step_keeps_missing_priority_even_with_overlapping_detected_range(self):
        sop = SopData(
            name="组装手机",
            stepCount=3,
            steps=[
                SopStep(stepNo=12, description="拧紧机身内部固定螺丝"),
                SopStep(stepNo=13, description="压合手机后盖"),
                SopStep(stepNo=14, description="启动手机并进行基础开机检查", prerequisiteStepNos=[13]),
            ],
        )
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 12,
                    "description": "拧紧机身内部固定螺丝",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 43.1,
                    "detectedEndSec": 47.8,
                    "evidence": "螺丝拧紧完成",
                },
                {
                    "stepNo": 13,
                    "description": "压合手机后盖",
                    "passed": True,
                    "confidence": 0.98,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 47.8,
                    "detectedEndSec": 49.7,
                    "evidence": "后盖安装完成",
                },
                {
                    "stepNo": 14,
                    "description": "启动手机并进行基础开机检查",
                    "passed": False,
                    "confidence": 0.9,
                    "applicable": True,
                    "issueType": "缺失",
                    "completionLevel": "未完成",
                    "orderIssue": False,
                    "prerequisiteViolated": True,
                    "detectedStartSec": 46.2,
                    "detectedEndSec": 49.7,
                    "evidence": "视频结束时仅显示后盖安装完成，未实际执行开机动作。",
                },
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)

        step14 = result["stepResults"][2]
        self.assertFalse(result["passed"])
        self.assertFalse(step14["passed"])
        self.assertEqual(step14["issueType"], "缺失")
        self.assertFalse(step14["orderIssue"])
        self.assertFalse(step14["prerequisiteViolated"])
        self.assertFalse(step14["passed"])
        self.assertNotIn("score", step14)
        self.assertIn("步骤 14 缺失", result["issues"])
        self.assertNotIn("步骤 14 前置条件缺失", result["issues"])

    def test_global_validation_content_prefers_step_detected_range_over_stage1_segment(self):
        sop = _build_test_sop()
        step_results = [
            {
                "stepNo": 1,
                "description": "做出“1”手势",
                "passed": True,
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
        self.assertIn("而非缺失", system_prompt)
        self.assertIn("x.xs 秒数格式", system_prompt)
        self.assertIn("顺序问题", system_prompt)

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
        self.assertIn("startSec", all_text)
        self.assertIn("endSec", all_text)
        self.assertEqual(sum(1 for item in blocks if item.get("type") == "video_url"), 1)
        self.assertNotIn("鐢ㄦ埛瑙嗛鍏抽敭甯", all_text)

    def test_batch_step_evaluation_system_prompt_mentions_batch_scope(self):
        system_prompt = prompt.build_batch_step_evaluation_system_prompt()

        self.assertIn("stepResults", system_prompt)
        self.assertIn("stepNo", system_prompt)
        self.assertIn("mm:ss", system_prompt)
        self.assertIn("重复操作", system_prompt)
        self.assertIn("detectedOccurrences", str(prompt.build_batch_step_evaluation_schema(3)))
        self.assertIn(
            "stepResults",
            prompt.build_batch_step_evaluation_schema(3)["json_schema"]["schema"]["required"],
        )

    def test_post_process_marks_repeated_step_occurrences_as_duplicate_operation(self):
        sop = _build_test_sop()
        evaluation_payload = {
            "passed": True,
            "feedback": "",
            "issues": [],
            "sequenceAssessment": "",
            "prerequisiteViolated": False,
            "stepResults": [
                {
                    "stepNo": 1,
                    "description": "做出“1”手势",
                    "passed": True,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 0.5,
                    "detectedEndSec": 1.0,
                    "repeatedExecution": False,
                    "detectedOccurrences": [
                        {"startSec": 0.5, "endSec": 1.0, "note": "第一次形成手势1"}
                    ],
                    "evidence": "步骤1正常完成。",
                },
                {
                    "stepNo": 2,
                    "description": "做出“2”手势",
                    "passed": False,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "重复操作",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 2.0,
                    "detectedEndSec": 3.0,
                    "repeatedExecution": True,
                    "detectedOccurrences": [
                        {"startSec": 2.0, "endSec": 3.0, "note": "第一次形成手势2"},
                        {"startSec": 4.5, "endSec": 5.2, "note": "重复形成手势2"},
                    ],
                    "evidence": "步骤2不必要地重复执行。",
                },
                {
                    "stepNo": 3,
                    "description": "做出“3”手势",
                    "passed": True,
                    "confidence": 0.95,
                    "applicable": True,
                    "issueType": "正常",
                    "completionLevel": "完整",
                    "orderIssue": False,
                    "prerequisiteViolated": False,
                    "detectedStartSec": 6.0,
                    "detectedEndSec": 7.0,
                    "repeatedExecution": False,
                    "detectedOccurrences": [
                        {"startSec": 6.0, "endSec": 7.0, "note": "第一次形成手势3"}
                    ],
                    "evidence": "步骤3正常完成。",
                },
            ],
        }

        result = scoring.post_process_evaluation_result(sop, evaluation_payload)
        step2 = result["stepResults"][1]

        self.assertFalse(result["passed"])
        self.assertFalse(step2["passed"])
        self.assertEqual(step2["issueType"], "重复操作")
        self.assertEqual(step2["detectedStartSec"], 2.0)
        self.assertEqual(step2["detectedEndSec"], 5.2)
        self.assertEqual(len(step2["detectedOccurrences"]), 2)
        self.assertIn("步骤 2 重复操作", result["issues"])
        self.assertIn("后端规则判断该步骤重复出现 2 次", step2["evidence"])

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
                            '{"stepNo":1,"passed":true,"confidence":1.0,"applicable":true,'
                            '"issueType":"姝ｅ父","completionLevel":"瀹屾暣","orderIssue":false,'
                            '"prerequisiteViolated":false,"detectedStartSec":1.1,"detectedEndSec":1.9,"evidence":"ok1"},'
                            '{"stepNo":2,"passed":true,"confidence":0.9,"applicable":true,'
                            '"issueType":"姝ｅ父","completionLevel":"瀹屾暣","orderIssue":false,'
                            '"prerequisiteViolated":false,"detectedStartSec":3.2,"detectedEndSec":3.9,"evidence":"ok2"},'
                            '{"stepNo":3,"passed":false,"confidence":0.8,"applicable":true,'
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

    def test_run_per_step_evaluation_batch_keeps_long_sop_in_one_model_call(self):
        sop = _build_many_step_sop(12)
        segments = {
            step.stepNo: {
                "stepNo": step.stepNo,
                "detected": True,
                "startSec": float(step.stepNo),
                "endSec": float(step.stepNo) + 0.5,
            }
            for step in sop.steps
        }

        with mock.patch(
            "backend.evaluation.read_video_meta",
            return_value={"durationSec": 30.0, "fps": 30.0, "frameCount": 900},
        ), mock.patch(
            "backend.evaluation.call_chat_completion",
            new=mock.AsyncMock(return_value=_raw_step_eval_json(range(1, 13))),
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
        self.assertEqual([item["stepNo"] for item in results], list(range(1, 13)))
        self.assertIn("_batchPayloadPreview", results[0])
        self.assertNotIn("_batchPayloadPreview", results[1])

        payload = call_mock.await_args.args[1]
        min_items = payload["response_format"]["json_schema"]["schema"]["properties"]["stepResults"]["minItems"]
        prompt_text = "\n".join(
            block.get("text", "")
            for block in payload["messages"][1]["content"]
            if block.get("type") == "text"
        )
        self.assertEqual(min_items, 12)
        self.assertIn("步骤 1\n", prompt_text)
        self.assertIn("步骤 12\n", prompt_text)
        self.assertNotIn("本次评估步骤范围", prompt_text)

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
                            '{"stepNo":1,"passed":true,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":1.0,"detectedEndSec":2.0,"evidence":"ok"},',
                            '{"stepNo":2,"passed":true,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":3.0,"detectedEndSec":4.0,"evidence":"ok"},',
                            '{"stepNo":3,"passed":true,"confidence":1.0,"applicable":true,',
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
                            '{"stepNo":1,"passed":true,"confidence":1.0,"applicable":true,',
                            '"issueType":"正常","completionLevel":"完整","orderIssue":false,',
                            '"prerequisiteViolated":false,"detectedStartSec":1.0,"detectedEndSec":2.0,"evidence":"ok"},',
                            '{"stepNo":3,"passed":true,"confidence":0.9,"applicable":true,',
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
        self.assertNotIn("score", results[1])
        self.assertEqual(results[1]["issueType"], "证据不足")

    def test_prepare_reference_bundle_uses_full_video_samples_when_candidate_window_exists(self):
        sample_calls = []

        def fake_extract_samples(
            video_path,
            duration_sec,
            start_sec=0,
            end_sec=None,
            sample_count=10,
            sample_fps=2.0,
        ):
            sample_calls.append((start_sec, end_sec))
            if float(start_sec or 0) == 0 and end_sec is None:
                return [1.0, 3.0], ["full-frame-1", "full-frame-2"]
            return [5.5], ["candidate-frame"]

        with mock.patch(
            "backend.evaluation.data_url_to_temp_path",
            return_value="demo.mp4",
        ), mock.patch(
            "backend.evaluation.read_video_meta",
            return_value={"durationSec": 10.0, "fps": 30.0, "frameCount": 300},
        ), mock.patch(
            "backend.evaluation.extract_analysis_samples",
            side_effect=fake_extract_samples,
        ), mock.patch(
            "backend.evaluation.build_ai_reference_plan",
            new=mock.AsyncMock(return_value=(None, None)),
        ), mock.patch(
            "backend.evaluation.build_reference_bundle",
            return_value={
                "referenceFrames": [],
                "referenceSummary": "步骤 1：测试步骤",
                "referenceFeatures": {},
                "substeps": [],
                "roiHint": "",
                "analysisSampleTimestamps": [],
            },
        ), mock.patch("backend.evaluation.cleanup_file"):
            bundle = evaluation.asyncio.run(
                evaluation.prepare_reference_bundle(
                    step_no=1,
                    description="测试步骤",
                    video_data_url="data:video/mp4;base64,demo",
                    api_config=evaluation.ApiConfig(apiKey="k"),
                    start_sec=5.0,
                    end_sec=6.0,
                )
            )

        self.assertTrue(
            any(float(start or 0) == 0 and end is None for start, end in sample_calls),
            sample_calls,
        )
        self.assertIn("full-frame-1", bundle["analysisFrames"])

    def test_sanitize_step_result_clamps_range_and_strips_impossible_timestamps(self):
        result = {
            "stepNo": 3,
            "description": "做出“3”手势",
            "passed": False,
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

        self.assertEqual(cleaned["issueType"], "顺序问题")
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
            side_effect=lambda _sop, merged: merged,
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
            side_effect=lambda _sop, merged: merged,
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

