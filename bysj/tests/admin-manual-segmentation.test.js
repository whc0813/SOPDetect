const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const adminVuePath = path.resolve(__dirname, '../src/views/Admin.vue')

function readAdminVue() {
  return fs.readFileSync(adminVuePath, 'utf8')
}

test('admin manual segmentation uses visual frame calibration controls', () => {
  const source = readAdminVue()

  assert.match(source, /frame-calibration-panel/)
  assert.match(source, /<video/)
  assert.match(source, /当前播放/)
  assert.match(source, /设为开始点/)
  assert.match(source, /设为结束点/)
  assert.match(source, /添加为关键帧/)
  assert.match(source, /保存校准并重建关键帧/)
})

test('admin manual segmentation avoids duplicate range sliders around the video player', () => {
  const source = readAdminVue()

  assert.doesNotMatch(source, /type="range"/)
  assert.doesNotMatch(source, /步骤开始 \{\{ formatSeconds\(step\.segmentStartSec\) \}\}/)
  assert.doesNotMatch(source, /步骤结束 \{\{ formatSeconds\(step\.segmentEndSec\) \}\}/)
})

test('admin manual segmentation keeps detail dialog state after rebuild', () => {
  const source = readAdminVue()

  assert.match(source, /applyDebugSopState\(result\.data, \{ reloadVideoUrls: false \}\)/)
  assert.doesNotMatch(source, /await refreshDebugSopState\(result\.data\)/)
})

test('admin manual segmentation loads protected demo videos as blob urls', () => {
  const source = readAdminVue()

  assert.match(source, /fetchAuthorizedMediaBlobUrl/)
  assert.match(source, /demoVideoBlobUrl/)
  assert.match(source, /revokeStepDemoVideoUrls/)
})

test('admin manual segmentation no longer relies on raw timestamp text input', () => {
  const source = readAdminVue()

  assert.doesNotMatch(source, /输入时间点，例如/)
  assert.doesNotMatch(source, /v-model="step\.manualTimestampInput"/)
})

test('admin reference frame thumbnails can be opened in image preview', () => {
  const source = readAdminVue()

  assert.match(source, /<el-image/)
  assert.match(source, /:preview-src-list="step\.referenceFrames \|\| \[\]"/)
  assert.match(source, /:initial-index="index"/)
  assert.match(source, /preview-teleported/)
})

test('admin manual frame selection starts empty instead of resubmitting existing keyframes', () => {
  const source = readAdminVue()

  assert.match(source, /manualSelectedTimestamps:\s*\[\]/)
  assert.doesNotMatch(source, /manualSelectedTimestamps:\s*keyframeTimestamps/)
})

test('admin manual rebuild submits only explicitly selected frames', () => {
  const source = readAdminVue()

  assert.match(source, /return selected\.length \? selected : \[\]/)
  assert.doesNotMatch(source, /return normalizeTimestampList\(\[start, \.\.\.selected, end\]\)/)
})
