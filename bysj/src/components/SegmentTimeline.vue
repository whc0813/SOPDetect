<template>
  <div :class="['segment-timeline', { readonly }]">
    <div ref="trackRef" class="track" @click="onTrackClick">
      <div
        v-for="gap in gaps"
        :key="gap.key"
        class="gap"
        :style="gapStyle(gap)"
      >
        <span v-if="(gap.endSec - gap.startSec) >= 1.5" class="gap-label">间隙 {{ formatTime(gap.endSec - gap.startSec) }}</span>
      </div>
      <div
        v-for="(segment, index) in sortedSegments"
        :key="segment.stepNo"
        :class="['segment', `is-${segment.status || 'pending'}`]"
        :style="segmentStyle(segment, index)"
        @click.stop="$emit('seek', segment.startSec)"
      >
        <button
          v-if="!readonly"
          class="handle handle-start"
          type="button"
          aria-label="拖动调整起点"
          @click.stop
          @pointerdown.stop="startDrag(index, 'start', $event)"
        />
        <div class="segment-body">
          <div class="segment-title">
            <span class="segment-no">#{{ segment.stepNo }}</span>
            <span class="segment-desc">{{ segment.description || '步骤 ' + segment.stepNo }}</span>
          </div>
          <div class="segment-meta">
            <span class="segment-range">{{ formatTime(segment.startSec) }} – {{ formatTime(segment.endSec) }}</span>
            <span class="segment-duration">{{ formatTime(segment.endSec - segment.startSec) }}</span>
          </div>
        </div>
        <button
          v-if="!readonly"
          class="handle handle-end"
          type="button"
          aria-label="拖动调整终点"
          @click.stop
          @pointerdown.stop="startDrag(index, 'end', $event)"
        />
      </div>
      <div
        v-if="duration > 0"
        class="cursor"
        :style="{ left: `${cursorPct}%` }"
        aria-hidden="true"
      />
    </div>
    <div class="ticks">
      <span v-for="tick in ticks" :key="tick.sec" :style="{ left: `${tick.pct}%` }">
        {{ formatTime(tick.sec) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  duration: { type: Number, required: true },
  segments: { type: Array, required: true },
  readonly: { type: Boolean, default: false },
  currentTime: { type: Number, default: 0 }
})
const emit = defineEmits(['update:segments', 'seek'])

const trackRef = ref(null)
const drag = ref(null)
const MIN_LEN = 0.5

const cursorPct = computed(() => {
  if (!props.duration) return 0
  return Math.max(0, Math.min(100, (Number(props.currentTime || 0) / props.duration) * 100))
})

const sortedSegments = computed(() => {
  return [...props.segments].sort((a, b) => Number(a.stepNo) - Number(b.stepNo))
})

const gaps = computed(() => {
  const items = []
  let cursor = 0
  for (const segment of sortedSegments.value) {
    const start = Number(segment.startSec || 0)
    if (start > cursor) {
      items.push({ key: `gap-${cursor}-${start}`, startSec: cursor, endSec: start })
    }
    cursor = Math.max(cursor, Number(segment.endSec || 0))
  }
  if (props.duration > cursor) {
    items.push({ key: `gap-${cursor}-${props.duration}`, startSec: cursor, endSec: props.duration })
  }
  return items
})

const ticks = computed(() => {
  if (!props.duration) return []
  const steps = 6
  return Array.from({ length: steps + 1 }, (_, i) => ({
    sec: (props.duration * i) / steps,
    pct: (i / steps) * 100
  }))
})

function pct(sec) {
  if (!props.duration) return 0
  return Math.max(0, Math.min(100, (Number(sec || 0) / props.duration) * 100))
}

function segmentStyle(segment, index) {
  // 给不同 step 一个稳定的色相，避免相邻块同色
  const hueSeed = (Number(segment.stepNo) || index + 1) * 47
  return {
    left: `${pct(segment.startSec)}%`,
    width: `${Math.max(0, pct(segment.endSec) - pct(segment.startSec))}%`,
    '--seg-hue': hueSeed % 360
  }
}

function gapStyle(gap) {
  return {
    left: `${pct(gap.startSec)}%`,
    width: `${Math.max(0, pct(gap.endSec) - pct(gap.startSec))}%`
  }
}

function formatTime(sec) {
  const value = Math.max(0, Number(sec || 0))
  if (value >= 60) {
    const m = Math.floor(value / 60)
    const s = Math.round(value - m * 60)
    return `${m}:${String(s).padStart(2, '0')}`
  }
  return value < 10 ? `${value.toFixed(1)}s` : `${value.toFixed(0)}s`
}

