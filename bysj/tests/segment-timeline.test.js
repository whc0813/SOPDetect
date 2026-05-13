const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const sourcePath = path.join(__dirname, '..', 'src', 'components', 'SegmentTimeline.vue')

function readSource() {
  return fs.readFileSync(sourcePath, 'utf-8')
}

test('SegmentTimeline exposes segment dragging and seek events', () => {
  const source = readSource()

  assert.match(source, /defineEmits\(\['update:segments', 'seek'\]\)/)
  assert.match(source, /pointerdown/)
  assert.match(source, /pointermove/)
  assert.match(source, /onTrackClick/)
})

test('SegmentTimeline clamps boundaries to duration and adjacent segments', () => {
  const source = readSource()

  assert.match(source, /Math\.max\(0, Math\.min\(1/)
  assert.match(source, /prev \? prev\.endSec : 0/)
  assert.match(source, /next \? next\.startSec : props\.duration/)
  assert.match(source, /MIN_LEN/)
})

test('SegmentTimeline renders gaps and readonly mode', () => {
  const source = readSource()

  assert.match(source, /gapStyle/)
  assert.match(source, /readonly/)
  assert.match(source, /repeating-linear-gradient/)
})
