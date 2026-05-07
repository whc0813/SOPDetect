from typing import Optional

try:
    from .models import (
        COMPLETION_LEVEL_VALUES,
        DEFAULT_COMPLETION_LEVEL,
        DEFAULT_ISSUE_TYPE,
        DEFAULT_STEP_TYPE,
        DEFAULT_STEP_WEIGHT,
        ISSUE_TYPE_VALUES,
        STEP_TYPE_VALUES,
        SopData,
        SopStep,
    )
except ImportError:
    from models import (
        COMPLETION_LEVEL_VALUES,
        DEFAULT_COMPLETION_LEVEL,
        DEFAULT_ISSUE_TYPE,
        DEFAULT_STEP_TYPE,
        DEFAULT_STEP_WEIGHT,
        ISSUE_TYPE_VALUES,
        STEP_TYPE_VALUES,
        SopData,
        SopStep,
    )

# ── Normalisation helpers ──────────────────────────────────────

def normalize_step_type(value):
    text = str(value or "").strip().lower()
    return text if text in STEP_TYPE_VALUES else DEFAULT_STEP_TYPE


def normalize_issue_type(value):
    text = str(value or "").strip()
    return text if text in ISSUE_TYPE_VALUES else DEFAULT_ISSUE_TYPE


def normalize_completion_level(value):
    text = str(value or "").strip()
    return text if text in COMPLETION_LEVEL_VALUES else DEFAULT_COMPLETION_LEVEL


def normalize_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return round(float(value), 3)
    except Exception:
        return None


def normalize_duration_limit(value):
    number = normalize_optional_float(value)
    if number is None or number <= 0:
        return None
    return number


def normalize_step_weight(value):
    try:
        weight = round(float(value), 1)
    except Exception:
        return DEFAULT_STEP_WEIGHT
    return min(5.0, max(0.5, weight))


def normalize_prerequisite_step_nos(values, current_step_no=None):
    result = []
    current = int(current_step_no or 0)
    for raw in values or []:
        try:
            step_no = int(raw)
        except Exception:
            continue
        if step_no <= 0:
            continue
        if current and step_no >= current:
            continue
        if step_no not in result:
            result.append(step_no)
    return sorted(result)


def normalize_step_payload(step: dict) -> dict:
    step_no = int(step.get("stepNo") or 0)
    return {
        **step,
        "stepType": normalize_step_type(step.get("stepType")),
        "stepWeight": normalize_step_weight(step.get("stepWeight")),
        "conditionText": (step.get("conditionText") or "").strip(),
        "prerequisiteStepNos": normalize_prerequisite_step_nos(
            step.get("prerequisiteStepNos"), step_no or None
        ),
        "minDurationSec": normalize_duration_limit(step.get("minDurationSec")),
        "maxDurationSec": normalize_duration_limit(step.get("maxDurationSec")),
    }


# ── Scoring logic helpers ──────────────────────────────────────

def step_result_indicates_execution(result: dict) -> bool:
    issue_type = normalize_issue_type(result.get("issueType"))
    completion_level = normalize_completion_level(result.get("completionLevel"))
    if issue_type == "缺失" or completion_level == "未完成":
        return False
    return (
        normalize_optional_float(result.get("detectedStartSec")) is not None
        or normalize_optional_float(result.get("detectedEndSec")) is not None
        or issue_type != "缺失"
        or completion_level in {"完整", "部分完成"}
    )


def determine_included_in_score(step: SopStep, result: dict) -> bool:
    if step.stepType == "required":
        return True
    if step.stepType == "optional":
        return step_result_indicates_execution(result)
    return bool(result.get("applicable"))


def step_result_is_abnormal(result: dict) -> bool:
    issue_type = normalize_issue_type(result.get("issueType"))
    completion_level = normalize_completion_level(result.get("completionLevel"))
    return (
        not bool(result.get("passed"))
        or issue_type != "正常"
        or completion_level in {"部分完成", "未完成", "无法判断"}
        or bool(result.get("orderIssue"))
        or bool(result.get("prerequisiteViolated"))
    )