function startDrag(index, edge, event) {
  if (props.readonly || !trackRef.value) return
  drag.value = { index, edge }
  event.currentTarget.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', endDrag)
}

function onDragMove(event) {
  if (!drag.value || !trackRef.value) return
  const rect = trackRef.value.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
  const newSec = ratio * props.duration
  const { index, edge } = drag.value
  const ordered = sortedSegments.value
  const current = { ...ordered[index] }

  if (edge === 'start') {
    const prev = index > 0 ? ordered[index - 1] : null
    const lower = prev ? prev.endSec : 0
    current.startSec = Math.max(lower, Math.min(current.endSec - MIN_LEN, newSec))
  } else {
    const next = index < ordered.length - 1 ? ordered[index + 1] : null
    const upper = next ? next.startSec : props.duration
    current.endSec = Math.min(upper, Math.max(current.startSec + MIN_LEN, newSec))
  }

  emit('update:segments', props.segments.map((item) => (
    Number(item.stepNo) === Number(current.stepNo) ? current : item
  )))
  // 同步视频画面：让被拖动的边界处的时间在视频里实时预览
  emit('seek', edge === 'start' ? current.startSec : current.endSec)
}

function endDrag() {
  drag.value = null
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', endDrag)
}

function onTrackClick(event) {
  if (!trackRef.value) return
  const rect = trackRef.value.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width))
  emit('seek', ratio * props.duration)
}

onBeforeUnmount(endDrag)
</script>

<style scoped>
.segment-timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.track {
  position: relative;
  height: 76px;
  overflow: hidden;
  border-radius: 12px;
  background: linear-gradient(180deg, #f5f7fb 0%, #eef1f7 100%);
  border: 1px solid #e4e7ed;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
}

.segment {
  position: absolute;
  top: 6px;
  bottom: 6px;
  display: flex;
  align-items: stretch;
  overflow: hidden;
  border-radius: 8px;
  color: #fff;
  background: hsl(var(--seg-hue, 210), 70%, 52%);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
  cursor: pointer;
}

.segment:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);
}

.segment.is-completed { background: linear-gradient(135deg, #34d399, #059669); }
.segment.is-processing {
  background: linear-gradient(135deg, #fbbf24, #d97706);
  animation: segPulse 1.4s ease-in-out infinite;
}
.segment.is-failed { background: linear-gradient(135deg, #f87171, #dc2626); }

@keyframes segPulse {
  0%, 100% { box-shadow: 0 2px 6px rgba(217, 119, 6, 0.5); }
  50% { box-shadow: 0 4px 14px rgba(217, 119, 6, 0.8); }
}

.segment-body {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 6px 10px;
  min-width: 0;
}

.segment-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.segment-no {
  flex: 0 0 auto;
  opacity: 0.85;
  font-size: 11px;
}

.segment-desc {
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.segment-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 2px;
  font-size: 11px;
  opacity: 0.9;
  font-variant-numeric: tabular-nums;
}

.gap {
  position: absolute;
  top: 6px;
  bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(15, 23, 42, 0.45);
  font-size: 11px;
  background-image: repeating-linear-gradient(
    45deg,
    rgba(15, 23, 42, 0.04),
    rgba(15, 23, 42, 0.04) 6px,
    rgba(15, 23, 42, 0.09) 6px,
    rgba(15, 23, 42, 0.09) 12px
  );
  border-radius: 6px;
}

.gap-label {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
}

.handle {
  flex: 0 0 auto;
  width: 10px;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  cursor: ew-resize;
  position: relative;
  transition: background 0.12s ease;
}

.handle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2px;
  height: 18px;
  background: rgba(15, 23, 42, 0.4);
  transform: translate(-50%, -50%);
  border-radius: 1px;
}

.handle:hover {
  background: #fff;
}

.readonly .track { cursor: default; }
.readonly .segment { cursor: default; }
.readonly .segment:hover { transform: none; box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15); }

.ticks {
  position: relative;
  height: 16px;
  color: #94a3b8;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.ticks span {
  position: absolute;
  transform: translateX(-50%);
}

.cursor {
  position: absolute;
  top: -2px;
  bottom: -2px;
  width: 2px;
  background: #ef4444;
  pointer-events: none;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
  z-index: 5;
}

.cursor::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
  transform: translateX(-50%);
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.7);
}
</style>
