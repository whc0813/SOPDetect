const STAGE_ORDER = {
  stage1_segmentation: 1,
  stage2_step_eval: 2,
  stage3_validation: 3,
}

const STAGE_LABELS = {
  stage1_segmentation: '阶段1：时序定位',
  stage2_step_eval: '阶段2：步骤评测',
  stage3_validation: '阶段3：全局校验',
}

export function normalizeHistory(record = {}) {
  return {
    ...record,
    detail: {
      feedback: record.detail?.feedback || '',
      issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
      stepResults: Array.isArray(record.detail?.stepResults) ? record.detail.stepResults : [],
      uploadedVideo: record.detail?.uploadedVideo || null,
      tokenUsage: record.detail?.tokenUsage || null,
      payloadPreview: record.detail?.payloadPreview || null,
      rawModelResult: record.detail?.rawModelResult || null,
      sequenceAssessment: record.detail?.sequenceAssessment || '',
      prerequisiteViolated: !!record.detail?.prerequisiteViolated,
      segmentPreview: Array.isArray(record.detail?.segmentPreview) ? record.detail.segmentPreview : [],
      overviewPreview: record.detail?.overviewPreview || null,
      evaluationProcess: buildEvaluationProcess(record.detail),
    },
    manualReview: record.manualReview || null,
  }
}

export function buildEvaluationResultFromHistory(record = {}) {
  return {
    passed: record.status === 'passed',
    score: record.score,
    feedback: record.detail?.feedback || '',
    issues: Array.isArray(record.detail?.issues) ? record.detail.issues : [],
    sequenceAssessment: record.detail?.sequenceAssessment || '',
    prerequisiteViolated: !!record.detail?.prerequisiteViolated,
    stepResults: Array.isArray(record.detail?.stepResults) ? record.detail.stepResults : [],
    tokenUsage: record.detail?.tokenUsage || null,
    payloadPreview: record.detail?.payloadPreview || null,
    rawModelResult: record.detail?.rawModelResult || null,
    segmentPreview: Array.isArray(record.detail?.segmentPreview) ? record.detail.segmentPreview : [],
    overviewPreview: record.detail?.overviewPreview || null,
  }
}

export function formatTokenUsage(usage) {
  if (!usage) return '暂无'
  const input = Number.isFinite(Number(usage.inputTokens)) ? Number(usage.inputTokens) : '-'
  const output = Number.isFinite(Number(usage.outputTokens)) ? Number(usage.outputTokens) : '-'
  const total = Number.isFinite(Number(usage.totalTokens)) ? Number(usage.totalTokens) : '-'
  return `输入 ${input} / 输出 ${output} / 总计 ${total}`
}

export function buildEvaluationProcess(detail = {}) {
  const payloadStages = Array.isArray(detail?.payloadPreview?.stages) &&
    detail?.payloadPreview?.mode === 'multistage'
    ? detail.payloadPreview.stages
    : []
  const resultStages = Array.isArray(detail?.rawModelResult?.stages) &&
    detail?.rawModelResult?.mode === 'multistage'
    ? detail.rawModelResult.stages
    : []

  if (!payloadStages.length && !resultStages.length) {
    return { stages: [] }
  }

  const stageMap = new Map()

  for (const item of payloadStages) {
    const entry = ensureStageEntry(stageMap, item?.stage, item?.stepNo)
    entry.payloadPreview = item?.payload || null
    entry.promptText = buildPromptText(item?.payload)
    entry.media = extractPayloadMedia(item)
    entry.note = typeof item?.payload?.fallbackNote === 'string' ? item.payload.fallbackNote.trim() : entry.note
  }

  for (const item of resultStages) {
    const entry = ensureStageEntry(stageMap, item?.stage, item?.stepNo)
    entry.rawModelResult = item?.result || null
    entry.responseText = extractResponseText(item?.result)
    entry.tokenUsage = extractTokenUsage(item?.result?.usage)
  }

  const stages = Array.from(stageMap.values())
    .sort(compareStageEntries)
    .map((item) => ({
      ...item,
      label: buildStageLabel(item.stage, item.stepNo),
    }))

  if (stages.length && !stages.some((item) => item.stage === 'stage1_segmentation')) {
    stages.unshift(buildSyntheticStage1())
  }

  return { stages }
}

function ensureStageEntry(stageMap, stage, stepNo) {
  const normalizedStage = String(stage || '').trim()
  const normalizedStepNo =
    stepNo === null || stepNo === undefined || stepNo === ''
      ? null
      : (Number.isFinite(Number(stepNo)) ? Number(stepNo) : null)
  const key = `${normalizedStage}::${normalizedStepNo ?? ''}`

  if (!stageMap.has(key)) {
    stageMap.set(key, {
      key,
      stage: normalizedStage,
      stepNo: normalizedStepNo,
      promptText: '',
      responseText: '',
      tokenUsage: null,
      note: '',
      isSynthetic: false,
      media: {
        images: [],
        videos: [],
      },
      payloadPreview: null,
      rawModelResult: null,
    })
  }

  return stageMap.get(key)
}

