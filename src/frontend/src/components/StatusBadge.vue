<template>
  <span :class="['status-badge', `status-${status}`]">
    {{ label || getStatusLabel(status) }}
  </span>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const props = defineProps({
  status: {
    type: String,
    required: false,
    default: 'unknown'
  },
  label: {
    type: String,
    default: null
  }
})

const { t } = useI18n()

const getStatusLabel = (status) => {
  if (!status || typeof status !== 'string') {
    return t('status.unknown') || 'Unknown'
  }
  const statusKey = `status.${status.toLowerCase()}`
  const translated = t(statusKey)
  // If translation exists (not the same as key), use it, otherwise use status as-is
  return translated !== statusKey ? translated : status
}
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.875rem;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.status-ready {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
}

.status-processing {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  animation: pulse 2s var(--ease-in-out) infinite;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}

.status-queued {
  background: #fef3c7;
  color: #92400e;
}

.status-completed {
  background: #d1fae5;
  color: #065f46;
}

.status-active {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
  animation: glow-pulse 2s var(--ease-in-out) infinite;
  box-shadow: 0 0 10px rgba(5, 95, 70, 0.3);
}

.status-inactive {
  background: #e5e7eb;
  color: #374151;
}

.status-pending {
  background: #fef3c7;
  color: #92400e;
}

.status-approved {
  background: #d1fae5;
  color: #065f46;
}

.status-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.status-approved {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
}

.status-changes_requested {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
}

.status-in_progress {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  animation: pulse 2s var(--ease-in-out) infinite;
}

.status-available {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
}

.status-not_available {
  background: #fee2e2;
  color: #991b1b;
}

.status-unknown {
  background: #e5e7eb;
  color: #374151;
}
</style>

