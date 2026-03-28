<template>
  <GlassCard class="grouped-list" :padding="false">
    <!-- Table mode (when columns are provided) -->
    <table v-if="columns.length" class="grouped-list-table">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="{ textAlign: col.align || 'left', width: col.width }"
          >{{ col.label }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, idx) in data"
          :key="row.id || idx"
          :style="{ animationDelay: (idx * 30) + 'ms' }"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :style="{ textAlign: col.align || 'left' }"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]" :index="idx">
              {{ row[col.key] }}
            </slot>
          </td>
        </tr>
        <tr v-if="data.length === 0" class="empty-placeholder">
          <td :colspan="columns.length">
            <slot name="empty">
              <div class="grouped-list-empty">{{ emptyText }}</div>
            </slot>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- List mode (custom row template via #item slot) -->
    <div v-else class="grouped-list-items">
      <div
        v-for="(row, idx) in data"
        :key="row.id || idx"
        class="grouped-list-row"
        :style="{ animationDelay: (idx * 30) + 'ms' }"
      >
        <slot name="item" :row="row" :index="idx" />
      </div>
      <div v-if="data.length === 0">
        <slot name="empty">
          <div class="grouped-list-empty">{{ emptyText }}</div>
        </slot>
      </div>
    </div>
  </GlassCard>
</template>

<script setup>
import GlassCard from './GlassCard.vue'

defineProps({
  columns: { type: Array, default: () => [] },
  data: { type: Array, default: () => [] },
  emptyText: { type: String, default: '暂无数据' }
})
</script>

<style scoped>
.grouped-list-table {
  width: 100%;
  border-collapse: collapse;
}

.grouped-list-table thead th {
  text-align: left;
  padding: 13px var(--sp-5);
  font-size: var(--fs-caption1);
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: transparent;
  white-space: nowrap;
  border-bottom: 1px solid var(--separator);
}

.grouped-list-table tbody tr {
  position: relative;
  animation: itemEnter 0.4s var(--ease-decelerate) both;
}

.grouped-list-table tbody tr:not(:last-child)::after {
  content: '';
  position: absolute;
  left: var(--sp-5);
  right: var(--sp-5);
  bottom: 0;
  height: 0.5px;
  background: var(--separator);
}

.grouped-list-table tbody td {
  padding: 14px var(--sp-5);
  font-size: var(--fs-subheadline);
  color: var(--text-main);
  vertical-align: middle;
  transition: background var(--duration-micro);
  border-bottom: none;
}

.grouped-list-table tbody tr:hover td {
  background: var(--fill-quaternary);
}

.grouped-list-table .empty-placeholder td {
  border-bottom: none;
}

.grouped-list-table .empty-placeholder:hover td {
  background: transparent;
}

.grouped-list-table .empty-placeholder::after {
  display: none;
}

.grouped-list-items .grouped-list-row {
  position: relative;
  animation: itemEnter 0.4s var(--ease-decelerate) both;
}

.grouped-list-items .grouped-list-row:not(:last-child)::after {
  content: '';
  position: absolute;
  left: var(--sp-5);
  right: var(--sp-5);
  bottom: 0;
  height: 0.5px;
  background: var(--separator);
}

.grouped-list-empty {
  text-align: center;
  color: var(--text-faint);
  padding: var(--sp-12) var(--sp-4);
  font-size: 14px;
}

@keyframes itemEnter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .grouped-list-table tbody tr,
  .grouped-list-items .grouped-list-row {
    animation: none;
  }
}
</style>