def resolve_prerequisite_violation(step: SopStep, result: dict, processed_results: dict) -> bool:
    if not step.prerequisiteStepNos or not step_result_indicates_execution(result):
        return False
    current_start = normalize_optional_float(result.get("detectedStartSec"))
    for prerequisite_step_no in step.prerequisiteStepNos:
        prerequisite_item = processed_results.get(prerequisite_step_no)
        if not prerequisite_item:
            return True
        if prerequisite_item.get("applicable") is False:
            continue
        if not step_result_indicates_execution(prerequisite_item):
            return True
        prerequisite_end = normalize_optional_float(prerequisite_item.get("detectedEndSec"))
        if current_start is not None and prerequisite_end is not None and current_start < prerequisite_end:
            return True
        if normalize_issue_type(prerequisite_item.get("issueType")) == "缺失":
            return True
        if normalize_completion_level(prerequisite_item.get("completionLevel")) in {"未完成", "无法判断"}:
            return True
    return False


def append_rule_note(evidence: str, note: str) -> str:
    text = (evidence or "").strip()
    if note in text:
        return text
    if not text:
        return note
    return f"{text}；{note}"


def apply_duration_constraint(step: SopStep, result: dict) -> dict:
    start_sec = normalize_optional_float(result.get("detectedStartSec"))
    end_sec = normalize_optional_float(result.get("detectedEndSec"))
    if start_sec is None or end_sec is None or end_sec < start_sec:
        return result

    min_duration = normalize_duration_limit(getattr(step, "minDurationSec", None))
    max_duration = normalize_duration_limit(getattr(step, "maxDurationSec", None))
    if min_duration is None and max_duration is None:
        return result

    actual_duration = round(end_sec - start_sec, 3)
    if min_duration is not None and actual_duration < min_duration:
        result["issueType"] = "过快完成"
        result["evidence"] = append_rule_note(
            result.get("evidence") or "",
            f"后端规则判断该步骤实际耗时 {actual_duration:.1f}s，短于最短耗时 {min_duration:.1f}s",
        )
    elif max_duration is not None and actual_duration > max_duration:
        result["issueType"] = "超时完成"
        result["evidence"] = append_rule_note(
            result.get("evidence") or "",
            f"后端规则判断该步骤实际耗时 {actual_duration:.1f}s，超过最长耗时 {max_duration:.1f}s",
        )
    return result


def apply_default_sequence_constraint(
    previous_result: Optional[dict], current_result: dict
) -> dict:
    if (
        not previous_result
        or not current_result.get("includedInScore")
        or not step_result_indicates_execution(current_result)
    ):
        return current_result
    previous_end = normalize_optional_float(previous_result.get("detectedEndSec"))
    current_start = normalize_optional_float(current_result.get("detectedStartSec"))
    if previous_end is None or current_start is None or current_start >= previous_end:
        return current_result

    current_result["orderIssue"] = True
    if normalize_issue_type(current_result.get("issueType")) == "正常":
        current_result["issueType"] = "过早执行"
    current_result["evidence"] = append_rule_note(
        current_result.get("evidence") or "",
        (
            f"后端规则判断该步骤开始时间 {current_start:.1f}s "
            f"早于上一计分步骤结束时间 {previous_end:.1f}s"
        ),
    )
    return current_result


