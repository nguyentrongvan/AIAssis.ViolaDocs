<template>
  <span :class="['status-badge', `status-${status}`]">
    {{ label || status }}
  </span>
</template>

<script setup>
const props = defineProps({
  status: {
    type: String,
    required: true
  },
  label: {
    type: String,
    default: null
  }
})
</script>

<style scoped>
.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-ready {
  background: #d1fae5;
  color: #065f46;
}

.status-processing {
  background: #dbeafe;
  color: #1e40af;
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
  background: #d1fae5;
  color: #065f46;
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
</style>

