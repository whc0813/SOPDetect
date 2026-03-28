<template>
  <div class="section-header">
    <div class="section-header-text">
      <h3 class="section-header-title">{{ title }}</h3>
      <p v-if="subtitle" class="section-header-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="section-header-trailing">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})
</script>

<style scoped>
.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-4);
}

.section-header-text {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.section-header-title {
  font-size: var(--fs-title3);
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.02em;
  margin: 0;
}

.section-header-subtitle {
  font-size: 14px;
  color: var(--text-soft);
  margin: 0;
}
</style>
