<template>
  <div v-if="totalPagesComputed > 1" class="pagination">
    <button
      @click="goToPage(currentPage - 1)"
      :disabled="currentPage === 1"
      class="pagination-btn"
    >
      <ChevronLeft :size="16" />
    </button>
    <div class="pagination-pages">
      <button
        v-for="p in visiblePages"
        :key="p"
        @click="goToPage(p)"
        :class="['pagination-page', { 'pagination-page-active': p === currentPage }]"
      >
        {{ p }}
      </button>
    </div>
    <button
      @click="goToPage(currentPage + 1)"
      :disabled="currentPage === totalPagesComputed"
      class="pagination-btn"
    >
      <ChevronRight :size="16" />
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  page: {
    type: Number,
    default: null
  },
  'current-page': {
    type: Number,
    default: null
  },
  totalPages: {
    type: Number,
    default: null
  },
  'total-items': {
    type: Number,
    default: null
  },
  'items-per-page': {
    type: Number,
    default: 20
  },
  maxVisible: {
    type: Number,
    default: 5
  }
})

const emit = defineEmits(['update:page', 'change', 'page-change'])

// Computed properties for flexible prop usage
const currentPage = computed(() => {
  return props.page ?? props['current-page'] ?? 1
})

const totalPagesComputed = computed(() => {
  if (props.totalPages !== null) {
    return props.totalPages
  }
  if (props['total-items'] !== null && props['items-per-page']) {
    return Math.ceil(props['total-items'] / props['items-per-page'])
  }
  return 1
})

const visiblePages = computed(() => {
  const pages = []
  const half = Math.floor(props.maxVisible / 2)
  let start = Math.max(1, currentPage.value - half)
  let end = Math.min(totalPagesComputed.value, start + props.maxVisible - 1)
  
  if (end - start < props.maxVisible - 1) {
    start = Math.max(1, end - props.maxVisible + 1)
  }
  
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  
  return pages
})

const goToPage = (newPage) => {
  if (newPage >= 1 && newPage <= totalPagesComputed.value && newPage !== currentPage.value) {
    emit('update:page', newPage)
    emit('change', newPage)
    emit('page-change', newPage)
  }
}
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 2rem;
}

.pagination-btn {
  padding: 0.5rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-light);
  border-color: var(--primary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  gap: 0.25rem;
}

.pagination-page {
  min-width: 2.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  background: white;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-page:hover {
  background: var(--bg-light);
  border-color: var(--primary);
}

.pagination-page-active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}
</style>

