<template>
  <span :class="['status-badge', `status-badge-${type}`]">
    <slot />
  </span>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'default',
    validator: (v) => ['success', 'danger', 'warning', 'info', 'default'].includes(v)
  }
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: var(--fs-caption1);
  font-weight: 600;
  white-space: nowrap;
  line-height: 1.4;
}

.status-badge-success {
  background: var(--success-fill);
  color: var(--badge-success-color);
}

.status-badge-danger {
  background: var(--danger-fill);
  color: var(--badge-danger-color);
}

.status-badge-warning {
  background: var(--warning-fill);
  color: var(--badge-warning-color);
}

.status-badge-info {
  background: var(--info-fill);
  color: var(--badge-info-color);
}

.status-badge-default {
  background: var(--fill-tertiary);
  color: var(--text-soft);
}

@media (prefers-color-scheme: dark) {
  .status-badge-success { color: #4dd268; }
  .status-badge-danger { color: #ff6961; }
  .status-badge-warning { color: #ffd426; }
  .status-badge-info { color: #5ac8fa; }
}
</style>
