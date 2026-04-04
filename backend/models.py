from typing import List, Optional

from pydantic import BaseModel, Field

# ── Shared constants ───────────────────────────────────────────
STEP_TYPE_VALUES = {"required", "optional", "conditional"}
ISSUE_TYPE_VALUES = {
    "正常", "缺失", "顺序颠倒", "过早执行", "延后执行",
    "重复操作", "动作错误", "部分完成", "证据不足", "前置条件缺失",
}
COMPLETION_LEVEL_VALUES = {"完整", "部分完成", "未完成", "无法判断"}
DEFAULT_STEP_TYPE = "required"
DEFAULT_STEP_WEIGHT = 1.0
DEFAULT_ISSUE_TYPE = "证据不足"
DEFAULT_COMPLETION_LEVEL = "无法判断"


class ApiConfig(BaseModel):
    apiKey: str = ""
    baseURL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-plus"
    fps: float = 6
    temperature: float = 0.1
    timeoutMs: int = 120000


class KeyMoment(BaseModel):
    title: str
    timestampSec: float


class StepFeatures(BaseModel):
    durationSec: float = 0
    fps: float = 0
    frameCount: int = 0
    sampleTimestamps: List[float] = Field(default_factory=list)


class SopStep(BaseModel):
    stepNo: int
    description: str
    stepType: str = DEFAULT_STEP_TYPE
    stepWeight: float = DEFAULT_STEP_WEIGHT
    conditionText: str = ""
    prerequisiteStepNos: List[int] = Field(default_factory=list)
    referenceFrames: List[str] = Field(default_factory=list)
    referenceSummary: str = ""
    referenceFeatures: Optional[StepFeatures] = None
    substeps: List[KeyMoment] = Field(default_factory=list)
    roiHint: str = ""


class SopData(BaseModel):
    name: str
    scene: Optional[str] = None
    stepCount: int
    steps: List[SopStep] = Field(default_factory=list)
    penaltyConfig: Optional[dict] = None  # Per-SOP configurable penalty weights (Phase 4)


class StepResultPayload(BaseModel):
    stepNo: int
    description: str
    passed: bool
    score: float
    confidence: float
    applicable: bool = True
    includedInScore: bool = True
    issueType: str = ""
    completionLevel: str = ""
    orderIssue: bool = False
    prerequisiteViolated: bool = False
    detectedStartSec: Optional[float] = None
    detectedEndSec: Optional[float] = None
    stepType: str = DEFAULT_STEP_TYPE
    stepWeight: float = DEFAULT_STEP_WEIGHT
    evidence: str = ""


class EvaluationResultPayload(BaseModel):
    passed: bool
    score: float
    feedback: str
    issues: List[str] = Field(default_factory=list)
    sequenceAssessment: str = ""
    prerequisiteViolated: bool = False
    stepResults: List[StepResultPayload] = Field(default_factory=list)
    payloadPreview: Optional[dict] = None
    rawModelResult: Optional[dict] = None


class AIReferencePlan(BaseModel):
    stepSummary: str
    roiHint: str
    keyMoments: List[KeyMoment] = Field(default_factory=list)
