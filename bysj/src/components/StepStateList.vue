<template>
  <GroupedList
    :columns="columns"
    :data="rows"
    empty-text="暂无步骤数据"
  >
    <template #cell-status="{ row }">
      <StatusBadge :type="badgeType(row.status)">{{ statusLabel(row.status) }}</StatusBadge>
    </template>
    <template #cell-actions="{ row }">
      <button class="text-btn" @click="$emit('seek', row.startSec || 0)">跳转</button>
      <button
        class="text-btn"
        :disabled="row.startSec == null || row.endSec == null"
        @click="$emit('preview', row)"
      >预览本步</button>
      <button
        v-if="row.status === 'failed'"
        class="text-btn danger"
        @click="$emit('retry', row.stepNo)"
      >重试</button>
    </template>
  </GroupedList>
</template>

<script setup>
import { computed } from 'vue'
import GroupedList from './GroupedList.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  stepStates: { type: Object, required: true },
  segments: { type: Array, required: true },
  stepsMeta: { type: Array, required: true }
})
defineEmits(['seek', 'preview', 'retry'])

const columns = [
  { key: 'stepNo', label: '#', width: '52px' },
  { key: 'range', label: '时间窗', width: '140px' },
  { key: 'description', label: '描述' },
  { key: 'status', label: '状态', width: '110px' },
  { key: 'actions', label: '操作', width: '210px' }
]

const rows = computed(() => props.stepsMeta.map((meta) => {
  const stepNo = Number(meta.stepNo)
  const segment = props.segments.find((item) => Number(item.stepNo) === stepNo) || {}
  const state = props.stepStates[String(stepNo)] || { status: 'pending' }
  const startSec = segment.startSec ?? null
  const endSec = segment.endSec ?? null
  return {
    stepNo,
    description: meta.description || '',
    range: startSec == null || endSec == null
      ? '未确认'
      : `${Number(startSec).toFixed(1)}-${Number(endSec).toFixed(1)}s`,
    startSec,
    endSec,
    status: state.status || 'pending',
    error: state.error || ''
  }
}))

function badgeType(status) {
  return {
    pending: 'default',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }[status] || 'default'
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
