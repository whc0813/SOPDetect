const test = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const adminVuePath = path.resolve(__dirname, '../src/views/Admin.vue')

function readAdminVue() {
  return fs.readFileSync(adminVuePath, 'utf8')
}

test('admin no longer exposes numeric penalty configuration', () => {
  const source = readAdminVue()

  assert.doesNotMatch(source, /PENALTY_ISSUE_TYPES/)
  assert.doesNotMatch(source, /DEFAULT_PENALTY_VALUES/)
  assert.doesNotMatch(source, /自定义罚分参数/)
  assert.doesNotMatch(source, /penaltyConfig/)
})

test('admin SOP stats use binary status metrics only', () => {
  const source = readAdminVue()

  assert.doesNotMatch(source, /averageScore/)
  assert.doesNotMatch(source, /平均得分/)
  assert.match(source, /pendingReviewCount/)
})

test('admin history table exposes delete record action', () => {
  const source = readAdminVue()

  assert.match(source, /deleteHistory/)
  assert.match(source, /deleteHistoryRecord/)
  assert.match(source, />删除记录</)
})
