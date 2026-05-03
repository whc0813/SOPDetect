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

# ── Default penalty table (points deducted per issue type) ─────
DEFAULT_ISSUE_TYPE_PENALTIES = {
    "正常": 0,
    "证据不足": 15,
    "重复操作": 10,
    "部分完成": 20,
    "过早执行": 25,
    "延后执行": 25,
    "过快完成": 25,
    "超时完成": 25,
    "动作错误": 35,
    "顺序颠倒": 40,
    "前置条件缺失": 45,
    "缺失": 60,
}

PASS_THRESHOLD = 80       # Minimum overall score to pass
STEP_PASS_THRESHOLD = 60  # Minimum per-step score to pass


def get_penalty_config(sop_record: dict) -> dict:
    """Return the merged penalty config for a SOP (custom overrides default)."""
    custom = sop_record.get("penaltyConfig") or {}
    merged = dict(DEFAULT_ISSUE_TYPE_PENALTIES)
    for key, value in custom.items():
        if key in merged:
            try:
                merged[key] = max(0, min(100, int(value)))
            except (TypeError, ValueError):
                pass
    return merged


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


def clamp_score(value) -> float:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return max(0.0, min(100.0, round(number, 2)))


# ── Scoring logic helpers ──────────────────────────────────────

def step_result_indicates_execution(result: dict) -> bool:
    issue_type = normalize_issue_type(result.get("issueType"))
    completion_level = normalize_completion_level(result.get("completionLevel"))
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


def post_process_evaluation_result(
    sop: SopData, evaluation: dict, penalty_config: Optional[dict] = None
) -> dict:
    """
    Apply rule-based post-processing to the raw model evaluation result.

    penalty_config: optional override dict; if None uses DEFAULT_ISSUE_TYPE_PENALTIES.
                    Pass sop.penaltyConfig to apply per-SOP weights.
    """
    effective_penalties = dict(DEFAULT_ISSUE_TYPE_PENALTIES)
    if penalty_config:
        for k, v in penalty_config.items():
            if k in effective_penalties:
                try:
                    effective_penalties[k] = max(0, min(100, int(v)))
                except (TypeError, ValueError):
                    pass

    raw_step_results = {
        int(item.get("stepNo") or 0): dict(item)
        for item in (evaluation.get("stepResults") or [])
        if int(item.get("stepNo") or 0) > 0
    }
    processed_steps = []
    processed_map = {}
    weighted_score_sum = 0.0
    weighted_score_total = 0.0
    hard_failed = False

    for step in sop.steps:
        raw_result = raw_step_results.get(step.stepNo, {})
        applicable = bool(raw_result.get("applicable")) if step.stepType == "conditional" else True
        step_result = {
            "stepNo": step.stepNo,
            "description": raw_result.get("description") or step.description,
            "passed": bool(raw_result.get("passed")),
            "score": clamp_score(raw_result.get("score")),
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
        step_result["prerequisiteViolated"] = resolve_prerequisite_violation(
            step, step_result, processed_map
        )

        if step_result["prerequisiteViolated"]:
            step_result["issueType"] = "前置条件缺失"
            step_result["orderIssue"] = True
            step_result["evidence"] = append_rule_note(
                step_result["evidence"], "后端规则判断该步骤违反前置依赖"
            )

        step_result = apply_duration_constraint(step, step_result)

        base_penalty = effective_penalties.get(
            step_result["issueType"], effective_penalties.get(DEFAULT_ISSUE_TYPE, 15)
        )
        prerequisite_penalty = 20 if step_result["prerequisiteViolated"] else 0

        if step_result["includedInScore"]:
            adjusted_score = clamp_score(step_result["score"] - base_penalty - prerequisite_penalty)
            step_result["score"] = adjusted_score
            step_result["passed"] = adjusted_score >= STEP_PASS_THRESHOLD
            weighted_score_sum += adjusted_score * step_result["stepWeight"]
            weighted_score_total += step_result["stepWeight"]
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

        if (
            step.stepType in {"required", "conditional"}
            and step_result["applicable"]
            and step_result["score"] < STEP_PASS_THRESHOLD
        ):
            hard_failed = True

        processed_steps.append(step_result)
        processed_map[step.stepNo] = step_result

    overall_score = (
        clamp_score(weighted_score_sum / weighted_score_total) if weighted_score_total else 0.0
    )
    order_issue_count = sum(
        1
        for item in processed_steps
        if item.get("orderIssue") or item.get("prerequisiteViolated")
    )
    if weighted_score_total == 0:
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
    rule_summary = f"最终得分 {overall_score:.1f}，已按步骤权重和前置依赖进行规则修正。"
    feedback = f"{feedback}\n\n{rule_summary}" if feedback else rule_summary

    return {
        **evaluation,
        "passed": (not hard_failed) and overall_score >= PASS_THRESHOLD,
        "score": overall_score,
        "feedback": feedback,
        "issues": issues,
        "sequenceAssessment": sequence_assessment,
        "prerequisiteViolated": any(
            item.get("prerequisiteViolated") for item in processed_steps
        ),
        "stepResults": processed_steps,
    }
