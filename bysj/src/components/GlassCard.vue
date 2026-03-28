<template>
  <div :class="['glass-card-wrap', { 'no-pad': !padding }]">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  padding: { type: Boolean, default: true }
})
</script>

<style scoped>
.glass-card-wrap {
  background: var(--material-chrome);
  backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  -webkit-backdrop-filter: blur(var(--blur-lg)) saturate(150%);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow:
    0 2px 12px rgba(0, 0, 0, 0.05),
    0 8px 32px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  padding: var(--sp-5);
}

.glass-card-wrap.no-pad {
  padding: 0;
}

@media (prefers-color-scheme: dark) {
  .glass-card-wrap {
    border-color: rgba(84, 84, 88, 0.4);
    box-shadow:
      0 2px 12px rgba(0, 0, 0, 0.2),
      0 8px 32px rgba(0, 0, 0, 0.15);
  }
}
</style>