def post_process_evaluation_result(sop: SopData, evaluation: dict) -> dict:
    """
    Apply rule-based post-processing to the raw model evaluation result.
    """
    raw_step_results = {
        int(item.get("stepNo") or 0): dict(item)
        for item in (evaluation.get("stepResults") or [])
        if int(item.get("stepNo") or 0) > 0
    }
    processed_steps = []
    processed_map = {}
    included_step_count = 0
    abnormal_count = 0
    previous_included_step_result = None

    for step in sop.steps:
        raw_result = raw_step_results.get(step.stepNo, {})
        applicable = bool(raw_result.get("applicable")) if step.stepType == "conditional" else True
        step_result = {
            "stepNo": step.stepNo,
            "description": raw_result.get("description") or step.description,
            "passed": bool(raw_result.get("passed")),
            "confidence": max(0.0, min(1.0, float(raw_result.get("confidence") or 0))),
            "applicable": applicable,
            "includedInScore": True,
            "issueType": normalize_issue_type(raw_result.get("issueType")),
            "completionLevel": normalize_completion_level(raw_result.get("completionLevel")),
            "orderIssue": bool(raw_result.get("orderIssue")),
            "prerequisiteViolated": bool(raw_result.get("prerequisiteViolated")),
            "detectedStartSec": normalize_optional_float(raw_result.get("detectedStartSec")),
            "detectedEndSec": normalize_optional_float(raw_result.get("detectedEndSec")),
            "minDurationSec": normalize_duration_limit(getattr(step, "minDurationSec", None)),
            "maxDurationSec": normalize_duration_limit(getattr(step, "maxDurationSec", None)),
            "stepType": step.stepType,
            "stepWeight": normalize_step_weight(step.stepWeight),
            "evidence": (raw_result.get("evidence") or "").strip(),
        }

        step_result["includedInScore"] = determine_included_in_score(step, step_result)
        if not step_result_indicates_execution(step_result):
            step_result["prerequisiteViolated"] = False
            step_result["orderIssue"] = False
        step_result["prerequisiteViolated"] = bool(
            step_result["prerequisiteViolated"]
        ) or resolve_prerequisite_violation(
            step, step_result, processed_map
        )

        if step_result["prerequisiteViolated"]:
            step_result["issueType"] = "前置条件缺失"
            step_result["orderIssue"] = True
            step_result["evidence"] = append_rule_note(
                step_result["evidence"], "后端规则判断该步骤违反前置依赖"
            )

        step_result = apply_duration_constraint(step, step_result)
        step_result = apply_default_sequence_constraint(
            previous_included_step_result, step_result
        )

        if step_result["includedInScore"]:
            included_step_count += 1
            step_result["passed"] = not step_result_is_abnormal(step_result)
            if not step_result["passed"]:
                abnormal_count += 1
        else:
            step_result["passed"] = True
            if step.stepType == "optional" and not step_result_indicates_execution(step_result):
                step_result["evidence"] = append_rule_note(
                    step_result["evidence"], "该步骤为可选步骤且未执行，本次不计入总分"
                )
            if step.stepType == "conditional" and not step_result["applicable"]:
                step_result["evidence"] = append_rule_note(
                    step_result["evidence"], "该步骤被判定为本次场景不适用，不计入总分"
                )

        processed_steps.append(step_result)
        processed_map[step.stepNo] = step_result
        if step_result["includedInScore"]:
            previous_included_step_result = step_result

    order_issue_count = sum(
        1
        for item in processed_steps
        if item.get("orderIssue") or item.get("prerequisiteViolated")
    )
    if included_step_count == 0:
        sequence_assessment = "无法判断顺序"
    elif order_issue_count == 0:
        sequence_assessment = "顺序正确"
    elif order_issue_count == 1:
        sequence_assessment = "轻微顺序偏差"
    else:
        sequence_assessment = "明显顺序错误"

    issues = []
    for item in processed_steps:
        if item.get("includedInScore") and item.get("issueType") != "正常":
            issue_label = f"步骤 {item['stepNo']} {item['issueType']}"
            if issue_label not in issues:
                issues.append(issue_label)

    feedback = (evaluation.get("feedback") or "").strip()
    final_status = "通过" if abnormal_count == 0 else "异常"
    rule_summary = f"最终结论：{final_status}，已按步骤状态、前置依赖和耗时规则进行修正。"
    feedback = f"{feedback}\n\n{rule_summary}" if feedback else rule_summary

    return {
        **evaluation,
        "passed": abnormal_count == 0,
        "feedback": feedback,
        "issues": issues,
        "sequenceAssessment": sequence_assessment,
        "prerequisiteViolated": any(
            item.get("prerequisiteViolated") for item in processed_steps
        ),
        "stepResults": processed_steps,
    }