function compareStageEntries(left, right) {
  const leftOrder = STAGE_ORDER[left.stage] || 99
  const rightOrder = STAGE_ORDER[right.stage] || 99
  if (leftOrder !== rightOrder) return leftOrder - rightOrder

  const leftStepNo = left.stepNo ?? Number.MAX_SAFE_INTEGER
  const rightStepNo = right.stepNo ?? Number.MAX_SAFE_INTEGER
  if (leftStepNo !== rightStepNo) return leftStepNo - rightStepNo

  return String(left.stage).localeCompare(String(right.stage))
}

function buildStageLabel(stage, stepNo) {
  if (stage === 'stage2_step_eval' && Number.isFinite(Number(stepNo)) && Number(stepNo) > 0) {
    return `阶段2：步骤 ${Number(stepNo)} 评测`
  }
  if (stage === 'stage2_step_eval') {
    return '阶段2：批量步骤评测'
  }
  return STAGE_LABELS[stage] || stage || '评测阶段'
}

function buildSyntheticStage1() {
  return {
    key: 'stage1_segmentation::synthetic',
    stage: 'stage1_segmentation',
    stepNo: null,
    label: buildStageLabel('stage1_segmentation'),
    promptText: '',
    responseText: '',
    tokenUsage: null,
    note: '阶段1原始过程未保存在该记录中，系统可能在时序定位失败后已回退为兜底分段继续评测。',
    isSynthetic: true,
    media: {
      images: [],
      videos: [],
    },
    payloadPreview: null,
    rawModelResult: null,
  }
}

function buildPromptText(payload) {
  const messages = Array.isArray(payload?.messages) ? payload.messages : []
  const parts = []

  for (const message of messages) {
    const role = message?.role === 'system' ? '系统提示词' : message?.role === 'user' ? '用户输入' : '消息'
    const contentText = extractContentText(message?.content)
    if (!contentText) continue
    parts.push(`${role}：\n${contentText}`)
  }

  return parts.join('\n\n').trim()
}

function extractContentText(content) {
  if (typeof content === 'string') {
    return content.trim()
  }

  if (!Array.isArray(content)) {
    return ''
  }

  const textParts = []
  for (const item of content) {
    if (!item || typeof item !== 'object') continue
    if (item.type === 'text' && typeof item.text === 'string' && item.text.trim()) {
      textParts.push(item.text.trim())
    }
  }
  return textParts.join('\n').trim()
}

function extractPayloadMedia(stageItem) {
  const previewImages = Array.isArray(stageItem?.mediaPreview?.images) ? stageItem.mediaPreview.images : []
  const previewVideos = Array.isArray(stageItem?.mediaPreview?.videos) ? stageItem.mediaPreview.videos : []

  if (previewImages.length || previewVideos.length) {
    return {
      images: previewImages.map((item) => ({
        url: item?.url || '',
        kind: item?.type || getMediaKindFromUrl(item?.url || '', 'image'),
      })),
      videos: previewVideos.map((item) => ({
        url: item?.url || '',
        kind: item?.type || getMediaKindFromUrl(item?.url || '', 'video'),
        label: item?.label || '',
      })),
    }
  }

  const payload = stageItem?.payload
  const messages = Array.isArray(payload?.messages) ? payload.messages : []
  const images = []
  const videos = []

  for (const message of messages) {
    const content = Array.isArray(message?.content) ? message.content : []
    for (const item of content) {
      if (!item || typeof item !== 'object') continue

      if (item.type === 'image_url') {
        const url = item?.image_url?.url || ''
        if (url) {
          images.push({
            url,
            kind: getMediaKindFromUrl(url, 'image'),
          })
        }
      }

      if (item.type === 'video_url') {
        const url = item?.video_url?.url || ''
        if (url) {
          videos.push({
            url,
            kind: getMediaKindFromUrl(url, 'video'),
            label: '',
          })
        }
      }
    }
  }

  return { images, videos }
}

function getMediaKindFromUrl(url, fallback) {
  if (typeof url !== 'string') return fallback
  if (url.startsWith('data:image/')) return 'image'
  if (url.startsWith('data:video/')) return 'video'
  return fallback
}

function extractResponseText(result) {
  const choices = Array.isArray(result?.choices) ? result.choices : []
  const content = choices[0]?.message?.content

  if (typeof content === 'string') {
    return content.trim()
  }

  if (!Array.isArray(content)) {
    return ''
  }

  return content
    .filter((item) => item?.type === 'text' && typeof item?.text === 'string' && item.text.trim())
    .map((item) => item.text.trim())
    .join('\n')
    .trim()
}

function extractTokenUsage(usage) {
  if (!usage || typeof usage !== 'object') return null

  const inputTokens = pickNumber(usage, ['prompt_tokens', 'input_tokens', 'promptTokens', 'inputTokens'])
  const outputTokens = pickNumber(usage, ['completion_tokens', 'output_tokens', 'completionTokens', 'outputTokens'])
  const totalTokens = pickNumber(usage, ['total_tokens', 'totalTokens'])

  if (inputTokens == null && outputTokens == null && totalTokens == null) {
    return null
  }

  return {
    inputTokens,
    outputTokens,
    totalTokens: totalTokens ?? (inputTokens || 0) + (outputTokens || 0),
  }
}

function pickNumber(source, keys) {
  for (const key of keys) {
    const value = source?.[key]
    if (value == null || value === '') continue
    const number = Number(value)
    if (Number.isFinite(number)) {
      return number
    }
  }
  return null
}
