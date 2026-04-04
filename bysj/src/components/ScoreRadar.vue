<template>
  <div class="score-radar" v-if="hasData">
    <div class="radar-label">得分分布雷达图</div>
    <svg
      :width="size"
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      class="radar-svg"
    >
      <!-- Background rings -->
      <polygon
        v-for="ring in rings"
        :key="ring.level"
        :points="ringPoints(ring.radius)"
        fill="none"
        :stroke="ringStroke"
        stroke-width="0.5"
      />

      <!-- Axes -->
      <line
        v-for="(axis, i) in axes"
        :key="i"
        :x1="cx"
        :y1="cy"
        :x2="axis.outerX"
        :y2="axis.outerY"
        :stroke="ringStroke"
        stroke-width="0.5"
      />

      <!-- Data area -->
      <polygon
        :points="dataPoints"
        :fill="fillColor"
        :stroke="strokeColor"
        stroke-width="1.5"
      />

      <!-- Data dots -->
      <circle
        v-for="(pt, i) in dataCoords"
        :key="i"
        :cx="pt.x"
        :cy="pt.y"
        r="3"
        :fill="strokeColor"
      />

      <!-- Labels -->
      <text
        v-for="(axis, i) in axes"
        :key="`lbl-${i}`"
        :x="axis.labelX"
        :y="axis.labelY"
        text-anchor="middle"
        dominant-baseline="middle"
        :font-size="labelFontSize"
        fill="currentColor"
        class="radar-axis-label"
      >
        步骤{{ axis.stepNo }}
      </text>

      <!-- Score values near dots -->
      <text
        v-for="(pt, i) in dataCoords"
        :key="`val-${i}`"
        :x="pt.x"
        :y="pt.y - 6"
        text-anchor="middle"
        :font-size="valueFontSize"
        :fill="scoreColor(sortedSteps[i].score)"
        class="radar-value"
      >
        {{ Math.round(sortedSteps[i].score) }}
      </text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stepResults: {
    type: Array,
    default: () => [],
  },
  size: {
    type: Number,
    default: 260,
  },
})

const cx = computed(() => props.size / 2)
const cy = computed(() => props.size / 2)
const maxRadius = computed(() => props.size * 0.36)
const labelRadius = computed(() => maxRadius.value + 20)

const fillColor = 'rgba(99,102,241,0.25)'
const strokeColor = '#818cf8'
const ringStroke = 'rgba(255,255,255,0.1)'

const labelFontSize = computed(() => Math.max(9, props.size * 0.042))
const valueFontSize = computed(() => Math.max(8, props.size * 0.038))

const sortedSteps = computed(() =>
  [...props.stepResults].sort((a, b) => a.stepNo - b.stepNo)
)

const hasData = computed(() => sortedSteps.value.length >= 3)

const n = computed(() => sortedSteps.value.length)

function angleForIndex(i) {
  return (2 * Math.PI * i) / n.value - Math.PI / 2
}

const axes = computed(() =>
  sortedSteps.value.map((step, i) => {
    const angle = angleForIndex(i)
    const r = maxRadius.value
    const lr = labelRadius.value
    return {
      stepNo: step.stepNo,
      outerX: cx.value + r * Math.cos(angle),
      outerY: cy.value + r * Math.sin(angle),
      labelX: cx.value + lr * Math.cos(angle),
      labelY: cy.value + lr * Math.sin(angle),
    }
  })
)

const rings = computed(() =>
  [0.25, 0.5, 0.75, 1.0].map(level => ({ level, radius: maxRadius.value * level }))
)

function ringPoints(r) {
  return sortedSteps.value
    .map((_, i) => {
      const angle = angleForIndex(i)
      return `${cx.value + r * Math.cos(angle)},${cy.value + r * Math.sin(angle)}`
    })
    .join(' ')
}

const dataCoords = computed(() =>
  sortedSteps.value.map((step, i) => {
    const angle = angleForIndex(i)
    const r = (Math.max(0, Math.min(100, step.score)) / 100) * maxRadius.value
    return {
      x: cx.value + r * Math.cos(angle),
      y: cy.value + r * Math.sin(angle),
    }
  })
)

const dataPoints = computed(() =>
  dataCoords.value.map(pt => `${pt.x},${pt.y}`).join(' ')
)

function scoreColor(score) {
  if (score >= 80) return '#4ade80'
  if (score >= 60) return '#facc15'
  return '#f87171'
}
</script>

<style scoped>
.score-radar {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.radar-label {
  font-size: 12px;
  color: var(--text-muted, #8b8d97);
  margin-bottom: 6px;
  font-weight: 500;
  align-self: flex-start;
}

.radar-svg {
  overflow: visible;
}

.radar-axis-label {
  opacity: 0.7;
  font-family: inherit;
}

.radar-value {
  font-weight: 600;
  font-family: inherit;
}
</style>
