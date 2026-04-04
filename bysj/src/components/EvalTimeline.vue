<template>
  <div class="eval-timeline" v-if="stepResults && stepResults.length">
    <div class="timeline-label">执行时间轴</div>
    <div class="timeline-track" ref="trackRef">
      <!-- Background bar -->
      <div class="timeline-bg"></div>

      <!-- Step segments -->
      <template v-for="step in visibleSteps" :key="step.stepNo">
        <div
          class="timeline-segment"
          :class="segmentClass(step)"
          :style="segmentStyle(step)"
          @mouseenter="hoveredStep = step.stepNo"
          @mouseleave="hoveredStep = null"
        ></div>
      </template>

      <!-- Tooltip -->
      <Transition name="fade">
        <div
          v-if="hoveredStep !== null"
          class="timeline-tooltip"
          :style="tooltipStyle"
        >
          <template v-for="step in visibleSteps" :key="step.stepNo">
            <template v-if="step.stepNo === hoveredStep">
              <div class="tooltip-title">步骤 {{ step.stepNo }}: {{ step.description }}</div>
              <div class="tooltip-row">
                <span>得分：</span><span :class="scoreClass(step.score)">{{ Math.round(step.score) }}</span>
              </div>
              <div class="tooltip-row" v-if="step.detectedStartSec != null">
                <span>区间：</span><span>{{ step.detectedStartSec.toFixed(1) }}s – {{ (step.detectedEndSec ?? '?') }}s</span>
              </div>
              <div class="tooltip-row">
                <span>问题：</span><span>{{ step.issueType || '正常' }}</span>
              </div>
            </template>
          </template>
        </div>
      </Transition>
    </div>

    <!-- Step labels row -->
    <div class="timeline-labels-row">
      <div
        v-for="step in visibleSteps"
        :key="step.stepNo"
        class="step-label"
        :class="segmentClass(step)"
        :style="labelStyle(step)"
      >
        {{ step.stepNo }}
      </div>
    </div>

    <!-- Legend -->
    <div class="timeline-legend">
      <span class="legend-item passed">通过</span>
      <span class="legend-item failed">未通过/缺失</span>
      <span class="legend-item order-issue">顺序问题</span>
      <span class="legend-item insufficient">证据不足</span>
      <span class="legend-item undetected">未检测到</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  stepResults: {
    type: Array,
    default: () => [],
  },
  videoDurationSec: {
    type: Number,
    default: 0,
  },
})

const hoveredStep = ref(null)

const totalDuration = computed(() => {
  if (props.videoDurationSec > 0) return props.videoDurationSec
  // Infer from step results
  let maxEnd = 0
  for (const step of props.stepResults) {
    if (step.detectedEndSec != null && step.detectedEndSec > maxEnd) {
      maxEnd = step.detectedEndSec
    }
  }
  return maxEnd > 0 ? maxEnd * 1.05 : 60
})

const visibleSteps = computed(() => props.stepResults.filter(s => s.includedInScore !== false || s.detectedStartSec != null))

function segmentClass(step) {
  if (step.issueType === '缺失' || (!step.passed && step.issueType !== '证据不足')) {
    if (step.orderIssue || step.prerequisiteViolated) return 'order-issue'
    return 'failed'
  }
  if (step.issueType === '证据不足') return 'insufficient'
  if (step.detectedStartSec == null) return 'undetected'
  if (step.passed) return 'passed'
  return 'failed'
}

function scoreClass(score) {
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-ok'
  return 'score-bad'
}

function segmentStyle(step) {
  const dur = totalDuration.value
  if (!dur) return { display: 'none' }
  if (step.detectedStartSec == null) return { display: 'none' }
  const left = (step.detectedStartSec / dur) * 100
  const width = Math.max(1, ((step.detectedEndSec ?? step.detectedStartSec + 1) - step.detectedStartSec) / dur * 100)
  return {
    left: `${left}%`,
    width: `${width}%`,
  }
}

function labelStyle(step) {
  const dur = totalDuration.value
  if (!dur || step.detectedStartSec == null) return { display: 'none' }
  const mid = ((step.detectedStartSec + (step.detectedEndSec ?? step.detectedStartSec + 1)) / 2 / dur) * 100
  return {
    left: `${mid}%`,
    transform: 'translateX(-50%)',
    position: 'absolute',
  }
}

const tooltipStyle = computed(() => ({
  left: '50%',
  top: '-70px',
  transform: 'translateX(-50%)',
}))
</script>

<style scoped>
.eval-timeline {
  margin: 12px 0 4px;
  user-select: none;
}

.timeline-label {
  font-size: 12px;
  color: var(--text-muted, #8b8d97);
  margin-bottom: 6px;
  font-weight: 500;
}

.timeline-track {
  position: relative;
  height: 20px;
  margin-bottom: 4px;
}

.timeline-bg {
  position: absolute;
  inset: 4px 0;
  background: var(--border-color, rgba(255,255,255,0.08));
  border-radius: 4px;
}

.timeline-segment {
  position: absolute;
  top: 2px;
  height: 16px;
  border-radius: 3px;
  opacity: 0.85;
  transition: opacity 0.15s, transform 0.1s;
  cursor: pointer;
}

.timeline-segment:hover {
  opacity: 1;
  transform: scaleY(1.15);
}

.timeline-segment.passed   { background: #4ade80; }
.timeline-segment.failed   { background: #f87171; }
.timeline-segment.order-issue { background: #fb923c; }
.timeline-segment.insufficient { background: #94a3b8; }
.timeline-segment.undetected   { background: #64748b; }

.timeline-labels-row {
  position: relative;
  height: 16px;
}

.step-label {
  position: absolute;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 3px;
  border-radius: 3px;
  color: #fff;
  line-height: 14px;
}

.step-label.passed     { background: #16a34a; }
.step-label.failed     { background: #dc2626; }
.step-label.order-issue { background: #ea580c; }
.step-label.insufficient { background: #64748b; }
.step-label.undetected   { display: none !important; }

.timeline-tooltip {
  position: absolute;
  background: var(--card-bg, #1e2235);
  border: 1px solid var(--border-color, rgba(255,255,255,0.12));
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  z-index: 100;
  white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  pointer-events: none;
}

.tooltip-title {
  font-weight: 600;
  margin-bottom: 4px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tooltip-row {
  display: flex;
  gap: 4px;
  color: var(--text-muted, #8b8d97);
  margin-top: 2px;
}

.score-good { color: #4ade80; }
.score-ok   { color: #facc15; }
.score-bad  { color: #f87171; }

.timeline-legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.legend-item {
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted, #8b8d97);
}

.legend-item::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item.passed::before     { background: #4ade80; }
.legend-item.failed::before     { background: #f87171; }
.legend-item.order-issue::before { background: #fb923c; }
.legend-item.insufficient::before { background: #94a3b8; }
.legend-item.undetected::before  { background: #64748b; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
