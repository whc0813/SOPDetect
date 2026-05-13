<template>
  <el-table :data="rows" border size="small" class="step-state-list">
    <el-table-column prop="stepNo" label="#" width="60" />
    <el-table-column label="时间窗" width="150">
      <template #default="{ row }">{{ formatRange(row) }}</template>
    </el-table-column>
    <el-table-column prop="description" label="描述" />
    <el-table-column label="状态" width="120">
      <template #default="{ row }">
        <el-tag :type="tagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="220">
      <template #default="{ row }">
        <el-button size="small" link @click="$emit('seek', row.startSec || 0)">跳转</el-button>
        <el-button
          size="small"
          type="primary"
          link
          :disabled="row.startSec == null || row.endSec == null"
          @click="$emit('preview', row)"
        >
          预览本步
        </el-button>
        <el-button
          v-if="row.status === 'failed'"
          size="small"
          type="warning"
          link
          @click="$emit('retry', row.stepNo)"
        >
          重试
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stepStates: { type: Object, required: true },
  segments: { type: Array, required: true },
  stepsMeta: { type: Array, required: true }
})
defineEmits(['seek', 'preview', 'retry'])

const rows = computed(() => props.stepsMeta.map((meta) => {
  const stepNo = Number(meta.stepNo)
  const segment = props.segments.find((item) => Number(item.stepNo) === stepNo) || {}
  const state = props.stepStates[String(stepNo)] || { status: 'pending' }
  return {
    stepNo,
    description: meta.description || '',
    startSec: segment.startSec ?? null,
    endSec: segment.endSec ?? null,
    status: state.status || 'pending',
    error: state.error || ''
  }
}))

function formatRange(row) {
  if (row.startSec == null || row.endSec == null) return '未确认'
  return `${Number(row.startSec).toFixed(1)}-${Number(row.endSec).toFixed(1)}s`
}

function tagType(status) {
  return {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }[status] || 'info'
}

function statusLabel(status) {
  return {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }[status] || status
}
</script>

<style scoped>
.step-state-list {
  width: 100%;
}
</style>
