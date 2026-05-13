const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

function read(relPath) {
  return fs.readFileSync(path.join(__dirname, '..', relPath), 'utf-8')
}

test('client exposes preparation job API helpers with wrapped data extraction', () => {
  const source = read('src/api/client.js')

  for (const name of [
    'createSopDraft',
    'listDraftSops',
    'getPreparationJob',
    'confirmSegmentation',
    'retryPreparationStep',
    'retrySegmentation',
    'cancelPreparation'
  ]) {
    assert.match(source, new RegExp(`export async function ${name}`))
  }
  assert.match(source, /return payload\.data/)
})

test('router registers admin preparation route', () => {
  const source = read('src/router/index.js')

  assert.match(source, /\/admin\/sop-preparation\/:jobId/)
  assert.match(source, /SopPreparation/)
})

test('SopPreparation page composes timeline, state list, polling and confirmation APIs', () => {
  const source = read('src/views/SopPreparation.vue')

  assert.match(source, /SegmentTimeline/)
  assert.match(source, /StepStateList/)
  assert.match(source, /getPreparationJob/)
  assert.match(source, /confirmSegmentation/)
  assert.match(source, /setInterval/)
  assert.match(source, /awaiting_confirmation/)
  assert.match(source, /processing_steps/)
})

test('SopPreparation page lets admin return to the admin page', () => {
  const source = read('src/views/SopPreparation.vue')

  assert.match(source, />返回</)
  assert.match(source, /function goBack/)
  assert.match(source, /router\.push\('\/admin'\)/)
})

test('SopPreparation page can set a step boundary from current playback time', () => {
  const source = read('src/views/SopPreparation.vue')

  assert.match(source, /@timeupdate="onTimeUpdate"/)
  assert.match(source, /boundaryIndex/)
  assert.match(source, /currentTime/)
  assert.match(source, /setBoundaryAtCurrentTime/)
  assert.match(source, /设为步骤边界/)
})

test('Admin save flow jumps to preparation page and shows drafts', () => {
  const source = read('src/views/Admin.vue')

  assert.match(source, /createSopDraft/)
  assert.match(source, /listDraftSops/)
  assert.match(source, /draft-section/)
  assert.match(source, /sop-preparation\/\$\{data\.jobId\}/)
})
