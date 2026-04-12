const test = require('node:test')
const assert = require('node:assert/strict')

async function loadUserHistoryModule() {
  return import('../src/utils/user-history.mjs')
}

test('normalizeHistory keeps token usage in detail', async () => {
  const { normalizeHistory } = await loadUserHistoryModule()
  const record = normalizeHistory({
    detail: {
      feedback: '完成',
      tokenUsage: {
        inputTokens: 120,
        outputTokens: 30,
        totalTokens: 150,
      },
    },
  })

  assert.deepEqual(record.detail.tokenUsage, {
    inputTokens: 120,
    outputTokens: 30,
    totalTokens: 150,
  })
})

test('buildEvaluationResultFromHistory exposes token usage for result card', async () => {
  const { buildEvaluationResultFromHistory } = await loadUserHistoryModule()
  const result = buildEvaluationResultFromHistory({
    status: 'passed',
    score: 96,
    detail: {
      feedback: '通过',
      tokenUsage: {
        inputTokens: 200,
        outputTokens: 40,
        totalTokens: 240,
      },
    },
  })

  assert.equal(result.passed, true)
  assert.deepEqual(result.tokenUsage, {
    inputTokens: 200,
    outputTokens: 40,
    totalTokens: 240,
  })
})

test('normalizeHistory builds evaluation process stages from multistage traces', async () => {
  const { normalizeHistory } = await loadUserHistoryModule()
  const record = normalizeHistory({
    detail: {
      payloadPreview: {
        mode: 'multistage',
        stages: [
          {
            stage: 'stage1_segmentation',
            payload: {
              messages: [
                { role: 'system', content: '阶段1系统提示词' },
                {
                  role: 'user',
                  content: [
                    { type: 'text', text: '阶段1用户提示词' },
                    { type: 'video_url', video_url: { url: 'data:video/mp4;base64,stage1' } },
                  ],
                },
              ],
            },
          },
          {
            stage: 'stage2_step_eval',
            stepNo: 2,
            payload: {
              messages: [
                { role: 'system', content: '阶段2系统提示词' },
                {
                  role: 'user',
                  content: [
                    { type: 'text', text: '步骤2用户提示词' },
                    { type: 'image_url', image_url: { url: 'data:image/png;base64,ref' } },
                    { type: 'image_url', image_url: { url: 'data:image/png;base64,focus' } },
                    { type: 'video_url', video_url: { url: 'data:video/mp4;base64,stage2' } },
                  ],
                },
              ],
            },
            mediaPreview: {
              images: [
                { url: 'data:image/png;base64,renderable-preview', type: 'image' },
              ],
              videos: [
                { label: '整段用户视频', type: 'video' },
              ],
            },
          },
          {
            stage: 'stage3_validation',
            payload: {
              messages: [
                { role: 'system', content: '阶段3系统提示词' },
                {
                  role: 'user',
                  content: [
                    { type: 'text', text: '阶段3用户提示词' },
                  ],
                },
              ],
            },
          },
        ],
      },
      rawModelResult: {
        mode: 'multistage',
        stages: [
          {
            stage: 'stage1_segmentation',
            result: {
              usage: {
                prompt_tokens: 100,
                completion_tokens: 20,
                total_tokens: 120,
              },
              choices: [
                { message: { content: '{"segments":[]}' } },
              ],
            },
          },
          {
            stage: 'stage2_step_eval',
            stepNo: 2,
            result: {
              usage: {
                prompt_tokens: 60,
                completion_tokens: 15,
                total_tokens: 75,
              },
              choices: [
                { message: { content: '{"stepNo":2,"passed":true}' } },
              ],
            },
          },
          {
            stage: 'stage3_validation',
            result: {
              usage: {
                prompt_tokens: 40,
                completion_tokens: 10,
                total_tokens: 50,
              },
              choices: [
                { message: { content: '{"passed":true}' } },
              ],
            },
          },
        ],
      },
    },
  })

  assert.equal(record.detail.evaluationProcess.stages.length, 3)
  assert.equal(record.detail.evaluationProcess.stages[0].label, '阶段1：时序定位')
  assert.equal(record.detail.evaluationProcess.stages[1].stepNo, 2)
  assert.equal(record.detail.evaluationProcess.stages[1].media.images.length, 1)
  assert.equal(record.detail.evaluationProcess.stages[1].media.videos.length, 1)
  assert.equal(record.detail.evaluationProcess.stages[1].media.images[0].url, 'data:image/png;base64,renderable-preview')
  assert.equal(record.detail.evaluationProcess.stages[1].promptText.includes('阶段2系统提示词'), true)
  assert.equal(record.detail.evaluationProcess.stages[1].promptText.includes('步骤2用户提示词'), true)
  assert.equal(record.detail.evaluationProcess.stages[1].responseText, '{"stepNo":2,"passed":true}')
  assert.deepEqual(record.detail.evaluationProcess.stages[1].tokenUsage, {
    inputTokens: 60,
    outputTokens: 15,
    totalTokens: 75,
  })
})

test('normalizeHistory returns empty evaluation process for non-multistage traces', async () => {
  const { normalizeHistory } = await loadUserHistoryModule()
  const record = normalizeHistory({
    detail: {
      payloadPreview: { foo: 'bar' },
      rawModelResult: { usage: { total_tokens: 12 } },
    },
  })

  assert.deepEqual(record.detail.evaluationProcess, {
    stages: [],
  })
})

test('formatTokenUsage renders compact token summary', async () => {
  const { formatTokenUsage } = await loadUserHistoryModule()
  assert.equal(
    formatTokenUsage({
      inputTokens: 88,
      outputTokens: 12,
      totalTokens: 100,
    }),
    '输入 88 / 输出 12 / 总计 100',
  )
})

test('formatTokenUsage falls back when token usage is missing', async () => {
  const { formatTokenUsage } = await loadUserHistoryModule()
  assert.equal(formatTokenUsage(null), '暂无')
})
