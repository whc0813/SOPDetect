# Evaluation Process Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户端历史记录详情中新增“评测过程”展开区，展示多阶段评测时发送给 AI 的图片/视频、提示词、AI 回复内容以及每一步 token 用量。

**Architecture:** 保持后端接口和存储结构不变，直接复用历史记录中已有的 `payloadPreview` 与 `rawModelResult` 多阶段 trace。先在 `user-history.mjs` 中补一个纯函数，将 trace 解析为前端可渲染的阶段/步骤结构；再在 `User.vue` 的现有详情弹窗中增加折叠式展示区。通过 `node:test` 先覆盖解析逻辑，再实现界面。

**Tech Stack:** Vue 3、Element Plus、Node `node:test`

---

### Task 1: 为评测过程解析补充测试并实现数据整形

**Files:**
- Modify: `D:\毕业设计\bysj\tests\user-history.test.js`
- Modify: `D:\毕业设计\bysj\src\utils\user-history.mjs`

- [ ] **Step 1: 写失败测试**

```js
test('normalizeHistory builds evaluation process stages from multistage traces', async () => {
  const { normalizeHistory } = await loadUserHistoryModule()
  const record = normalizeHistory({
    detail: {
      payloadPreview: {
        mode: 'multistage',
        stages: [
          { stage: 'stage1_segmentation', payload: { messages: [{ role: 'system', content: '阶段1系统提示词' }, { role: 'user', content: [{ type: 'text', text: '阶段1用户提示词' }, { type: 'video_url', video_url: { url: 'data:video/mp4;base64,abc' } }] }] } },
          { stage: 'stage2_step_eval', stepNo: 2, payload: { messages: [{ role: 'system', content: '阶段2系统提示词' }, { role: 'user', content: [{ type: 'text', text: '步骤2用户提示词' }, { type: 'image_url', image_url: { url: 'data:image/png;base64,ref' } }, { type: 'video_url', video_url: { url: 'data:video/mp4;base64,xyz' } }] }] } },
          { stage: 'stage3_validation', payload: { messages: [{ role: 'system', content: '阶段3系统提示词' }, { role: 'user', content: [{ type: 'text', text: '阶段3用户提示词' }] }] } },
        ],
      },
      rawModelResult: {
        mode: 'multistage',
        stages: [
          { stage: 'stage1_segmentation', result: { usage: { prompt_tokens: 100, completion_tokens: 20, total_tokens: 120 }, choices: [{ message: { content: '{\"segments\":[]}' } }] } },
          { stage: 'stage2_step_eval', stepNo: 2, result: { usage: { prompt_tokens: 60, completion_tokens: 15, total_tokens: 75 }, choices: [{ message: { content: '{\"stepNo\":2}' } }] } },
          { stage: 'stage3_validation', result: { usage: { prompt_tokens: 40, completion_tokens: 10, total_tokens: 50 }, choices: [{ message: { content: '{\"passed\":true}' } }] } },
        ],
      },
    },
  })

  assert.equal(record.detail.evaluationProcess.stages.length, 3)
  assert.equal(record.detail.evaluationProcess.stages[1].stepNo, 2)
  assert.equal(record.detail.evaluationProcess.stages[1].media.images.length, 1)
  assert.equal(record.detail.evaluationProcess.stages[1].media.videos.length, 1)
  assert.deepEqual(record.detail.evaluationProcess.stages[1].tokenUsage, {
    inputTokens: 60,
    outputTokens: 15,
    totalTokens: 75,
  })
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npm test -- user-history.test.js`
Expected: FAIL because `evaluationProcess` is missing from normalized history detail.

- [ ] **Step 3: 写最小实现**

```js
export function normalizeHistory(record = {}) {
  return {
    ...record,
    detail: {
      ...existingDetail,
      evaluationProcess: buildEvaluationProcess(record.detail),
    },
  }
}

function buildEvaluationProcess(detail = {}) {
  // 将 payloadPreview/rawModelResult 中同阶段、同 stepNo 的条目合并，
  // 提取系统提示词、用户提示词、图片、视频、AI 回复和 tokenUsage。
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `npm test -- user-history.test.js`
Expected: PASS

### Task 2: 在历史记录详情弹窗中接入评测过程展开区

**Files:**
- Modify: `D:\毕业设计\bysj\src\views\User.vue`

- [ ] **Step 1: 接入数据结构**

```js
const processStageCollapse = ref(['stage1', 'stage2', 'stage3'])
```

- [ ] **Step 2: 在详情弹窗中新增“评测过程”展示区**

```vue
<div class="detail-box" v-if="selectedHistoryRecord.detail.evaluationProcess?.stages?.length">
  <div class="detail-title">评测过程</div>
  <el-collapse>
    <!-- 阶段1 / 阶段2 / 阶段3 -->
  </el-collapse>
</div>
```

- [ ] **Step 3: 展示图片、视频标记、提示词、AI 回复、token**

```vue
<div class="process-media-grid">
  <img v-for="image in stage.media.images" :key="image.url" :src="image.url" class="process-image" />
</div>
<pre class="process-json">{{ stage.responseText }}</pre>
```

- [ ] **Step 4: 补齐样式并保持旧记录兼容**

Run: `npm test -- user-history.test.js`
Expected: PASS
